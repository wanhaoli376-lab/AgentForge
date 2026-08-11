from pathlib import Path

from agentforge.skills.loader import SkillLoader


def test_loader_parses_a_valid_skill_document(tmp_path: Path) -> None:
    skill_dir = tmp_path / "test-runner"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: test-runner
version: 0.1.0
description: Run project tests and explain failures.
author: AgentForge contributors
required_plugins:
  - filesystem
  - shell
keywords:
  - tests
  - pytest
---
# Test Runner

Inspect the project, run its tests, and explain failures.
""",
        encoding="utf-8",
    )

    skills = SkillLoader(tmp_path).load_all()

    assert len(skills) == 1
    skill = skills[0]
    assert skill.name == "test-runner"
    assert skill.required_plugins == ("filesystem", "shell")
    assert skill.keywords == ("tests", "pytest")
    assert "explain failures" in skill.instructions
