from pathlib import Path

import pytest

from agentforge.agent.context import ExecutionPlan
from agentforge.agent.planner import Planner
from agentforge.exceptions import PlanValidationError
from agentforge.llm.client import LLMRequest
from agentforge.plugins.base import PluginManifest
from agentforge.security.permissions import Permission
from agentforge.skills.models import Skill


class StaticLLM:
    def __init__(self, output: str) -> None:
        self.output = output
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> str:
        self.requests.append(request)
        return self.output


def _skill() -> Skill:
    return Skill(
        name="repository-summary",
        version="0.1.0",
        description="Summarize a repository.",
        author="AgentForge contributors",
        required_plugins=("filesystem",),
        keywords=("repository",),
        instructions="Read repository files and summarize them.",
        source_path=Path("skills/repository-summary/SKILL.md"),
    )


def _filesystem_manifest() -> PluginManifest:
    return PluginManifest(
        name="filesystem",
        version="0.1.0",
        description="Read workspace files.",
        actions=("read",),
        permissions=(Permission.FILESYSTEM_READ,),
    )


def test_planner_accepts_json_in_a_markdown_code_fence() -> None:
    planner = Planner(StaticLLM('```json\n{"skills": ["repository-summary"]}\n```'))

    selected = planner.select_skills("summarize this repository", (_skill(),))

    assert selected == ("repository-summary",)


def test_planner_rejects_a_skill_name_that_is_not_registered() -> None:
    planner = Planner(StaticLLM('{"skills": ["invented-skill"]}'))

    with pytest.raises(PlanValidationError, match="unknown Skill.*invented-skill"):
        planner.select_skills("summarize this repository", (_skill(),))


def test_planner_enforces_the_runtime_step_limit() -> None:
    planner = Planner(
        StaticLLM(
            '{"steps": ['
            '{"plugin": "filesystem", "action": "read", "arguments": {"path": "a"}},'
            '{"plugin": "filesystem", "action": "read", "arguments": {"path": "b"}}'
            "]}"
        ),
        max_steps=1,
    )

    with pytest.raises(PlanValidationError, match="1-step runtime limit"):
        planner.create_plan("read files", (), (_filesystem_manifest(),))


@pytest.mark.parametrize(
    ("step", "message"),
    [
        (
            '{"plugin": "network", "action": "get", "arguments": {}}',
            "unknown Plugin: network",
        ),
        (
            '{"plugin": "filesystem", "action": "delete", "arguments": {}}',
            "unknown action: filesystem.delete",
        ),
    ],
)
def test_planner_rejects_unknown_plugin_capabilities(step: str, message: str) -> None:
    planner = Planner(StaticLLM(f'{{"steps": [{step}]}}'))

    with pytest.raises(PlanValidationError, match=message):
        planner.create_plan("perform a task", (), (_filesystem_manifest(),))


def test_planner_rejects_malformed_model_output_without_echoing_it() -> None:
    unsafe_output = "not-json-with-sensitive-details"
    planner = Planner(StaticLLM(unsafe_output))

    with pytest.raises(PlanValidationError, match="SkillSelection") as caught:
        planner.select_skills("summarize", (_skill(),))

    assert unsafe_output not in str(caught.value)


def test_planner_strips_surrounding_whitespace_from_the_final_answer() -> None:
    llm = StaticLLM("  concise answer  \n")
    planner = Planner(llm)

    answer = planner.summarize("summarize", ExecutionPlan(), ())

    assert answer == "concise answer"
