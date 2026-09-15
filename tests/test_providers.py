"""Offline unit tests for aicli.providers — no network calls."""

from aicli.config import ConfigError
from aicli.providers import (
    OpenAIProvider,
    OllamaProvider,
    OpenRouterProvider,
    _parse_sse_line,
    get_provider,
)


def test_parse_sse_line_ignores_non_data():
    assert _parse_sse_line("event: message") is None


def test_parse_sse_line_ignores_done_sentinel():
    assert _parse_sse_line("data: [DONE]") is None


def test_parse_sse_line_parses_json():
    assert _parse_sse_line('data: {"a": 1}') == {"a": 1}


def test_get_provider_ollama():
    prov = get_provider("ollama")
    assert isinstance(prov, OllamaProvider)
    assert prov.name == "ollama"


def test_get_provider_openai_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    try:
        get_provider("openai")
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError when OPENAI_API_KEY missing")


def test_get_provider_openrouter_requires_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        get_provider("openrouter")
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError when OPENROUTER_API_KEY missing")


def test_get_provider_unknown():
    try:
        get_provider("bogus")
    except ConfigError:
        pass
    else:
        raise AssertionError("expected ConfigError for unknown provider")


def test_openai_base_urls():
    assert OpenAIProvider.base_url == "https://api.openai.com/v1"
    assert OpenRouterProvider.base_url == "https://openrouter.ai/api/v1"
