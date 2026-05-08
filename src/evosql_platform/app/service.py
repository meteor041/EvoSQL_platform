from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from evosql_platform.app.audit import AuditLogStore
from evosql_platform.app.charts import recommend_chart
from evosql_platform.clients.base import LLMClient
from evosql_platform.clients.mock import BirdReferenceClient, DemoCampusLLMClient
from evosql_platform.clients.qwen import QwenClient
from evosql_platform.config import BIRD_DIR, CAMPUS_DIR, DEFAULT_TIMEOUT_SECONDS, MAX_SQL_ROWS
from evosql_platform.datasets.bird import BirdDatasetLoader
from evosql_platform.engine.engine import EvoSqlEngine
from evosql_platform.engine.resolver import DomainKnowledgeResolver
from evosql_platform.engine.scheduler import AdaptiveScheduler
from evosql_platform.executor.safety import SQLSafetyInterceptor
from evosql_platform.executor.sandbox import SQLiteSandboxExecutor
from evosql_platform.executor.schema import SchemaRegistry
from evosql_platform.models import ContextState, EngineResult, QueryTask


class QueryService:
    def __init__(self) -> None:
        self.schema_registry = SchemaRegistry()
        self.audit_store = AuditLogStore()
        self.tasks: dict[str, QueryTask] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.knowledge_resolver = DomainKnowledgeResolver()
        self.qwen_client = QwenClient()
        self.demo_campus_client = DemoCampusLLMClient()
        self.bird_loader = BirdDatasetLoader(BIRD_DIR)

    def create_query(self, session_id: str, question: str, user_id: str, role: str, domain: str, llm_mode: str | None = None) -> QueryTask:
        task_id = uuid.uuid4().hex
        task = QueryTask(
            task_id=task_id,
            session_id=session_id,
            question=question,
            user_id=user_id,
            role=role,
            domain=domain,
            status="running",
        )
        self.tasks[task_id] = task
        if domain == "campus":
            result, pending = self._run_campus_query(question, user_id, role, llm_mode=llm_mode)
        else:
            result, pending = self._run_bird_demo(question, user_id, role)
        chart_spec = recommend_chart(result.result_rows)
        if result.chart_spec:
            chart_spec = {**result.chart_spec, **chart_spec}
        result.chart_spec = chart_spec
        result.summary_text = self._summarize(question, result)
        task.result = result
        task.status = result.status
        task.pending_clarification = pending
        if pending:
            self.sessions[session_id] = pending
        elif session_id in self.sessions:
            del self.sessions[session_id]
        self.audit_store.record(
            {
                "task_id": task_id,
                "session_id": session_id,
                "user_id": user_id,
                "role": role,
                "domain": domain,
                "question": question,
                "status": result.status,
                "final_sql": result.final_sql,
                "error": result.error,
                "safety_checks": result.safety_checks,
                "llm_mode": result.execution_mode or self._campus_mode(llm_mode),
                "result_source": result.result_source,
                "fallback_reason": result.fallback_reason,
                "fallback_applied": result.fallback_applied,
                "candidate_count": len(result.candidate_records),
                "attempted_candidate_count": len(result.attempted_candidate_records),
                "candidate_snapshot": self._candidate_snapshot(result.candidate_records),
                "attempted_candidate_snapshot": self._candidate_snapshot(result.attempted_candidate_records),
                "schema_linking": result.chart_spec.get("schema_linking", {}) if isinstance(result.chart_spec, dict) else {},
            }
        )
        return task

    def _candidate_snapshot(self, records: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
        snapshots: list[dict[str, Any]] = []
        for item in records[:limit]:
            snapshots.append(
                {
                    "iteration": item.get("iteration"),
                    "rank": item.get("rank"),
                    "status": item.get("status"),
                    "selected": item.get("selected"),
                    "score": item.get("score"),
                    "sql_preview": str(item.get("sql", ""))[:180],
                    "preview_row_count": item.get("preview_row_count", 0),
                    "error": item.get("error"),
                }
            )
        return snapshots

    def get_task(self, task_id: str) -> QueryTask:
        return self.tasks[task_id]

    def followup(self, task_id: str, answer: str) -> QueryTask:
        task = self.tasks[task_id]
        pending = task.pending_clarification or self.sessions.get(task.session_id)
        if not pending:
            raise ValueError("Task does not require clarification.")
        rewritten_question = self.knowledge_resolver.resolve_followup(pending, answer)
        if not rewritten_question:
            raise ValueError("Follow-up answer did not match any clarification option.")
        return self.create_query(task.session_id, rewritten_question, task.user_id, task.role, task.domain)

    def _campus_mode(self, requested_mode: str | None = None) -> str:
        mode = (requested_mode or os.getenv("CAMPUS_LLM_MODE", "auto")).strip().lower()
        if mode not in {"auto", "mock", "qwen"}:
            mode = "auto"
        if mode == "auto":
            return "qwen_openrouter" if self.qwen_client.is_available else "mock"
        if mode == "qwen":
            return "qwen_openrouter"
        return "mock"

    def _build_engine(self, db_path: Path, allowed_tables: set[str], llm_client: LLMClient) -> EvoSqlEngine:
        safety = SQLSafetyInterceptor(allowed_tables=allowed_tables, max_rows=MAX_SQL_ROWS)
        executor = SQLiteSandboxExecutor(db_path=db_path, timeout_seconds=DEFAULT_TIMEOUT_SECONDS, max_rows=MAX_SQL_ROWS)
        return EvoSqlEngine(llm_client=llm_client, scheduler=AdaptiveScheduler(), safety=safety, executor=executor)

    def _run_campus_query(self, question: str, user_id: str, role: str, llm_mode: str | None = None) -> tuple[EngineResult, dict[str, Any] | None]:
        db_path = CAMPUS_DIR / "campus.sqlite"
        full_schema = self.schema_registry.load_sqlite_schema(db_path)
        knowledge = self.knowledge_resolver.resolve(question)
        pending = None
        mode = self._campus_mode(llm_mode)
        use_qwen = mode == "qwen_openrouter"
        campus_client: LLMClient = self.qwen_client if use_qwen else self.demo_campus_client

        if use_qwen and not self.qwen_client.is_available:
            result = EngineResult(
                status="failed",
                error="OPENROUTER_API_KEY is not configured. Real EvoSQL campus mode requires Qwen.",
                execution_mode=mode,
                result_source="qwen",
            )
            return result, pending

        linking_context = ContextState(
            instruction="Select the minimal relevant schema subset before SQL generation.",
            question=question,
            schema_subset=full_schema,
            external_knowledge=knowledge,
            domain="campus",
            user_id=user_id,
            role=role,
        )
        schema_link = campus_client.select_schema(linking_context, max_tables=6)
        linked_tables = self._expand_linked_tables(full_schema, schema_link.get("tables", []), knowledge)
        schema_subset = self.schema_registry.subset(full_schema, linked_tables)
        if not schema_subset.get("tables"):
            schema_subset = full_schema
            linked_tables = list(full_schema.get("tables", {}).keys())

        knowledge["schema_linking"] = {
            "selected_tables": linked_tables,
            "reasoning": schema_link.get("reasoning", ""),
            "heuristic_tables": schema_link.get("heuristic_tables", []),
        }

        context = ContextState(
            instruction="Translate the campus analytics request into a safe read-only SQL query using the linked schema subset.",
            question=question,
            schema_subset=schema_subset,
            external_knowledge=knowledge,
            domain="campus",
            user_id=user_id,
            role=role,
        )
        allowed_tables = set(full_schema["tables"].keys())
        engine = self._build_engine(db_path, allowed_tables, campus_client)

        try:
            result = engine.run(context)
        except Exception as exc:
            source = "Qwen" if use_qwen else "mock"
            result = EngineResult(
                status="failed",
                error=f"{source} execution failed: {exc}",
                execution_mode=mode,
                result_source="qwen" if use_qwen else "mock",
            )
            return result, pending

        result.execution_mode = mode
        result.result_source = "qwen" if use_qwen else "mock"
        result.attempted_sql = result.final_sql
        result.attempted_result_rows = list(result.result_rows)
        result.attempted_candidate_records = list(result.candidate_records)
        self._mark_candidate_statuses(result, source_prefix="real" if use_qwen else "mock")
        result.chart_spec = {
            "schema_linking": knowledge["schema_linking"],
        }

        if result.status == "clarification_required":
            pending = {
                "task_id": uuid.uuid4().hex,
                "question": question,
                "clarification_question": knowledge.get("clarification_question"),
                "options": knowledge.get("clarification_options", []),
                "followups": knowledge.get("followups", {}),
            }
        return result, pending

    def _run_bird_demo(self, question: str, user_id: str, role: str) -> tuple[EngineResult, dict[str, Any] | None]:
        sample = self.bird_loader.get_sample(0)
        db_path = self.bird_loader.get_db_path(sample["db_id"])
        schema = self.schema_registry.load_sqlite_schema(db_path)
        context = ContextState(
            instruction="Use the reference SQL to validate the pipeline.",
            question=question,
            schema_subset=schema,
            external_knowledge={"reference_sql": sample["SQL"], "evidence": sample.get("evidence")},
            domain="bird",
            user_id=user_id,
            role=role,
        )
        allowed_tables = set(schema["tables"].keys())
        engine = self._build_engine(db_path, allowed_tables, BirdReferenceClient())
        result = engine.run(context)
        result.execution_mode = "bird_reference"
        result.result_source = "bird_reference"
        result.attempted_candidate_records = list(result.candidate_records)
        self._mark_candidate_statuses(result, source_prefix="reference")
        return result, None

    def _expand_linked_tables(self, schema: dict[str, Any], linked_tables: list[str], knowledge: dict[str, Any]) -> list[str]:
        if not linked_tables:
            linked_tables = knowledge.get("domain_tables", [])
        available = set(schema.get("tables", {}).keys())
        selected = [table for table in linked_tables if table in available]
        expanded = set(selected)
        for table in list(selected):
            spec = schema["tables"].get(table, {})
            for fk in spec.get("foreign_keys", []):
                target = fk.get("to_table")
                if target in available and len(expanded) < 8:
                    expanded.add(target)
            for candidate_name, candidate_spec in schema["tables"].items():
                for fk in candidate_spec.get("foreign_keys", []):
                    if fk.get("to_table") == table and len(expanded) < 8:
                        expanded.add(candidate_name)
        return list(dict.fromkeys(selected + sorted(expanded - set(selected)))) or list(available)

    def _mark_candidate_statuses(self, result: EngineResult, source_prefix: str) -> None:
        for record in result.candidate_records:
            if record.get("selected"):
                record["status"] = f"{source_prefix}_selected"
            elif record.get("status") == "executed":
                record["status"] = f"{source_prefix}_executed"
            elif record.get("status") == "blocked":
                record["status"] = f"{source_prefix}_blocked"
            elif record.get("status") == "failed":
                record["status"] = f"{source_prefix}_failed"

    def _summarize(self, question: str, result: EngineResult) -> str:
        if result.status == "clarification_required":
            return result.clarification_question or "Need clarification."
        if result.error:
            return result.error
        if not result.result_rows:
            return "Query succeeded but returned no rows."
        if self.qwen_client.is_available and result.result_source == "qwen":
            try:
                return self.qwen_client.summarize_query_result(question, result.result_rows)
            except Exception:
                pass
        row_count = len(result.result_rows)
        columns = list(result.result_rows[0].keys())
        return f"Query returned {row_count} rows with columns: {', '.join(columns)}."
