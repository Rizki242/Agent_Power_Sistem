"""API Routers package."""

from pple.api.routers.knowledge import router as knowledge_router
from pple.api.routers.vibration import router as vibration_router
from pple.api.routers.work_orders import router as work_orders_router

__all__ = ["knowledge_router", "vibration_router", "work_orders_router"]
