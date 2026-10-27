"""
Structured logging setup.

Text output in development, JSON (python-json-logger) otherwise. Every record
carries the current request id (set by the request-id middleware).
"""

import contextvars
import logging
import sys

from app.config import settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


_configured = False


def setup_logging() -> None:
    """Configure the root logger once (idempotent)."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if settings.ENVIRONMENT == "development":
        formatter: logging.Formatter = logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"
        )
    else:
        from pythonjsonlogger import jsonlogger

        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(request_id)s %(message)s"
        )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())
    _configured = True
