"""Structured state passed through one Agent run."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agentforge.plugins.base import PluginResult


class LLMControlModel(BaseModel):
    """Base for untrusted model output that rejects unknown control fields."""

    model_config = ConfigDict(extra="forbid")


class SkillSelection(LLMControlModel):
    """Validated names selected from the available Skill registry."""

    skills: tuple[str, ...] = Field(default=(), max_length=3)


class PlanStep(LLMControlModel):
    """One plugin action proposed by the untrusted model."""

    plugin: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ExecutionPlan(LLMControlModel):
    """Bounded, validated sequence of plugin calls."""

    rationale: str = Field(default="", max_length=2_000)
    steps: tuple[PlanStep, ...] = Field(default=(), max_length=16)


class ToolExecutionRecord(BaseModel):
    """A plan step paired with its structured plugin result."""

    step: PlanStep
    result: PluginResult


class AgentErrorInfo(BaseModel):
    """Safe error returned instead of crashing the CLI."""

    code: str
    message: str


class AgentResult(BaseModel):
    """Public result of Agent.run."""

    ok: bool
    answer: str = ""
    selected_skills: tuple[str, ...] = ()
    plan: ExecutionPlan | None = None
    tool_results: tuple[ToolExecutionRecord, ...] = ()
    error: AgentErrorInfo | None = None
