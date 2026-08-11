"""Validated AgentForge configuration models."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base model that rejects misspelled or unsupported configuration keys."""

    model_config = ConfigDict(extra="forbid")


class AgentConfig(StrictModel):
    """LLM behavior that does not contain credentials."""

    model: str = "gpt-5.6-luna"
    max_tool_rounds: int = Field(default=8, ge=1, le=32)


class WorkspaceConfig(StrictModel):
    """Filesystem roots used by plugins and skill discovery."""

    root: Path = Path(".")
    skills_dir: Path = Path("skills")


class PermissionsConfig(StrictModel):
    """Least-privilege capability grants."""

    filesystem_read: bool = True
    filesystem_write: bool = False
    filesystem_delete: bool = False
    shell_execute: bool = False
    python_execute: bool = False
    network_access: bool = False
    github_read: bool = True
    github_write: bool = False


class SecurityConfig(StrictModel):
    """Limits applied independently of model or skill instructions."""

    redact_secrets: Literal[True] = True
    command_timeout: float = Field(default=30.0, gt=0, le=300)
    max_output_chars: int = Field(default=50_000, ge=1_000, le=1_000_000)
    allowed_commands: tuple[str, ...] = ("git", "pytest", "python")
    network_allowlist: tuple[str, ...] = ("api.github.com",)


class GitHubConfig(StrictModel):
    """GitHub adapter settings. Tokens are intentionally absent."""

    read_only: bool = True
    api_url: str = "https://api.github.com"


class AppConfig(StrictModel):
    """Complete AgentForge application configuration."""

    agent: AgentConfig = Field(default_factory=AgentConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    permissions: PermissionsConfig = Field(default_factory=PermissionsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    github: GitHubConfig = Field(default_factory=GitHubConfig)
