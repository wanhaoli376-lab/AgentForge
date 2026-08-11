"""Workspace confinement for all filesystem paths."""

from pathlib import Path

from agentforge.exceptions import PolicyViolationError


class PathPolicy:
    """Resolve paths once and reject traversal, absolute, and symlink escapes."""

    _SENSITIVE_PARTS = frozenset({".ssh", ".aws", ".git"})
    _SENSITIVE_NAMES = frozenset({".env", ".git-credentials", "id_rsa", "id_ed25519"})

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.expanduser().resolve()
        if not self.workspace_root.is_dir():
            raise PolicyViolationError("Workspace root must be an existing directory")

    def resolve(self, requested: str | Path, *, must_exist: bool = False) -> Path:
        """Return a canonical in-workspace path or reject it."""

        raw = Path(requested)
        if raw.is_absolute() or raw.drive:
            raise PolicyViolationError("Absolute filesystem paths are not allowed")
        if any(part in {"..", "~"} for part in raw.parts):
            raise PolicyViolationError("Path traversal is not allowed")

        candidate = (self.workspace_root / raw).resolve(strict=False)
        if candidate != self.workspace_root and self.workspace_root not in candidate.parents:
            raise PolicyViolationError("Path resolves outside the workspace")

        relative_parts = candidate.relative_to(self.workspace_root).parts
        if any(part.lower() in self._SENSITIVE_PARTS for part in relative_parts):
            raise PolicyViolationError("Access to sensitive directories is blocked")
        if candidate.name.lower() in self._SENSITIVE_NAMES:
            raise PolicyViolationError("Access to sensitive files is blocked")
        if candidate.name.lower().startswith(".env.") and candidate.name != ".env.example":
            raise PolicyViolationError("Access to environment secret files is blocked")
        if must_exist and not candidate.exists():
            raise PolicyViolationError("Requested path does not exist")
        return candidate

    def display(self, path: Path) -> str:
        """Return a stable workspace-relative path for plugin output."""

        relative = path.relative_to(self.workspace_root)
        return relative.as_posix() or "."
