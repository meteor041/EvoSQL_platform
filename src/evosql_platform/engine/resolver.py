from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evosql_platform.config import CAMPUS_DIR


class DomainKnowledgeResolver:
    def __init__(self, metadata_path: Path | None = None, qa_path: Path | None = None) -> None:
        metadata_path = metadata_path or (CAMPUS_DIR / "campus_metadata.json")
        qa_path = qa_path or (CAMPUS_DIR / "campus_qa.json")
        self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.qa_items = json.loads(qa_path.read_text(encoding="utf-8"))

    def resolve(self, question: str) -> dict[str, Any]:
        lower = question.lower()
        matched_terms = []
        for term, info in self.metadata.get("business_terms", {}).items():
            if term.lower() in lower:
                matched_terms.append({"term": term, "definition": info})

        clarification = None
        for item in self.qa_items:
            if item.get("type") != "clarification":
                continue
            if question.strip() == item["question"] or question.strip() in item.get("aliases", []):
                clarification = item
                break

        payload: dict[str, Any] = {
            "matched_terms": matched_terms,
            "domain_tables": self._infer_domain_tables(question),
            "synonym_hits": self._match_synonyms(question),
        }
        if clarification:
            payload.update(
                {
                    "requires_clarification": True,
                    "clarification_question": clarification["clarification_question"],
                    "clarification_options": clarification["options"],
                    "followups": clarification["followups"],
                }
            )
        return payload

    def resolve_followup(self, pending: dict[str, Any], answer: str) -> str | None:
        normalized = answer.strip().lower()
        mapping = pending.get("followups", {})
        for key, value in mapping.items():
            if normalized == key.lower():
                return value
        for key, value in mapping.items():
            if key.lower() in normalized:
                return value
        return None

    def _infer_domain_tables(self, question: str) -> list[str]:
        lower = question.lower()
        matched: list[str] = []
        for tables in self.metadata.get("domains", {}).values():
            domain_tables = [table for table in tables if table.lower() in lower]
            matched.extend(domain_tables)
        return list(dict.fromkeys(matched))

    def _match_synonyms(self, question: str) -> list[dict[str, Any]]:
        lower = question.lower()
        hits: list[dict[str, Any]] = []
        for canonical, aliases in self.metadata.get("synonyms", {}).items():
            alias_hits = [alias for alias in aliases if alias.lower() in lower]
            if alias_hits or canonical.lower() in lower:
                hits.append({
                    "canonical": canonical,
                    "aliases": alias_hits,
                })
        return hits
