"""Populates the shared pple.engineering.registry.registry singleton with
every built-in engineering module.

SubAgentCoordinator and ReliabilityFusionAgent each build their own private
ModuleRegistry instance (they don't need to share state with anything else).
This module exists for callers that DO need one shared, queryable registry -
currently just pple.api's /api/v2/modules endpoints.
"""

from pple.engineering.registry import registry
from pple.engineering.modules.vibration import VibrationModule
from pple.engineering.modules.mcsa import MCSAModule
from pple.engineering.modules.dga import DGAModule
from pple.engineering.modules.partial_discharge import PartialDischargeModule
from pple.engineering.modules.tribology import TribologyModule
from pple.engineering.modules.thermal import ThermalModule

BUILTIN_MODULES = (
    VibrationModule,
    MCSAModule,
    DGAModule,
    PartialDischargeModule,
    TribologyModule,
    ThermalModule,
)


def register_builtin_modules() -> None:
    """Idempotent: ModuleRegistry.register() overwrites by id, so calling
    this more than once (e.g. from multiple importers) is harmless."""
    for module_cls in BUILTIN_MODULES:
        registry.register(module_cls())
