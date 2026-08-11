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


@pytest.mark.parametrize(
    "content",
    [
        "workspace: not-a-mapping\n",
        "security:\n  redact_secrets: false\n",
        "permissions:\n  misspelled_permission: true\n",
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
