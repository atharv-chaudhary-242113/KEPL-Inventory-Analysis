# src/logger_config.py
"""
Centralised Logging Configuration module.

Establishes deterministic log formatting and rotation policies.
Forces handler primacy over third-party library defaults.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import os


def setup_logger() -> None:
    """
    Configure the root logger with dual handlers: file (DEBUG) and console (INFO).
    Purges any pre-existing handlers established by external dependencies.
    """
    root_logger = logging.getLogger()

    # Force purge existing handlers injected by third-party libraries (e.g., matplotlib)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(module)s] — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    project_root = Path(__file__).resolve().parent.parent
    log_dir = project_root / 'logs'
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / 'app.log'

    file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Prevent propagation bypass
    root_logger.propagate = False