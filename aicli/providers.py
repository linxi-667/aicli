"""Provider adapters for Ollama, OpenAI, and OpenRouter.

Every provider exposes a small httpx-based interface::

    class Provider:
        name: str
        model: str
        def chat(self, messages, stream=True) -> Iterator[str]
        def list_models(self) -> list[str]

``chat`` streams text deltas as they arrive (or yields the full reply in one
chunk when ``stream=False``). ``messages`` is a list of ``{"role", "content"}``
dicts. All adapters are synchronous and dependency-light.
"""

from __future__ import annotations

import json
from typing import Iterator

import httpx

from .config import (
    ConfigError,
    PROVIDER_OPENAI,
    PROVIDER_OPENROUTER,
    default_model,
    get_ollama_base_url,
    require_api_key,
)

TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def _parse_sse_line(line: str) -> dict | None:
    """Parse a single SSE ``data:`` line into a JSON object (or ``None``).

    Returns ``None`` for non-data lines, empty payloads, and the
    ``[DONE]`` sentinel used by OpenAI-compatible streams.
    """
    line = line.strip()
    if not line.startswith("data:"):
        return None
    payload = line[len("data:") :].strip()
    if not payload or payload == "[DONE]":
        return None
    return json.loads(payload)


class Provider:
    """Base class for provider adapters."""

    name: str = "base"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or default_model(self.name)

    def chat(self, messages: list[dict], stream: bool = True) -> Iterator[str]:
        raise NotImplementedError

    def list_models(self) -> list[str]:
        raise NotImplementedError


class OllamaProvider(Provider):
    """Local Ollama via ``/api/chat`` (no API key required)."""

    name = "ollama"

    def __init__(self, model: str | None = None, base_url: str | None = None) -> None:
        super().__init__(model)
        self.base_url = (base_url or get_ollama_base_url()).rstrip("/")

    def chat(self, messages: list[dict], stream: bool = True) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": stream,
        }
        with httpx.stream(
            "POST", f"{self.base_url}/api/chat", json=payload, timeout=TIMEOUT
        ) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.strip():
                    continue
                data = json.loads(line)
                if not data.get("done") and data.get("message", {}).get("content"):
                    yield data["message"]["content"]

    def list_models(self) -> list[str]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            return sorted(m["name"] for m in resp.json().get("models", []))


class OpenAIProvider(Provider):
    """OpenAI-compatible chat completions with SSE streaming."""

    name = PROVIDER_OPENAI
    base_url = "https://api.openai.com/v1"

    def __init__(self, model: str | None = None) -> None:
        super().__init__(model)
        self.api_key = require_api_key(self.name)

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def chat(self, messages: list[dict], stream: bool = True) -> Iterator[str]:
        payload = {
            "model": self.model,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "stream": stream,
        }
        url = f"{self.base_url}/chat/completions"
        if stream:
            with httpx.stream(
                "POST", url, json=payload, headers=self._headers(), timeout=TIMEOUT
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    data = _parse_sse_line(line)
                    if not data:
                        continue
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    if delta.get("content"):
                        yield delta["content"]
        else:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(
                    url, json={**payload, "stream": False}, headers=self._headers(), timeout=TIMEOUT
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                yield content

    def list_models(self) -> list[str]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/models", headers=self._headers())
            resp.raise_for_status()
            return sorted(m["id"] for m in resp.json().get("data", []))


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter — same OpenAI wire format, different endpoint and key."""

    name = PROVIDER_OPENROUTER
    base_url = "https://openrouter.ai/api/v1"


_PROVIDER_CLASSES = {
    OllamaProvider.name: OllamaProvider,
    OpenAIProvider.name: OpenAIProvider,
    OpenRouterProvider.name: OpenRouterProvider,
}


def get_provider(name: str, model: str | None = None, **kwargs) -> Provider:
    """Instantiate a provider by name, raising :class:`ConfigError` if unknown."""
    cls = _PROVIDER_CLASSES.get(name)
    if cls is None:
        raise ConfigError(
            f"Unknown provider '{name}'. Choose from: {', '.join(sorted(_PROVIDER_CLASSES))}"
        )
    return cls(model=model, **kwargs)
