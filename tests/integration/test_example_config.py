from pathlib import Path

from agentforge.config.loader import load_config


def test_published_example_config_is_valid_and_least_privilege() -> None:
    config = load_config(Path("agentforge.example.yaml"))

    assert config.workspace.root == Path.cwd().resolve()
    assert config.permissions.filesystem_read is True
    assert config.permissions.filesystem_write is False
    assert config.permissions.shell_execute is False
    assert config.permissions.python_execute is False
    assert config.permissions.network_access is False
    assert config.permissions.github_write is False
