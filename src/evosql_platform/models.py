from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ContextState:
    instruction: str
    question: str
    schema_subset: dict[str, Any]
    history_hints: list[dict[str, Any]] = field(default_factory=list)
    external_knowledge: dict[str, Any] = field(default_factory=dict)
    domain: str = "campus"
    user_id: str = "demo-user"
    role: str = "admin"


@dataclass(slots=True)
class CandidateSQL:
    sql: str
    referenced_tables: list[str] = field(default_factory=list)
    referenced_columns: list[str] = field(default_factory=list)
    execution_signature: str | None = None
    execution_preview: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    score: float = 0.0
    source: str = "llm"


@dataclass(slots=True)
class EngineTraceStep:
    iteration: int
    strategy: str
    candidate_count: int
    summary: str


@dataclass(slots=True)
class EngineResult:
    status: str
    final_sql: str | None = None
    result_rows: list[dict[str, Any]] = field(default_factory=list)
    summary_text: str = ""
    chart_spec: dict[str, Any] = field(default_factory=dict)
    used_tables: list[str] = field(default_factory=list)
    used_columns: list[str] = field(default_factory=list)
    safety_checks: list[dict[str, Any]] = field(default_factory=list)
    trace_steps: list[EngineTraceStep] = field(default_factory=list)
    clarification_question: str | None = None
    clarification_options: list[str] = field(default_factory=list)
    error: str | None = None
    execution_mode: str = ""
    result_source: str = ""
    fallback_reason: str | None = None
    attempted_sql: str | None = None
    attempted_result_rows: list[dict[str, Any]] = field(default_factory=list)
    fallback_applied: bool = False
    candidate_records: list[dict[str, Any]] = field(default_factory=list)
    attempted_candidate_records: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class SafetyResult:
    allowed: bool
    checks: list[dict[str, Any]]
    normalized_sql: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class QueryTask:
    task_id: str
    session_id: str
    question: str
    user_id: str
    role: str
    domain: str
    status: str
    result: EngineResult | None = None
    pending_clarification: dict[str, Any] | None = None
