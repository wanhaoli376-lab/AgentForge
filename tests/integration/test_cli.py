from collections import deque
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentforge.cli import app
from agentforge.llm.client import LLMRequest, OpenAILLMClient

runner = CliRunner()


def _script_openai(
    monkeypatch: pytest.MonkeyPatch,
    *responses: str,
) -> None:
    scripted = deque(responses)

    def generate(_client: OpenAILLMClient, _request: LLMRequest) -> str:
        return scripted.popleft()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value-that-must-not-leak")
    monkeypatch.setattr(OpenAILLMClient, "generate", generate)


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


def test_version_reports_the_installed_package_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0a1"


def test_doctor_reports_capabilities_without_exposing_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    openai_key = "sk-doctor-secret-that-must-not-leak"
    github_token = "github_pat_doctor-secret-that-must-not-leak"  # noqa: S105
    monkeypatch.setenv("OPENAI_API_KEY", openai_key)
    monkeypatch.setenv("GITHUB_TOKEN", github_token)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Skills: 4" in result.stdout
    assert "Plugins: 4" in result.stdout
    assert "OPENAI_API_KEY: present" in result.stdout
    assert "GITHUB_TOKEN: present" in result.stdout
    assert "shell_execute=False" in result.stdout
    assert openai_key not in result.stdout
    assert github_token not in result.stdout


def test_doctor_reports_the_selected_provider_without_exposing_its_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    custom_key = "custom-provider-secret-that-must-not-leak"
    monkeypatch.setenv("CUSTOM_LLM_API_KEY", custom_key)
    config_path = tmp_path / "agentforge.yaml"
    config_path.write_text(
        """agent:
  model: provider-model
  api_mode: chat_completions
  base_url: https://provider.example/v1
  api_key_env: CUSTOM_LLM_API_KEY
""",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["--config", str(config_path), "doctor"])

    assert result.exit_code == 0
    assert "LLM model: provider-model" in result.stdout
    assert "LLM API mode: chat_completions" in result.stdout
    assert "LLM base URL: https://provider.example/v1" in result.stdout
    assert "CUSTOM_LLM_API_KEY: present" in result.stdout
    assert custom_key not in result.stdout


def test_inspection_commands_list_builtin_skills_and_plugins() -> None:
    skills = runner.invoke(app, ["skills", "list"])
    plugins = runner.invoke(app, ["plugins", "list"])

    assert skills.exit_code == 0
    assert "repository-summary 0.1.0" in skills.stdout
    assert "github-maintainer 0.1.0" in skills.stdout
    assert plugins.exit_code == 0
    assert "filesystem - actions:" in plugins.stdout
    assert "github - actions:" in plugins.stdout


def test_run_can_emit_a_structured_success_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _script_openai(
        monkeypatch,
        '{"skills": []}',
        '{"rationale": "No tools needed", "steps": []}',
        "The task completed safely.",
    )

    result = runner.invoke(app, ["run", "answer without tools", "--json"])

    assert result.exit_code == 0
    assert '"ok": true' in result.stdout
    assert '"answer": "The task completed safely."' in result.stdout


def test_interactive_mode_skips_blank_input_then_runs_a_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _script_openai(
        monkeypatch,
        '{"skills": []}',
        '{"rationale": "No tools needed", "steps": []}',
        "Interactive answer.",
    )

    result = runner.invoke(app, [], input="\nanswer this\nquit\n")

    assert result.exit_code == 0
    assert "Interactive answer." in result.stdout
