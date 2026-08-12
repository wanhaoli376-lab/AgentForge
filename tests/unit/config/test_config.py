from pathlib import Path

import pytest

from agentforge.config.loader import ConfigError, load_config


def test_default_config_uses_least_privilege(tmp_path: Path) -> None:
    config = load_config(workspace_root=tmp_path)

    assert config.workspace.root == tmp_path.resolve()
    assert config.permissions.filesystem_read is True
    assert config.permissions.filesystem_write is False
    assert config.permissions.filesystem_delete is False
    assert config.permissions.shell_execute is False
    assert config.permissions.python_execute is False
    assert config.permissions.network_access is False
    assert config.permissions.github_write is False
    assert config.agent.api_mode == "responses"
    assert config.agent.api_key_env == "OPENAI_API_KEY"
    assert config.agent.base_url is None


def test_config_accepts_an_openai_compatible_chat_provider(tmp_path: Path) -> None:
    path = tmp_path / "agentforge.yaml"
    path.write_text(
        """agent:
  model: qwen-plus
  api_mode: chat_completions
  base_url: https://dashscope.example/compatible-mode/v1
  api_key_env: DASHSCOPE_API_KEY
""",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.agent.model == "qwen-plus"
    assert config.agent.api_mode == "chat_completions"
    assert config.agent.base_url == "https://dashscope.example/compatible-mode/v1"
    assert config.agent.api_key_env == "DASHSCOPE_API_KEY"


def test_config_allows_plain_http_only_for_a_local_provider(tmp_path: Path) -> None:
    local = tmp_path / "local.yaml"
    local.write_text(
        "agent:\n  base_url: http://localhost:11434/v1\n  api_key_env: LOCAL_LLM_API_KEY\n",
        encoding="utf-8",
    )
    remote = tmp_path / "remote.yaml"
    remote.write_text(
        "agent:\n  base_url: http://provider.example/v1\n",
        encoding="utf-8",
    )

    assert load_config(local).agent.base_url == "http://localhost:11434/v1"
    with pytest.raises(ConfigError):
        load_config(remote)


@pytest.mark.parametrize(
    "content",
    [
        "workspace: not-a-mapping\n",
        "security:\n  redact_secrets: false\n",
        "permissions:\n  misspelled_permission: true\n",
        "agent:\n  api_key: secret-must-not-be-stored-here\n",
        "agent:\n  api_key_env: invalid-name-with-dashes\n",
    ],
)
def test_unsafe_or_malformed_config_is_rejected(tmp_path: Path, content: str) -> None:
    path = tmp_path / "agentforge.yaml"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(path)


def test_validation_error_does_not_echo_secret_value(tmp_path: Path) -> None:
    sensitive_value = "sk-do-not-repeat-this-value"
    path = tmp_path / "agentforge.yaml"
    path.write_text(
        f"agent:\n  model:\n    - {sensitive_value}\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as caught:
        load_config(path)

    assert sensitive_value not in str(caught.value)
    assert caught.value.__cause__ is None
