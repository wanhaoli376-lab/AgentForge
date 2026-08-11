"""Allowlisted argv execution through the restricted subprocess layer."""

import shutil
import subprocess
import sys
from collections.abc import Collection
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from agentforge.exceptions import PluginExecutionError, PolicyViolationError
from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.command_policy import CommandPolicy
from agentforge.security.path_policy import PathPolicy
from agentforge.security.permissions import Permission
from agentforge.security.sandbox import ProcessSandbox
from agentforge.security.secret_filter import SecretFilter


class ShellArguments(BaseModel):
    """Validated, non-shell command arguments."""

    model_config = ConfigDict(extra="forbid")

    argv: tuple[str, ...] = Field(min_length=1, max_length=64)
    cwd: str = Field(default=".", min_length=1, max_length=4_096)
    timeout: float | None = Field(default=None, gt=0, le=300)


class ShellPlugin(Plugin):
    """Execute only policy-approved commands with shell=False."""

    name = "shell"
    description = "Run allowlisted argv commands in the workspace with bounded output."
    action_models: ClassVar = {"run": ShellArguments}
    action_permissions: ClassVar = {
        "run": frozenset({Permission.SHELL_EXECUTE}),
    }

    def __init__(
        self,
        *,
        allowed_commands: Collection[str] = ("git", "pytest", "python"),
        timeout: float = 30.0,
        max_output_chars: int = 50_000,
        secret_filter: SecretFilter | None = None,
    ) -> None:
        self._policy = CommandPolicy(allowed_commands)
        self._timeout = timeout
        self._secret_filter = secret_filter or SecretFilter.from_environment()
        self._sandbox = ProcessSandbox(
            secret_filter=self._secret_filter,
            max_output_chars=max_output_chars,
        )

    def _execute(
        self,
        action: str,
        arguments: BaseModel,
        context: PluginContext,
    ) -> PluginResult:
        del action
        args = ShellArguments.model_validate(arguments.model_dump())
        path_policy = PathPolicy(context.workspace_root)
        cwd = path_policy.resolve(args.cwd, must_exist=True)
        if not cwd.is_dir():
            raise PolicyViolationError("Shell cwd must be a workspace directory")

        approved = self._policy.validate(args.argv)
        executable_argv = self._resolve_executable(approved, path_policy)
        result = self._sandbox.run(
            executable_argv,
            cwd=cwd,
            timeout=min(args.timeout or self._timeout, self._timeout),
        )
        command = self._secret_filter.redact_text(subprocess.list2cmdline(list(approved)))
        return PluginResult.success(
            {
                "command": command,
                "argv": approved,
                "cwd": path_policy.display(cwd),
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "truncated": result.truncated,
                "timed_out": result.timed_out,
                "duration_seconds": result.duration_seconds,
            }
        )

    @staticmethod
    def _resolve_executable(
        argv: tuple[str, ...],
        path_policy: PathPolicy,
    ) -> tuple[str, ...]:
        command = argv[0].lower().removesuffix(".exe")
        arguments = list(argv[1:])
        if command == "python":
            if not arguments:
                raise PolicyViolationError("Interactive Python is not allowed")
            if arguments[0] not in {"--help", "--version", "-V"}:
                if arguments[0].startswith("-"):
                    raise PolicyViolationError("Unsupported Python interpreter option")
                script = path_policy.resolve(arguments[0], must_exist=True)
                if not script.is_file() or script.suffix.lower() != ".py":
                    raise PolicyViolationError("Python command requires a workspace .py file")
                arguments[0] = str(script)
            return (sys.executable, *arguments)
        if command == "pytest":
            return (sys.executable, "-m", "pytest", *arguments)
        if command == "git":
            executable = shutil.which("git")
            if executable is None:
                raise PluginExecutionError("The allowlisted git executable was not found")
            return (executable, *arguments)
        raise PolicyViolationError(f"No trusted executable adapter exists for: {command}")
