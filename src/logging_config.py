"""Centralized logging configuration for NewLearner.

Logs are written to `logs/YYYY-MM-DD.log` under the project root.
Same-day restarts append to the existing file; new day creates a new file.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

# Resolve project root (parent of src/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"

_INITIALIZED = False

# Endpoints to suppress from uvicorn access log (polling / health-check)
_SUPPRESSED_ENDPOINTS = ("/api/boot-time",)


class _PollingEndpointFilter(logging.Filter):
    """Suppress access-log entries for high-frequency polling endpoints."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(ep in msg for ep in _SUPPRESSED_ENDPOINTS)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure project-wide logging.

    Call once at application entry point (app.py, cli.py).
    Subsequent calls are no-ops.
    """
    global _INITIALIZED
    if _INITIALIZED:
        return
    _INITIALIZED = True

    _LOG_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = _LOG_DIR / f"{today}.log"

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-28s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — append mode so same-day restarts continue writing
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — only WARNING+ to avoid duplicating uvicorn output
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)

    # Configure the root "newlearner" logger
    root_logger = logging.getLogger("newlearner")
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Also capture uvicorn access log into our file
    for uvicorn_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        uv_logger = logging.getLogger(uvicorn_name)
        uv_logger.addHandler(file_handler)

    # Filter out noisy polling endpoints from uvicorn access log
    logging.getLogger("uvicorn.access").addFilter(_PollingEndpointFilter())

    root_logger.info("=" * 72)
    root_logger.info("NewLearner logging started — log file: %s", log_file)
    root_logger.info("=" * 72)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the ``newlearner`` namespace.

    Usage::

        from src.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("something happened")
    """
    return logging.getLogger(f"newlearner.{name}")
