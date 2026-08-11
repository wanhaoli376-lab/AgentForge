"""Strict parser for Markdown Skill definitions."""

import re
from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import ValidationError

from agentforge.exceptions import AgentForgeError
from agentforge.skills.models import Skill, SkillMetadata


class SkillValidationError(AgentForgeError):
    """Raised for malformed, oversized, or escaped Skill files."""

    code = "skill_validation_error"


_FRONT_MATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<metadata>.*?)\r?\n---[ \t]*\r?\n(?P<body>.*)\Z",
    re.DOTALL,
)


def parse_skill_document(
    path: Path,
    *,
    root: Path | None = None,
    max_bytes: int = 256_000,
) -> Skill:
    """Parse one SKILL.md after confining it to the expected root."""

    try:
        source = path.resolve(strict=True)
    except OSError as exc:
        raise SkillValidationError(f"Skill file does not exist: {path}") from exc
    if not source.is_file() or source.name != "SKILL.md":
        raise SkillValidationError("Skill definitions must be regular SKILL.md files")
    if root is not None:
        expected_root = root.resolve(strict=True)
        if source != expected_root and expected_root not in source.parents:
            raise SkillValidationError("Skill file resolves outside its configured root")
    if source.stat().st_size > max_bytes:
        raise SkillValidationError(f"Skill file exceeds the {max_bytes}-byte limit")

    try:
        text = source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise SkillValidationError(f"Could not read Skill file: {source}") from exc
    match = _FRONT_MATTER.fullmatch(text)
    if match is None:
        raise SkillValidationError("SKILL.md must start with YAML front matter")
    try:
        raw_metadata = yaml.safe_load(match.group("metadata"))
    except yaml.YAMLError as exc:
        raise SkillValidationError("SKILL.md front matter is invalid YAML") from exc
    if not isinstance(raw_metadata, Mapping):
        raise SkillValidationError("SKILL.md front matter must be a mapping")

    body = match.group("body").strip()
    try:
        metadata = SkillMetadata.model_validate(dict(raw_metadata))
        return Skill(
            **metadata.model_dump(),
            instructions=body,
            source_path=source,
        )
    except ValidationError as exc:
        raise SkillValidationError(f"Invalid Skill metadata or body: {exc}") from exc
