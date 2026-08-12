"""Application logging configured with credential redaction."""

import logging
from collections.abc import Collection, Mapping
from io import TextIOBase

from agentforge.security.secret_filter import RedactingLogFilter, SecretFilter


def configure_logging(
    *,
    level: str = "INFO",
    stream: TextIOBase | None = None,
    environ: Mapping[str, str] | None = None,
    additional_secret_names: Collection[str] = (),
) -> logging.Logger:
    """Configure the AgentForge logger for a CLI process."""

    logger = logging.getLogger("agentforge")
    logger.setLevel(level.upper())
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    secret_filter = SecretFilter.from_environment(
        environ,
        additional_names=additional_secret_names,
    )
    handler.addFilter(RedactingLogFilter(secret_filter))
    logger.handlers = [handler]
    logger.propagate = False
    return logger
