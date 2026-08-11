"""Convert untrusted LLM text into validated Skill choices and tool plans."""

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from agentforge.agent.context import ExecutionPlan, SkillSelection, ToolExecutionRecord
from agentforge.exceptions import PlanValidationError
from agentforge.llm.client import LLMClient, LLMRequest
from agentforge.llm.prompts import planning_request, skill_selection_request, summary_request
from agentforge.plugins.base import PluginManifest
from agentforge.skills.models import Skill

ModelT = TypeVar("ModelT", bound=BaseModel)


class Planner:
    """Own all model interactions for a single-agent run."""

    def __init__(self, llm: LLMClient, *, max_steps: int = 8) -> None:
        self._llm = llm
        self._max_steps = max_steps

    def select_skills(self, task: str, available: tuple[Skill, ...]) -> tuple[str, ...]:
        instructions, input_text = skill_selection_request(task, available)
        output = self._llm.generate(LLMRequest(instructions=instructions, input=input_text))
        selection = self._parse(output, SkillSelection)
        available_names = {skill.name for skill in available}
        unknown = sorted(set(selection.skills) - available_names)
        if unknown:
            raise PlanValidationError(f"Model selected unknown Skill(s): {', '.join(unknown)}")
        return selection.skills

    def create_plan(
        self,
        task: str,
        skills: tuple[Skill, ...],
        plugins: tuple[PluginManifest, ...],
    ) -> ExecutionPlan:
        instructions, input_text = planning_request(
            task,
            skills,
            plugins,
            max_steps=self._max_steps,
        )
        output = self._llm.generate(LLMRequest(instructions=instructions, input=input_text))
        plan = self._parse(output, ExecutionPlan)
        if len(plan.steps) > self._max_steps:
            raise PlanValidationError(f"Plan exceeds the {self._max_steps}-step runtime limit")
        available = {manifest.name: set(manifest.actions) for manifest in plugins}
        for step in plan.steps:
            if step.plugin not in available:
                raise PlanValidationError(f"Plan references unknown Plugin: {step.plugin}")
            if step.action not in available[step.plugin]:
                raise PlanValidationError(
                    f"Plan references unknown action: {step.plugin}.{step.action}"
                )
        return plan

    def summarize(
        self,
        task: str,
        plan: ExecutionPlan,
        records: tuple[ToolExecutionRecord, ...],
    ) -> str:
        instructions, input_text = summary_request(task, plan, records)
        return self._llm.generate(LLMRequest(instructions=instructions, input=input_text)).strip()

    @staticmethod
    def _parse(text: str, model_type: type[ModelT]) -> ModelT:
        candidate = text.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            lines = candidate.splitlines()
            candidate = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(candidate)
            return model_type.model_validate(value)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise PlanValidationError(
                f"Model response did not match {model_type.__name__}"
            ) from exc
