"""Asset Engine data shapes (docs/final.md's Plant -> Unit -> Equipment
hierarchy, MVP slice).

Deliberately plain dataclasses, not a database model - see
pple/assets/registry.py for why this stays a read-through view over the
existing per-domain data instead of a new persisted store.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Equipment:
    """One monitored asset instance (a transformer, a motor-driven pump/fan, ...).

    `id` and `domain` together are unique (`domain` distinguishes, e.g., a DGA
    transformer id from a vibration asset_id - they are different id spaces
    today, see pple/assets/registry.py `_dga_equipment`/`_vibration_equipment`).
    """
    id: str
    name: str
    unit: str
    domain: str  # "dga" | "vibration" (grows as more domains are wired in)
    equipment_class: str = ""
    status: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "unit": self.unit,
            "domain": self.domain,
            "equipment_class": self.equipment_class,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass
class Unit:
    """A plant unit (e.g. "UNIT 1") grouping equipment across domains."""
    id: str
    name: str
    equipment: List[Equipment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "equipment_count": len(self.equipment),
            "equipment": [e.to_dict() for e in self.equipment],
        }


@dataclass
class Plant:
    """The top of the hierarchy - one power plant, made up of units."""
    id: str
    name: str
    units: List[Unit] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "unit_count": len(self.units),
            "units": [u.to_dict() for u in self.units],
        }
