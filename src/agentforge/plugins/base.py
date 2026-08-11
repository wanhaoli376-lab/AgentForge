"""Small public interface shared by built-in and community plugins."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, final

from pydantic import BaseModel, Field, ValidationError

from agentforge.exceptions import AgentForgeError
from agentforge.security.permissions import Permission, PermissionManager


class PluginErrorInfo(BaseModel):
    """A safe, structured plugin error."""

    code: str
    message: str


class PluginResult(BaseModel):
    """Stable result envelope returned by every plugin action."""

    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: PluginErrorInfo | None = None

    @classmethod
    def success(cls, data: Mapping[str, Any] | None = None) -> "PluginResult":
        return cls(ok=True, data=dict(data or {}))

    @classmethod
    def failure(cls, code: str, message: str) -> "PluginResult":
        return cls(ok=False, error=PluginErrorInfo(code=code, message=message))


@dataclass(frozen=True, slots=True)
class PluginContext:
    """Trusted execution context constructed by the application."""

    workspace_root: Path
    permissions: PermissionManager


class PluginManifest(BaseModel):
    """Introspection metadata safe to expose to planners and users."""

    name: str
    version: str
    description: str
    actions: tuple[str, ...]
    permissions: tuple[Permission, ...]


class Plugin(ABC):
    """Base class that validates every action before dispatching it."""

    name: ClassVar[str]
    description: ClassVar[str]
    version: ClassVar[str] = "0.1.0"
    action_models: ClassVar[Mapping[str, type[BaseModel]]] = {}
    action_permissions: ClassVar[Mapping[str, frozenset[Permission]]] = {}

    @property
    def manifest(self) -> PluginManifest:
        permissions = {
            permission for required in self.action_permissions.values() for permission in required
        }
        return PluginManifest(
            name=self.name,
            version=self.version,
            description=self.description,
            actions=tuple(sorted(self.action_models)),
            permissions=tuple(sorted(permissions, key=str)),
        )

    @final
    def execute(
        self,
        action: str,
        arguments: Mapping[str, Any],
        context: PluginContext,
    ) -> PluginResult:
        """Validate action, permissions, and arguments before implementation code."""

        model_type = self.action_models.get(action)
        if model_type is None:
            return PluginResult.failure("unknown_action", f"Unsupported action: {action}")

        try:
            context.permissions.require(self.action_permissions.get(action, frozenset()))
            validated = model_type.model_validate(arguments)
            return self._execute(action, validated, context)
        except ValidationError as exc:
            return PluginResult.failure("invalid_arguments", str(exc))
        except AgentForgeError as exc:
            return PluginResult.failure(exc.code, str(exc))
        except Exception:  # noqa: BLE001 - plugin failures must not crash the agent loop
            return PluginResult.failure(
                "plugin_internal_error",
                "Plugin execution failed without exposing internal details",
            )

    @abstractmethod
    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        """Execute an already-authorized, validated action."""
