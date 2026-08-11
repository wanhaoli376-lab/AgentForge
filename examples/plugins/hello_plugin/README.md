# Hello Plugin

This example shows the smallest safe community Plugin:

1. `GreetArguments` rejects unknown fields and bounds user text.
2. `HelloPlugin` declares one action and an explicit empty permission set.
3. `_execute` returns a structured result and performs no side effect.
4. `plugin.yaml` makes provenance and requested capabilities reviewable.

Explicit registration:

```python
from pathlib import Path

from agentforge.plugins.base import PluginContext
from agentforge.plugins.registry import PluginRegistry
from agentforge.security.permissions import PermissionManager

from plugin import HelloPlugin

registry = PluginRegistry()
registry.register(HelloPlugin())
result = registry.get("hello").execute(
    "greet",
    {"name": "Contributor"},
    PluginContext(Path.cwd(), PermissionManager(set())),
)
print(result.data["message"])
```

Automatic package discovery is not implemented in v0.1. Review third-party Python before importing
and register it explicitly. Add permissions only when an action actually needs a capability.
