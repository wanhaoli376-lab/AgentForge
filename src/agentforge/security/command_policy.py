"""Allowlist policy for argv-based subprocess execution."""

import re
from collections.abc import Collection, Sequence
from pathlib import PurePosixPath, PureWindowsPath

from agentforge.exceptions import PolicyViolationError


class CommandPolicy:
    """Validate commands before they reach a subprocess adapter."""

    _HARD_DENY = frozenset(
        {
            "bash",
            "cmd",
            "curl",
            "dd",
            "mkfs",
            "powershell",
            "pwsh",
            "rm",
            "shutdown",
            "sudo",
            "wget",
        }
    )
    _SHELL_META = re.compile(r"[;&|<>`\r\n]|\$\(")
    _PATH_TRAVERSAL = re.compile(r"(?:^|[\\/])\.\.(?:$|[\\/])")
    _READ_ONLY_GIT_ACTIONS = frozenset({"diff", "log", "show", "status"})

    def __init__(self, allowed_commands: Collection[str]) -> None:
        normalized = {command.lower().removesuffix(".exe") for command in allowed_commands}
        unsafe = normalized & self._HARD_DENY
        if unsafe:
            raise PolicyViolationError(
                f"Dangerous commands cannot be allowlisted: {', '.join(sorted(unsafe))}"
            )
        self._allowed_commands = frozenset(normalized)

    def validate(self, argv: Sequence[str]) -> tuple[str, ...]:
        """Return immutable argv after rejecting injection and unsafe actions."""

        if isinstance(argv, (str, bytes)) or not argv:
            raise PolicyViolationError("Commands must be provided as a non-empty argv list")
        if any(not isinstance(argument, str) or not argument for argument in argv):
            raise PolicyViolationError("Every argv item must be a non-empty string")

        executable = argv[0]
        if any(separator in executable for separator in ("/", "\\", ":")):
            raise PolicyViolationError("Executable paths are not accepted")
        command = executable.lower().removesuffix(".exe")
        if command in self._HARD_DENY or command not in self._allowed_commands:
            raise PolicyViolationError(f"Command is not allowed: {command}")
        if any(self._SHELL_META.search(argument) for argument in argv):
            raise PolicyViolationError("Shell metacharacters are not accepted")
        for argument in argv[1:]:
            candidate = argument.split("=", 1)[-1] if argument.startswith("--") else argument
            windows_path = PureWindowsPath(candidate)
            posix_path = PurePosixPath(candidate)
            if (
                candidate.startswith("~")
                or bool(windows_path.drive)
                or bool(windows_path.root)
                or windows_path.is_absolute()
                or bool(posix_path.root)
                or posix_path.is_absolute()
                or self._PATH_TRAVERSAL.search(candidate)
            ):
                raise PolicyViolationError("Command arguments cannot escape the workspace")

        arguments = tuple(argv[1:])
        if command == "git":
            self._validate_git(arguments)
        elif command == "python":
            self._validate_python(arguments)
        return tuple(argv)

    def _validate_git(self, arguments: tuple[str, ...]) -> None:
        if not arguments or arguments[0] not in self._READ_ONLY_GIT_ACTIONS:
            raise PolicyViolationError(
                "Only read-only git status/diff/log/show actions are allowed"
            )
        blocked_flags = {
            "-c",
            "--config",
            "--ext-diff",
            "--no-index",
            "--output",
            "--textconv",
        }
        if any(
            argument in blocked_flags
            or argument.startswith("--config=")
            or argument.startswith("--output=")
            or argument.startswith("--git-dir")
            or argument.startswith("--work-tree")
            for argument in arguments
        ):
            raise PolicyViolationError(
                "Git execution-affecting or output-writing flags are blocked"
            )

    def _validate_python(self, arguments: tuple[str, ...]) -> None:
        blocked = {"-", "-c", "-m"}
        if any(argument in blocked for argument in arguments):
            raise PolicyViolationError(
                "Inline, module, and stdin Python execution are blocked here"
            )
