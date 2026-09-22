"""Event bus subscribers for PPLE V2.
Binds events like RECOMMENDATION_CREATED or WORKORDER_REQUESTED to the audit log.
"""
from typing import Any, Dict
from pple.core.events import subscribe, Events
from pple.core.audit import record_change

def on_recommendation_created(event_name: str, payload: Dict[str, Any]) -> None:
    """Subscriber to log AI recommendations or generated suggestions to the audit trail."""
    equipment = payload.get("equipment")
    source = payload.get("source", "CHATBOT")
    text = payload.get("text_snippet", "")
    
    if equipment:
        record_change(
            entity=equipment,
            field="recommendation_generated",
            old_value=None,
            new_value="RECOMMENDED",
            source=source,
            details={"text": text}
        )

def on_workorder_requested(event_name: str, payload: Dict[str, Any]) -> None:
    """Subscriber to log Work Order requests to the audit trail."""
    equipment = payload.get("equipment")
    domain = payload.get("domain", "CBM")
    wo_number = payload.get("wo_number")
    priority = payload.get("priority")
    
    if equipment and wo_number:
        record_change(
            entity=equipment,
            field="workorder_requested",
            old_value=None,
            new_value=wo_number,
            source="SYSTEM",
            details={"domain": domain, "priority": priority}
        )

def init_subscribers() -> None:
    """Register all application-level event handlers."""
    subscribe(Events.RECOMMENDATION_CREATED, on_recommendation_created)
    subscribe(Events.WORKORDER_REQUESTED, on_workorder_requested)

