"""Centralized logging configuration for cloud-resource-inefficiency."""

import logging
import logging.config
import os
from typing import Any, Dict, Optional


def get_log_level() -> str:
    """
    Get log level from environment variable or default to INFO.

    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    level = os.getenv("CRI_LOG_LEVEL", "INFO").upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    return level if level in valid_levels else "INFO"


def get_log_format() -> str:
    """
    Get log format string from environment or use default.

    Returns:
        Log format string.
    """
    return os.getenv(
        "CRI_LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def configure_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configure centralized logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses CRI_LOG_LEVEL env var or defaults to INFO.
        log_format: Log format string. If None, uses default format.
        log_file: Path to log file. If None, logs to console only.

    Environment Variables:
        CRI_LOG_LEVEL: Log level (default: INFO)
        CRI_LOG_FORMAT: Log format string
        CRI_LOG_FILE: Path to log file
    """
    log_level = level or get_log_level()
    log_fmt = log_format or get_log_format()
    log_path = log_file or os.getenv("CRI_LOG_FILE")

    handlers: Dict[str, Any] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": log_level,
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        }
    }

    if log_path:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "level": log_level,
            "formatter": "standard",
            "filename": log_path,
            "mode": "a",
            "encoding": "utf-8",
        }

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": log_fmt,
            },
        },
        "handlers": handlers,
        "root": {
            "level": log_level,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            "cloud_resource_inefficiency": {
                "level": log_level,
                "propagate": True,
            },
        },
    }

    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for a module.

    Args:
        name: Logger name (typically __name__ from calling module).

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


# Configure logging on module import with environment variables
try:
    configure_logging()
except Exception:  # pragma: no cover
    # Fallback to basic configuration if dict config fails
    logging.basicConfig(
        level=get_log_level(),
        format=get_log_format(),
    )
