"""Structured logging configuration for the Trip Planner API."""

import logging
import sys
import contextvars


request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)


class _RequestIDFilter(logging.Filter):
    """Injects the per-request correlation ID into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


def _make_formatter() -> logging.Formatter:
    return logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "request=%(request_id)s | %(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str = "trip_planner") -> logging.Logger:
    """Return a logger pre-configured with the request‑ID filter."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(_make_formatter())
    handler.addFilter(_RequestIDFilter())
    logger.addHandler(handler)

    return logger


logger = get_logger("trip_planner.api")
