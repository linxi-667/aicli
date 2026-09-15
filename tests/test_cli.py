"""Offline CLI tests using click.testing.CliRunner."""

from click.testing import CliRunner

from aicli.cli import main


def test_version_output():
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_help_output():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "chat" in result.output
    assert "models" in result.output


def test_models_invalid_provider_rejected():
    runner = CliRunner()
    result = runner.invoke(main, ["models", "--provider", "bogus"])
    assert result.exit_code != 0


def test_chat_invalid_provider_rejected():
    runner = CliRunner()
    result = runner.invoke(main, ["chat", "--provider", "bogus", "hi"])
    assert result.exit_code == 2
    assert "is not one of" in result.output


def test_chat_missing_key_reports_clean_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, ["chat", "--provider", "openai", "hi"])
    assert result.exit_code == 1
    assert "No API key found" in result.output
