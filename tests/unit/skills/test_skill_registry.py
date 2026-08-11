from pathlib import Path

import pytest

from agentforge.skills.models import Skill
from agentforge.skills.registry import SkillRegistry
from agentforge.skills.validator import SkillValidationError


def _test_runner() -> Skill:
    return Skill(
        name="test-runner",
        version="0.1.0",
        description="Run tests and explain failures.",
        author="AgentForge contributors",
        required_plugins=("filesystem", "shell"),
        keywords=("test", "pytest"),
        instructions="Run tests only through the Shell Plugin.",
        source_path=Path("skills/test-runner/SKILL.md"),
    )


def test_registry_matches_task_and_marks_skill_text_untrusted() -> None:
    registry = SkillRegistry([_test_runner()])

    selected = registry.match("Please run pytest and explain the test failure")
    fragment = registry.prompt_fragment(selected)

    assert tuple(skill.name for skill in selected) == ("test-runner",)
    assert "untrusted guidance" in fragment
    assert "<untrusted-skill" in fragment


def test_registry_rejects_missing_required_plugins() -> None:
    registry = SkillRegistry([_test_runner()])

    with pytest.raises(SkillValidationError, match="shell"):
        registry.validate_required_plugins({"filesystem"})
