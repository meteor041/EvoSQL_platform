from evosql_platform.app.service import QueryService


def test_campus_query_returns_rows() -> None:
    service = QueryService()
    task = service.create_query(
        session_id="test-session-1",
        question="统计各学院当前学生人数",
        user_id="tester",
        role="admin",
        domain="campus",
    )
    assert task.status == "completed"
    assert task.result.final_sql
    assert task.result.result_rows


def test_clarification_flow() -> None:
    service = QueryService()
    task = service.create_query(
        session_id="test-session-2",
        question="查看近三年项目趋势",
        user_id="tester",
        role="admin",
        domain="campus",
    )
    assert task.status == "clarification_required"
    next_task = service.followup(task.task_id, "国家级项目")
    assert next_task.status == "completed"
    assert next_task.result.result_rows
