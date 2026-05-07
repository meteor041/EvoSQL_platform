from __future__ import annotations

import copy
from evosql_platform.clients.base import LLMClient
from evosql_platform.engine.refiners import ECARefiner, SCRRefiner, extract_references
from evosql_platform.engine.scheduler import AdaptiveScheduler
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
        "preview_row_count": len(candidate.execution_preview),
        "error": candidate.error,
        "score": round(candidate.score, 4),
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
        working_schema = copy.deepcopy(context.schema_subset)
        schema_size = len(working_schema.get("tables", {}))
        plan = self.scheduler.build_plan(context.question, schema_size)
        current_tables = set(working_schema.get("tables", {}).keys())
        previous_tables: set[str] = set()
        stable_rounds = 0
        best_candidate: CandidateSQL | None = None
        trace: list[EngineTraceStep] = []
        history_hints = context.history_hints[:]
        candidate_records: list[dict[str, object]] = []

        for iteration in range(1, plan.iterations + 1):
            iteration_context = ContextState(
                instruction=context.instruction,
                question=context.question,
                schema_subset=working_schema,
                history_hints=history_hints[:],
                external_knowledge=dict(context.external_knowledge),
                domain=context.domain,
                user_id=context.user_id,
                role=context.role,
            )
            candidates = self._generate_and_score(iteration_context, plan.sample_size)
            candidate_records.extend(
                serialize_candidate(candidate, iteration, rank)
                for rank, candidate in enumerate(candidates, start=1)
            )
            executable_candidates = [item for item in candidates if not item.error]
            strategy = "ECA" if executable_candidates else "SCR"
            if executable_candidates:
                tables, anchors, selected = self.eca_refiner.refine(executable_candidates, plan.top_k)
                if selected is not None:
                    best_candidate = selected
                    history_hints = anchors
            else:
                tables, anchors = self.scr_refiner.refine(candidates)
                if candidates:
                    best_candidate = max(candidates, key=lambda item: item.score)
                    history_hints = anchors

            if not tables:
                tables = set(current_tables)

            next_tables = {table for table in tables if table in base_schema.get("tables", {})}
            if not next_tables:
                next_tables = set(current_tables)

            previous_tables = set(current_tables)
            current_tables = set(next_tables)
            working_schema = {
                "tables": {
                    name: copy.deepcopy(spec)
                    for name, spec in base_schema.get("tables", {}).items()
                    if name in current_tables
                }
            }
            stable_rounds = stable_rounds + 1 if previous_tables == current_tables else 0
            trace.append(
                EngineTraceStep(
                    iteration=iteration,
                    strategy=strategy,
                    candidate_count=len(candidates),
                    summary=f"{strategy} kept {len(current_tables)} tables and {len(history_hints)} hints.",
                )
            )
            if self.scheduler.should_stop(previous_tables, current_tables, stable_rounds):
                trace.append(
                    EngineTraceStep(
                        iteration=iteration,
                        strategy="early_stop",
                        candidate_count=len(candidates),
                        summary="Schema subset converged across iterations.",
                    )
                )
                break

        if best_candidate is None:
            return EngineResult(status="failed", error="No valid SQL candidate was produced.", trace_steps=trace, candidate_records=candidate_records)

        final_safety = self.safety.validate(best_candidate.sql)
        if not final_safety.allowed:
            for record in candidate_records:
                if record["sql"] == best_candidate.sql:
                    record["selected"] = True
                    record["status"] = "selected_blocked"
                    break
            return EngineResult(
                status="blocked",
                final_sql=best_candidate.sql,
                safety_checks=final_safety.checks,
                trace_steps=trace,
                error=final_safety.reason,
                candidate_records=candidate_records,
            )

        final_sql = final_safety.normalized_sql or best_candidate.sql
        for record in candidate_records:
            if record["sql"] == final_sql or record["sql"] == best_candidate.sql:
                record["selected"] = True
                record["status"] = "selected"
                break
        rows, _ = self.executor.execute(final_sql)
        return EngineResult(
            status="completed",
            final_sql=final_sql,
            result_rows=rows,
            used_tables=best_candidate.referenced_tables,
            used_columns=best_candidate.referenced_columns,
            safety_checks=final_safety.checks,
            trace_steps=trace,
            candidate_records=candidate_records,
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
                score=max(0.1, 1.0 - rank * 0.1),
            )
            if not safety.allowed:
                candidate.error = safety.reason
                candidates.append(candidate)
                continue
            try:
                rows, signature = self.executor.execute(candidate.sql)
                candidate.execution_signature = signature
                candidate.execution_preview = rows[:5]
                candidate.score += min(len(rows), 5) * 0.02
            except Exception as exc:
                candidate.error = str(exc)
            candidates.append(candidate)
        return candidates
