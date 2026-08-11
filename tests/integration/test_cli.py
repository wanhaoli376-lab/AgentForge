from typer.testing import CliRunner

from agentforge.cli import app

runner = CliRunner()


def test_help_describes_the_agentforge_cli() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "security-aware AI agent framework" in result.stdout


def test_run_reports_missing_openai_key_without_traceback(
    monkeypatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = runner.invoke(app, ["run", "summarize this repository"])

    assert result.exit_code == 2
    assert "OPENAI_API_KEY is not set" in result.output
    assert "Traceback" not in result.output


def test_interactive_mode_can_exit_cleanly() -> None:
    result = runner.invoke(app, [], input="quit\n")

    assert result.exit_code == 0
    assert "AgentForge interactive mode" in result.output
    assert "AgentForge >" in result.output
