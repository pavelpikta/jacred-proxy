"""Logging setup."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from jacred_proxy.config import Settings, get_settings

LOG_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(settings: Settings | None = None) -> logging.Logger:
    """Configure rotating file + console handlers (idempotent)."""
    global _configured
    settings = settings or get_settings()
    logger = logging.getLogger("jacred_proxy")
    if _configured:
        return logger

    level = getattr(logging, settings.log_level, logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    try:
        file_handler = RotatingFileHandler(
            settings.log_file, maxBytes=10_485_760, backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    except Exception as exc:
        print(f"Failed to setup logging: {exc}", file=sys.stderr)

    _configured = True
    logger.info("Torznab proxy started")
    logger.info("Backend base URL: %s", settings.base_url)
    logger.info("Log level: %s", settings.log_level)
    return logger


def get_logger() -> logging.Logger:
    """Module logger (call ``setup_logging`` once at startup)."""
    return logging.getLogger("jacred_proxy")
