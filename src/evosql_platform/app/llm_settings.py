from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evosql_platform.config import RUNTIME_CONFIG_DB_PATH


class LLMSettingsStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or RUNTIME_CONFIG_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()
        self._seed_defaults()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_configs (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    base_url TEXT NOT NULL DEFAULT '',
                    api_key TEXT NOT NULL DEFAULT '',
                    temperature REAL NOT NULL DEFAULT 0.4,
                    timeout_seconds INTEGER NOT NULL DEFAULT 45,
                    max_retries INTEGER NOT NULL DEFAULT 2,
                    scope TEXT NOT NULL DEFAULT 'campus',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _seed_defaults(self) -> None:
        with self._lock, self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) FROM llm_configs").fetchone()[0]
            if count:
                return
            now = self._now()
            rows = [
                {
                    "id": "mock-campus",
                    "display_name": "校园演示 Mock",
                    "provider": "mock",
                    "model": "campus-reference-qa",
                    "base_url": "local://campus_qa",
                    "api_key": "",
                    "temperature": 0,
                    "timeout_seconds": 2,
                    "max_retries": 0,
                    "scope": "campus",
                    "enabled": 1,
                    "is_default": 1,
                    "notes": "local reference set",
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": "openrouter-qwen",
                    "display_name": "OpenRouter Qwen",
                    "provider": "openrouter",
                    "model": "qwen/qwen3.6-plus:free",
                    "base_url": "https://openrouter.ai/api/v1/chat/completions",
                    "api_key": "",
                    "temperature": 0.4,
                    "timeout_seconds": 45,
                    "max_retries": 2,
                    "scope": "campus",
                    "enabled": 0,
                    "is_default": 0,
                    "notes": "qwen_openrouter",
                    "created_at": now,
                    "updated_at": now,
                },
            ]
            conn.executemany(
                """
                INSERT INTO llm_configs (
                    id, display_name, provider, model, base_url, api_key,
                    temperature, timeout_seconds, max_retries, scope,
                    enabled, is_default, notes, created_at, updated_at
                )
                VALUES (
                    :id, :display_name, :provider, :model, :base_url, :api_key,
                    :temperature, :timeout_seconds, :max_retries, :scope,
                    :enabled, :is_default, :notes, :created_at, :updated_at
                )
                """,
                rows,
            )
            conn.commit()

    def list_configs(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM llm_configs
                ORDER BY is_default DESC, enabled DESC, updated_at DESC, display_name ASC
                """
            ).fetchall()
        return [self._public_row(row) for row in rows]

    def create_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        config_id = uuid.uuid4().hex
        row = self._normalize_payload(payload)
        with self._lock, self._connect() as conn:
            has_default = conn.execute("SELECT COUNT(*) FROM llm_configs WHERE is_default = 1").fetchone()[0] > 0
            is_default = 0 if has_default else 1
            conn.execute(
                """
                INSERT INTO llm_configs (
                    id, display_name, provider, model, base_url, api_key,
                    temperature, timeout_seconds, max_retries, scope,
                    enabled, is_default, notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
                """,
                (
                    config_id,
                    row["display_name"],
                    row["provider"],
                    row["model"],
                    row["base_url"],
                    row["api_key"],
                    row["temperature"],
                    row["timeout_seconds"],
                    row["max_retries"],
                    row["scope"],
                    is_default,
                    row["notes"],
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get_config(config_id)

    def get_config(self, config_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM llm_configs WHERE id = ?", (config_id,)).fetchone()
        if row is None:
            raise KeyError(config_id)
        return self._public_row(row)

    def set_default(self, config_id: str) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT id FROM llm_configs WHERE id = ?", (config_id,)).fetchone()
            if row is None:
                raise KeyError(config_id)
            now = self._now()
            conn.execute("UPDATE llm_configs SET is_default = 0")
            conn.execute(
                "UPDATE llm_configs SET is_default = 1, enabled = 1, updated_at = ? WHERE id = ?",
                (now, config_id),
            )
            conn.commit()
        return self.get_config(config_id)

    def set_enabled(self, config_id: str, enabled: bool) -> dict[str, Any]:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT is_default FROM llm_configs WHERE id = ?", (config_id,)).fetchone()
            if row is None:
                raise KeyError(config_id)
            now = self._now()
            is_default = int(row["is_default"])
            conn.execute(
                "UPDATE llm_configs SET enabled = ?, updated_at = ? WHERE id = ?",
                (1 if enabled else 0, now, config_id),
            )
            if not enabled and is_default:
                conn.execute("UPDATE llm_configs SET is_default = 0 WHERE id = ?", (config_id,))
                fallback = conn.execute(
                    "SELECT id FROM llm_configs WHERE enabled = 1 AND id <> ? ORDER BY updated_at DESC LIMIT 1",
                    (config_id,),
                ).fetchone()
                if fallback is not None:
                    conn.execute("UPDATE llm_configs SET is_default = 1 WHERE id = ?", (fallback["id"],))
            conn.commit()
        return self.get_config(config_id)

    def delete_config(self, config_id: str) -> None:
        with self._lock, self._connect() as conn:
            row = conn.execute("SELECT is_default FROM llm_configs WHERE id = ?", (config_id,)).fetchone()
            if row is None:
                raise KeyError(config_id)
            was_default = int(row["is_default"]) == 1
            conn.execute("DELETE FROM llm_configs WHERE id = ?", (config_id,))
            if was_default:
                fallback = conn.execute(
                    "SELECT id FROM llm_configs WHERE enabled = 1 ORDER BY updated_at DESC LIMIT 1"
                ).fetchone()
                if fallback is not None:
                    conn.execute("UPDATE llm_configs SET is_default = 1 WHERE id = ?", (fallback["id"],))
            conn.commit()

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        display_name = str(payload.get("display_name", "")).strip()
        provider = str(payload.get("provider", "")).strip().lower()
        model = str(payload.get("model", "")).strip()
        base_url = str(payload.get("base_url", "")).strip()
        api_key = str(payload.get("api_key", "")).strip()
        scope = str(payload.get("scope", "campus")).strip().lower() or "campus"
        notes = str(payload.get("notes", "")).strip()
        if not display_name:
            raise ValueError("display_name is required.")
        if not provider:
            raise ValueError("provider is required.")
        if not model:
            raise ValueError("model is required.")
        if provider != "mock" and not base_url:
            raise ValueError("base_url is required.")
        return {
            "display_name": display_name,
            "provider": provider,
            "model": model,
            "base_url": base_url,
            "api_key": api_key,
            "temperature": float(payload.get("temperature", 0.4)),
            "timeout_seconds": int(payload.get("timeout_seconds", 45)),
            "max_retries": int(payload.get("max_retries", 2)),
            "scope": scope,
            "notes": notes,
        }

    def _public_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "displayName": row["display_name"],
            "provider": row["provider"],
            "model": row["model"],
            "baseUrl": row["base_url"],
            "apiKeyMasked": self._mask_secret(row["api_key"]),
            "temperature": row["temperature"],
            "timeoutSeconds": row["timeout_seconds"],
            "maxRetries": row["max_retries"],
            "scope": row["scope"],
            "enabled": bool(row["enabled"]),
            "isDefault": bool(row["is_default"]),
            "notes": row["notes"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def _mask_secret(self, value: str) -> str:
        if not value:
            return "not set"
        if len(value) <= 8:
            return "••••"
        return f"{value[:4]}••••{value[-4:]}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
