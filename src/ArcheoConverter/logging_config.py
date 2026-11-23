"""Logging setup for ArcheoConverter.

A single root logger named ``archeoconverter`` is configured with:

* a console handler (always present);
* an optional rotating file handler (``logging.file`` in the configuration).

Every module of the engine obtains its own child logger through
``logging.getLogger("archeoconverter.<module>")`` so that logs are easy to
filter per component.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from ArcheoConverter.config import LoggingConfig

#: Root logger name shared by the whole application.
ROOT_LOGGER_NAME = "archeoconverter"

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(config: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """Configure and return the application root logger.

    Args:
        config: the logging section of the application configuration.
        force: when True, previously attached handlers are removed first
            (useful in tests and when the server is reloaded).

    Returns:
        The configured root logger.
    """
    root = logging.getLogger(ROOT_LOGGER_NAME)
    root.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    if force:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            try:
                handler.close()
            except Exception:  # pragma: no cover - defensive
                pass

    formatter = logging.Formatter(_FORMAT)

    console = logging.StreamHandler(stream=sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    if config.file:
        try:
            log_path = Path(config.file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError as exc:
            # Logging must never prevent the application from starting.
            root.warning("unable to create log file %r: %s", config.file, exc)

    # Silence noisy third-party loggers a bit.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    return root
