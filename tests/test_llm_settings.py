from evosql_platform.app.llm_settings import LLMSettingsStore


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
