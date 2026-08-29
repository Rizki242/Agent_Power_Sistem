"""Generic JSON-backed upsert store for a domain's sample/record overrides.

DGA, Tribology, Thermal, and Partial Discharge each have a base dataset that
is either hardcoded in source (DGA, PD) or parsed from a fixed Excel export
(Tribology, Thermal) - none of them have a real write path today. Rather than
inventing a bespoke persistence mechanism per domain, this mirrors the
atomic-write JSON pattern already used by
pple.engineering.equipment_modules.EquipmentModuleStore (itself following the
"config JSON separate from code" pattern of data/MCSA/config/equipment_master.json
- see CLAUDE.md). Each domain module gets its own DomainOverrideStore instance
pointed at its own file under get_data_path('config', ...); overrides are
merged on top of the base records by the domain module's own search/detail
functions, keyed by that domain's natural record id (transformer_id,
sample_id, etc.) - an override with a new id is effectively "add new record",
one with an existing id is "edit that record".
"""

import json
import os
from threading import Lock

_LOCK = Lock()


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


class DomainOverrideStore:
    """Reads/writes {record_id: fields dict} overrides for one domain."""

    def __init__(self, path: str):
        self._path = path

    def all(self) -> dict:
        """Every override currently recorded, as {record_id: fields dict}."""
        return dict(_load(self._path))

    def get(self, record_id: str):
        return _load(self._path).get(record_id)

    def set(self, record_id: str, fields: dict) -> None:
        """Add or replace the override for `record_id`."""
        with _LOCK:
            data = _load(self._path)
            data[record_id] = fields
            _save(self._path, data)
