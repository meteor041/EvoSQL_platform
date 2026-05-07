from __future__ import annotations

from collections import defaultdict

from sqlglot import exp, parse_one

from evosql_platform.models import CandidateSQL


def extract_references(sql: str) -> tuple[list[str], list[str]]:
    try:
        tree = parse_one(sql, read="sqlite")
    except Exception:
        return [], []
    tables = sorted({node.name for node in tree.find_all(exp.Table) if node.name})
    columns = []
    for node in tree.find_all(exp.Column):
        if node.table:
            columns.append(f"{node.table}.{node.name}")
        elif node.name:
            columns.append(node.name)
    return tables, sorted(set(columns))


class SCRRefiner:
    def refine(self, candidates: list[CandidateSQL]) -> tuple[set[str], list[dict[str, str]]]:
        tables: set[str] = set()
        for candidate in candidates:
            tables.update(candidate.referenced_tables)
        return tables, []


class ECARefiner:
    def refine(self, candidates: list[CandidateSQL], top_k: int) -> tuple[set[str], list[dict[str, str]], CandidateSQL | None]:
        clusters: dict[str, list[CandidateSQL]] = defaultdict(list)
        for candidate in candidates:
            if candidate.error:
                continue
            clusters[candidate.execution_signature or "error"].append(candidate)
        if not clusters:
            return set(), [], None
        ordered = sorted(clusters.values(), key=lambda items: (-len(items), -max(item.score for item in items)))
        anchors: list[dict[str, str]] = []
        tables: set[str] = set()
        best = ordered[0][0]
        for cluster in ordered[:top_k]:
            representative = max(cluster, key=lambda item: item.score)
            tables.update(representative.referenced_tables)
            anchors.append({"sql": representative.sql, "signature": representative.execution_signature or ""})
        return tables, anchors, best
