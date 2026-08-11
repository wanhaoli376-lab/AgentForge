"""Restricted subprocess runner used by executable plugins.

This module deliberately does not claim OS or container isolation. It provides
argv execution, workspace cwd, environment filtering, timeout, output limits,
and secret redaction as defense in depth.
"""

import os
import subprocess
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import BinaryIO

from pydantic import BaseModel

from agentforge.exceptions import PluginExecutionError, PolicyViolationError
from agentforge.security.secret_filter import SecretFilter


class ProcessResult(BaseModel):
    """Structured result from a restricted subprocess."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str
    truncated: bool
    timed_out: bool
    duration_seconds: float


class ProcessSandbox:
    """Run a subprocess without a shell and with bounded observable output."""

    _ENV_ALLOWLIST = frozenset(
        {
            "COLORTERM",
            "LANG",
            "LC_ALL",
            "NO_COLOR",
            "PATH",
            "PATHEXT",
            "PYTHONIOENCODING",
            "SYSTEMROOT",
            "TEMP",
            "TERM",
            "TMP",
            "TMPDIR",
            "VIRTUAL_ENV",
            "WINDIR",
        }
    )
    _SECRET_NAME_PARTS = ("CREDENTIAL", "KEY", "PASSWORD", "SECRET", "TOKEN")

    def __init__(
        self,
        *,
        secret_filter: SecretFilter,
        max_output_chars: int = 50_000,
        base_environment: Mapping[str, str] | None = None,
    ) -> None:
        if max_output_chars <= 0:
            raise ValueError("max_output_chars must be positive")
        self._secret_filter = secret_filter
        self._max_output_chars = max_output_chars
        self._base_environment = dict(
            base_environment if base_environment is not None else os.environ
        )

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float,
    ) -> ProcessResult:
        """Execute trusted argv with no stdin and a filtered environment."""

        if isinstance(argv, (str, bytes)) or not argv:
            raise PolicyViolationError("Subprocess argv must be a non-empty list")
        if timeout <= 0:
            raise PolicyViolationError("Subprocess timeout must be positive")
        resolved_cwd = cwd.resolve()
        if not resolved_cwd.is_dir():
            raise PolicyViolationError("Subprocess cwd must be an existing directory")

        stdout_buffer = bytearray()
        stderr_buffer = bytearray()
        budget = {"remaining": self._max_output_chars}
        budget_lock = threading.Lock()
        truncated = threading.Event()
        started = time.monotonic()
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

        try:
            process = subprocess.Popen(  # noqa: S603 - argv is policy-validated by callers
                list(argv),
                cwd=resolved_cwd,
                env=self._safe_environment(),
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise PluginExecutionError(f"Could not start subprocess: {exc}") from exc

        assert process.stdout is not None
        assert process.stderr is not None
        readers = (
            threading.Thread(
                target=self._drain_limited,
                args=(process.stdout, stdout_buffer, budget, budget_lock, truncated),
                daemon=True,
            ),
            threading.Thread(
                target=self._drain_limited,
                args=(process.stderr, stderr_buffer, budget, budget_lock, truncated),
                daemon=True,
            ),
        )
        for reader in readers:
            reader.start()

        timed_out = False
        try:
            exit_code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            exit_code = process.wait()
        for reader in readers:
            reader.join(timeout=2)

        stdout = self._clean_output(stdout_buffer)
        stderr = self._clean_output(stderr_buffer)
        safe_argv = tuple(self._secret_filter.redact_text(argument) for argument in argv)
        return ProcessResult(
            argv=safe_argv,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            truncated=truncated.is_set(),
            timed_out=timed_out,
            duration_seconds=round(time.monotonic() - started, 6),
        )

    def _safe_environment(self) -> dict[str, str]:
        environment: dict[str, str] = {}
        for name, value in self._base_environment.items():
            upper = name.upper()
            if upper not in self._ENV_ALLOWLIST:
                continue
            if any(part in upper for part in self._SECRET_NAME_PARTS):
                continue
            environment[name] = value
        environment.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "NO_COLOR": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUNBUFFERED": "1",
            }
        )
        return environment

    def _clean_output(self, data: bytearray) -> str:
        decoded = data.decode("utf-8", errors="replace")
        return self._secret_filter.redact_text(decoded)[: self._max_output_chars]

    @staticmethod
    def _drain_limited(
        stream: BinaryIO,
        target: bytearray,
        budget: dict[str, int],
        budget_lock: threading.Lock,
        truncated: threading.Event,
    ) -> None:
        try:
            while chunk := stream.read(8_192):
                with budget_lock:
                    accepted = min(len(chunk), budget["remaining"])
                    budget["remaining"] -= accepted
                if accepted:
                    target.extend(chunk[:accepted])
                if accepted < len(chunk):
                    truncated.set()
        finally:
            stream.close()
