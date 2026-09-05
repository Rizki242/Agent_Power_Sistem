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
from pydantic import BaseModel

from pple.assets.registry import AssetRegistry
from pple.core.exceptions import ModuleNotRegisteredError
from pple.engineering.base import EngineeringModule
from pple.engineering.equipment_modules import EquipmentModuleStore
from pple.engineering.loader import load_modules_from_manifests
from pple.reliability import ReliabilityFusionEngine

_registry, _load_results = load_modules_from_manifests()
_equipment_module_store = EquipmentModuleStore()
_asset_registry = AssetRegistry()
_reliability_engine = ReliabilityFusionEngine()

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


class SetEquipmentModuleRequest(BaseModel):
    enabled: bool


@router.get("/equipment/{equipment_id}/modules")
def list_equipment_modules(equipment_id: str):
    """Which engineering modules are enabled for this equipment instance
    (docs/final.md Phase 8) - same data the `pple equipment modules` CLI
    command shows, read from the same EquipmentModuleStore."""
    return {
        "equipment_id": equipment_id,
        "modules": [
            {
                "module_id": m.id,
                "name": m.name,
                "enabled": _equipment_module_store.is_enabled(equipment_id, m.id),
            }
            for m in _registry.list()
        ],
    }


@router.put("/equipment/{equipment_id}/modules/{module_id}")
def set_equipment_module(equipment_id: str, module_id: str, body: SetEquipmentModuleRequest):
    """Enable/disable one engineering module for one equipment instance -
    same effect as `pple equipment module-add`/`module-remove`. Does not
    itself change any currently-running analysis; SubAgentCoordinator and
    ReliabilityFusionAgent each read the store fresh via
    EquipmentModuleStore().is_enabled() the next time they run."""
    try:
        _registry.get(module_id)
    except ModuleNotRegisteredError:
        raise HTTPException(status_code=404, detail=f"Engineering module '{module_id}' not found")
    _equipment_module_store.set_enabled(equipment_id, module_id, body.enabled)
    return {"equipment_id": equipment_id, "module_id": module_id, "enabled": body.enabled}


@router.get("/assets/tree")
def assets_tree(domain: str = None):
    """Full Plant -> Unit -> Equipment hierarchy (docs/final.md Phase 3),
    read-through from src.dga_data / src.vibration_data - see
    pple.assets.registry for why this isn't a separate persisted store."""
    return _asset_registry.plant(domain=domain).to_dict()


@router.get("/assets")
def assets_list(unit: str = None, domain: str = None):
    """Flat equipment list, optionally filtered by unit and/or domain."""
    return {"equipment": [e.to_dict() for e in _asset_registry.list_equipment(unit=unit, domain=domain)]}


@router.get("/assets/{equipment_id}")
def assets_get(equipment_id: str, domain: str = None):
    eq = _asset_registry.get_equipment(equipment_id, domain=domain)
    if eq is None:
        raise HTTPException(status_code=404, detail=f"Equipment '{equipment_id}' not found")
    return eq.to_dict()


@router.get("/reliability/{equipment_id}")
def reliability_health(equipment_id: str, criticality: str = "B"):
    """Fuse every domain's latest real measurement for this equipment into
    one health/risk/RUL picture (docs/final.md Phase 11) - the read-through
    pple.assets registry plus pple.engineering's module registry, never a
    fabricated score for a domain with no data (see FusionResult.notes)."""
    try:
        result = _reliability_engine.fuse_equipment(equipment_id, criticality=criticality)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return result.model_dump(mode="json")
