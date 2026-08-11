# Plugin Development

A Plugin answers “what can the Agent call?” It should expose a small action interface and keep
validation, policy, timeouts, result shaping, and external-client details behind that interface.

## Minimal Plugin

```python
from typing import ClassVar

from pydantic import BaseModel, Field

from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.security.permissions import Permission


class GreetArguments(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class HelloPlugin(Plugin):
    name = "hello"
    version = "0.1.0"
    description = "Return a safe greeting."
    action_models: ClassVar = {"greet": GreetArguments}
    action_permissions: ClassVar = {"greet": frozenset()}

    def _execute(self, action, arguments, context):
        del action, context
        args = GreetArguments.model_validate(arguments.model_dump())
        return PluginResult.success({"message": f"Hello, {args.name}!"})
```

Register it explicitly:

```python
registry.register(HelloPlugin())
```

See the complete [`hello_plugin`](../examples/plugins/hello_plugin/) example.

## Interface contract

Every Plugin declares:

- a stable lowercase `name`, semantic `version`, and concise `description`;
- a mapping from action names to Pydantic argument models;
- permissions for every action, including an explicit empty set for no capability;
- structured `PluginResult` data with bounded output;
- expected error behavior without credentials or sensitive internal details.

Do not override `execute`. The base method owns permission and argument validation. Put behavior in
`_execute`, and re-validate/cast the action model there for static type clarity.

## Permission selection

Use the narrowest action-level permission:

- `FILESYSTEM_READ`, `FILESYSTEM_WRITE`, `FILESYSTEM_DELETE`
- `SHELL_EXECUTE`, `PYTHON_EXECUTE`
- `NETWORK_ACCESS`
- `GITHUB_READ`, `GITHUB_WRITE`

Do not request all Plugin permissions for a read action. A Plugin cannot infer a permission from
prompt text or silently upgrade it.

## External systems

External clients belong behind a small adapter and should be injectable in tests. Apply:

- explicit host/domain allowlists;
- HTTPS and private-IP denial;
- connection/read timeout;
- response/body limits before parsing;
- no automatic redirects across trust boundaries;
- environment credentials rather than config literals;
- secret-free error messages and logs.

Mock only the external system boundary. Tests should otherwise call `Plugin.execute` so schemas,
permissions, policy, and result shaping run together.

## Executable Plugins

Never use `shell=True`. Accept an argv list, validate it, resolve a trusted executable, set the
workspace as `cwd`, filter environment variables, close stdin, enforce timeout, and cap output.
Even then, document that a subprocess is not an OS sandbox. Running a repository's tests executes
repository code.

## Third-party manifest

Until signed Plugin distribution is designed, include a reviewable manifest alongside examples:

```yaml
name: hello
version: 0.1.0
author: Example contributor
entrypoint: plugin:HelloPlugin
actions: [greet]
permissions: []
```

v0.1 does not automatically discover or install this entry point. Consumers review the code and
register it explicitly. This is an intentional supply-chain safety choice.

## Review checklist

- Are action arguments strict, bounded, and unambiguous?
- Are permissions checked before any side effect?
- Can a path, URL, redirect, symlink, command flag, or environment variable escape policy?
- Can result, error, or logging data reveal a token?
- Is output bounded before it enters memory or LLM context?
- Are unknown failures converted to safe structured errors?
- Do tests include an adversarial case under `tests/security/`?
