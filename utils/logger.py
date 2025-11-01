"""
Logging system for YT-DLP EZ-UI.
Provides centralized logging with file rotation and console output.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from config.constants import (
    LOG_FILE,
    LOG_FORMAT,
    LOG_DATE_FORMAT,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT,
    CONFIG_DIR
)


def setup_logger(
    name: str = "YT-DLP-EZ-UI",
    level: int = logging.INFO,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up the application logger with file and optional console handlers.

    Args:
        name: Logger name (default: "YT-DLP-EZ-UI")
        level: Logging level (default: logging.INFO)
        console_output: Whether to output to console (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)

    # Ensure log directory exists
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create log directory: {e}", file=sys.stderr)

    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logging: {e}", file=sys.stderr)

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.info(f"Logger '{name}' initialized successfully")
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance. If name is None, returns the root application logger.

    Args:
        name: Logger name (default: None, returns root logger)

    Returns:
        Logger instance
    """
    if name is None:
        return logging.getLogger("YT-DLP-EZ-UI")
    return logging.getLogger(f"YT-DLP-EZ-UI.{name}")


class LoggerMixin:
    """
    Mixin class to add logging capability to any class.
    Automatically creates a logger based on the class name.
    """

    @property
    def logger(self) -> logging.Logger:
        """Get a logger instance for this class."""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger
