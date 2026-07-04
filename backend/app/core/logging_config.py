"""
Centralized logging configuration.

Design decision
----------------
We log structured JSON (one JSON object per line) rather than free-text
strings. In production this is what lets you ship logs straight into
tools like ELK / Datadog / CloudWatch Logs Insights and query them
(e.g. "show me all ERROR logs for request_id=X"), instead of grepping
raw text.

In local development, JSON logs are hard to read by eye, so we switch
to a human-readable formatter when `settings.DEBUG` is True. This is a
common pattern: dev-friendly output locally, machine-friendly output
in production.
"""

import logging
import sys
from logging import Logger

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        import json

        log_entry = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def configure_logging() -> None:
    """
    Configures the root logger once, at application startup.

    Called exactly once from `app.main` on startup — logging config
    should never be scattered across modules with each one calling
    `logging.basicConfig()` independently, which leads to duplicate
    handlers and inconsistent formats.
    """
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.DEBUG:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    else:
        formatter = JSONFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    # Quiet down noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> Logger:
    """
    Returns a named logger.

    Usage: `logger = get_logger(__name__)` at the top of any module.
    Using `__name__` means log lines are automatically traceable to the
    exact module that emitted them.
    """
    return logging.getLogger(name)
