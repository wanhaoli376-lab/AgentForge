"""Plugin registration without import-time global state."""

from agentforge.plugins.base import Plugin, PluginManifest
from agentforge.security.permissions import PermissionManager


class PluginRegistry:
    """Own named plugin adapters for one Agent instance."""

    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}

    def register(self, plugin: Plugin) -> None:
        if not plugin.name or plugin.name in self._plugins:
            raise ValueError(f"Plugin name is empty or already registered: {plugin.name!r}")
        plugin.validate_contract()
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Plugin:
        try:
            return self._plugins[name]
        except KeyError as exc:
            raise KeyError(f"Unknown plugin: {name}") from exc

    def manifests(
        self,
        *,
        permissions: PermissionManager | None = None,
    ) -> tuple[PluginManifest, ...]:
        """Describe all actions, or only those available to the current planner.

        This filters discovery only; Plugin.execute still enforces every grant.
        """

        manifests: list[PluginManifest] = []
        for name in sorted(self._plugins):
            plugin = self._plugins[name]
            manifest = plugin.manifest
            if permissions is not None:
                actions = tuple(
                    action
                    for action in manifest.actions
                    if plugin.action_permissions[action] <= permissions.granted
                )
                if not actions:
                    continue
                required = {
                    permission
                    for action in actions
                    for permission in plugin.action_permissions[action]
                }
                manifest = manifest.model_copy(
                    update={
                        "actions": actions,
                        "permissions": tuple(sorted(required, key=str)),
                        "action_schemas": {
                            action: manifest.action_schemas[action] for action in actions
                        },
                    }
                )
            manifests.append(manifest)
        return tuple(manifests)

    def names(self) -> frozenset[str]:
        return frozenset(self._plugins)

    def __contains__(self, name: object) -> bool:
        return name in self._plugins
