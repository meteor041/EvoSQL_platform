from evosql_platform.app.llm_settings import LLMSettingsStore
from evosql_platform.app.service import QueryService
from evosql_platform.clients.mock import DemoCampusLLMClient


def test_llm_settings_store_persists_configs(tmp_path) -> None:
    db_path = tmp_path / "settings.sqlite"
    store = LLMSettingsStore(db_path)
    initial = store.list_configs()
    assert len(initial) == 2
    assert any(item["isDefault"] for item in initial)

    created = store.create_config(
        {
            "display_name": "Campus Qwen",
            "provider": "openrouter",
            "model": "qwen/test",
            "base_url": "https://example.test/chat/completions",
            "api_key": "sk-test-secret",
            "temperature": 0.2,
            "timeout_seconds": 30,
            "max_retries": 1,
            "scope": "campus",
            "notes": "test",
        }
    )
    assert created["displayName"] == "Campus Qwen"
    assert created["apiKeyMasked"] == "sk-t••••cret"

    reopened = LLMSettingsStore(db_path)
    configs = reopened.list_configs()
    assert any(item["id"] == created["id"] for item in configs)


def test_query_service_resolves_configured_mock_client(tmp_path) -> None:
    service = QueryService()
    service.llm_settings_store = LLMSettingsStore(tmp_path / "settings.sqlite")
    client, source_label, requires_api_key = service._resolve_campus_client("config:mock-campus")
    assert isinstance(client, DemoCampusLLMClient)
    assert source_label == "mock"
    assert requires_api_key is False
