import json
from collections import deque
from pathlib import Path

import pytest

from agentforge.agent.core import Agent
from agentforge.exceptions import LLMError
from agentforge.llm.client import LLMRequest
from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.permissions import Permission, PermissionManager
from agentforge.security.secret_filter import SecretFilter
from agentforge.skills.models import Skill
from agentforge.skills.registry import SkillRegistry


class ScriptedLLM:
    def __init__(self, responses: list[str | Exception]) -> None:
        self._responses = deque(responses)
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> str:
        self.requests.append(request)
        response = self._responses.popleft()
        if isinstance(response, Exception):
            raise response
        return response


def _agent(tmp_path: Path, llm: ScriptedLLM, *, writable: bool = False) -> Agent:
    plugins = PluginRegistry()
    plugins.register(FilesystemPlugin())
    permissions = {Permission.FILESYSTEM_READ}
    if writable:
        permissions.add(Permission.FILESYSTEM_WRITE)
    return Agent(
        llm=llm,
        skills=SkillRegistry(),
        plugins=plugins,
        plugin_context=PluginContext(tmp_path, PermissionManager(permissions)),
        secret_filter=SecretFilter(),
    )


def test_failed_tool_stops_later_writes_and_marks_the_run_unsuccessful(tmp_path: Path) -> None:
    plan = {
        "steps": [
            {"plugin": "filesystem", "action": "read", "arguments": {"path": "missing.txt"}},
            {
                "plugin": "filesystem",
                "action": "write",
                "arguments": {"path": "report.txt", "content": "must not be written"},
            },
        ],
    }
    llm = ScriptedLLM(['{"skills": []}', json.dumps(plan), "The input file is missing."])

    result = _agent(tmp_path, llm, writable=True).run("Read the input and write a report")

    assert result.ok is False
    assert result.error is not None
    assert result.error.code == "tool_execution_failed"
    assert result.answer == "The input file is missing."
    assert result.plan is not None and len(result.plan.steps) == 2
    assert len(result.tool_results) == 1
    assert result.tool_results[0].result.ok is False
    assert not (tmp_path / "report.txt").exists()


def test_summary_failure_preserves_completed_work_without_repeating_it(tmp_path: Path) -> None:
    plan = {
        "steps": [
            {
                "plugin": "filesystem",
                "action": "create",
                "arguments": {
                    "path": "created.txt",
                    "content": "created once",
                },
            }
        ]
    }
    llm = ScriptedLLM(['{"skills": []}', json.dumps(plan), LLMError("Summary unavailable")])

    result = _agent(tmp_path, llm, writable=True).run("Create a file")

    assert result.ok is False
    assert result.error is not None and result.error.code == "llm_error"
    assert result.plan is not None
    assert len(result.tool_results) == 1
    assert result.tool_results[0].result.ok is True
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "created once"
    assert len(llm.requests) == 3


def test_planning_receives_argument_schemas_and_only_granted_actions(tmp_path: Path) -> None:
    llm = ScriptedLLM(['{"skills": []}', '{"steps": []}', "No action needed."])

    _agent(tmp_path, llm).run("Inspect available actions")

    manifest = json.loads(llm.requests[1].input)["plugins"][0]
    assert manifest["actions"] == ["list", "read"]
    assert manifest["permissions"] == ["filesystem.read"]
    assert set(manifest["action_schemas"]) == {"list", "read"}
    assert manifest["action_schemas"]["read"]["properties"]["path"]["type"] == "string"
    assert manifest["action_schemas"]["read"]["additionalProperties"] is False


def test_disabled_action_is_rejected_before_any_tool_executes(tmp_path: Path) -> None:
    plan = {
        "steps": [
            {
                "plugin": "filesystem",
                "action": "write",
                "arguments": {
                    "path": "blocked.txt",
                    "content": "blocked",
                },
            }
        ]
    }
    llm = ScriptedLLM(['{"skills": []}', json.dumps(plan)])

    result = _agent(tmp_path, llm).run("Write without a permission grant")

    assert result.ok is False
    assert result.error is not None and result.error.code == "invalid_plan"
    assert not result.tool_results
    assert not (tmp_path / "blocked.txt").exists()


def test_completed_actions_are_retained_when_a_later_tool_fails(tmp_path: Path) -> None:
    plan = {
        "steps": [
            {
                "plugin": "filesystem",
                "action": "create",
                "arguments": {
                    "path": "created.txt",
                    "content": "retained",
                },
            },
            {"plugin": "filesystem", "action": "read", "arguments": {"path": "missing.txt"}},
        ]
    }
    llm = ScriptedLLM(['{"skills": []}', json.dumps(plan), "Created a file; reading failed."])

    result = _agent(tmp_path, llm, writable=True).run("Create a file and then inspect another")

    assert result.ok is False
    assert [record.result.ok for record in result.tool_results] == [True, False]
    assert (tmp_path / "created.txt").read_text(encoding="utf-8") == "retained"


@pytest.mark.parametrize("summary_fails", [False, True])
def test_custom_llm_output_and_errors_are_redacted(tmp_path: Path, summary_fails: bool) -> None:
    secret = "sk-test-invented-sensitive-value"  # noqa: S105 - synthetic redaction fixture
    plan = {
        "rationale": secret,
        "steps": [
            {
                "plugin": "filesystem",
                "action": "create",
                "arguments": {"path": "note.txt", "content": secret},
            }
        ],
    }
    summary: str | Exception = LLMError(secret) if summary_fails else secret
    llm = ScriptedLLM(['{"skills": []}', json.dumps(plan), summary])

    result = _agent(tmp_path, llm, writable=True).run("Create a note")

    assert result.ok is (not summary_fails)
    assert secret not in result.model_dump_json()
    assert "[REDACTED]" in result.model_dump_json()
    assert all(secret not in request.input for request in llm.requests)
    assert (tmp_path / "note.txt").read_text(encoding="utf-8") == "[REDACTED]"


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
