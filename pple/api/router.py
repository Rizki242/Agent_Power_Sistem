"""Generic /api/v2/* REST API (docs/final.md Phase 24).

Additive only: mounted alongside the existing legacy /api/* routes in
api_server.py via app.include_router(router) - does not replace, modify,
or duplicate any existing endpoint. Legacy /api/* stays the source of
truth for the current UI; /api/v2/* is where the module-registry-driven
architecture is exposed as it grows.

The registry backing these routes is populated by scanning
pple/engineering/manifests/*.yaml (docs/final.md Phase 6-7) rather than
registering built-in modules directly, so /api/v2/module-load-report
reflects real manifest validation/load status.
"""

from fastapi import APIRouter, HTTPException

from pple.core.exceptions import ModuleNotRegisteredError
from pple.engineering.base import EngineeringModule
from pple.engineering.loader import load_modules_from_manifests

_registry, _load_results = load_modules_from_manifests()

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
    return {"modules": [_module_summary(m) for m in _registry.list()]}


@router.get("/modules/{module_id}")
def get_module(module_id: str):
    try:
        module = _registry.get(module_id)
    except ModuleNotRegisteredError:
        raise HTTPException(status_code=404, detail=f"Engineering module '{module_id}' not found")
    return _module_summary(module)


@router.get("/module-load-report")
def module_load_report():
    """Per-manifest load status (ACTIVE/DISABLED/ERROR/INCOMPATIBLE)."""
    return {"results": [r.to_dict() for r in _load_results]}
