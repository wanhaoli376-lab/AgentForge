"""Workspace-confined filesystem plugin."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from agentforge.exceptions import PluginExecutionError, PolicyViolationError
from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.path_policy import PathPolicy
from agentforge.security.permissions import Permission


class PathArguments(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(default=".", min_length=1, max_length=4_096)


class ListArguments(PathArguments):
    recursive: bool = False
    max_entries: int = Field(default=200, ge=1, le=2_000)


class ReadArguments(PathArguments):
    max_chars: int | None = Field(default=None, ge=1_000, le=1_000_000)


class WriteArguments(PathArguments):
    content: str = Field(max_length=1_000_000)


class DeleteArguments(PathArguments):
    recursive: bool = False


class FilesystemPlugin(Plugin):
    """Read and optionally mutate files below the configured workspace."""

    name = "filesystem"
    description = "List, read, create, write, or delete workspace files."
    action_models: ClassVar = {
        "list": ListArguments,
        "read": ReadArguments,
        "write": WriteArguments,
        "create": WriteArguments,
        "delete": DeleteArguments,
    }
    action_permissions: ClassVar = {
        "list": frozenset({Permission.FILESYSTEM_READ}),
        "read": frozenset({Permission.FILESYSTEM_READ}),
        "write": frozenset({Permission.FILESYSTEM_WRITE}),
        "create": frozenset({Permission.FILESYSTEM_WRITE}),
        "delete": frozenset({Permission.FILESYSTEM_DELETE}),
    }

    def __init__(self, *, max_output_chars: int = 50_000) -> None:
        self._max_output_chars = max_output_chars

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        policy = PathPolicy(context.workspace_root)
        try:
            if action == "read":
                return self._read(arguments, policy)
            if action == "list":
                return self._list(arguments, policy)
            if action in {"write", "create"}:
                return self._write(action, arguments, policy)
            if action == "delete":
                return self._delete(arguments, policy)
        except OSError as exc:
            raise PluginExecutionError(f"Filesystem operation failed: {exc}") from exc
        raise PluginExecutionError(f"Filesystem action was not dispatched: {action}")

    def _read(self, arguments: BaseModel, policy: PathPolicy) -> PluginResult:
        args = ReadArguments.model_validate(arguments.model_dump())
        path = policy.resolve(args.path, must_exist=True)
        if not path.is_file():
            raise PolicyViolationError("Read action requires a regular file")
        limit = min(args.max_chars or self._max_output_chars, self._max_output_chars)
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.read(limit + 1)
        truncated = len(content) > limit
        return PluginResult.success(
            {
                "path": policy.display(path),
                "content": content[:limit],
                "truncated": truncated,
            }
        )

    def _list(self, arguments: BaseModel, policy: PathPolicy) -> PluginResult:
        args = ListArguments.model_validate(arguments.model_dump())
        path = policy.resolve(args.path, must_exist=True)
        if not path.is_dir():
            raise PolicyViolationError("List action requires a directory")

        candidates = path.rglob("*") if args.recursive else path.iterdir()
        entries: list[dict[str, object]] = []
        truncated = False
        for candidate in sorted(candidates):
            try:
                safe_path = policy.resolve(policy.display(candidate))
            except (PolicyViolationError, ValueError):
                continue
            if len(entries) >= args.max_entries:
                truncated = True
                break
            entries.append(
                {
                    "path": policy.display(safe_path),
                    "type": "directory" if safe_path.is_dir() else "file",
                }
            )
        return PluginResult.success({"entries": entries, "truncated": truncated})

    def _write(
        self,
        action: str,
        arguments: BaseModel,
        policy: PathPolicy,
    ) -> PluginResult:
        args = WriteArguments.model_validate(arguments.model_dump())
        path = policy.resolve(args.path)
        if not path.parent.is_dir():
            raise PolicyViolationError("Parent directory does not exist")
        mode = "x" if action == "create" else "w"
        with path.open(mode, encoding="utf-8", newline="") as handle:
            handle.write(args.content)
        return PluginResult.success(
            {"path": policy.display(path), "bytes_written": len(args.content.encode("utf-8"))}
        )

    def _delete(self, arguments: BaseModel, policy: PathPolicy) -> PluginResult:
        args = DeleteArguments.model_validate(arguments.model_dump())
        path = policy.resolve(args.path, must_exist=True)
        if path == policy.workspace_root:
            raise PolicyViolationError("Deleting the workspace root is forbidden")
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir() and not args.recursive:
            path.rmdir()
        else:
            raise PolicyViolationError("Recursive directory deletion is not supported")
        return PluginResult.success({"path": args.path, "deleted": True})
