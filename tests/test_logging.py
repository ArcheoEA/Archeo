"""Tests for :mod:`ArcheoConverter.logging_config`."""

from __future__ import annotations

import logging

import pytest

from ArcheoConverter.config import AppConfig, LoggingConfig
from ArcheoConverter.logging_config import ROOT_LOGGER_NAME, setup_logging


def test_console_handler_always_present(tmp_path):
    """A console handler is attached even when no log file is configured."""
    config = LoggingConfig(level="DEBUG", file=None)
    logger = setup_logging(config, force=True)
    names = [type(h).__name__ for h in logger.handlers]
    assert "StreamHandler" in names
    assert logger.level == logging.DEBUG


def test_rotating_file_handler_created(tmp_path):
    """A rotating file handler is created when a file is configured."""
    log_file = tmp_path / "logs" / "test.log"
    config = LoggingConfig(level="INFO", file=str(log_file), max_bytes=1024, backup_count=1)
    logger = setup_logging(config, force=True)
    file_handlers = [h for h in logger.handlers if type(h).__name__ == "RotatingFileHandler"]
    assert len(file_handlers) == 1
    logger.info("hello from test")
    for handler in logger.handlers:
        handler.flush()
    assert log_file.exists()
    assert "hello from test" in log_file.read_text(encoding="utf-8")


def test_bad_file_does_not_break_setup(tmp_path):
    """An unwritable log file degrades gracefully (console only)."""
    blocker = tmp_path / "afile.log"
    blocker.write_text("x", encoding="utf-8")
    # 'afile.log' is a file, so the sub-path cannot be created (OSError).
    bad_path = blocker / "sub" / "x.log"
    config = LoggingConfig(level="INFO", file=str(bad_path))
    logger = setup_logging(config, force=True)
    # The console handler must still be present.
    assert any(type(h).__name__ == "StreamHandler" for h in logger.handlers)


def test_force_removes_previous_handlers():
    """force=True detaches previously attached handlers."""
    config = LoggingConfig(level="INFO", file=None)
    logger1 = setup_logging(config, force=True)
    count1 = len(logger1.handlers)
    logger2 = setup_logging(config, force=True)
    assert logger2 is logger1
    assert len(logger2.handlers) == count1  # no accumulation
