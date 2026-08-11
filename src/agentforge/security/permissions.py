"""Capability grants enforced independently from LLM output."""

from collections.abc import Collection
from enum import StrEnum

from agentforge.config.models import PermissionsConfig
from agentforge.exceptions import PermissionDeniedError


class Permission(StrEnum):
    """Capabilities that plugins may request for an action."""

    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"
    FILESYSTEM_DELETE = "filesystem.delete"
    SHELL_EXECUTE = "shell.execute"
    PYTHON_EXECUTE = "python.execute"
    NETWORK_ACCESS = "network.access"
    GITHUB_READ = "github.read"
    GITHUB_WRITE = "github.write"


class PermissionManager:
    """Own the authoritative set of capabilities granted to this run."""

    def __init__(self, granted: Collection[Permission]) -> None:
        self._granted = frozenset(granted)

    @classmethod
    def from_config(cls, config: PermissionsConfig) -> "PermissionManager":
        mapping = {
            Permission.FILESYSTEM_READ: config.filesystem_read,
            Permission.FILESYSTEM_WRITE: config.filesystem_write,
            Permission.FILESYSTEM_DELETE: config.filesystem_delete,
            Permission.SHELL_EXECUTE: config.shell_execute,
            Permission.PYTHON_EXECUTE: config.python_execute,
            Permission.NETWORK_ACCESS: config.network_access,
            Permission.GITHUB_READ: config.github_read,
            Permission.GITHUB_WRITE: config.github_write,
        }
        return cls({permission for permission, enabled in mapping.items() if enabled})

    @property
    def granted(self) -> frozenset[Permission]:
        """Return an immutable view of the grants."""

        return self._granted

    def allows(self, permission: Permission) -> bool:
        """Return whether a capability has been granted."""

        return permission in self._granted

    def require(self, permissions: Collection[Permission]) -> None:
        """Reject an action unless every requested capability is granted."""

        missing = sorted(set(permissions) - self._granted)
        if missing:
            names = ", ".join(permission.value for permission in missing)
            raise PermissionDeniedError(f"Missing required permission(s): {names}")
