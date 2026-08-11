from pathlib import Path

from agentforge.plugins.base import PluginContext
from agentforge.plugins.shell import ShellPlugin
from agentforge.security.permissions import Permission, PermissionManager


def test_shell_plugin_rejects_injection_without_spawning_process(tmp_path: Path) -> None:
    plugin = ShellPlugin(allowed_commands={"git", "pytest", "python"})
    context = PluginContext(
        tmp_path,
        PermissionManager({Permission.SHELL_EXECUTE}),
    )

    result = plugin.execute(
        "run",
        {"argv": ["pytest", ";", "cat", "~/.ssh/id_rsa"]},
        context,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "policy_violation"


def test_shell_plugin_runs_an_allowlisted_argv_without_a_shell(tmp_path: Path) -> None:
    plugin = ShellPlugin(allowed_commands={"python"})
    context = PluginContext(
        tmp_path,
        PermissionManager({Permission.SHELL_EXECUTE}),
    )

    result = plugin.execute("run", {"argv": ["python", "--version"]}, context)

    assert result.ok is True
    assert result.data["exit_code"] == 0
    assert "Python" in f"{result.data['stdout']}{result.data['stderr']}"
    assert result.data["timed_out"] is False
