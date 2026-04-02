"""Structured logging setup using structlog.

Dev environment: colored console output.
Production: JSON lines.
"""

from __future__ import annotations

import os
import uuid

import structlog


def setup_logging(*, env: str | None = None) -> None:
    """Configure structlog for the given environment.

    Args:
        env: "development" for console renderer, "production" for JSON.
             Defaults to XSPY_ENV env var, falling back to "development".
    """
    env = env or os.getenv("XSPY_ENV", "development")

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if env == "production":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer(ensure_ascii=False)
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            _log_level_from_env(),
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def new_trace_id() -> str:
    """Generate a short trace ID for a pipeline run."""
    return uuid.uuid4().hex[:12]


def _log_level_from_env() -> int:
    """Map XSPY_LOG__LEVEL env var to structlog log level int."""
    import logging

    level_name = os.getenv("XSPY_LOG__LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)
