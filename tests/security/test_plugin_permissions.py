from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel

from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.permissions import Permission, PermissionManager


class NoArguments(BaseModel):
    pass


class NetworkProbePlugin(Plugin):
    name = "network-probe"
    description = "Test-only network permission probe."
    action_models: ClassVar = {"probe": NoArguments}
    action_permissions: ClassVar = {
        "probe": frozenset({Permission.NETWORK_ACCESS}),
    }

    def __init__(self) -> None:
        self.was_called = False

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        del action, arguments, context
        self.was_called = True
        return PluginResult.success()


def test_plugin_without_network_permission_never_reaches_implementation(tmp_path: Path) -> None:
    plugin = NetworkProbePlugin()
    context = PluginContext(tmp_path, PermissionManager(set()))

    result = plugin.execute("probe", {}, context)

    assert result.ok is False
    assert plugin.was_called is False
    assert result.error is not None
    assert result.error.code == "permission_denied"
