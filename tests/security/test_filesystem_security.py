import os
from pathlib import Path

import pytest

from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.security.permissions import Permission, PermissionManager


def _read_context(workspace: Path) -> PluginContext:
    return PluginContext(
        workspace_root=workspace,
        permissions=PermissionManager({Permission.FILESYSTEM_READ}),
    )


@pytest.mark.parametrize("requested", ["../../etc/passwd", "~/.ssh/id_rsa", ".env"])
def test_traversal_and_sensitive_home_paths_are_rejected(
    tmp_path: Path,
    requested: str,
) -> None:
    result = FilesystemPlugin().execute("read", {"path": requested}, _read_context(tmp_path))

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "policy_violation"


def test_symlink_cannot_escape_the_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private", encoding="utf-8")
    link = workspace / "escape.txt"
    try:
        os.symlink(outside, link)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    result = FilesystemPlugin().execute("read", {"path": "escape.txt"}, _read_context(workspace))

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "policy_violation"
