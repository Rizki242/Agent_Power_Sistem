"""API Routers package."""

from pple.api.routers.agents import router as agents_router
from pple.api.routers.equipment import router as equipment_router
from pple.api.routers.knowledge import router as knowledge_router
from pple.api.routers.reports import router as reports_router
from pple.api.routers.vibration import router as vibration_router
from pple.api.routers.work_orders import router as work_orders_router

__all__ = [
    "agents_router",
    "equipment_router",
    "knowledge_router",
    "reports_router",
    "vibration_router",
    "work_orders_router",
]
