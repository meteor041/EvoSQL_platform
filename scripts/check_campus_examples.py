from __future__ import annotations

import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "campus" / "campus.sqlite"
QA_PATH = ROOT / "data" / "campus" / "campus_qa.json"

EXAMPLE_QUESTIONS = [
    "统计各学院当前学生人数",
    "各专业平均成绩排名",
    "本月科研项目经费趋势",
    "近一年课程挂科率分布",
    "论文数量最高的教师 Top 5",
    "本学期选课人数最多的课程",
    "各学院师生比对比",
    "各学院科研经费排名",
    "近三年一区论文趋势",
    "各学院奖励惩罚记录对比",
]


def main() -> None:
    qa_items = json.loads(QA_PATH.read_text(encoding="utf-8"))
    sql_by_question = {item["question"]: item["sql"] for item in qa_items if "sql" in item}
    missing = [question for question in EXAMPLE_QUESTIONS if question not in sql_by_question]
    if missing:
        raise SystemExit(f"Missing QA SQL for examples: {missing}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        for question in EXAMPLE_QUESTIONS:
            rows = conn.execute(sql_by_question[question]).fetchall()
            if not rows:
                raise SystemExit(f"No rows returned for example: {question}")
            print(f"{question}: {len(rows)} rows")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
