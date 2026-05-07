from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evosql_platform.config import AUDIT_LOG_PATH


class AuditLogStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or AUDIT_LOG_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._items: list[dict[str, Any]] = []
        self.reload()

    def reload(self) -> dict[str, Any]:
        loaded: list[dict[str, Any]] = []
        skipped = 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    loaded.append(json.loads(line))
                except Exception:
                    skipped += 1
        with self._lock:
            self._items = loaded
        return {"loaded": len(loaded), "skipped": skipped}

    def record(self, payload: dict[str, Any]) -> None:
        event = {"timestamp": datetime.now(timezone.utc).isoformat(), **payload}
        with self._lock:
            self._items.append(event)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event, ensure_ascii=False) + "\n")

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
        with self._lock:
            items = list(reversed(self._items))

        def _matches(item: dict[str, Any]) -> bool:
            if domain and item.get("domain") != domain:
                return False
            if llm_mode and item.get("llm_mode") != llm_mode:
                return False
            if status and item.get("status") != status:
                return False
            if result_source and item.get("result_source") != result_source:
                return False
            if query:
                lowered = query.lower()
                haystacks = (
                    str(item.get("question", "")),
                    str(item.get("final_sql", "")),
                    str(item.get("attempted_sql", "")),
                    str(item.get("fallback_reason", "")),
                )
                if not any(lowered in value.lower() for value in haystacks):
                    return False
            return True

        filtered = [item for item in items if _matches(item)]
        total = len(filtered)
        page = filtered[offset : offset + limit]
        return {
            "items": page,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total,
        }
