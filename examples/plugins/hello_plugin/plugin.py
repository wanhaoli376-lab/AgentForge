"""A deliberately harmless community Plugin example."""

from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from agentforge.plugins.base import Plugin, PluginContext, PluginResult


class GreetArguments(BaseModel):
    """Strict external data accepted by the example action."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)


class HelloPlugin(Plugin):
    """Return a greeting without filesystem, process, or network access."""

    name = "hello"
    version = "0.1.0"
    description = "Return a safe greeting for Plugin development examples."
    action_models: ClassVar = {"greet": GreetArguments}
    # An explicit empty set documents that this action needs no real capability.
    action_permissions: ClassVar = {"greet": frozenset()}

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        # Plugin.execute has already checked the action, permission set, and schema.
        del action, context
        args = GreetArguments.model_validate(arguments.model_dump())
        return PluginResult.success({"message": f"Hello, {args.name}!"})
