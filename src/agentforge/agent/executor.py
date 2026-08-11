"""Execute a validated plan exclusively through registered Plugins."""

from agentforge.agent.context import ExecutionPlan, ToolExecutionRecord
from agentforge.plugins.base import PluginContext, PluginResult
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.secret_filter import SecretFilter


class Executor:
    """Dispatch plan steps while preserving permission and redaction layers."""

    def __init__(
        self,
        plugins: PluginRegistry,
        context: PluginContext,
        secret_filter: SecretFilter,
    ) -> None:
        self._plugins = plugins
        self._context = context
        self._secret_filter = secret_filter

    def execute(self, plan: ExecutionPlan) -> tuple[ToolExecutionRecord, ...]:
        records: list[ToolExecutionRecord] = []
        for step in plan.steps:
            plugin = self._plugins.get(step.plugin)
            result = plugin.execute(step.action, step.arguments, self._context)
            safe_result = PluginResult.model_validate(
                self._secret_filter.redact(result.model_dump())
            )
            records.append(ToolExecutionRecord(step=step, result=safe_result))
        return tuple(records)
