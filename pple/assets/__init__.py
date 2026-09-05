"""Asset Engine (docs/final.md Phase 3): Plant -> Unit -> Equipment hierarchy.

MVP slice - see pple/assets/registry.py for what this does and does not do.
"""

from pple.assets.registry import AssetRegistry
from pple.assets.schemas import Equipment, Plant, Unit

__all__ = ["AssetRegistry", "Equipment", "Plant", "Unit"]
