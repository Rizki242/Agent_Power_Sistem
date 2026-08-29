"""Manifest scanning + module loading (docs/final.md Phase 6-7).

Scans a directory of manifest YAML files, validates each one, and
registers the matching EngineeringModule implementation into a fresh
ModuleRegistry. A broken manifest, an unknown module id, or a module
that fails to instantiate is captured as a per-file ModuleLoadResult -
it never raises and never aborts the rest of the scan, so one bad
manifest cannot take down the whole application at startup.
"""

import os
from enum import Enum

import yaml
from pydantic import ValidationError

from pple.engineering.bootstrap import BUILTIN_MODULES
from pple.engineering.manifest import ModuleManifest
from pple.engineering.registry import ModuleRegistry

MANIFEST_DIR = os.path.join(os.path.dirname(__file__), "manifests")


class ModuleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    ERROR = "ERROR"
    INCOMPATIBLE = "INCOMPATIBLE"


class ModuleLoadResult:
    def __init__(self, module_id: str, status: ModuleStatus, detail: str = ""):
        self.module_id = module_id
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict:
        return {"module_id": self.module_id, "status": self.status.value, "detail": self.detail}


def _builtin_classes_by_id() -> dict:
    return {cls.id: cls for cls in BUILTIN_MODULES}


def load_modules_from_manifests(manifest_dir: str = MANIFEST_DIR) -> tuple[ModuleRegistry, list[ModuleLoadResult]]:
    registry = ModuleRegistry()
    results: list[ModuleLoadResult] = []

    if not os.path.isdir(manifest_dir):
        return registry, results

    classes_by_id = _builtin_classes_by_id()

    for filename in sorted(os.listdir(manifest_dir)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(manifest_dir, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            manifest = ModuleManifest(**(raw or {}))
        except (yaml.YAMLError, ValidationError, TypeError) as exc:
            results.append(ModuleLoadResult(filename, ModuleStatus.ERROR, f"Invalid manifest: {exc}"))
            continue

        module_cls = classes_by_id.get(manifest.id)
        if module_cls is None:
            results.append(ModuleLoadResult(
                manifest.id, ModuleStatus.INCOMPATIBLE,
                "No EngineeringModule implementation registered for this manifest id",
            ))
            continue

        if not manifest.enabled:
            results.append(ModuleLoadResult(manifest.id, ModuleStatus.DISABLED, "enabled: false in manifest"))
            continue

        try:
            registry.register(module_cls())
            results.append(ModuleLoadResult(manifest.id, ModuleStatus.ACTIVE))
        except Exception as exc:
            results.append(ModuleLoadResult(manifest.id, ModuleStatus.ERROR, f"Failed to instantiate module: {exc}"))

    return registry, results
