from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("EVOSQL_DATA_DIR", ROOT / "data")).resolve()
BIRD_DIR = DATA_DIR / "dev"
CAMPUS_DIR = DATA_DIR / "campus"
AUDIT_LOG_PATH = DATA_DIR / "audit_logs.jsonl"
RUNTIME_CONFIG_DB_PATH = DATA_DIR / "runtime_config.sqlite"
MAX_SQL_ROWS = 200
DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_ITERATIONS = 3
DEFAULT_SAMPLE_SIZE = 6
DEFAULT_TOP_K = 2
