"""The set of built-in EngineeringModule classes (docs/final.md Phase 1).

pple.engineering.loader cross-references this against manifest ids to
decide whether a manifest is loadable (ACTIVE), unimplemented
(INCOMPATIBLE), or references code that doesn't exist here yet.
"""

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
