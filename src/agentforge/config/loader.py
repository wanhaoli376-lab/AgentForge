"""Load AgentForge configuration from YAML or TOML."""

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from agentforge.config.models import AppConfig


class ConfigError(ValueError):
    """Raised when a configuration file cannot be safely interpreted."""


def _read_mapping(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ConfigError(f"Could not read config file: {path}") from exc

    try:
        if path.suffix.lower() == ".toml":
            value = tomllib.loads(raw.decode("utf-8"))
        elif path.suffix.lower() in {".yaml", ".yml"}:
            value = yaml.safe_load(raw.decode("utf-8")) or {}
        else:
            raise ConfigError("Config files must use .toml, .yaml, or .yml")
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"Invalid config file: {path}") from exc

    if not isinstance(value, Mapping):
        raise ConfigError("The top level of the config file must be a mapping")
    return dict(value)


def load_config(
    path: Path | str | None = None,
    *,
    workspace_root: Path | str | None = None,
) -> AppConfig:
    """Load and validate configuration, resolving its workspace root.

    Relative roots in a file are resolved from that file's directory. Without a
    file they are resolved from the current working directory.
    """

    config_path = Path(path).expanduser().resolve() if path is not None else None
    data = _read_mapping(config_path) if config_path is not None else {}
    base_dir = config_path.parent if config_path is not None else Path.cwd()

    raw_workspace = data.get("workspace", {})
    if not isinstance(raw_workspace, Mapping):
        raise ConfigError("The workspace configuration must be a mapping")
    workspace_data = dict(raw_workspace)
    configured_root = (
        Path(workspace_root)
        if workspace_root is not None
        else Path(workspace_data.get("root", "."))
    )
    if not configured_root.is_absolute():
        configured_root = base_dir / configured_root
    workspace_data["root"] = configured_root.expanduser().resolve()
    data["workspace"] = workspace_data

    try:
        return AppConfig.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Configuration validation failed: {exc}") from exc
