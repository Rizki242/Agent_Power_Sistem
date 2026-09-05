"""Asset Engine registry (docs/final.md's "Asset Engine" box, MVP slice).

Deliberately a *read-through aggregation* over the existing per-domain data
(src.dga_data, src.vibration_data), not a new persisted store: those modules
already are the source of truth for their equipment (CLAUDE.md's "Preserve
the existing MCSA workflow and data model" / "Rule-based logic is the source
of truth"). Forking equipment identity into a second, separately-edited JSON
file would create two sources of truth that can drift apart. Instead,
AssetRegistry.plant() builds the Plant -> Unit -> Equipment tree fresh from
those modules every call, tagging each equipment with which domain(s) - dga,
vibration, and more as they're wired in - actually monitor it.

No caching: both domains already do their own caching/connection handling
(sqlite for vibration, CSV read for DGA), and equipment lists are small
(dozens, not thousands), so re-deriving the tree per call keeps this module
simple and always current.
"""

from typing import Dict, List, Optional

from pple.assets.schemas import Equipment, Plant, Unit

DEFAULT_PLANT_ID = "PLTU-JERANJANG"
DEFAULT_PLANT_NAME = "PLTU Jeranjang (3 x 25 MW)"


def _dga_equipment() -> List[Equipment]:
    try:
        from src.dga_data import search_dga_transformers
    except Exception:
        return []
    equipment = []
    for t in search_dga_transformers():
        equipment.append(Equipment(
            id=t.get("transformer_id", t.get("name", "")),
            name=t.get("name", ""),
            unit=t.get("unit") or "UNKNOWN",
            domain="dga",
            equipment_class="Transformer",
            status=t.get("status", ""),
            metadata={"voltage_ratio": t.get("voltage_ratio", "-")},
        ))
    return equipment


def _vibration_equipment() -> List[Equipment]:
    try:
        from src.vibration_data import search_vibration_assets
    except Exception:
        return []
    equipment = []
    for a in search_vibration_assets():
        equipment.append(Equipment(
            id=a.get("asset_id", ""),
            name=a.get("equipment", ""),
            unit=a.get("unit_group") or "UNKNOWN",
            domain="vibration",
            equipment_class=a.get("asset_category_derived") or a.get("equipment_class_normalized") or "",
            status=a.get("status_vibrasi", ""),
            metadata={"kks": a.get("kks", "")},
        ))
    return equipment


# Domain name -> loader. Add an entry here (and nowhere else) to wire in a
# new domain's equipment - the tree/list/get methods below need no changes.
_DOMAIN_LOADERS = {
    "dga": _dga_equipment,
    "vibration": _vibration_equipment,
}


class AssetRegistry:
    """Builds and queries the Plant -> Unit -> Equipment hierarchy."""

    def __init__(self, plant_id: str = DEFAULT_PLANT_ID, plant_name: str = DEFAULT_PLANT_NAME):
        self.plant_id = plant_id
        self.plant_name = plant_name

    def _all_equipment(self, domain: Optional[str] = None) -> List[Equipment]:
        loaders = _DOMAIN_LOADERS if not domain else {domain: _DOMAIN_LOADERS[domain]} if domain in _DOMAIN_LOADERS else {}
        equipment: List[Equipment] = []
        for loader in loaders.values():
            equipment.extend(loader())
        return equipment

    def plant(self, domain: Optional[str] = None) -> Plant:
        """The full hierarchy, optionally restricted to one domain's equipment."""
        by_unit: Dict[str, List[Equipment]] = {}
        for eq in self._all_equipment(domain):
            by_unit.setdefault(eq.unit, []).append(eq)

        units = [
            Unit(id=unit_name, name=unit_name, equipment=sorted(eqs, key=lambda e: e.id))
            for unit_name, eqs in sorted(by_unit.items())
        ]
        return Plant(id=self.plant_id, name=self.plant_name, units=units)

    def list_units(self) -> List[str]:
        """Unit names that have at least one piece of monitored equipment."""
        return [u.name for u in self.plant().units]

    def list_equipment(self, unit: Optional[str] = None, domain: Optional[str] = None) -> List[Equipment]:
        equipment = self._all_equipment(domain)
        if unit:
            equipment = [e for e in equipment if e.unit.upper() == unit.upper()]
        return sorted(equipment, key=lambda e: (e.unit, e.id))

    def get_equipment(self, equipment_id: str, domain: Optional[str] = None) -> Optional[Equipment]:
        """Look up one equipment by id. Pass `domain` when the same id string
        could collide across domains (dga transformer ids and vibration
        asset ids are separate spaces today, so this is mostly future-proofing)."""
        for eq in self._all_equipment(domain):
            if eq.id == equipment_id:
                return eq
        return None

    @staticmethod
    def available_domains() -> List[str]:
        return sorted(_DOMAIN_LOADERS.keys())
