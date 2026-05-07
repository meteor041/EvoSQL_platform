from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path

from evosql_platform.clients.base import LLMClient
from evosql_platform.config import CAMPUS_DIR
from evosql_platform.models import ContextState


class DemoCampusLLMClient(LLMClient):
    def __init__(self, qa_path: Path | None = None) -> None:
        path = qa_path or (CAMPUS_DIR / "campus_qa.json")
        self.qa_items = json.loads(path.read_text(encoding="utf-8"))

    def generate_candidates(self, context: ContextState, sample_size: int) -> list[str]:
        if context.external_knowledge.get("requires_clarification"):
            return []
        question = context.question.strip().lower()
        ranked: list[tuple[float, str]] = []
        for item in self.qa_items:
            if item.get("type") == "clarification":
                continue
            aliases = item.get("aliases", [])
            score = max(
                SequenceMatcher(None, question, item["question"].lower()).ratio(),
                max((SequenceMatcher(None, question, alias.lower()).ratio() for alias in aliases), default=0.0),
            )
            ranked.append((score, item["sql"]))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [sql for _, sql in ranked[:sample_size]]


class BirdReferenceClient(LLMClient):
    def generate_candidates(self, context: ContextState, sample_size: int) -> list[str]:
        reference_sql = context.external_knowledge.get("reference_sql")
        if not reference_sql:
            return []
        candidates = [reference_sql]
        if " LIMIT " not in reference_sql.upper():
            candidates.append(reference_sql.rstrip("; ") + " LIMIT 5")
        candidates.append(reference_sql)
        return candidates[:sample_size]
