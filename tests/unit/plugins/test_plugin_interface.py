from pathlib import Path
from typing import ClassVar

import pytest
from pydantic import BaseModel

from agentforge.exceptions import PluginContractError
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


class MissingPermissionsPlugin(Plugin):
    name = "missing-permissions"
    description = "Invalid test plugin."
    action_models: ClassVar = {"echo": EchoArguments}

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        raise AssertionError("invalid plugins must never execute")


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
    assert manifest.action_schemas["echo"]["required"] == ["message"]
    assert manifest.action_schemas["echo"]["properties"]["message"]["type"] == "string"


def test_registry_hides_ungranted_actions_without_mutating_the_full_catalog() -> None:
    registry = PluginRegistry()
    registry.register(EchoPlugin())

    assert registry.manifests(permissions=PermissionManager(set())) == ()
    assert registry.manifests()[0].actions == ("echo",)
    allowed = registry.manifests(permissions=PermissionManager({Permission.SHELL_EXECUTE}))
    assert allowed == registry.manifests()


def test_registry_keeps_actions_that_require_no_permissions() -> None:
    class UnrestrictedEcho(EchoPlugin):
        action_permissions: ClassVar = {"echo": frozenset()}

    registry = PluginRegistry()
    registry.register(UnrestrictedEcho())

    manifest = registry.manifests(permissions=PermissionManager(set()))[0]
    assert manifest.actions == ("echo",)
    assert manifest.permissions == ()


def test_registry_rejects_plugin_with_missing_permission_metadata() -> None:
    registry = PluginRegistry()

    with pytest.raises(PluginContractError):
        registry.register(MissingPermissionsPlugin())


def test_argument_validation_error_does_not_echo_secret(tmp_path: Path) -> None:
    sensitive_value = "ghp_do-not-repeat-this-value"
    plugin = EchoPlugin()
    context = PluginContext(
        workspace_root=tmp_path,
        permissions=PermissionManager({Permission.SHELL_EXECUTE}),
    )

    result = plugin.execute("echo", {"message": {"token": sensitive_value}}, context)

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "invalid_arguments"
    assert sensitive_value not in result.error.message
