from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp

from evosql_platform.models import SafetyResult


class SQLSafetyInterceptor:
    def __init__(self, allowed_tables: set[str] | None = None, max_rows: int = 200) -> None:
        self.allowed_tables = allowed_tables or set()
        self.max_rows = max_rows

    def validate(self, sql: str) -> SafetyResult:
        checks: list[dict[str, Any]] = []
        statements = sqlglot.parse(sql, read="sqlite")
        checks.append({"name": "single_statement", "ok": len(statements) == 1})
        if len(statements) != 1:
            return SafetyResult(False, checks, reason="Only one SQL statement is allowed.")

        statement = statements[0]
        readonly = isinstance(statement, (exp.Select, exp.Subquery, exp.Union, exp.Intersect, exp.Except))
        if isinstance(statement, exp.With) and isinstance(statement.this, exp.Select):
            readonly = True
        checks.append({"name": "read_only", "ok": readonly})
        if not readonly:
            return SafetyResult(False, checks, reason="Only read-only SELECT queries are allowed.")

        table_nodes = list(statement.find_all(exp.Table))
        used_tables = {node.name for node in table_nodes if node.name}
        allowed = (not self.allowed_tables) or used_tables.issubset(self.allowed_tables)
        checks.append({"name": "table_permission", "ok": allowed, "used_tables": sorted(used_tables)})
        if not allowed:
            return SafetyResult(False, checks, reason="SQL references unauthorized tables.")

        limit_clause = statement.args.get("limit")
        limit_ok = True
        if limit_clause is not None:
            try:
                limit_value = int(limit_clause.expression.name)
                limit_ok = limit_value <= self.max_rows
            except Exception:
                limit_ok = False
        checks.append({"name": "limit_guard", "ok": limit_ok})
        if not limit_ok:
            return SafetyResult(False, checks, reason=f"LIMIT exceeds max rows {self.max_rows}.")

        normalized_sql = statement.sql(dialect="sqlite")
        return SafetyResult(True, checks, normalized_sql=normalized_sql)

