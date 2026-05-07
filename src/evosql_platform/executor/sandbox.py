from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any


class SQLiteSandboxExecutor:
    def __init__(self, db_path: Path, timeout_seconds: float = 2.0, max_rows: int = 200) -> None:
        self.db_path = db_path
        self.timeout_seconds = timeout_seconds
        self.max_rows = max_rows

    def execute(self, sql: str) -> tuple[list[dict[str, Any]], str]:
        started = time.monotonic()
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            def progress_handler() -> int:
                if time.monotonic() - started > self.timeout_seconds:
                    return 1
                return 0

            conn.set_progress_handler(progress_handler, 10000)
            cursor = conn.execute(sql)
            rows = [dict(row) for row in cursor.fetchmany(self.max_rows + 1)]
            if len(rows) > self.max_rows:
                raise TimeoutError(f"Result row count exceeds max_rows={self.max_rows}")
            signature = self._signature(rows)
            return rows, signature
        finally:
            conn.close()

    @staticmethod
    def _signature(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "empty"
        keys = sorted(rows[0].keys())
        values = [tuple(row.get(key) for key in keys) for row in rows[:5]]
        return repr((tuple(keys), tuple(values), len(rows)))
