from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlglot import exp, parse_one

from evosql_platform.models import CandidateSQL, ContextState


def extract_references(sql: str) -> tuple[list[str], list[str]]:
    try:
        tree = parse_one(sql, read="sqlite")
    except Exception:
        return [], []
    tables = sorted({node.name for node in tree.find_all(exp.Table) if node.name})
    aliases = {
        table.alias_or_name: table.name
        for table in tree.find_all(exp.Table)
        if table.alias_or_name and table.name
    }
    columns = []
    for node in tree.find_all(exp.Column):
        if node.table:
            table_name = aliases.get(node.table, node.table)
            columns.append(f"{table_name}.{node.name}")
        elif node.name:
            columns.append(node.name)
    return tables, sorted(set(columns))


def normalize_column_refs(columns: list[str], tables: list[str]) -> dict[str, set[str]]:
    by_table: dict[str, set[str]] = defaultdict(set)
    if len(tables) == 1:
        default_table = tables[0]
    else:
        default_table = ""
    for ref in columns:
        if "." in ref:
            table, column = ref.split(".", 1)
            by_table[table].add(column)
        elif default_table:
            by_table[default_table].add(ref)
    return by_table


def summarize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    table_summaries = []
    for table_name, spec in schema.get("tables", {}).items():
        columns = [column.get("name") for column in spec.get("columns", [])]
        table_summaries.append(
            {
                "table": table_name,
                "column_count": len(columns),
                "columns": columns,
            }
        )
    return {
        "table_count": len(table_summaries),
        "column_count": sum(item["column_count"] for item in table_summaries),
        "tables": table_summaries,
    }


def snapshot_context(context: ContextState, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "iteration": context.iteration,
        "instruction": context.instruction,
        "schema": summarize_schema(context.schema_subset),
        "history_hint_count": len(context.history_hints),
        "semantic_anchor_count": len(context.semantic_anchors),
        "history_hints": list(context.history_hints),
        "semantic_anchors": list(context.semantic_anchors),
        "external_knowledge_keys": sorted(context.external_knowledge.keys()),
    }


def trim_schema_columns(
    schema: dict[str, Any],
    tables: set[str],
    columns_by_table: dict[str, set[str]],
) -> dict[str, Any]:
    if not tables:
        return copy.deepcopy(schema)
    trimmed: dict[str, Any] = {"tables": {}}
    for table_name, spec in schema.get("tables", {}).items():
        if table_name not in tables:
            continue
        selected_columns = columns_by_table.get(table_name, set())
        if not selected_columns:
            trimmed["tables"][table_name] = copy.deepcopy(spec)
            continue
        fk_columns = {
            fk.get("from")
            for fk in spec.get("foreign_keys", [])
            if fk.get("from")
        }
        keep_columns = set(selected_columns) | fk_columns
        trimmed["tables"][table_name] = {
            **copy.deepcopy(spec),
            "columns": [
                copy.deepcopy(column)
                for column in spec.get("columns", [])
                if column.get("name") in keep_columns or column.get("primary_key")
            ],
            "foreign_keys": [
                copy.deepcopy(fk)
                for fk in spec.get("foreign_keys", [])
                if fk.get("from") in keep_columns
            ],
        }
    return trimmed


@dataclass(slots=True)
class SCRResult:
    context: ContextState
    tables: set[str]
    columns_by_table: dict[str, set[str]]
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ECAResult:
    context: ContextState
    tables: set[str]
    columns_by_table: dict[str, set[str]]
    anchors: list[dict[str, Any]]
    clusters: list[dict[str, Any]]
    best_candidate: CandidateSQL | None
    details: dict[str, Any] = field(default_factory=dict)


class SCRRefiner:
    def refine(
        self,
        context: ContextState | list[CandidateSQL],
        candidates: list[CandidateSQL] | None = None,
        base_schema: dict[str, Any] | None = None,
    ) -> SCRResult | tuple[set[str], list[dict[str, str]]]:
        if candidates is None and isinstance(context, list):
            tables = self.collect_tables(context)
            return tables, []
        assert isinstance(context, ContextState)
        assert candidates is not None
        schema = base_schema or context.schema_subset
        tables, columns_by_table = self.collect_references(candidates)
        if not tables:
            tables = set(context.schema_subset.get("tables", {}).keys())
        refined_schema = trim_schema_columns(schema, tables, columns_by_table)
        next_context = ContextState(
            instruction=context.instruction,
            question=context.question,
            schema_subset=refined_schema,
            history_hints=[],
            external_knowledge=dict(context.external_knowledge),
            semantic_anchors=[],
            iteration=context.iteration + 1,
            domain=context.domain,
            user_id=context.user_id,
            role=context.role,
        )
        return SCRResult(
            context=next_context,
            tables=tables,
            columns_by_table=columns_by_table,
            details={
                "kept_tables": sorted(tables),
                "kept_columns": {
                    table: sorted(columns)
                    for table, columns in sorted(columns_by_table.items())
                },
                "cleared_history_hints": len(context.history_hints),
                "cleared_semantic_anchors": len(context.semantic_anchors),
                "context_snapshot": snapshot_context(next_context, f"C^({next_context.iteration})"),
            },
        )

    def collect_tables(self, candidates: list[CandidateSQL]) -> set[str]:
        tables: set[str] = set()
        for candidate in candidates:
            tables.update(candidate.referenced_tables)
        return tables

    def collect_references(self, candidates: list[CandidateSQL]) -> tuple[set[str], dict[str, set[str]]]:
        tables: set[str] = set()
        columns_by_table: dict[str, set[str]] = defaultdict(set)
        for candidate in candidates:
            candidate_tables = list(candidate.referenced_tables)
            tables.update(candidate_tables)
            normalized = normalize_column_refs(candidate.referenced_columns, candidate_tables)
            for table, columns in normalized.items():
                columns_by_table[table].update(columns)
        return tables, dict(columns_by_table)


class ECARefiner:
    def refine(
        self,
        context: ContextState | list[CandidateSQL],
        candidates: list[CandidateSQL] | int | None = None,
        top_k: int | None = None,
        base_schema: dict[str, Any] | None = None,
    ) -> ECAResult | tuple[set[str], list[dict[str, str]], CandidateSQL | None]:
        if isinstance(context, list):
            old_candidates = context
            old_top_k = int(top_k if top_k is not None else candidates)
            result = self._cluster(old_candidates, old_top_k)
            anchors = [
                {"sql": item["representative_sql"], "signature": item["signature"]}
                for item in result["clusters"][:old_top_k]
            ]
            tables = set()
            for candidate in old_candidates:
                if candidate.cluster_id == result["best_cluster_id"]:
                    tables.update(candidate.referenced_tables)
            return tables, anchors, result["best_candidate"]

        assert isinstance(context, ContextState)
        assert isinstance(candidates, list)
        assert top_k is not None
        schema = base_schema or context.schema_subset
        clustered = self._cluster(candidates, top_k)
        kept_clusters = clustered["clusters"][:top_k]
        anchors = [self._anchor_from_cluster(cluster) for cluster in kept_clusters]
        tables: set[str] = set()
        columns_by_table: dict[str, set[str]] = defaultdict(set)
        for cluster in kept_clusters:
            for table in cluster["referenced_tables"]:
                tables.add(table)
            for table, columns in cluster["referenced_columns"].items():
                columns_by_table[table].update(columns)
        if not tables:
            tables = set(context.schema_subset.get("tables", {}).keys())
        refined_schema = trim_schema_columns(schema, tables, dict(columns_by_table))
        next_context = ContextState(
            instruction=context.instruction,
            question=context.question,
            schema_subset=refined_schema,
            history_hints=list(anchors),
            external_knowledge=dict(context.external_knowledge),
            semantic_anchors=list(anchors),
            iteration=context.iteration + 1,
            domain=context.domain,
            user_id=context.user_id,
            role=context.role,
        )
        return ECAResult(
            context=next_context,
            tables=tables,
            columns_by_table=dict(columns_by_table),
            anchors=anchors,
            clusters=clustered["clusters"],
            best_candidate=clustered["best_candidate"],
            details={
                "kept_cluster_ids": [cluster["cluster_id"] for cluster in kept_clusters],
                "anchor_count": len(anchors),
                "context_snapshot": snapshot_context(next_context, f"C^({next_context.iteration})"),
            },
        )

    def _cluster(self, candidates: list[CandidateSQL], top_k: int) -> dict[str, Any]:
        clusters: dict[str, list[CandidateSQL]] = defaultdict(list)
        for candidate in candidates:
            if candidate.error:
                continue
            signature = candidate.execution_signature or "unknown"
            cluster_id = self._cluster_id(signature)
            candidate.cluster_id = cluster_id
            clusters[cluster_id].append(candidate)
        cluster_records = [
            self._cluster_record(cluster_id, items)
            for cluster_id, items in clusters.items()
        ]
        cluster_records.sort(
            key=lambda item: (
                -item["candidate_count"],
                -item["max_score"],
                item["cluster_id"],
            )
        )
        best = None
        if cluster_records:
            best_cluster_id = cluster_records[0]["cluster_id"]
            best = max(clusters[best_cluster_id], key=lambda item: item.score)
        else:
            best_cluster_id = None
        return {
            "clusters": cluster_records,
            "best_candidate": best,
            "best_cluster_id": best_cluster_id,
            "top_k": top_k,
        }

    def _cluster_record(self, cluster_id: str, candidates: list[CandidateSQL]) -> dict[str, Any]:
        representative = max(candidates, key=lambda item: item.score)
        referenced_tables = sorted({table for candidate in candidates for table in candidate.referenced_tables})
        columns_by_table: dict[str, set[str]] = defaultdict(set)
        for candidate in candidates:
            for table, columns in normalize_column_refs(candidate.referenced_columns, candidate.referenced_tables).items():
                columns_by_table[table].update(columns)
        return {
            "cluster_id": cluster_id,
            "signature": representative.execution_signature or "",
            "candidate_count": len(candidates),
            "candidate_sql": [candidate.sql for candidate in candidates],
            "representative_sql": representative.sql,
            "representative_score": round(representative.score, 4),
            "max_score": max(candidate.score for candidate in candidates),
            "result_summary": dict(representative.result_summary),
            "referenced_tables": referenced_tables,
            "referenced_columns": {
                table: sorted(columns)
                for table, columns in sorted(columns_by_table.items())
            },
        }

    def _anchor_from_cluster(self, cluster: dict[str, Any]) -> dict[str, Any]:
        return {
            "cluster_id": cluster["cluster_id"],
            "sql": cluster["representative_sql"],
            "signature": cluster["signature"],
            "result_summary": cluster["result_summary"],
            "referenced_tables": cluster["referenced_tables"],
            "referenced_columns": cluster["referenced_columns"],
        }

    def _cluster_id(self, signature: str) -> str:
        digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:10]
        return f"eca_{digest}"


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "columns": [],
            "preview": [],
            "aggregate_features": {},
        }
    columns = list(rows[0].keys())
    numeric_totals: dict[str, float] = {}
    for column in columns:
        values = [row.get(column) for row in rows]
        numeric_values = [value for value in values if isinstance(value, int | float)]
        if numeric_values:
            numeric_totals[column] = float(sum(numeric_values))
    return {
        "row_count": len(rows),
        "columns": columns,
        "preview": rows[:3],
        "aggregate_features": numeric_totals,
    }


def stable_result_signature(rows: list[dict[str, Any]]) -> str:
    summary = summarize_rows(rows)
    payload = {
        "row_count": summary["row_count"],
        "columns": summary["columns"],
        "preview": summary["preview"],
        "aggregate_features": summary["aggregate_features"],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
