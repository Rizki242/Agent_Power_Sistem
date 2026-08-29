"""Generic /api/v2/* REST API (docs/final.md Phase 24).

Additive only: mounted alongside the existing legacy /api/* routes in
api_server.py via app.include_router(router) - does not replace, modify,
or duplicate any existing endpoint. Legacy /api/* stays the source of
truth for the current UI; /api/v2/* is where the module-registry-driven
architecture is exposed as it grows.
"""

from fastapi import APIRouter, HTTPException

from pple.core.exceptions import ModuleNotRegisteredError
from pple.engineering.base import EngineeringModule
from pple.engineering.bootstrap import register_builtin_modules
from pple.engineering.registry import registry

register_builtin_modules()

router = APIRouter(prefix="/api/v2", tags=["engineering-modules-v2"])


def _module_summary(module: EngineeringModule) -> dict:
    return {
        "id": module.id,
        "name": module.name,
        "version": module.version,
        "applicable_equipment": module.applicable_equipment,
    }


@router.get("/modules")
def list_modules():
    return {"modules": [_module_summary(m) for m in registry.list()]}


@router.get("/modules/{module_id}")
def get_module(module_id: str):
    try:
        module = registry.get(module_id)
    except ModuleNotRegisteredError:
        raise HTTPException(status_code=404, detail=f"Engineering module '{module_id}' not found")
    return _module_summary(module)
