from pathlib import Path

from agentforge.skills.loader import SkillLoader


def test_four_builtin_skills_are_valid() -> None:
    skills = SkillLoader(Path("skills")).load_all()

    assert {skill.name for skill in skills} == {
        "code-review",
        "github-maintainer",
        "repository-summary",
        "test-runner",
    }
