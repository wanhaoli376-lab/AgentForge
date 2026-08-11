"""Plugin registration without import-time global state."""

from agentforge.plugins.base import Plugin, PluginManifest


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

    def manifests(self) -> tuple[PluginManifest, ...]:
        return tuple(self._plugins[name].manifest for name in sorted(self._plugins))

    def names(self) -> frozenset[str]:
        return frozenset(self._plugins)

    def __contains__(self, name: object) -> bool:
        return name in self._plugins
