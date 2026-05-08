from __future__ import annotations

import sqlite3
from pathlib import Path

from evosql_platform.clients.base import LLMClient
from evosql_platform.engine.engine import EvoSqlEngine
from evosql_platform.engine.refiners import ECARefiner, SCRRefiner, snapshot_context
from evosql_platform.engine.scheduler import AdaptiveScheduler, RuntimeSignals
from evosql_platform.executor.safety import SQLSafetyInterceptor
from evosql_platform.executor.sandbox import SQLiteSandboxExecutor
from evosql_platform.models import CandidateSQL, ContextState


SCHEMA = {
    "tables": {
        "students": {
            "columns": [
                {"name": "student_id", "type": "INTEGER", "primary_key": True},
                {"name": "student_name", "type": "TEXT", "primary_key": False},
                {"name": "college_id", "type": "INTEGER", "primary_key": False},
                {"name": "unused_note", "type": "TEXT", "primary_key": False},
            ],
            "foreign_keys": [{"from": "college_id", "to_table": "colleges", "to_column": "college_id"}],
        },
        "colleges": {
            "columns": [
                {"name": "college_id", "type": "INTEGER", "primary_key": True},
                {"name": "college_name", "type": "TEXT", "primary_key": False},
            ],
            "foreign_keys": [],
        },
    }
}


class FixedClient(LLMClient):
    def generate_candidates(self, context: ContextState, sample_size: int) -> list[str]:
        return [
            "SELECT c.college_name, COUNT(s.student_id) AS student_count "
            "FROM students s JOIN colleges c ON s.college_id = c.college_id "
            "GROUP BY c.college_name ORDER BY c.college_name",
            "SELECT c.college_name, COUNT(*) AS student_count "
            "FROM students s JOIN colleges c ON s.college_id = c.college_id "
            "GROUP BY c.college_name ORDER BY c.college_name",
        ][:sample_size]


def make_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "campus.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE colleges (college_id INTEGER PRIMARY KEY, college_name TEXT);
            CREATE TABLE students (
                student_id INTEGER PRIMARY KEY,
                student_name TEXT,
                college_id INTEGER,
                unused_note TEXT,
                FOREIGN KEY(college_id) REFERENCES colleges(college_id)
            );
            INSERT INTO colleges VALUES (1, 'Computer'), (2, 'Math');
            INSERT INTO students VALUES (1, 'A', 1, 'x'), (2, 'B', 1, 'y'), (3, 'C', 2, 'z');
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def test_context_snapshot_contains_iteration_and_anchors() -> None:
    context = ContextState(
        instruction="test",
        question="统计学生人数",
        schema_subset=SCHEMA,
        semantic_anchors=[{"sql": "SELECT 1"}],
        iteration=2,
    )
    snapshot = snapshot_context(context, "C^(2)")
    assert snapshot["iteration"] == 2
    assert snapshot["semantic_anchor_count"] == 1
    assert snapshot["schema"]["table_count"] == 2


def test_scr_refiner_trims_columns_and_resets_context() -> None:
    context = ContextState(
        instruction="test",
        question="统计学生人数",
        schema_subset=SCHEMA,
        history_hints=[{"old": "hint"}],
        semantic_anchors=[{"old": "anchor"}],
    )
    candidate = CandidateSQL(
        sql="SELECT s.student_id FROM students s",
        referenced_tables=["students"],
        referenced_columns=["students.student_id"],
    )
    result = SCRRefiner().refine(context, [candidate], SCHEMA)
    assert not isinstance(result, tuple)
    columns = [item["name"] for item in result.context.schema_subset["tables"]["students"]["columns"]]
    assert "student_id" in columns
    assert "unused_note" not in columns
    assert result.context.history_hints == []
    assert result.context.semantic_anchors == []


def test_eca_refiner_outputs_clusters_and_anchors() -> None:
    context = ContextState(instruction="test", question="统计学生人数", schema_subset=SCHEMA)
    candidates = [
        CandidateSQL(
            sql="SELECT 1",
            referenced_tables=["students"],
            referenced_columns=["students.student_id"],
            execution_signature="same",
            result_summary={"row_count": 1, "columns": ["one"]},
            score=0.9,
        ),
        CandidateSQL(
            sql="SELECT 1 LIMIT 5",
            referenced_tables=["students"],
            referenced_columns=["students.student_id"],
            execution_signature="same",
            result_summary={"row_count": 1, "columns": ["one"]},
            score=0.8,
        ),
    ]
    result = ECARefiner().refine(context, candidates, top_k=1, base_schema=SCHEMA)
    assert not isinstance(result, tuple)
    assert len(result.clusters) == 1
    assert result.anchors[0]["result_summary"]["row_count"] == 1
    assert result.context.semantic_anchors


def test_scheduler_uses_runtime_signals_for_stop_and_sampling() -> None:
    scheduler = AdaptiveScheduler()
    plan = scheduler.build_plan("统计学生人数", schema_size=2)
    failure_signals = RuntimeSignals(
        iteration=2,
        schema_stable=False,
        best_sql_stable=False,
        cluster_stable=False,
        success_rate=0.0,
        disagreement_rate=1.0,
        empty_result_rate=0.0,
        consecutive_failure_rounds=2,
    )
    assert scheduler.should_stop({"students"}, {"colleges"}, 0, failure_signals)
    assert scheduler.next_sample_size(plan, failure_signals) > plan.sample_size


def test_engine_returns_context_clusters_scores_and_rationale(tmp_path: Path) -> None:
    db_path = make_db(tmp_path)
    engine = EvoSqlEngine(
        llm_client=FixedClient(),
        scheduler=AdaptiveScheduler(),
        safety=SQLSafetyInterceptor(allowed_tables={"students", "colleges"}),
        executor=SQLiteSandboxExecutor(db_path=db_path),
    )
    result = engine.run(
        ContextState(
            instruction="Generate SQL.",
            question="统计各学院学生人数",
            schema_subset=SCHEMA,
        )
    )
    assert result.status == "completed"
    assert result.context_snapshots
    assert result.cluster_records
    assert result.selection_rationale["selected_sql"] == result.final_sql
    assert result.candidate_records[0]["score_breakdown"]["final_score"] > 0
