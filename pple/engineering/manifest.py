"""ModuleManifest schema (docs/final.md Phase 6).

A manifest describes a module's metadata declaratively (YAML) instead of
only living as Python class attributes on an EngineeringModule subclass.
The loader (loader.py) cross-checks a manifest's `id` against the actual
registered EngineeringModule implementation before activating it.
"""

from pydantic import BaseModel, Field


class ModuleManifest(BaseModel):
    id: str
    name: str
    version: str
    category: str = "condition_monitoring"
    enabled: bool = True
    applicable_equipment: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
