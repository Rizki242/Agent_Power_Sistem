"""Cross-cutting primitives (exceptions, audit, logging)."""

from pple.core.logging import (
    get_correlation_id,
    get_logger,
    log_diagnosis,
    log_event,
    log_fallback,
    log_ingest,
    log_report_generation,
    set_correlation_id,
)

__all__ = [
    "get_correlation_id",
    "get_logger",
    "log_diagnosis",
    "log_event",
    "log_fallback",
    "log_ingest",
    "log_report_generation",
    "set_correlation_id",
]
