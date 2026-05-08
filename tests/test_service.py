from evosql_platform.app.main import get_query_result, service as api_service
from evosql_platform.app.service import QueryService


def test_campus_query_returns_rows() -> None:
    service = QueryService()
    service.qwen_client.api_key = ""
    task = service.create_query(
        session_id="test-session-1",
        question="统计各学院当前学生人数",
        user_id="tester",
        role="admin",
        domain="campus",
        llm_mode="mock",
    )
    assert task.status == "completed"
    assert task.result.final_sql
    assert task.result.result_rows


def test_clarification_flow() -> None:
    service = QueryService()
    service.qwen_client.api_key = ""
    task = service.create_query(
        session_id="test-session-2",
        question="查看近三年项目趋势",
        user_id="tester",
        role="admin",
        domain="campus",
        llm_mode="mock",
    )
    assert task.status == "clarification_required"
    next_task = service.followup(task.task_id, "国家级项目")
    assert next_task.status == "completed"
    assert next_task.result.result_rows


def test_query_result_api_includes_eca_visualization_fields() -> None:
    task = api_service.create_query(
        session_id="test-session-eca-api",
        question="统计各学院当前学生人数",
        user_id="tester",
        role="admin",
        domain="campus",
        llm_mode="mock",
    )

    payload = get_query_result(task.task_id)

    assert payload["trace_steps"]
    assert payload["context_snapshots"]
    assert payload["cluster_records"]
    assert payload["selection_rationale"]["selected_sql"] == payload["final_sql"]
