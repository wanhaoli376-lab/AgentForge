from pathlib import Path

import pytest

from agentforge.plugins.base import PluginContext
from agentforge.plugins.python import PythonPlugin
from agentforge.security.permissions import Permission, PermissionManager


def _python_context(workspace: Path) -> PluginContext:
    return PluginContext(
        workspace,
        PermissionManager({Permission.PYTHON_EXECUTE}),
    )


def test_python_plugin_runs_safe_code_in_a_child_process(tmp_path: Path) -> None:
    result = PythonPlugin(timeout=2).execute(
        "run",
        {"code": "print(sum([1, 2, 3]))"},
        _python_context(tmp_path),
    )

    assert result.ok is True
    assert result.data["exit_code"] == 0
    assert result.data["stdout"].strip() == "6"


@pytest.mark.parametrize(
    "code",
    [
        "import os; print(os.environ)",
        "print(open('../outside.txt').read())",
        "print((1).__class__.__mro__)",
    ],
)
def test_python_plugin_rejects_io_and_interpreter_escape_code(
    tmp_path: Path,
    code: str,
) -> None:
    result = PythonPlugin(timeout=2).execute(
        "run",
        {"code": code},
        _python_context(tmp_path),
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "policy_violation"


def test_python_plugin_enforces_timeout(tmp_path: Path) -> None:
    result = PythonPlugin(timeout=0.05).execute(
        "run",
        {"code": "while True:\n    pass"},
        _python_context(tmp_path),
    )

    assert result.ok is False
    assert result.error is not None and result.error.code == "process_timeout"
    assert result.data["timed_out"] is True
    assert result.data["exit_code"] != 0


def test_python_runtime_failure_keeps_diagnostics_and_reports_failure(tmp_path: Path) -> None:
    result = PythonPlugin(timeout=2).execute(
        "run",
        {"code": "print(1 / 0)"},
        _python_context(tmp_path),
    )

    assert result.ok is False
    assert result.error is not None and result.error.code == "process_failed"
    assert result.data["exit_code"] != 0
    assert "ZeroDivisionError" in result.data["stderr"]
