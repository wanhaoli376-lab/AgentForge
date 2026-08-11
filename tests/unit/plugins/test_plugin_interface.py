from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel

from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.permissions import Permission, PermissionManager


class EchoArguments(BaseModel):
    message: str


class EchoPlugin(Plugin):
    name = "echo"
    description = "Echo a message for testing."
    action_models: ClassVar = {"echo": EchoArguments}
    action_permissions: ClassVar = {
        "echo": frozenset({Permission.SHELL_EXECUTE}),
    }

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        del action, context
        return PluginResult.success({"message": arguments.model_dump()["message"]})


def test_plugin_denies_action_before_execution_without_permission(tmp_path: Path) -> None:
    plugin = EchoPlugin()
    context = PluginContext(
        workspace_root=tmp_path,
        permissions=PermissionManager(granted=set()),
    )

    result = plugin.execute("echo", {"message": "hello"}, context)

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "permission_denied"
    assert result.data == {}


def test_registry_exposes_plugin_capabilities() -> None:
    registry = PluginRegistry()

    registry.register(EchoPlugin())

    assert registry.get("echo").name == "echo"
    manifest = registry.manifests()[0]
    assert manifest.actions == ("echo",)
    assert manifest.permissions == (Permission.SHELL_EXECUTE,)
