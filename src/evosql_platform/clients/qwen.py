from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from evosql_platform.clients.base import LLMClient
from evosql_platform.models import ContextState


class QwenClient(LLMClient):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.4,
        timeout_seconds: float = 45.0,
        max_retries: int = 2,
        base_url: str | None = None,
        provider_label: str | None = None,
    ) -> None:
        self.model = model or os.getenv("OPENROUTER_MODEL", "qwen/qwen3.6-plus:free")
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.request_url = self._chat_completions_url(self.base_url)
        self.provider_label = provider_label or self._infer_provider_label(self.base_url)
        self.referer = os.getenv("OPENROUTER_REFERER", "http://localhost")
        self.title = os.getenv("OPENROUTER_TITLE", "EvoSQLPlatform")

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    def select_schema(self, context: ContextState, max_tables: int = 6) -> dict[str, Any]:
        heuristic_tables = self._heuristic_schema_link(context)[:max_tables]
        if not self.api_key:
            return {
                "tables": heuristic_tables,
                "reasoning": f"Used heuristic schema linking because API key is not configured for {self.provider_label}.",
            }
        try:
            content = self._request(
                system_prompt=(
                    "You are an expert schema linker for Text-to-SQL. "
                    "Select only the most relevant SQLite tables for the user question. "
                    "Prefer a compact subset that still supports the needed joins and aggregations. "
                    "Return strictly valid JSON with keys: tables, reasoning."
                ),
                user_prompt=self._build_schema_link_prompt(context, max_tables, heuristic_tables),
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            return {
                "tables": heuristic_tables,
                "reasoning": f"{self.provider_label} schema linking request failed; used heuristic fallback. Detail: {exc}",
                "heuristic_tables": heuristic_tables,
                "fallback_reason": str(exc),
            }
        data = self._parse_json_object(content, "schema_linking")
        selected = [item for item in data.get("tables", []) if isinstance(item, str)]
        selected = [item for item in selected if item in context.schema_subset.get("tables", {})]
        unique = list(dict.fromkeys(selected))[:max_tables]
        if unique:
            return {
                "tables": unique,
                "reasoning": str(data.get("reasoning", "")),
                "heuristic_tables": heuristic_tables,
            }
        return {
            "tables": heuristic_tables,
            "reasoning": "Schema linker response was invalid; fell back to heuristic table selection.",
            "heuristic_tables": heuristic_tables,
        }

    def generate_candidates(self, context: ContextState, sample_size: int) -> list[str]:
        if not self.api_key:
            raise RuntimeError(f"API key is not configured for {self.provider_label}.")
        content = self._request(
            system_prompt=(
                "You are an expert Text-to-SQL assistant implementing an EvoSQL-style workflow. "
                "Only produce safe read-only SQLite SELECT statements. "
                "Use only the provided schema subset. "
                "In later rounds, use history hints and execution anchors to improve structural consistency. "
                "Never use INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, ATTACH, or multiple statements. "
                "Return strictly valid JSON with one key: sql_candidates."
            ),
            user_prompt=self._build_generation_prompt(context, sample_size),
            response_format={"type": "json_object"},
        )
        return self._parse_candidates(content, sample_size)

    def summarize_query_result(self, question: str, rows: list[dict[str, Any]]) -> str:
        if not self.api_key:
            raise RuntimeError(f"API key is not configured for {self.provider_label}.")
        preview = json.dumps(rows[:10], ensure_ascii=False)
        content = self._request(
            system_prompt=(
                "You are a campus data analyst. "
                "Write a concise Chinese summary of the query result. "
                "Do not mention SQL. "
                "Do not output markdown, file paths, code, XML-like tags, or special model tokens. "
                "Keep the answer within 2 sentences. "
                "If the data is empty, explain that no matching result was found."
            ),
            user_prompt=(
                f"User question: {question}\n"
                f"Result rows (JSON preview): {preview}\n"
                "Give a short natural-language summary in Chinese."
            ),
        )
        return self._clean_summary_text(content)

    def _request(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return self._post_json(payload)
            except Exception as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    break
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"{self.provider_label} request failed at {self.request_url}: {last_error}") from last_error

    def _post_json(self, payload: dict[str, Any]) -> str:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.request_url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.referer,
                "X-Title": self.title,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error: {exc}") from exc

        choices = raw.get("choices", [])
        if not choices:
            raise RuntimeError(f"No choices returned: {raw}")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise RuntimeError(f"Empty content returned: {raw}")
        return content

    def _parse_candidates(self, content: str, sample_size: int) -> list[str]:
        data = self._parse_json_object(content, "sql_candidates")
        candidates = data.get("sql_candidates", [])
        if not isinstance(candidates, list):
            raise RuntimeError(f"Invalid sql_candidates payload: {data}")
        cleaned: list[str] = []
        for item in candidates:
            if not isinstance(item, str):
                continue
            sql = self._clean_sql_text(item)
            if sql:
                cleaned.append(sql)
        unique = list(dict.fromkeys(cleaned))
        if not unique:
            raise RuntimeError(f"No SQL candidates parsed from response: {self._shorten(content)}")
        return unique[:sample_size]

    def _parse_json_object(self, content: str, label: str) -> dict[str, Any]:
        cleaned = self._strip_code_fences(content).strip()
        if not cleaned:
            raise RuntimeError(f"{label} response was empty.")

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

        extracted = self._extract_first_json_object(cleaned)
        if extracted is None:
            raise RuntimeError(
                f"{label} response was not valid JSON. Raw preview: {self._shorten(cleaned)}"
            )
        try:
            data = json.loads(extracted)
        except Exception:
            repaired = self._repair_json_object(extracted)
            try:
                data = json.loads(repaired)
            except Exception as exc:
                raise RuntimeError(
                    f"{label} response contained malformed JSON. Raw preview: {self._shorten(cleaned)}"
                ) from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"{label} response did not decode to a JSON object.")
        return data

    def _build_schema_link_prompt(self, context: ContextState, max_tables: int, heuristic_tables: list[str]) -> str:
        schema_text = self._format_schema(context.schema_subset, include_foreign_keys=True)
        knowledge = json.dumps(context.external_knowledge, ensure_ascii=False)
        return (
            f"Question: {context.question}\n"
            f"Role: {context.role}\n"
            f"External knowledge: {knowledge}\n"
            f"Heuristic candidate tables: {json.dumps(heuristic_tables, ensure_ascii=False)}\n"
            f"Schema:\n{schema_text}\n\n"
            f"Select at most {max_tables} tables needed to answer the question. "
            "Include bridge tables when joins are required. "
            "Return JSON exactly like: {\"tables\": [\"table_a\", \"table_b\"], \"reasoning\": \"...\"}"
        )

    def _build_generation_prompt(self, context: ContextState, sample_size: int) -> str:
        schema_text = self._format_schema(context.schema_subset, include_foreign_keys=True)
        hints = json.dumps(context.history_hints, ensure_ascii=False)
        anchors = json.dumps(context.semantic_anchors, ensure_ascii=False)
        knowledge = json.dumps(context.external_knowledge, ensure_ascii=False)
        return (
            f"Question: {context.question}\n"
            f"Role: {context.role}\n"
            f"Iteration: {context.iteration}\n"
            f"Instruction: {context.instruction}\n"
            f"External knowledge: {knowledge}\n"
            f"History hints: {hints}\n"
            f"Semantic anchors: {anchors}\n"
            f"Schema subset:\n{schema_text}\n\n"
            f"Generate {sample_size} distinct candidate SQL queries for SQLite. "
            "Each query must be a single read-only SELECT statement. "
            "Prefer explicit joins, valid grouping, and exact business definitions from external knowledge. "
            "If history hints contain prior anchor SQL or execution signatures, use them to improve structure, but do not copy invalid queries blindly. "
            "When the question asks for ranking or top-k, include a proper ORDER BY and LIMIT. "
            "When the question asks for a trend, include time-based grouping. "
            'Return JSON exactly like: {"sql_candidates": ["SELECT ...", "SELECT ..."]}'
        )

    def _heuristic_schema_link(self, context: ContextState) -> list[str]:
        question = context.question.lower()
        tables = context.schema_subset.get("tables", {})
        scores: dict[str, float] = {name: 0.0 for name in tables}
        tokens = set(re.findall(r"[a-zA-Z_]+", question))
        tokens.update(re.findall(r"[\u4e00-\u9fff]{1,8}", context.question))

        business_terms = context.external_knowledge.get("matched_terms", [])
        term_text = " ".join(str(item.get("term", "")) + " " + str(item.get("definition", "")) for item in business_terms).lower()

        for table_name, spec in tables.items():
            if table_name.lower() in question:
                scores[table_name] += 5.0
            for token in tokens:
                if token and token in table_name.lower():
                    scores[table_name] += 2.0
            for column in spec.get("columns", []):
                column_name = str(column.get("name", "")).lower()
                if column_name in question:
                    scores[table_name] += 1.8
                for token in tokens:
                    if token and token in column_name:
                        scores[table_name] += 0.5
            if table_name.lower().rstrip("s") in term_text or table_name.lower() in term_text:
                scores[table_name] += 1.5

        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
        selected = [name for name, score in ordered if score > 0]
        if not selected:
            selected = list(tables.keys())[: min(6, len(tables))]
        return selected

    def _format_schema(self, schema_subset: dict[str, Any], include_foreign_keys: bool = False) -> str:
        lines: list[str] = []
        for table_name, spec in schema_subset.get("tables", {}).items():
            columns = ", ".join(
                f"{column['name']}:{column['type'] or 'TEXT'}"
                for column in spec.get("columns", [])
            )
            lines.append(f"- {table_name}({columns})")
            if include_foreign_keys and spec.get("foreign_keys"):
                fk_text = ", ".join(
                    f"{fk['from']} -> {fk['to_table']}.{fk['to_column']}"
                    for fk in spec.get("foreign_keys", [])
                )
                lines.append(f"  foreign_keys: {fk_text}")
        return "\n".join(lines)

    def _strip_code_fences(self, text: str) -> str:
        stripped = text.strip()
        stripped = re.sub(r"^```(?:json|sql|text)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    def _extract_first_json_object(self, text: str) -> str | None:
        start = text.find("{")
        if start == -1:
            return None
        depth = 0
        in_string = False
        escape = False
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start : index + 1]
        return None


    def _repair_json_object(self, text: str) -> str:
        repaired = text
        repaired = re.sub(r'"\s+"', ' ', repaired)
        repaired = re.sub(r'\[\s+"', '["', repaired)
        repaired = re.sub(r'"\s+\]', '"]', repaired)
        repaired = re.sub(r'",\s+"', '__JSON_LIST_SEP__', repaired)
        repaired = re.sub(r'"\s+"', '', repaired)
        repaired = repaired.replace('__JSON_LIST_SEP__', '", "')
        repaired = re.sub(r'\s+', ' ', repaired).strip()
        return repaired

    def _clean_sql_text(self, text: str) -> str:
        sql = self._strip_code_fences(text)
        sql = sql.strip().strip("`")
        sql = re.sub(r"^sql\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r";+$", "", sql).strip()
        return sql

    def _clean_summary_text(self, text: str) -> str:
        cleaned = self._strip_code_fences(text)
        cleaned = re.sub(r"<\|[^>]+\|>", " ", cleaned)
        cleaned = re.sub(r"/[^\s]+\.(?:md|py|json|txt|yaml|yml)\b", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if "<|" in cleaned or "README" in cleaned or "fim_" in cleaned:
            cleaned = cleaned.split("<|", 1)[0].strip()
        sentence_split = re.split(r"(?<=[。！？!?])\s+", cleaned)
        cleaned = " ".join(sentence_split[:2]).strip()
        return cleaned or "查询已完成。"

    def _shorten(self, text: str, limit: int = 220) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."

    def _infer_provider_label(self, base_url: str) -> str:
        lower = base_url.lower()
        if "deepseek" in lower:
            return "DeepSeek"
        if "openrouter" in lower:
            return "OpenRouter"
        if "dashscope" in lower or "aliyun" in lower:
            return "DashScope"
        if "localhost" in lower or "127.0.0.1" in lower:
            return "local OpenAI-compatible endpoint"
        return "OpenAI-compatible endpoint"

    def _chat_completions_url(self, base_url: str) -> str:
        normalized = base_url.strip().rstrip("/")
        if not normalized:
            return normalized
        lower = normalized.lower()
        if lower.endswith("/chat/completions") or lower.endswith("/completions"):
            return normalized
        return f"{normalized}/v1/chat/completions"
