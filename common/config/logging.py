"""Structured JSON logging configuration with automatic secret sanitization."""

import json
import logging
import sys
from datetime import UTC, datetime

from common.auth.sanitizer import sanitize
from common.config.settings import settings


class SanitizingFilter(logging.Filter):
    """Log filter that scrubs API keys, hashes, and credentials from all log records.

    Attached to the root logger so every log message — including third-party
    libraries — is sanitized before it reaches any handler.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Sanitize the main message
        if record.args:
            # Format the message with args first, then sanitize
            try:
                record.msg = sanitize(record.msg % record.args)
                record.args = None
            except (TypeError, ValueError):
                record.msg = sanitize(str(record.msg))
        else:
            record.msg = sanitize(str(record.msg))

        # Sanitize exception info — eagerly format and sanitize the traceback
        # so it's clean before any handler (including pytest's caplog) sees it.
        if record.exc_info and record.exc_info[0] is not None:
            # Format the exception now and sanitize it
            formatter = logging.Formatter()
            record.exc_text = sanitize(formatter.formatException(record.exc_info))
            record.exc_info = None  # Prevent double-formatting
        elif record.exc_text:
            record.exc_text = sanitize(record.exc_text)

        # Sanitize extra fields that might contain secrets
        for attr in ("path", "method"):
            if hasattr(record, attr):
                val = getattr(record, attr)
                if isinstance(val, str):
                    setattr(record, attr, sanitize(val))

        return True


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON for Render / cloud log aggregators."""

    def __init__(self, service_name: str = "ai-identity-api", **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
            "environment": settings.environment,
        }

        # Add exception info if present — sanitize the traceback
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = sanitize(self.formatException(record.exc_info))

        # Add extra fields if attached
        for key in ("request_id", "method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        return json.dumps(log_entry)


def setup_logging(service_name: str = "ai-identity-api") -> None:
    """Configure structured JSON logging to stdout with automatic secret sanitization.

    Args:
        service_name: Identifies the service in log entries.
            Use "ai-identity-api" for the identity service,
            "ai-identity-gateway" for the proxy gateway.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Remove any existing handlers and filters
    root.handlers.clear()
    root.filters.clear()

    # Attach sanitizing filter to root logger — scrubs ALL log output
    root.addFilter(SanitizingFilter())

    # JSON handler → stdout (Render captures stdout)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name=service_name))
    root.addHandler(handler)

    # Quiet down noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if settings.debug else logging.WARNING
    )
