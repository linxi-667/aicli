"""Offline unit tests for aicli.config — no network, no API keys."""

from aicli.config import (
    DEFAULT_OLLAMA_BASE_URL,
    ConfigError,
    default_model,
    default_provider,
    get_api_key,
    get_ollama_base_url,
    require_api_key,
)


def test_get_api_key_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_api_key("openai") is None


def test_get_api_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert get_api_key("openai") == "sk-test"


def test_require_api_key_raises_when_missing(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        require_api_key("openrouter")
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError for missing key")


def test_ollama_needs_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert get_api_key("ollama") is None


def test_ollama_base_url_default(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    assert get_ollama_base_url() == DEFAULT_OLLAMA_BASE_URL


def test_ollama_base_url_custom(monkeypatch):
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/")
    assert get_ollama_base_url() == "http://127.0.0.1:11434"


def test_default_model_per_provider(monkeypatch):
    monkeypatch.delenv("AICLI_MODEL", raising=False)
    assert default_model("ollama") == "llama3.2"
    assert default_model("openai") == "gpt-4o-mini"


def test_default_model_override(monkeypatch):
    monkeypatch.setenv("AICLI_MODEL", "my-model")
    assert default_model("ollama") == "my-model"


def test_default_provider_env(monkeypatch):
    monkeypatch.setenv("AICLI_PROVIDER", "openai")
    assert default_provider() == "openai"
    monkeypatch.delenv("AICLI_PROVIDER", raising=False)
    assert default_provider() == "ollama"


def test_default_model_unknown_provider(monkeypatch):
    monkeypatch.delenv("AICLI_MODEL", raising=False)
    try:
        default_model("bogus")
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError for unknown provider")
