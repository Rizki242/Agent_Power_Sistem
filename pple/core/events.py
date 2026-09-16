"""Internal event bus (docs/final.md Phase 28).

Lets components signal "something happened" without importing each other -
e.g. a reporting subscriber can react to `analysis.completed` without the
diagnosis use case knowing reporting exists. In-process only: no queue, no
persistence, no cross-process delivery. That is deliberate for now (no
database yet either, docs/final.md Phase 2-4); this only decouples code
that already runs in the same Python process (FastAPI, Streamlit, CLI).

Every publish is also emitted as a structured log line via
`pple.core.logging.log_event` under the `pple.events` logger, so an event
has an audit trail even with zero subscribers - publishing is never a
no-op, and adding the first real subscriber later needs no change at the
call site.

A subscriber that raises never breaks the publisher: the error is logged
(fail-open, same principle as `pple.core.audit`) and the remaining
subscribers still run.

Wired publishers so far: `pple.application.diagnostics` (analysis.*,
diagnostic.created), `src.domain_ingest.commit_batch` (measurement.uploaded),
`src.work_orders.generate_cbm_work_order` (workorder.requested),
`src.asset_registry.upsert_asset` (equipment.created/updated).
`severity.changed` and `recommendation.created` are declared below but not
yet published anywhere - wiring them needs a "previous value" to compare
against, which no caller currently tracks.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional

from pple.core.logging import log_event

Handler = Callable[[str, Dict[str, Any]], None]


class Events:
    """Canonical event names (docs/final.md Phase 28). Publish only these."""

    EQUIPMENT_CREATED = "equipment.created"
    EQUIPMENT_UPDATED = "equipment.updated"
    MEASUREMENT_UPLOADED = "measurement.uploaded"
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    DIAGNOSTIC_CREATED = "diagnostic.created"
    SEVERITY_CHANGED = "severity.changed"
    RECOMMENDATION_CREATED = "recommendation.created"
    WORKORDER_REQUESTED = "workorder.requested"


ALL_EVENTS = frozenset(
    value for name, value in vars(Events).items() if not name.startswith("_")
)

_lock = threading.Lock()
_subscribers: Dict[str, List[Handler]] = {}


def subscribe(event: str, handler: Handler) -> None:
    """Register `handler(event, payload)` to run whenever `event` is published."""
    if event not in ALL_EVENTS:
        raise ValueError(f"Unknown event '{event}'. Add it to pple.core.events.Events first.")
    with _lock:
        _subscribers.setdefault(event, []).append(handler)


def unsubscribe(event: str, handler: Handler) -> None:
    """Remove a previously registered handler; a no-op if it was never subscribed."""
    with _lock:
        handlers = _subscribers.get(event)
        if handlers and handler in handlers:
            handlers.remove(handler)


def clear_subscribers(event: Optional[str] = None) -> None:
    """Drop all subscribers for one event, or every event if none is given. For tests."""
    with _lock:
        if event is None:
            _subscribers.clear()
        else:
            _subscribers.pop(event, None)


def publish(event: str, **payload: Any) -> None:
    """Log `event` and notify its subscribers. Always safe to call - never raises
    for an unknown event (logged as a warning instead) or a failing subscriber."""
    if event not in ALL_EVENTS:
        log_event(
            event="unknown_event_published",
            level=logging.WARNING,
            logger_name="pple.events",
            attempted_event=event,
        )
        return

    log_event(event=event, logger_name="pple.events", **payload)

    with _lock:
        handlers = list(_subscribers.get(event, ()))
    for handler in handlers:
        try:
            handler(event, payload)
        except Exception as exc:  # fail-open: one bad subscriber must not break the publisher
            log_event(
                event="event_handler_error",
                level=logging.WARNING,
                logger_name="pple.events",
                source_event=event,
                handler=getattr(handler, "__qualname__", repr(handler)),
                error=str(exc),
            )
