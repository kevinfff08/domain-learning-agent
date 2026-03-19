from __future__ import annotations

from src.llm import provider_client as pc


def _clear_llm_env(monkeypatch) -> None:
    for name in (
        "LLM_PROVIDER",
        "LLM_MODE",
        "LLM_MODEL",
        "LLM_PROXY_URL",
        "OPENAI_BASE_URL",
        "ANTHROPIC_API_KEY",
        "OPENAI_API_KEY",
        "LLM_MAX_TOKENS",
        "LLM_MAX_CONTINUATIONS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_resolve_llm_provider_defaults_to_anthropic(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert pc.resolve_llm_provider() == "anthropic"


def test_resolve_llm_provider_from_model(monkeypatch):
    _clear_llm_env(monkeypatch)
    assert pc.resolve_llm_provider(model="gpt-4.1") == "openai"
    assert pc.resolve_llm_provider(model="claude-sonnet-4-20250514") == "anthropic"


def test_resolve_llm_api_key_uses_provider_specific_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    assert pc.resolve_llm_api_key(provider="openai", model="gpt-4.1") == "sk-proj-test"
    assert (
        pc.resolve_llm_api_key(provider="anthropic", model="claude-sonnet-4-20250514")
        == "sk-ant-test"
    )


def test_resolve_llm_base_url_normalizes_openai(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/openai")

    assert (
        pc.resolve_llm_base_url(provider="openai", model="gpt-4.1")
        == "https://example.com/openai/v1"
    )
    assert (
        pc.resolve_llm_base_url(
            provider="openai",
            model="gpt-4.1",
            base_url="https://proxy.local/v1",
        )
        == "https://proxy.local/v1"
    )


def test_is_llm_ready_respects_mode_and_provider(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")

    assert pc.is_llm_ready(provider="openai", model="gpt-4.1", mode="api-key") is True
    assert pc.is_llm_ready(provider="anthropic", model="claude-sonnet-4-20250514", mode="api-key") is False
    assert pc.is_llm_ready(provider="anthropic", model="claude-sonnet-4-20250514", mode="setup-token") is True


def test_llm_client_builds_openai_client(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-test")

    class DummyOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(pc, "OpenAI", DummyOpenAI)

    client = pc.LLMClient(model="gpt-4.1")

    assert isinstance(client.client, DummyOpenAI)
    assert client.client.kwargs["api_key"] == "sk-proj-test"


def test_llm_client_builds_anthropic_client(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

    class DummyAnthropic:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(pc, "Anthropic", DummyAnthropic)

    client = pc.LLMClient(model="claude-sonnet-4-20250514")

    assert isinstance(client.client, DummyAnthropic)
    assert client.client.kwargs["api_key"] == "sk-ant-test"
