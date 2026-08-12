"""Validated AgentForge configuration models."""

import ipaddress
from contextlib import suppress
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base model that rejects misspelled or unsupported configuration keys."""

    model_config = ConfigDict(extra="forbid")


class AgentConfig(StrictModel):
    """LLM behavior that does not contain credentials."""

    model: str = Field(default="gpt-5.6-luna", min_length=1, max_length=200)
    max_tool_rounds: int = Field(default=8, ge=1, le=32)
    api_mode: Literal["responses", "chat_completions"] = "responses"
    base_url: str | None = Field(default=None, max_length=2_048)
    api_key_env: str = Field(
        default="OPENAI_API_KEY",
        pattern=r"^[A-Za-z_][A-Za-z0-9_]{0,127}$",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        """Require encrypted remote providers while allowing loopback development servers."""

        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.username or parsed.password:
            raise ValueError("LLM base URLs must not contain credentials")
        if not parsed.hostname or parsed.query or parsed.fragment:
            raise ValueError("LLM base URLs must be absolute and must not contain query data")

        hostname = parsed.hostname.lower().rstrip(".")
        is_loopback = hostname == "localhost" or hostname.endswith(".localhost")
        with suppress(ValueError):
            is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback

        scheme = parsed.scheme.lower()
        if scheme != "https" and not (scheme == "http" and is_loopback):
            raise ValueError("Remote LLM base URLs must use HTTPS")
        return value


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
