"""Experimental restricted Python execution in an isolated child interpreter."""

import hashlib
import sys
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.permissions import Permission
from agentforge.security.python_policy import PythonCodePolicy
from agentforge.security.sandbox import ProcessSandbox
from agentforge.security.secret_filter import SecretFilter


class PythonArguments(BaseModel):
    """Code and a caller-requested timeout bounded by plugin configuration."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=100_000)
    timeout: float | None = Field(default=None, gt=0, le=300)


class PythonPlugin(Plugin):
    """Run AST-checked code in a separate `python -I -S` process."""

    name = "python"
    description = "Run conservative Python snippets in a bounded child process (experimental)."
    action_models: ClassVar = {"run": PythonArguments}
    action_permissions: ClassVar = {
        "run": frozenset({Permission.PYTHON_EXECUTE}),
    }

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        max_output_chars: int = 50_000,
        policy: PythonCodePolicy | None = None,
        secret_filter: SecretFilter | None = None,
    ) -> None:
        self._timeout = timeout
        self._policy = policy or PythonCodePolicy()
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
        args = PythonArguments.model_validate(arguments.model_dump())
        self._policy.validate(args.code)
        result = self._sandbox.run(
            [sys.executable, "-I", "-S", "-c", args.code],
            cwd=context.workspace_root,
            timeout=min(args.timeout or self._timeout, self._timeout),
        )
        return PluginResult.success(
            {
                "command": "python -I -S -c <validated-code>",
                "code_sha256": hashlib.sha256(args.code.encode("utf-8")).hexdigest(),
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "truncated": result.truncated,
                "timed_out": result.timed_out,
                "duration_seconds": result.duration_seconds,
            }
        )
