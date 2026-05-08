from __future__ import annotations

import copy
from typing import Any

from evosql_platform.clients.base import LLMClient
from evosql_platform.engine.refiners import (
    ECARefiner,
    ECAResult,
    SCRRefiner,
    SCRResult,
    extract_references,
    normalize_column_refs,
    snapshot_context,
    stable_result_signature,
    summarize_rows,
)
from evosql_platform.engine.scheduler import AdaptiveScheduler, RuntimeSignals
from evosql_platform.executor.safety import SQLSafetyInterceptor
from evosql_platform.executor.sandbox import SQLiteSandboxExecutor
from evosql_platform.models import CandidateSQL, ContextState, EngineResult, EngineTraceStep


def serialize_candidate(candidate: CandidateSQL, iteration: int, rank: int) -> dict[str, object]:
    status = "generated"
    if candidate.error and candidate.execution_signature:
        status = "execution_warning"
    elif candidate.error:
        status = "blocked" if "Only read-only SELECT" in candidate.error or "not allowed" in candidate.error else "failed"
    elif candidate.execution_signature:
        status = "executed"
    return {
        "iteration": iteration,
        "rank": rank,
        "sql": candidate.sql,
        "referenced_tables": list(candidate.referenced_tables),
        "referenced_columns": list(candidate.referenced_columns),
        "execution_signature": candidate.execution_signature,
        "execution_preview": list(candidate.execution_preview),
        "result_summary": dict(candidate.result_summary),
        "preview_row_count": len(candidate.execution_preview),
        "error": candidate.error,
        "score": round(candidate.score, 4),
        "score_breakdown": dict(candidate.score_breakdown),
        "cluster_id": candidate.cluster_id,
        "source": candidate.source,
        "selected": False,
        "status": status,
    }


class EvoSqlEngine:
    def __init__(
        self,
        llm_client: LLMClient,
        scheduler: AdaptiveScheduler,
        safety: SQLSafetyInterceptor,
        executor: SQLiteSandboxExecutor,
    ) -> None:
        self.llm_client = llm_client
        self.scheduler = scheduler
        self.safety = safety
        self.executor = executor
        self.scr_refiner = SCRRefiner()
        self.eca_refiner = ECARefiner()

    def run(self, context: ContextState) -> EngineResult:
        if context.external_knowledge.get("requires_clarification"):
            return EngineResult(
                status="clarification_required",
                clarification_question=context.external_knowledge.get("clarification_question"),
                trace_steps=[
                    EngineTraceStep(
                        iteration=0,
                        strategy="fallback",
                        candidate_count=0,
                        summary="Question is ambiguous and requires clarification before SQL generation.",
                    )
                ],
            )

        base_schema = copy.deepcopy(context.schema_subset)
        plan = self.scheduler.build_plan(context.question, len(base_schema.get("tables", {})))
        current_context = ContextState(
            instruction=context.instruction,
            question=context.question,
            schema_subset=copy.deepcopy(context.schema_subset),
            history_hints=list(context.history_hints),
            external_knowledge=dict(context.external_knowledge),
            semantic_anchors=list(context.semantic_anchors),
            iteration=context.iteration,
            domain=context.domain,
            user_id=context.user_id,
            role=context.role,
        )
        context_snapshots = [snapshot_context(current_context, f"C^({current_context.iteration})")]
        current_tables = set(current_context.schema_subset.get("tables", {}).keys())
        previous_tables: set[str] = set()
        previous_best_sql = ""
        previous_cluster_signature = ""
        stable_rounds = 0
        failure_rounds = 0
        best_candidate: CandidateSQL | None = None
        trace: list[EngineTraceStep] = []
        candidate_records: list[dict[str, object]] = []
        cluster_records: list[dict[str, Any]] = []
        sample_size = plan.sample_size
        top_k = plan.top_k

        for iteration in range(1, plan.iterations + 1):
            generation_context = ContextState(
                instruction=current_context.instruction,
                question=current_context.question,
                schema_subset=copy.deepcopy(current_context.schema_subset),
                history_hints=list(current_context.history_hints),
                external_knowledge=dict(current_context.external_knowledge),
                semantic_anchors=list(current_context.semantic_anchors),
                iteration=iteration,
                domain=current_context.domain,
                user_id=current_context.user_id,
                role=current_context.role,
            )
            candidates = self._generate_and_score(generation_context, sample_size)
            executable_candidates = [item for item in candidates if not item.error]
            strategy = "ECA" if executable_candidates else "SCR"

            if executable_candidates:
                refinement = self.eca_refiner.refine(generation_context, executable_candidates, top_k, base_schema)
                assert isinstance(refinement, ECAResult)
                if refinement.best_candidate is not None:
                    best_candidate = refinement.best_candidate
            else:
                refinement = self.scr_refiner.refine(generation_context, candidates, base_schema)
                assert isinstance(refinement, SCRResult)
                if candidates:
                    best_candidate = max(candidates, key=lambda item: item.score)

            if isinstance(refinement, ECAResult):
                clusters = refinement.clusters
                for cluster in clusters:
                    cluster_records.append({"iteration": iteration, **cluster})
                main_cluster_id = clusters[0]["cluster_id"] if clusters else None
                self._apply_consistency_scores(candidates, main_cluster_id)
            else:
                clusters = []

            for rank, candidate in enumerate(candidates, start=1):
                candidate_records.append(serialize_candidate(candidate, iteration, rank))

            previous_tables = set(current_tables)
            current_context = refinement.context
            current_tables = set(current_context.schema_subset.get("tables", {}).keys())
            stable_rounds = stable_rounds + 1 if previous_tables == current_tables else 0
            context_snapshots.append(snapshot_context(current_context, f"C^({current_context.iteration})"))
            success_rate = len(executable_candidates) / len(candidates) if candidates else 0.0
            empty_rate = self._empty_result_rate(executable_candidates)
            cluster_signature = self._cluster_signature(clusters)
            cluster_stable = bool(cluster_signature and cluster_signature == previous_cluster_signature)
            best_sql = best_candidate.sql if best_candidate else ""
            best_sql_stable = bool(best_sql and best_sql == previous_best_sql)
            disagreement_rate = self._disagreement_rate(clusters, len(executable_candidates))
            failure_rounds = failure_rounds + 1 if not executable_candidates else 0
            signals = RuntimeSignals(
                iteration=iteration,
                schema_stable=previous_tables == current_tables,
                best_sql_stable=best_sql_stable,
                cluster_stable=cluster_stable,
                success_rate=success_rate,
                disagreement_rate=disagreement_rate,
                empty_result_rate=empty_rate,
                consecutive_failure_rounds=failure_rounds,
            )
            trace.append(
                EngineTraceStep(
                    iteration=iteration,
                    strategy=strategy,
                    candidate_count=len(candidates),
                    summary=(
                        f"{strategy} kept {len(current_tables)} tables, "
                        f"{len(current_context.semantic_anchors)} anchors, "
                        f"success_rate={success_rate:.2f}."
                    ),
                    context_snapshot=snapshot_context(current_context, f"C^({current_context.iteration})"),
                    refinement=refinement.details,
                    clusters=clusters,
                )
            )
            if self.scheduler.should_stop(previous_tables, current_tables, stable_rounds, signals):
                trace.append(
                    EngineTraceStep(
                        iteration=iteration,
                        strategy="early_stop",
                        candidate_count=len(candidates),
                        summary=self._early_stop_summary(signals),
                        context_snapshot=snapshot_context(current_context, f"C^({current_context.iteration})"),
                    )
                )
                break
            sample_size = self.scheduler.next_sample_size(plan, signals)
            top_k = self.scheduler.next_top_k(plan, signals)
            previous_best_sql = best_sql
            previous_cluster_signature = cluster_signature

        selected, rationale = self._select_final_candidate(candidate_records, best_candidate)
        if selected is None:
            return EngineResult(
                status="failed",
                error="No valid SQL candidate was produced.",
                trace_steps=trace,
                candidate_records=candidate_records,
                context_snapshots=context_snapshots,
                cluster_records=cluster_records,
                selection_rationale=rationale,
            )

        final_safety = self.safety.validate(selected.sql)
        if not final_safety.allowed:
            self._mark_selected_record(candidate_records, selected, "selected_blocked")
            return EngineResult(
                status="blocked",
                final_sql=selected.sql,
                safety_checks=final_safety.checks,
                trace_steps=trace,
                error=final_safety.reason,
                candidate_records=candidate_records,
                context_snapshots=context_snapshots,
                cluster_records=cluster_records,
                selection_rationale=rationale,
            )

        final_sql = final_safety.normalized_sql or selected.sql
        self._mark_selected_record(candidate_records, selected, "selected")
        rows, _ = self.executor.execute(final_sql)
        return EngineResult(
            status="completed",
            final_sql=final_sql,
            result_rows=rows,
            used_tables=selected.referenced_tables,
            used_columns=selected.referenced_columns,
            safety_checks=final_safety.checks,
            trace_steps=trace,
            candidate_records=candidate_records,
            context_snapshots=context_snapshots,
            cluster_records=cluster_records,
            selection_rationale=rationale,
        )

    def _generate_and_score(self, context: ContextState, sample_size: int) -> list[CandidateSQL]:
        raw_candidates = self.llm_client.generate_candidates(context, sample_size)
        candidates: list[CandidateSQL] = []
        for rank, sql in enumerate(raw_candidates):
            tables, columns = extract_references(sql)
            safety = self.safety.validate(sql)
            candidate = CandidateSQL(
                sql=safety.normalized_sql or sql,
                referenced_tables=tables,
                referenced_columns=columns,
            )
            candidate.score_breakdown = self._base_score_breakdown(context, candidate, rank)
            if not safety.allowed:
                candidate.error = safety.reason
                candidate.score_breakdown["execution_score"] = 0.0
                candidate.score_breakdown["final_score"] = self._final_score(candidate.score_breakdown)
                candidate.score = candidate.score_breakdown["final_score"]
                candidates.append(candidate)
                continue
            try:
                rows, _ = self.executor.execute(candidate.sql)
                candidate.execution_signature = stable_result_signature(rows)
                candidate.execution_preview = rows[:5]
                candidate.result_summary = summarize_rows(rows)
                candidate.score_breakdown["execution_score"] = 0.9 if rows else 0.55
            except Exception as exc:
                candidate.error = str(exc)
                candidate.score_breakdown["execution_score"] = 0.0
            candidate.score_breakdown["final_score"] = self._final_score(candidate.score_breakdown)
            candidate.score = candidate.score_breakdown["final_score"]
            candidates.append(candidate)
        return candidates

    def _base_score_breakdown(self, context: ContextState, candidate: CandidateSQL, rank: int) -> dict[str, float]:
        schema_tables = set(context.schema_subset.get("tables", {}).keys())
        referenced_tables = set(candidate.referenced_tables)
        allowed_ratio = len(referenced_tables & schema_tables) / len(referenced_tables) if referenced_tables else 0.5
        return {
            "prior_score": max(0.25, 1.0 - rank * 0.08),
            "schema_score": allowed_ratio,
            "structure_score": self._structure_score(context.question, candidate),
            "execution_score": 0.0,
            "consistency_score": 0.0,
            "final_score": 0.0,
        }

    def _structure_score(self, question: str, candidate: CandidateSQL) -> float:
        q = question.lower()
        sql = candidate.sql.lower()
        score = 0.65
        if any(token in q for token in ["统计", "人数", "数量", "count", "总数"]) and any(token in sql for token in ["count(", "sum("]):
            score += 0.15
        if any(token in q for token in ["排名", "top", "最高", "最多"]) and "order by" in sql:
            score += 0.1
        if any(token in q for token in ["趋势", "近", "年", "月"]) and "group by" in sql:
            score += 0.1
        if len(candidate.referenced_tables) > 1 and " join " in sql:
            score += 0.1
        return min(score, 1.0)

    def _apply_consistency_scores(self, candidates: list[CandidateSQL], main_cluster_id: str | None) -> None:
        cluster_sizes: dict[str, int] = {}
        for candidate in candidates:
            if candidate.cluster_id:
                cluster_sizes[candidate.cluster_id] = cluster_sizes.get(candidate.cluster_id, 0) + 1
        max_size = max(cluster_sizes.values(), default=1)
        for candidate in candidates:
            if not candidate.cluster_id:
                candidate.score_breakdown["consistency_score"] = 0.0
            elif candidate.cluster_id == main_cluster_id:
                candidate.score_breakdown["consistency_score"] = 1.0
            else:
                candidate.score_breakdown["consistency_score"] = cluster_sizes[candidate.cluster_id] / max_size * 0.7
            candidate.score_breakdown["final_score"] = self._final_score(candidate.score_breakdown)
            candidate.score = candidate.score_breakdown["final_score"]

    def _final_score(self, breakdown: dict[str, float]) -> float:
        weights = {
            "prior_score": 0.15,
            "schema_score": 0.2,
            "structure_score": 0.2,
            "execution_score": 0.25,
            "consistency_score": 0.2,
        }
        return round(sum(breakdown.get(key, 0.0) * weight for key, weight in weights.items()), 4)

    def _select_final_candidate(
        self,
        candidate_records: list[dict[str, object]],
        fallback_candidate: CandidateSQL | None,
    ) -> tuple[CandidateSQL | None, dict[str, Any]]:
        executable = [
            record
            for record in candidate_records
            if not record.get("error") and record.get("execution_signature")
        ]
        if not executable:
            if fallback_candidate is None:
                return None, {"reason": "No executable candidates were available."}
            return fallback_candidate, {"reason": "Selected fallback candidate because no executable record was available."}
        cluster_counts: dict[str, int] = {}
        for record in executable:
            cluster_id = str(record.get("cluster_id") or "")
            if cluster_id:
                cluster_counts[cluster_id] = cluster_counts.get(cluster_id, 0) + 1
        main_cluster = max(cluster_counts.items(), key=lambda item: item[1])[0] if cluster_counts else ""
        pool = [record for record in executable if record.get("cluster_id") == main_cluster] or executable
        selected_record = max(
            pool,
            key=lambda item: (
                float(item.get("score") or 0.0),
                float((item.get("score_breakdown") or {}).get("prior_score", 0.0)),
            ),
        )
        selected = CandidateSQL(
            sql=str(selected_record["sql"]),
            referenced_tables=list(selected_record.get("referenced_tables", [])),
            referenced_columns=list(selected_record.get("referenced_columns", [])),
            execution_signature=str(selected_record.get("execution_signature") or ""),
            execution_preview=list(selected_record.get("execution_preview", [])),
            score=float(selected_record.get("score") or 0.0),
            score_breakdown=dict(selected_record.get("score_breakdown") or {}),
            result_summary=dict(selected_record.get("result_summary") or {}),
            cluster_id=str(selected_record.get("cluster_id") or "") or None,
        )
        return selected, {
            "reason": "Selected highest final_score from the dominant execution-consistency cluster.",
            "dominant_cluster_id": main_cluster,
            "dominant_cluster_size": cluster_counts.get(main_cluster, 0) if main_cluster else 0,
            "selected_sql": selected.sql,
            "selected_score": selected.score,
            "score_breakdown": selected.score_breakdown,
        }

    def _mark_selected_record(self, records: list[dict[str, object]], selected: CandidateSQL, status: str) -> None:
        for record in records:
            if record["sql"] == selected.sql:
                record["selected"] = True
                record["status"] = status
                break

    def _empty_result_rate(self, executable_candidates: list[CandidateSQL]) -> float:
        if not executable_candidates:
            return 0.0
        empty = sum(1 for candidate in executable_candidates if candidate.result_summary.get("row_count", 0) == 0)
        return empty / len(executable_candidates)

    def _disagreement_rate(self, clusters: list[dict[str, Any]], executable_count: int) -> float:
        if executable_count <= 1 or not clusters:
            return 0.0
        main_size = max(int(cluster["candidate_count"]) for cluster in clusters)
        return 1.0 - (main_size / executable_count)

    def _cluster_signature(self, clusters: list[dict[str, Any]]) -> str:
        if not clusters:
            return ""
        return "|".join(
            f"{cluster['cluster_id']}:{cluster['candidate_count']}"
            for cluster in clusters
        )

    def _early_stop_summary(self, signals: RuntimeSignals) -> str:
        if signals.consecutive_failure_rounds >= 2:
            return "Stopped after consecutive rounds without executable candidates."
        return (
            "Stopped after convergence: "
            f"schema_stable={signals.schema_stable}, "
            f"cluster_stable={signals.cluster_stable}, "
            f"best_sql_stable={signals.best_sql_stable}."
        )
