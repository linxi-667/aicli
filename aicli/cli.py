"""Command-line interface for aicli.

Commands
--------
- ``chat``   single-shot or interactive chat session
- ``models`` list available models for a provider
"""

from __future__ import annotations

import sys

import click
import httpx

from . import __version__
from .config import ConfigError, default_model, default_provider
from .providers import get_provider

_EXIT_WORDS = {"exit", "quit", "bye"}


@click.group()
@click.version_option(__version__, prog_name="aicli")
def main() -> None:
    """aicli — a local-first AI assistant CLI (Ollama / OpenAI / OpenRouter)."""


@main.command()
@click.argument("prompt", required=False)
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "openrouter"]),
    default=None,
    help="Provider to use (default: AICLI_PROVIDER or ollama).",
)
@click.option("--model", default=None, help="Model name (default: per-provider).")
@click.option("--no-stream", is_flag=True, help="Disable streaming output.")
def chat(prompt: str | None, provider: str | None, model: str | None, no_stream: bool) -> None:
    """Chat with an AI assistant. Interactive REPL when PROMPT is omitted."""
    try:
        prov = get_provider(provider or default_provider(), model=model)
    except ConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)

    if prompt:
        _run_once(prov, prompt, stream=not no_stream)
    else:
        _run_interactive(prov, stream=not no_stream)


@main.command()
@click.option(
    "--provider",
    type=click.Choice(["ollama", "openai", "openrouter"]),
    default=None,
    help="Provider to use (default: AICLI_PROVIDER or ollama).",
)
@click.option("--model", default=None, help="Show models for this default model (informational).")
def models(provider: str | None, model: str | None) -> None:
    """List available models from a provider."""
    try:
        prov = get_provider(provider or default_provider(), model=model)
        names = prov.list_models()
    except ConfigError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except httpx.HTTPError as exc:
        click.echo(f"Error: cannot reach {prov.name}: {exc}", err=True)
        sys.exit(1)

    click.echo(f"[{prov.name}] {len(names)} model(s):")
    for name in names:
        click.echo(f"  - {name}")


def _run_once(prov, prompt: str, stream: bool) -> None:
    messages = [{"role": "user", "content": prompt}]
    try:
        for chunk in prov.chat(messages, stream=stream):
            sys.stdout.write(chunk)
            sys.stdout.flush()
    except httpx.HTTPError as exc:
        click.echo(f"\nError: {exc}", err=True)
        sys.exit(1)
    sys.stdout.write("\n")


def _run_interactive(prov, stream: bool) -> None:
    click.echo(
        f"Interactive chat with {prov.name} ({prov.model}). "
        "Type 'exit'/'quit' or Ctrl-C to leave."
    )
    messages: list[dict] = []
    while True:
        try:
            prompt = click.prompt("you")
        except (EOFError, KeyboardInterrupt):
            break
        if prompt.strip().lower() in _EXIT_WORDS:
            break
        if not prompt.strip():
            continue

        messages.append({"role": "user", "content": prompt})
        sys.stdout.write("ai: ")
        reply_parts: list[str] = []
        try:
            for chunk in prov.chat(messages, stream=stream):
                sys.stdout.write(chunk)
                sys.stdout.flush()
                reply_parts.append(chunk)
        except httpx.HTTPError as exc:
            click.echo(f"\nError: {exc}", err=True)
            break
        sys.stdout.write("\n")
        messages.append({"role": "assistant", "content": "".join(reply_parts)})


if __name__ == "__main__":
    main()
