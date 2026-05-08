from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class SchemaRegistry:
    def load_sqlite_schema(self, db_path: Path) -> dict[str, Any]:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        tables = {}
        try:
            table_names = [
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
                ).fetchall()
            ]
            for table_name in table_names:
                columns = conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                foreign_keys = conn.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
                tables[table_name] = {
                    "columns": [
                        {
                            "name": col[1],
                            "type": col[2],
                            "notnull": bool(col[3]),
                            "default": col[4],
                            "primary_key": bool(col[5]),
                        }
                        for col in columns
                    ],
                    "foreign_keys": [
                        {
                            "from": fk[3],
                            "to_table": fk[2],
                            "to_column": fk[4],
                        }
                        for fk in foreign_keys
                    ],
                }
        finally:
            conn.close()
        return {"tables": tables}

    def subset(self, schema: dict[str, Any], allowed_tables: list[str]) -> dict[str, Any]:
        if not allowed_tables:
            return schema
        return {"tables": {name: spec for name, spec in schema["tables"].items() if name in set(allowed_tables)}}

    def subset_columns(
        self,
        schema: dict[str, Any],
        allowed_tables: set[str],
        allowed_columns: dict[str, set[str]] | None = None,
    ) -> dict[str, Any]:
        if not allowed_tables:
            return schema
        allowed_columns = allowed_columns or {}
        tables: dict[str, Any] = {}
        for table_name, spec in schema.get("tables", {}).items():
            if table_name not in allowed_tables:
                continue
            column_names = allowed_columns.get(table_name, set())
            if not column_names:
                tables[table_name] = spec
                continue
            tables[table_name] = {
                **spec,
                "columns": [
                    column
                    for column in spec.get("columns", [])
                    if column.get("name") in column_names or column.get("primary_key")
                ],
                "foreign_keys": [
                    fk
                    for fk in spec.get("foreign_keys", [])
                    if fk.get("from") in column_names or fk.get("to_column") in column_names
                ],
            }
        return {"tables": tables}
