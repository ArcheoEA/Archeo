"""Application configuration for ArcheoConverter.

The configuration is fully externalized and layered, in this order
(later sources win):

1. built-in defaults (Pydantic field defaults);
2. a JSON configuration file (explicit path > ``ARCHEOCONVERTER_CONFIG``
   environment variable > ``config/app.json`` relative to the current
   working directory);
3. environment variables prefixed with ``ARCHEOCONVERTER__`` using a double
   underscore as nesting separator, e.g.
   ``ARCHEOCONVERTER__SERVER__PORT=9000`` sets ``server.port = 9000``.

Environment variable values are parsed as JSON when possible (numbers,
booleans, lists, objects), otherwise kept as strings.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ArcheoConverter.exceptions import ConfigError

logger = logging.getLogger("archeoconverter.config")

#: Environment variable that may point to an explicit configuration file.
CONFIG_ENV_VAR = "ARCHEOCONVERTER_CONFIG"
#: Prefix of environment variables that override configuration values.
ENV_PREFIX = "ARCHEOCONVERTER__"
#: Default configuration file searched in the current working directory.
DEFAULT_CONFIG_PATH = Path("config") / "app.json"


class ServerConfig(BaseModel):
    """HTTP server settings (host/port used by the ``archeoconverter`` CLI)."""

    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    workers: int = Field(default=1, ge=1)


class LoggingConfig(BaseModel):
    """Logging settings (level + optional rotating file handler)."""

    level: str = "INFO"
    file: str | None = "logs/archeoconverter.log"
    max_bytes: int = Field(default=5_242_880, ge=1024)
    backup_count: int = Field(default=3, ge=0)


class LimitsConfig(BaseModel):
    """Safety limits protecting the in-memory engine against huge inputs."""

    max_upload_mb: int = Field(default=50, ge=1)
    max_search_results: int = Field(default=500, ge=1)
    max_navigation_depth: int = Field(default=5, ge=1, le=20)
    max_graph_nodes: int = Field(default=2000, ge=10)


class FormalismsConfig(BaseModel):
    """Formalism / namespace registry overrides.

    ``namespaces`` maps ``"<formalism>:<version>"`` keys to the root XML
    namespace used when exporting. Parsers are namespace tolerant and use
    these values for export and detection hints only.
    """

    namespaces: dict[str, str] = Field(default_factory=dict)
    accept_any_namespace: bool = True


class ConversionConfig(BaseModel):
    """Default policies applied when a conversion rule has no explicit one."""

    unmapped_element_policy: str = "stereotype"  # keep | stereotype | drop
    unmapped_relationship_policy: str = "drop"  # drop | keep


class ComparisonConfig(BaseModel):
    """Default matching strategy for model comparisons."""

    match_by: str = "id_then_name"  # id | name | id_then_name


class AppConfig(BaseModel):
    """Root configuration object of the application."""

    app_name: str = "ArcheoConverter"
    version: str = "1.0.0"
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    formalisms: FormalismsConfig = Field(default_factory=FormalismsConfig)
    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)
    ui_enabled: bool = True
    data_dir: str = "data"

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def namespace_for(self, formalism: str, version: str) -> str:
        """Return the export namespace for ``formalism:version``."""
        key = f"{formalism}:{version}"
        ns = self.formalisms.namespaces.get(key)
        if ns:
            return ns
        # Fallback: any namespace registered for the same formalism.
        for registered_key, registered_ns in self.formalisms.namespaces.items():
            if registered_key.split(":", 1)[0] == formalism:
                return registered_ns
        return ""


def _parse_env_value(raw: str) -> Any:
    """Parse an environment variable value: JSON when possible, else string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


def _apply_env_overrides(data: dict[str, Any]) -> dict[str, Any]:
    """Overlay ``ARCHEOCONVERTER__`` environment variables onto ``data``."""
    for key, raw in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        path = key[len(ENV_PREFIX):].lower().split("__")
        node: dict[str, Any] = data
        for part in path[:-1]:
            child = node.get(part)
            if not isinstance(child, dict):
                child = {}
                node[part] = child
            node = child
        node[path[-1]] = _parse_env_value(raw)
        logger.debug("config: env override %s -> %r", ".".join(path), node[path[-1]])
    return data


def load_config(path: str | os.PathLike | None = None) -> AppConfig:
    """Load the application configuration.

    Args:
        path: explicit path to a JSON configuration file. When omitted, the
            ``ARCHEOCONVERTER_CONFIG`` environment variable is used, then
            ``config/app.json`` in the current working directory, and finally
            the built-in defaults.

    Raises:
        ConfigError: if the selected file cannot be read or does not contain
            a JSON object, or if the final configuration is invalid.
    """
    data: dict[str, Any] = {}
    source = "defaults"

    candidate: Path | None = None
    if path is not None:
        candidate = Path(path)
    elif os.environ.get(CONFIG_ENV_VAR):
        candidate = Path(os.environ[CONFIG_ENV_VAR])
    elif DEFAULT_CONFIG_PATH.is_file():
        candidate = DEFAULT_CONFIG_PATH

    if candidate is not None:
        try:
            raw = candidate.read_text(encoding="utf-8")
            loaded = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(
                f"Unable to read configuration file '{candidate}': {exc}",
                details=[str(candidate)],
            ) from exc
        if not isinstance(loaded, dict):
            raise ConfigError(
                f"Configuration file '{candidate}' must contain a JSON object."
            )
        data = loaded
        source = str(candidate)

    data = _apply_env_overrides(data)

    try:
        config = AppConfig.model_validate(data)
    except Exception as exc:  # pydantic.ValidationError
        raise ConfigError(
            f"Invalid configuration (source: {source}): {exc}",
            details=[source],
        ) from exc

    logger.info("configuration loaded from: %s", source)
    return config
