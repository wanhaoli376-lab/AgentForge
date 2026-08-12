"""Compose one AgentForge runtime from validated configuration."""

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from agentforge.agent.core import Agent
from agentforge.config.models import AppConfig
from agentforge.llm.client import create_llm_client
from agentforge.plugins.base import PluginContext
from agentforge.plugins.filesystem import FilesystemPlugin
from agentforge.plugins.github import GitHubPlugin
from agentforge.plugins.python import PythonPlugin
from agentforge.plugins.registry import PluginRegistry
from agentforge.plugins.shell import ShellPlugin
from agentforge.security.permissions import PermissionManager
from agentforge.security.secret_filter import SecretFilter
from agentforge.skills.loader import SkillLoader
from agentforge.skills.models import Skill
from agentforge.skills.registry import SkillRegistry
from agentforge.skills.validator import SkillValidationError


@dataclass(frozen=True, slots=True)
class Runtime:
    """Objects useful to CLI commands and embedders."""

    config: AppConfig
    agent: Agent
    skills: SkillRegistry
    plugins: PluginRegistry


def build_runtime(config: AppConfig) -> Runtime:
    """Construct built-in adapters while preserving config-enforced permissions."""

    secret_filter = SecretFilter.from_environment(
        additional_names=(config.agent.api_key_env,),
    )
    skills = SkillRegistry(_load_skills(config))
    plugins = PluginRegistry()
    plugins.register(FilesystemPlugin(max_output_chars=config.security.max_output_chars))
    plugins.register(
        ShellPlugin(
            allowed_commands=config.security.allowed_commands,
            timeout=config.security.command_timeout,
            max_output_chars=config.security.max_output_chars,
            secret_filter=secret_filter,
        )
    )
    plugins.register(
        PythonPlugin(
            timeout=config.security.command_timeout,
            max_output_chars=config.security.max_output_chars,
            secret_filter=secret_filter,
        )
    )
    plugins.register(
        GitHubPlugin(
            read_only=config.github.read_only,
            api_url=config.github.api_url,
            timeout=config.security.command_timeout,
            allowed_domains=config.security.network_allowlist,
        )
    )

    permission_manager = PermissionManager.from_config(config.permissions)
    plugin_context = PluginContext(
        workspace_root=config.workspace.root,
        permissions=permission_manager,
    )
    llm = create_llm_client(
        model=config.agent.model,
        api_mode=config.agent.api_mode,
        api_key_env=config.agent.api_key_env,
        base_url=config.agent.base_url,
        secret_filter=secret_filter,
    )
    agent = Agent(
        llm=llm,
        skills=skills,
        plugins=plugins,
        plugin_context=plugin_context,
        secret_filter=secret_filter,
        max_steps=config.agent.max_tool_rounds,
    )
    return Runtime(config=config, agent=agent, skills=skills, plugins=plugins)


def _load_skills(config: AppConfig) -> tuple[Skill, ...]:
    configured = config.workspace.skills_dir
    if not configured.is_absolute():
        configured = config.workspace.root / configured
    if configured.exists():
        return SkillLoader(configured).load_all()
    if config.workspace.skills_dir != Path("skills"):
        raise SkillValidationError(f"Configured Skills directory does not exist: {configured}")

    package_root = resources.files("agentforge").joinpath("builtin_skills")
    if package_root.is_dir():
        with resources.as_file(package_root) as path:
            return SkillLoader(path).load_all()

    repository_skills = Path(__file__).resolve().parents[2] / "skills"
    if repository_skills.is_dir():
        return SkillLoader(repository_skills).load_all()
    raise SkillValidationError("No workspace or packaged Skills directory was found")
