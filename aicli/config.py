"""Configuration handling for aicli.

API keys are read from environment variables or a local ``.env`` file
(loaded via python-dotenv). No key is required to talk to a local Ollama
instance.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Provider identifiers
PROVIDER_OLLAMA = "ollama"
PROVIDER_OPENAI = "openai"
PROVIDER_OPENROUTER = "openrouter"

PROVIDERS = (PROVIDER_OLLAMA, PROVIDER_OPENAI, PROVIDER_OPENROUTER)

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

_DEFAULT_MODELS = {
    PROVIDER_OLLAMA: "llama3.2",
    PROVIDER_OPENAI: "gpt-4o-mini",
    PROVIDER_OPENROUTER: "meta-llama/llama-3.3-70b-instruct",
}

_ENV_KEY_MAP = {
    PROVIDER_OPENAI: "OPENAI_API_KEY",
    PROVIDER_OPENROUTER: "OPENROUTER_API_KEY",
}


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


def default_provider() -> str:
    """Return the default provider (env ``AICLI_PROVIDER``, else ``ollama``)."""
    return os.getenv("AICLI_PROVIDER", PROVIDER_OLLAMA).strip() or PROVIDER_OLLAMA


def get_api_key(provider: str) -> str | None:
    """Return the API key for *provider*, or ``None`` if not configured."""
    env = _ENV_KEY_MAP.get(provider)
    if env is None:
        return None
    key = os.getenv(env, "").strip()
    return key or None


def require_api_key(provider: str) -> str:
    """Return the API key for *provider* or raise :class:`ConfigError`."""
    key = get_api_key(provider)
    if not key:
        env = _ENV_KEY_MAP.get(provider)
        raise ConfigError(
            f"No API key found for provider '{provider}'. "
            f"Set the {env} environment variable or add it to your .env file."
        )
    return key


def get_ollama_base_url() -> str:
    """Return the Ollama base URL, with no trailing slash."""
    return os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/") or DEFAULT_OLLAMA_BASE_URL


def default_model(provider: str) -> str:
    """Return a sensible default model for *provider* (override via ``AICLI_MODEL``)."""
    env_model = os.getenv("AICLI_MODEL", "").strip()
    if env_model:
        return env_model
    if provider not in _DEFAULT_MODELS:
        raise ConfigError(f"Unknown provider '{provider}'. Choose from: {', '.join(PROVIDERS)}")
    return _DEFAULT_MODELS[provider]
