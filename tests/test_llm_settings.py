from evosql_platform.app.llm_settings import LLMSettingsStore
from evosql_platform.app.service import QueryService
from evosql_platform.clients.mock import DemoCampusLLMClient
from evosql_platform.clients.qwen import QwenClient
from evosql_platform.models import ContextState


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


def test_llm_settings_store_updates_configs_and_preserves_secret(tmp_path) -> None:
    store = LLMSettingsStore(tmp_path / "settings.sqlite")
    created = store.create_config(
        {
            "display_name": "ChatGPT",
            "provider": "openai-compatible",
            "model": "gpt-test",
            "base_url": "https://api.example.com",
            "api_key": "sk-original-secret",
            "temperature": 0.3,
            "timeout_seconds": 30,
            "max_retries": 1,
            "scope": "campus",
            "notes": "old",
        }
    )

    updated = store.update_config(
        created["id"],
        {
            "display_name": "ChatGPT Meteor",
            "provider": "openai-compatible",
            "model": "gpt-test-new",
            "base_url": "https://api.meteor041.com",
            "api_key": "",
            "temperature": 0.4,
            "timeout_seconds": 45,
            "max_retries": 2,
            "scope": "campus",
            "notes": "updated",
        },
    )

    private = store.get_private_config(created["id"])
    assert updated["displayName"] == "ChatGPT Meteor"
    assert updated["baseUrl"] == "https://api.meteor041.com"
    assert private["apiKey"] == "sk-original-secret"


def test_seeded_openrouter_qwen_can_be_deleted(tmp_path) -> None:
    store = LLMSettingsStore(tmp_path / "settings.sqlite")
    assert any(item["id"] == "openrouter-qwen" for item in store.list_configs())

    store.delete_config("openrouter-qwen")

    assert all(item["id"] != "openrouter-qwen" for item in store.list_configs())


def test_query_service_resolves_configured_mock_client(tmp_path) -> None:
    service = QueryService()
    service.llm_settings_store = LLMSettingsStore(tmp_path / "settings.sqlite")
    client, source_label, requires_api_key = service._resolve_campus_client("config:mock-campus")
    assert isinstance(client, DemoCampusLLMClient)
    assert source_label == "mock"
    assert requires_api_key is False


def test_openai_compatible_schema_linking_falls_back_to_heuristics() -> None:
    class BusyDeepSeekClient(QwenClient):
        def _request(self, *args, **kwargs) -> str:
            raise RuntimeError("DeepSeek request failed at https://api.deepseek.com/chat/completions: HTTP 503")

    client = BusyDeepSeekClient(
        model="deepseek-chat",
        api_key="sk-test",
        base_url="https://api.deepseek.com/chat/completions",
        provider_label="DeepSeek",
    )
    result = client.select_schema(
        ContextState(
            instruction="link",
            question="统计 students 人数",
            schema_subset={
                "tables": {
                    "students": {"columns": [{"name": "student_id", "type": "INTEGER"}]},
                    "courses": {"columns": [{"name": "course_id", "type": "INTEGER"}]},
                }
            },
        )
    )
    assert result["tables"] == ["students"]
    assert "DeepSeek schema linking request failed" in result["reasoning"]
    assert "OpenRouter" not in result["reasoning"]


def test_openai_compatible_base_url_expands_to_chat_completions() -> None:
    root_client = QwenClient(
        model="gpt-test",
        api_key="sk-test",
        base_url="https://api.meteor041.com",
        provider_label="ChatGPT",
    )
    full_client = QwenClient(
        model="gpt-test",
        api_key="sk-test",
        base_url="https://api.meteor041.com/v1/chat/completions",
        provider_label="ChatGPT",
    )

    assert root_client.base_url == "https://api.meteor041.com"
    assert root_client.request_url == "https://api.meteor041.com/v1/chat/completions"
    assert full_client.request_url == "https://api.meteor041.com/v1/chat/completions"
