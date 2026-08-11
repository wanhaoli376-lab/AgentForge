"""Single-agent orchestration with code-enforced tool boundaries."""

from agentforge.agent.context import AgentErrorInfo, AgentResult
from agentforge.agent.executor import Executor
from agentforge.agent.planner import Planner
from agentforge.exceptions import AgentForgeError
from agentforge.llm.client import LLMClient
from agentforge.plugins.base import PluginContext
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.secret_filter import SecretFilter
from agentforge.skills.registry import SkillRegistry
from agentforge.skills.validator import SkillValidationError


class Agent:
    """Select Skills, plan Plugin calls, execute them, and synthesize a result."""

    def __init__(
        self,
        *,
        llm: LLMClient,
        skills: SkillRegistry,
        plugins: PluginRegistry,
        plugin_context: PluginContext,
        secret_filter: SecretFilter,
        max_steps: int = 8,
    ) -> None:
        self._skills = skills
        self._plugins = plugins
        self._planner = Planner(llm, max_steps=max_steps)
        self._executor = Executor(plugins, plugin_context, secret_filter)
        self._secret_filter = secret_filter

    def run(self, task: str) -> AgentResult:
        """Run one natural-language task without giving the LLM direct system access."""

        safe_task = self._secret_filter.redact_text(task).strip()
        if not safe_task:
            return AgentResult(
                ok=False,
                error=AgentErrorInfo(code="invalid_task", message="Task must not be empty"),
            )
        try:
            selected_names = self._planner.select_skills(safe_task, self._skills.all())
            selected = tuple(self._skills.get(name) for name in selected_names)
            self._validate_selected_plugins(selected_names)
            plan = self._planner.create_plan(safe_task, selected, self._plugins.manifests())
            records = self._executor.execute(plan)
            answer = self._planner.summarize(safe_task, plan, records)
            return AgentResult(
                ok=True,
                answer=answer,
                selected_skills=selected_names,
                plan=plan,
                tool_results=records,
            )
        except AgentForgeError as exc:
            return AgentResult(
                ok=False,
                error=AgentErrorInfo(code=exc.code, message=str(exc)),
            )

    def _validate_selected_plugins(self, selected_names: tuple[str, ...]) -> None:
        for name in selected_names:
            skill = self._skills.get(name)
            missing = sorted(set(skill.required_plugins) - self._plugins.names())
            if missing:
                raise SkillValidationError(
                    f"Selected Skill {name!r} requires missing plugin(s): {', '.join(missing)}"
                )
