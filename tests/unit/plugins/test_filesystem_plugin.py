from pathlib import Path

from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.security.permissions import Permission, PermissionManager


def _context(workspace: Path, *permissions: Permission) -> PluginContext:
    return PluginContext(
        workspace_root=workspace,
        permissions=PermissionManager(set(permissions)),
    )


def test_filesystem_plugin_reads_a_workspace_file(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("hello AgentForge", encoding="utf-8")
    context = _context(tmp_path, Permission.FILESYSTEM_READ)

    result = FilesystemPlugin().execute("read", {"path": "notes.txt"}, context)

    assert result.ok is True
    assert result.data == {
        "path": "notes.txt",
        "content": "hello AgentForge",
        "truncated": False,
    }


def test_filesystem_plugin_truncates_read_output_at_the_plugin_limit(tmp_path: Path) -> None:
    (tmp_path / "long.txt").write_text("0123456789", encoding="utf-8")

    result = FilesystemPlugin(max_output_chars=5).execute(
        "read",
        {"path": "long.txt"},
        _context(tmp_path, Permission.FILESYSTEM_READ),
    )

    assert result.ok is True
    assert result.data["content"] == "01234"
    assert result.data["truncated"] is True


def test_filesystem_plugin_creates_overwrites_and_deletes_a_file(tmp_path: Path) -> None:
    context = _context(
        tmp_path,
        Permission.FILESYSTEM_WRITE,
        Permission.FILESYSTEM_DELETE,
    )
    plugin = FilesystemPlugin()

    created = plugin.execute(
        "create",
        {"path": "result.txt", "content": "first"},
        context,
    )
    overwritten = plugin.execute(
        "write",
        {"path": "result.txt", "content": "updated"},
        context,
    )
    deleted = plugin.execute("delete", {"path": "result.txt"}, context)

    assert created.ok is True
    assert created.data["bytes_written"] == 5
    assert overwritten.ok is True
    assert overwritten.data["bytes_written"] == 7
    assert deleted.data == {"path": "result.txt", "deleted": True}
    assert not (tmp_path / "result.txt").exists()


def test_filesystem_plugin_lists_recursively_with_a_bounded_result(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "one.txt").write_text("one", encoding="utf-8")
    (tmp_path / "two.txt").write_text("two", encoding="utf-8")

    result = FilesystemPlugin().execute(
        "list",
        {"path": ".", "recursive": True, "max_entries": 2},
        _context(tmp_path, Permission.FILESYSTEM_READ),
    )

    assert result.ok is True
    assert len(result.data["entries"]) == 2
    assert result.data["entries"][0] == {"path": "nested", "type": "directory"}
    assert result.data["truncated"] is True


def test_filesystem_plugin_deletes_an_empty_directory_but_rejects_recursive_delete(
    tmp_path: Path,
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    populated = tmp_path / "populated"
    populated.mkdir()
    (populated / "keep.txt").write_text("keep", encoding="utf-8")
    context = _context(tmp_path, Permission.FILESYSTEM_DELETE)
    plugin = FilesystemPlugin()

    deleted = plugin.execute("delete", {"path": "empty"}, context)
    rejected = plugin.execute(
        "delete",
        {"path": "populated", "recursive": True},
        context,
    )

    assert deleted.ok is True
    assert not empty.exists()
    assert rejected.ok is False
    assert rejected.error is not None
    assert rejected.error.code == "policy_violation"
    assert populated.exists()


def test_filesystem_plugin_returns_safe_errors_for_wrong_path_types(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("content", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    context = _context(tmp_path, Permission.FILESYSTEM_READ)
    plugin = FilesystemPlugin()

    read_directory = plugin.execute("read", {"path": "folder"}, context)
    list_file = plugin.execute("list", {"path": "file.txt"}, context)

    assert read_directory.ok is False
    assert read_directory.error is not None
    assert read_directory.error.code == "policy_violation"
    assert list_file.ok is False
    assert list_file.error is not None
    assert list_file.error.code == "policy_violation"
