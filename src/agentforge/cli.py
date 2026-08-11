"""Command-line interface for AgentForge."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from agentforge import __version__
from agentforge.config.loader import ConfigError, load_config
from agentforge.exceptions import AgentForgeError
from agentforge.logging_config import configure_logging
from agentforge.runtime import Runtime, build_runtime


@dataclass(frozen=True, slots=True)
class CLIState:
    """Values shared by root and nested commands."""

    config_path: Path | None


app = typer.Typer(
    name="agentforge",
    help="An extensible, security-aware AI agent framework.",
    no_args_is_help=False,
)
skills_app = typer.Typer(help="Inspect loaded Skills.")
plugins_app = typer.Typer(help="Inspect registered Plugins and required permissions.")
app.add_typer(skills_app, name="skills")
app.add_typer(plugins_app, name="plugins")


@app.callback(invoke_without_command=True)
def cli(
    ctx: typer.Context,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            "-c",
            help="Path to an AgentForge YAML or TOML config file.",
        ),
    ] = None,
) -> None:
    """Run secure, skill-driven automation from the terminal."""

    ctx.obj = CLIState(config_path=config)
    if ctx.invoked_subcommand is None:
        _interactive(ctx.obj)


@app.command("run")
def run_command(
    ctx: typer.Context,
    task: str = typer.Argument(..., help="Natural-language task for the Agent."),
    output_json: bool = typer.Option(False, "--json", help="Print the structured AgentResult."),
) -> None:
    """Run one task and exit."""

    state = _state(ctx)
    runtime = _runtime_or_exit(state)
    result = runtime.agent.run(task)
    if output_json:
        typer.echo(result.model_dump_json(indent=2))
    elif result.ok:
        typer.echo(result.answer)
    else:
        assert result.error is not None
        typer.echo(f"Error [{result.error.code}]: {result.error.message}", err=True)
    if not result.ok:
        raise typer.Exit(code=2)


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Validate configuration and report credential presence without values."""

    runtime = _runtime_or_exit(_state(ctx))
    permissions = runtime.config.permissions
    typer.echo(f"Workspace: {runtime.config.workspace.root}")
    typer.echo(f"Skills: {len(runtime.skills.all())}")
    typer.echo(f"Plugins: {len(runtime.plugins.manifests())}")
    typer.echo(f"OPENAI_API_KEY: {'present' if os.getenv('OPENAI_API_KEY') else 'missing'}")
    github_status = "present" if os.getenv("GITHUB_TOKEN") else "missing (public only)"
    typer.echo(f"GITHUB_TOKEN: {github_status}")
    typer.echo(
        "High-risk permissions: "
        f"filesystem_write={permissions.filesystem_write}, "
        f"shell_execute={permissions.shell_execute}, "
        f"python_execute={permissions.python_execute}, "
        f"network_access={permissions.network_access}, "
        f"github_write={permissions.github_write}"
    )


@app.command()
def version() -> None:
    """Print the installed AgentForge version."""

    typer.echo(__version__)


@skills_app.command("list")
def list_skills(ctx: typer.Context) -> None:
    """List validated Skills and their required Plugins."""

    runtime = _runtime_or_exit(_state(ctx))
    for skill in runtime.skills.all():
        required = ", ".join(skill.required_plugins) or "none"
        typer.echo(f"{skill.name} {skill.version} - {skill.description} [plugins: {required}]")


@plugins_app.command("list")
def list_plugins(ctx: typer.Context) -> None:
    """List Plugin actions and declared permissions."""

    runtime = _runtime_or_exit(_state(ctx))
    for manifest in runtime.plugins.manifests():
        actions = ", ".join(manifest.actions)
        permissions = ", ".join(permission.value for permission in manifest.permissions) or "none"
        typer.echo(f"{manifest.name} - actions: {actions}; permissions: {permissions}")


def _interactive(state: CLIState) -> None:
    runtime = _runtime_or_exit(state)
    typer.echo("AgentForge interactive mode. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            task = input("AgentForge > ").strip()
        except (EOFError, KeyboardInterrupt):
            typer.echo()
            return
        if task.casefold() in {"exit", "quit"}:
            return
        if not task:
            continue
        result = runtime.agent.run(task)
        if result.ok:
            typer.echo(result.answer)
        else:
            assert result.error is not None
            typer.echo(f"Error [{result.error.code}]: {result.error.message}", err=True)


def _runtime_or_exit(state: CLIState) -> Runtime:
    try:
        config = load_config(state.config_path)
        configure_logging()
        return build_runtime(config)
    except (AgentForgeError, ConfigError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc


def _state(ctx: typer.Context) -> CLIState:
    state = ctx.find_root().obj
    if not isinstance(state, CLIState):
        raise RuntimeError("CLI state was not initialized")
    return state


def main() -> None:
    """Run the AgentForge CLI."""

    app()


if __name__ == "__main__":  # pragma: no cover
    main()
