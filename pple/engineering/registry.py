"""In-memory EngineeringModule registry (docs/final.md Phase 7).

Phase 1 scope: a plain dict-backed registry. Manifest-file scanning
(plugins/*/manifest.yaml) and ACTIVE/DISABLED/ERROR status tracking are
later-phase additions - see docs/pple_v2_baseline.md.
"""

from pple.core.exceptions import ModuleNotRegisteredError
from pple.engineering.base import EngineeringModule


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, EngineeringModule] = {}

    def register(self, module: EngineeringModule) -> None:
        self._modules[module.id] = module

    def unregister(self, module_id: str) -> None:
        self._modules.pop(module_id, None)

    def get(self, module_id: str) -> EngineeringModule:
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise ModuleNotRegisteredError(f"No engineering module registered as '{module_id}'") from exc

    def list(self) -> list[EngineeringModule]:
        return list(self._modules.values())

    def get_for_equipment(self, equipment_type: str) -> list[EngineeringModule]:
        equipment_type = (equipment_type or "").upper()
        return [
            m for m in self._modules.values()
            if not m.applicable_equipment or equipment_type in m.applicable_equipment
        ]


registry = ModuleRegistry()
