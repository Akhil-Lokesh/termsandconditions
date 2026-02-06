"""Logging configuration and utilities."""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str, level: int = logging.INFO, format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.

    Since main.py calls logging.basicConfig() which sets up the root logger,
    we don't need to add our own handlers - just return the logger.
    This prevents duplicate log messages.

    Args:
        name: Logger name (typically __name__)
        level: Logging level
        format_string: Custom format string (optional)

    Returns:
        logging.Logger: Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Don't add handlers - let the root logger (configured in main.py) handle output
    # This prevents duplicate log messages
    # Set propagate to True so logs go to root logger
    logger.propagate = True

    return logger
