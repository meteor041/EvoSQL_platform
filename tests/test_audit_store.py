from __future__ import annotations

import json
import sqlite3

from evosql_platform.app.audit import AuditLogStore


def test_audit_store_records_to_sqlite(tmp_path) -> None:
    db_path = tmp_path / "runtime.sqlite"
    legacy_path = tmp_path / "audit_logs.jsonl"
    store = AuditLogStore(db_path=db_path, legacy_path=legacy_path)
    store.record(
        {
            "task_id": "task-1",
            "session_id": "session-1",
            "user_id": "tester",
            "role": "admin",
            "domain": "campus",
            "question": "统计学生人数",
            "status": "completed",
            "final_sql": "SELECT COUNT(*) FROM students",
            "llm_mode": "mock",
            "result_source": "mock",
        }
    )

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
        row = conn.execute("SELECT question, payload_json FROM audit_logs").fetchone()

    assert count == 1
    assert row[0] == "统计学生人数"
    assert json.loads(row[1])["task_id"] == "task-1"


def test_audit_store_filters_and_pages_from_sqlite(tmp_path) -> None:
    store = AuditLogStore(db_path=tmp_path / "runtime.sqlite", legacy_path=tmp_path / "missing.jsonl")
    store.record({"task_id": "task-1", "domain": "campus", "status": "completed", "question": "统计学生人数"})
    store.record({"task_id": "task-2", "domain": "bird", "status": "failed", "question": "bird query"})
    store.record({"task_id": "task-3", "domain": "campus", "status": "failed", "question": "DeepSeek fallback"})

    result = store.list_logs(limit=1, offset=0, domain="campus", status="failed", query="deepseek")

    assert result["total"] == 1
    assert result["items"][0]["task_id"] == "task-3"
    assert not result["has_more"]


def test_audit_store_imports_legacy_jsonl_once(tmp_path) -> None:
    legacy_path = tmp_path / "audit_logs.jsonl"
    legacy_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-05-08T09:19:37.111616+00:00",
                "task_id": "legacy-1",
                "domain": "campus",
                "status": "completed",
                "question": "旧日志",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    db_path = tmp_path / "runtime.sqlite"
    store = AuditLogStore(db_path=db_path, legacy_path=legacy_path)
    assert store.count() == 1

    reloaded = store.reload()
    assert reloaded["imported"] == 0
    assert store.count() == 1
    assert store.list_logs()["items"][0]["task_id"] == "legacy-1"
