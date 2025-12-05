"""
utils/logging_setup.py
----------------------

Central logging configuration for Abstract Wiki Architect.

Goals:
- Provide a single place to configure logging format and level.
- Make it easy to get a logger in any module:
      from utils.logging_setup import get_logger
      log = get_logger(__name__)
- Allow overrides via environment variables:
      AW_LOG_LEVEL   (e.g. DEBUG, INFO, WARNING, ERROR)
      AW_LOG_FILE    (path to a log file; if unset, log to stderr only)

Usage
=====

In your module:

    from utils.logging_setup import get_logger

    log = get_logger(__name__)

    log.info("Starting Romance engine")
    log.debug("Config: %s", config)

In your CLI script (optional):

    from utils.logging_setup import init_logging

    if __name__ == "__main__":
        init_logging()  # ensures consistent global config

Implementation notes
====================

- We use Python's built-in `logging` module.
- `init_logging` is idempotent; calling it multiple times is safe.
- The default level is INFO, with a concise format including timestamp,
  level, logger name, and message.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

# Internal flag to avoid re-configuring logging multiple times
_INITIALIZED = False

# Default format and date format
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_env_log_level() -> int:
    """
    Read AW_LOG_LEVEL from environment and map it to a logging level.
    Defaults to logging.INFO if unset or invalid.
    """
    level_name = os.getenv("AW_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def init_logging(
    level: Optional[int] = None,
    log_to_file: bool = False,
    filename: Optional[str] = None,
    *,
    force: bool = False,
) -> None:
    """
    Initialize root logging configuration.

    Args:
        level:
            Logging level (e.g. logging.DEBUG). If None, it is read from
            the AW_LOG_LEVEL environment variable, defaulting to INFO.
        log_to_file:
            If True, log to a file instead of (or in addition to) stderr.
            If False, log only to stderr.
        filename:
            Path to the log file. If None and log_to_file is True, we
            default to "abstract_wiki.log" in the current working directory.
        force:
            If True, reconfigure logging even if it was already initialized.
    """
    global _INITIALIZED

    if _INITIALIZED and not force:
        return

    if level is None:
        level = _get_env_log_level()

    log_file_env = os.getenv("AW_LOG_FILE")
    if log_file_env:
        log_to_file = True
        filename = log_file_env

    handlers = []

    # Console handler (stderr)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
    )
    handlers.append(console_handler)

    # Optional file handler
    if log_to_file:
        if not filename:
            filename = "abstract_wiki.log"
        file_handler = logging.FileHandler(filename, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter(DEFAULT_LOG_FORMAT, DEFAULT_DATE_FORMAT)
        )
        handlers.append(file_handler)

    # Use basicConfig with our custom handlers
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,  # reset any previous basicConfig
    )

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name, ensuring logging is initialized.

    If logging has not been initialized yet, this will initialize it with
    default settings (level from AW_LOG_LEVEL, stderr output only).

    Args:
        name:
            Logger name, usually __name__ of the calling module.

    Returns:
        A `logging.Logger` instance.
    """
    if not _INITIALIZED:
        init_logging()
    return logging.getLogger(name)


__all__ = ["init_logging", "get_logger"]
