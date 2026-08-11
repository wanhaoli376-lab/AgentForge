from pathlib import Path

from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.security.permissions import Permission, PermissionManager


def test_filesystem_plugin_reads_a_workspace_file(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("hello AgentForge", encoding="utf-8")
    context = PluginContext(
        workspace_root=tmp_path,
        permissions=PermissionManager({Permission.FILESYSTEM_READ}),
    )

    result = FilesystemPlugin().execute("read", {"path": "notes.txt"}, context)

    assert result.ok is True
    assert result.data == {
        "path": "notes.txt",
        "content": "hello AgentForge",
        "truncated": False,
    }
