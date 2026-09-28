"""Logging configuration for smoosh."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "smoosh", level: int = logging.INFO, log_file: Optional[Path] = None
) -> logging.Logger:
    """Configure and return a logger instance.

    Args:
    ----
        name: Logger name
        level: Logging level
        log_file: Optional path to log file

    Returns:
    -------
        Configured logger instance

    """
    # Create logger
    log = logging.getLogger(name)
    log.setLevel(level)

    # Remove any existing handlers
    for handler in log.handlers[:]:
        log.removeHandler(handler)

    # Create formatters
    console_formatter = logging.Formatter("%(levelname)s: %(message)s")
    file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(console_formatter)
    log.addHandler(console_handler)

    # File handler if log_file is specified
    if log_file is not None:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(file_formatter)
            log.addHandler(file_handler)
        except OSError as e:
            log.warning("Failed to create log file at %s: %s", log_file, e)

    return log


# Create default logger instance
logger = setup_logger()
