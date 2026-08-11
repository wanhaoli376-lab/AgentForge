from collections import deque
from pathlib import Path

from agentforge.agent.core import Agent
from agentforge.llm.client import LLMRequest
from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.permissions import Permission, PermissionManager
from agentforge.security.secret_filter import SecretFilter
from agentforge.skills.models import Skill
from agentforge.skills.registry import SkillRegistry


class ScriptedLLM:
    def __init__(self, responses: list[str]) -> None:
        self._responses = deque(responses)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> str:
        self.requests.append(request)
        return self._responses.popleft()


def test_agent_selects_skill_executes_plugin_and_summarizes(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo", encoding="utf-8")
    skills = SkillRegistry(
        [
            Skill(
                name="repository-summary",
                version="0.1.0",
                description="Summarize a repository.",
                author="AgentForge contributors",
                required_plugins=("filesystem",),
                keywords=("repository", "summarize"),
                instructions="List the repository and explain its purpose.",
                source_path=Path("skills/repository-summary/SKILL.md"),
            )
        ]
    )
    plugins = PluginRegistry()
    plugins.register(FilesystemPlugin())
    llm = ScriptedLLM(
        [
            '{"skills": ["repository-summary"]}',
            (
                '{"rationale": "Inspect the root", "steps": '
                '[{"plugin": "filesystem", "action": "list", '
                '"arguments": {"path": "."}}]}'
            ),
            "The repository contains a README.md file.",
        ]
    )
    agent = Agent(
        llm=llm,
        skills=skills,
        plugins=plugins,
        plugin_context=PluginContext(
            workspace_root=tmp_path,
            permissions=PermissionManager({Permission.FILESYSTEM_READ}),
        ),
        secret_filter=SecretFilter(),
    )

    result = agent.run("summarize this repository")

    assert result.ok is True
    assert result.answer == "The repository contains a README.md file."
    assert result.plan is not None
    assert result.plan.steps[0].plugin == "filesystem"
    assert result.tool_results[0].result.ok is True
    assert len(llm.requests) == 3
