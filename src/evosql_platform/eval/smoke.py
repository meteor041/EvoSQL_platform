from __future__ import annotations

import json

from evosql_platform.app.service import QueryService


def main() -> None:
    service = QueryService()
    campus_task = service.create_query(
        session_id="smoke-campus",
        question="统计各学院当前学生人数",
        user_id="smoke",
        role="admin",
        domain="campus",
    )
    bird_task = service.create_query(
        session_id="smoke-bird",
        question="Run BIRD sample 0",
        user_id="smoke",
        role="admin",
        domain="bird",
    )
    print(
        "campus:",
        json.dumps(
            {
                "status": campus_task.status,
                "sql": campus_task.result.final_sql,
                "rows": campus_task.result.result_rows[:3],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    print(
        "bird:",
        json.dumps(
            {
                "status": bird_task.status,
                "sql": bird_task.result.final_sql,
                "rows": bird_task.result.result_rows[:3],
            },
            ensure_ascii=False,
            indent=2,
        ),
    )


if __name__ == "__main__":
    main()
