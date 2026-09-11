"""Structured Logging & Observability framework for PPLE V2.

Provides contextual, JSON-compatible structured logging with correlation ID
propagation across FastAPI requests, CLI sessions, and background agents.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Context variable to hold request/session correlation ID across async and sync calls
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> Optional[str]:
    """Retrieve the active correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(corr_id: Optional[str]) -> None:
    """Set the active correlation ID in context."""
    correlation_id_var.set(corr_id)


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON lines with contextual metadata."""

    def format(self, record: logging.LogRecord) -> str:
        data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        corr_id = get_correlation_id()
        if corr_id:
            data["correlation_id"] = corr_id

        # Attach custom structured attributes if provided via extra={"structured": ...}
        structured = getattr(record, "structured", None)
        if isinstance(structured, dict):
            data.update(structured)

        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        return json.dumps(data, ensure_ascii=False)


_configured_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str = "pple") -> logging.Logger:
    """Obtain or configure a structured logger instance."""
    if name in _configured_loggers:
        return _configured_loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers if already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    _configured_loggers[name] = logger
    return logger


_app_logger = get_logger("pple.core")


def log_event(
    event: str,
    level: int = logging.INFO,
    logger_name: str = "pple.core",
    **metadata: Any,
) -> None:
    """Emit a structured event with contextual metadata."""
    logger = get_logger(logger_name)
    payload = {"event": event, **metadata}
    logger.log(level, event, extra={"structured": payload})


def log_ingest(
    domain: str,
    file_name: str,
    status: str,
    record_count: Optional[int] = None,
    **extra: Any,
) -> None:
    """Log condition data ingestion events (DGA, Vibrasi, etc.)."""
    log_event(
        event="data_ingest",
        logger_name="pple.ingest",
        domain=domain,
        file_name=file_name,
        status=status,
        record_count=record_count,
        **extra,
    )


def log_diagnosis(
    equipment: str,
    health_index: Optional[float],
    health_status: str,
    duration_ms: Optional[float] = None,
    **extra: Any,
) -> None:
    """Log diagnostic fusion and condition assessment calculations."""
    log_event(
        event="diagnostic_fusion",
        logger_name="pple.diagnosis",
        equipment=equipment,
        health_index=health_index,
        health_status=health_status,
        duration_ms=round(duration_ms, 2) if duration_ms is not None else None,
        **extra,
    )


def log_report_generation(
    report_id: str,
    equipment: str,
    report_type: str = "CBM_ASSESSMENT",
    status: str = "SUCCESS",
    **extra: Any,
) -> None:
    """Log report generation events."""
    log_event(
        event="report_generation",
        logger_name="pple.reports",
        report_id=report_id,
        equipment=equipment,
        report_type=report_type,
        status=status,
        **extra,
    )


def log_fallback(
    component: str,
    reason: str,
    fallback_used: str,
    **extra: Any,
) -> None:
    """Log fallback invocations (e.g. AI provider to rule-based fallback)."""
    log_event(
        event="provider_fallback",
        level=logging.WARNING,
        logger_name="pple.fallback",
        component=component,
        reason=reason,
        fallback_used=fallback_used,
        **extra,
    )
