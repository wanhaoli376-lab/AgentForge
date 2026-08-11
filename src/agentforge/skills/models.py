"""Validated Skill metadata and instructions."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class SkillMetadata(BaseModel):
    """Supply-chain metadata stored in SKILL.md front matter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
    description: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=200)
    required_plugins: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


class Skill(SkillMetadata):
    """A validated but untrusted set of task instructions."""

    instructions: str = Field(min_length=1, max_length=100_000)
    source_path: Path
