"""Discover and load SKILL.md files from a confined directory."""

from pathlib import Path

from agentforge.skills.models import Skill
from agentforge.skills.validator import SkillValidationError, parse_skill_document


class SkillLoader:
    """Load all Skills beneath one explicit root without following escapes."""

    def __init__(self, root: Path, *, max_skill_bytes: int = 256_000) -> None:
        self.root = root.expanduser().resolve()
        self.max_skill_bytes = max_skill_bytes

    def load_all(self) -> tuple[Skill, ...]:
        if not self.root.exists():
            return ()
        if not self.root.is_dir():
            raise SkillValidationError("Skills root must be a directory")

        skills = tuple(
            parse_skill_document(path, root=self.root, max_bytes=self.max_skill_bytes)
            for path in sorted(self.root.rglob("SKILL.md"))
        )
        names = [skill.name for skill in skills]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise SkillValidationError(f"Duplicate Skill names: {', '.join(duplicates)}")
        return skills
