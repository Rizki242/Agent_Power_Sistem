"""Equipment <-> Module mapping (docs/final.md Phase 8).

A lightweight, file-backed override store answering "which engineering
modules are enabled for this specific piece of equipment" (e.g. "CWP-1A"),
layered on top of the existing *type*-based filter from Phase 7
(`ModuleRegistry.get_for_equipment`, which only knows equipment types like
"PUMP"/"MOTOR" via each module's `applicable_equipment`).

No database exists yet (final.md Phase 2-4 is deliberately deferred - see
docs/pple_v2_baseline.md section 9, highest risk / not on the MVP critical
path), so this persists as JSON under the project's normal config
directory (`get_data_path('config', ...)`), the same "config JSON separate
from code" pattern already used by `data/MCSA/config/equipment_master.json`
(see src/data_loader.load_equipment_master and CLAUDE.md).

Default is opt-out, not opt-in: every module known to the registry is
enabled for every equipment unless an explicit override disables it. This
keeps the store purely additive - `SubAgentCoordinator` and
`ReliabilityFusionAgent` (Phase 10) do not consult it yet, so nothing
currently running is silently disabled by adding this file. Wiring it into
those call sites is a separate follow-up phase.
"""

import json
import os
from threading import Lock

_LOCK = Lock()


def _default_store_path() -> str:
    from src.data_loader import get_data_path

    return get_data_path("config", "pple_equipment_modules.json")


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _save(path: str, data: dict) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


class EquipmentModuleStore:
    """Reads/writes per-equipment engineering-module enable/disable overrides."""

    def __init__(self, path: str = None):
        self._path = path or _default_store_path()

    def overrides_for(self, equipment_id: str) -> dict:
        """Raw {module_id: bool} overrides recorded for this equipment (usually sparse)."""
        return dict(_load(self._path).get(equipment_id, {}))

    def is_enabled(self, equipment_id: str, module_id: str) -> bool:
        return self.overrides_for(equipment_id).get(module_id, True)

    def list_for_equipment(self, equipment_id: str, registry) -> list:
        """[(module_id, enabled)] for every module in `registry`, resolved against
        this equipment's overrides (unset modules default to enabled=True)."""
        overrides = self.overrides_for(equipment_id)
        return [(m.id, overrides.get(m.id, True)) for m in registry.list()]

    def set_enabled(self, equipment_id: str, module_id: str, enabled: bool) -> None:
        with _LOCK:
            data = _load(self._path)
            equipment_overrides = data.setdefault(equipment_id, {})
            if enabled:
                # Enabled is the default - storing it explicitly would just be dead
                # weight, so clearing a prior disable is enough to re-enable.
                equipment_overrides.pop(module_id, None)
                if not equipment_overrides:
                    data.pop(equipment_id, None)
            else:
                equipment_overrides[module_id] = False
            _save(self._path, data)

    def add_module(self, equipment_id: str, module_id: str) -> None:
        """Enable `module_id` for `equipment_id` (clears any existing disable override)."""
        self.set_enabled(equipment_id, module_id, True)

    def remove_module(self, equipment_id: str, module_id: str) -> None:
        """Disable `module_id` for `equipment_id`."""
        self.set_enabled(equipment_id, module_id, False)
