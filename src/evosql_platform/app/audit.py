from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evosql_platform.config import AUDIT_LOG_PATH, RUNTIME_CONFIG_DB_PATH


class AuditLogStore:
    def __init__(self, db_path: Path | None = None, legacy_path: Path | None = None) -> None:
        self.db_path = db_path or RUNTIME_CONFIG_DB_PATH
        self.legacy_path = legacy_path or AUDIT_LOG_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
        self._import_legacy_jsonl_once()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    task_id TEXT NOT NULL DEFAULT '',
                    session_id TEXT NOT NULL DEFAULT '',
                    user_id TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL DEFAULT '',
                    domain TEXT NOT NULL DEFAULT '',
                    question TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT '',
                    final_sql TEXT NOT NULL DEFAULT '',
                    attempted_sql TEXT NOT NULL DEFAULT '',
                    llm_mode TEXT NOT NULL DEFAULT '',
                    result_source TEXT NOT NULL DEFAULT '',
                    fallback_reason TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_domain ON audit_logs(domain)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_status ON audit_logs(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_llm_mode ON audit_logs(llm_mode)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_result_source ON audit_logs(result_source)")
            conn.commit()

    def reload(self) -> dict[str, Any]:
        result = self._import_legacy_jsonl_once(force=True)
        result["stored"] = self.count()
        result["storage"] = "sqlite"
        result["db_path"] = str(self.db_path)
        return result

    def record(self, payload: dict[str, Any]) -> None:
        event = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, task_id, session_id, user_id, role, domain, question,
                    status, final_sql, attempted_sql, llm_mode, result_source,
                    fallback_reason, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._event_params(event),
            )
            conn.commit()

    def list_logs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        domain: str | None = None,
        llm_mode: str | None = None,
        status: str | None = None,
        result_source: str | None = None,
        query: str | None = None,
    ) -> dict[str, Any]:
        where: list[str] = []
        params: list[Any] = []
        if domain:
            where.append("domain = ?")
            params.append(domain)
        if llm_mode:
            where.append("llm_mode = ?")
            params.append(llm_mode)
        if status:
            where.append("status = ?")
            params.append(status)
        if result_source:
            where.append("result_source = ?")
            params.append(result_source)
        if query:
            like = f"%{query.lower()}%"
            where.append(
                """
                (
                    lower(question) LIKE ?
                    OR lower(final_sql) LIKE ?
                    OR lower(attempted_sql) LIKE ?
                    OR lower(fallback_reason) LIKE ?
                )
                """
            )
            params.extend([like, like, like, like])
        clause = f"WHERE {' AND '.join(where)}" if where else ""
        with self._connect() as conn:
            total = conn.execute(f"SELECT COUNT(*) FROM audit_logs {clause}", params).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT payload_json FROM audit_logs
                {clause}
                ORDER BY timestamp DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [json.loads(row["payload_json"]) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }

    def count(self) -> int:
        with self._connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0])

    def _import_legacy_jsonl_once(self, force: bool = False) -> dict[str, Any]:
        if not self.legacy_path.exists():
            return {"loaded": 0, "skipped": 0, "imported": 0}
        loaded: list[dict[str, Any]] = []
        skipped = 0
        for line in self.legacy_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    loaded.append(item)
                else:
                    skipped += 1
            except Exception:
                skipped += 1
        imported = 0
        with self._lock, self._connect() as conn:
            for event in loaded:
                if not force and self._event_exists(conn, event):
                    continue
                if force and self._event_exists(conn, event):
                    continue
                conn.execute(
                    """
                    INSERT INTO audit_logs (
                        timestamp, task_id, session_id, user_id, role, domain, question,
                        status, final_sql, attempted_sql, llm_mode, result_source,
                        fallback_reason, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._event_params(event),
                )
                imported += 1
            conn.commit()
        return {"loaded": len(loaded), "skipped": skipped, "imported": imported}

    def _event_exists(self, conn: sqlite3.Connection, event: dict[str, Any]) -> bool:
        timestamp = str(event.get("timestamp", ""))
        task_id = str(event.get("task_id", ""))
        if not timestamp or not task_id:
            return False
        row = conn.execute(
            "SELECT 1 FROM audit_logs WHERE timestamp = ? AND task_id = ? LIMIT 1",
            (timestamp, task_id),
        ).fetchone()
        return row is not None

    def _event_params(self, event: dict[str, Any]) -> tuple[Any, ...]:
        normalized = dict(event)
        timestamp = str(normalized.get("timestamp") or datetime.now(timezone.utc).isoformat())
        normalized["timestamp"] = timestamp
        return (
            timestamp,
            str(normalized.get("task_id", "")),
            str(normalized.get("session_id", "")),
            str(normalized.get("user_id", "")),
            str(normalized.get("role", "")),
            str(normalized.get("domain", "")),
            str(normalized.get("question", "")),
            str(normalized.get("status", "")),
            str(normalized.get("final_sql", "")),
            str(normalized.get("attempted_sql", "")),
            str(normalized.get("llm_mode", "")),
            str(normalized.get("result_source", "")),
            str(normalized.get("fallback_reason", "")),
            json.dumps(normalized, ensure_ascii=False),
        )
