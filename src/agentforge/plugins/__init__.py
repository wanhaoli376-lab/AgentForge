"""AgentForge plugin interfaces and built-in adapters."""

from agentforge.plugins.base import Plugin, PluginContext, PluginResult
from agentforge.plugins.registry import PluginRegistry

__all__ = ["Plugin", "PluginContext", "PluginRegistry", "PluginResult"]
