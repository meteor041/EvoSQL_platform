from __future__ import annotations

from typing import Any


def recommend_chart(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"type": "table", "title": "No data"}
    columns = list(rows[0].keys())
    numeric_columns = []
    for column in columns:
        if all(isinstance(row.get(column), (int, float)) for row in rows if row.get(column) is not None):
            numeric_columns.append(column)
    if len(columns) >= 2 and numeric_columns:
        first = columns[0].lower()
        if any(token in first for token in ["date", "year", "month", "time"]):
            return {"type": "line", "x": columns[0], "y": numeric_columns[0], "title": f"{numeric_columns[0]} trend"}
        return {"type": "bar", "x": columns[0], "y": numeric_columns[0], "title": f"{numeric_columns[0]} by {columns[0]}"}
    return {"type": "table", "columns": columns}
