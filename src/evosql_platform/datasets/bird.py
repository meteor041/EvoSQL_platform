from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evosql_platform.config import BIRD_DIR


class BirdDatasetLoader:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or BIRD_DIR
        self.samples = json.loads((self.data_dir / "dev.json").read_text(encoding="utf-8"))
        tables_raw = json.loads((self.data_dir / "dev_tables.json").read_text(encoding="utf-8"))
        self.tables_by_db = {item["db_id"]: item for item in tables_raw}

    def get_sample(self, index: int) -> dict[str, Any]:
        return self.samples[index]

    def get_db_path(self, db_id: str) -> Path:
        return self.data_dir / "dev_databases" / "dev_databases" / db_id / (db_id + ".sqlite")

    def get_table_spec(self, db_id: str) -> dict[str, Any]:
        return self.tables_by_db[db_id]
