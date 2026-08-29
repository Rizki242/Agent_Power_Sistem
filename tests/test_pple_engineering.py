import os
import tempfile
import unittest

from pple.engineering.modules.dga import DGAModule
from pple.engineering.modules.mcsa import MCSAModule
from pple.engineering.modules.partial_discharge import PartialDischargeModule
from pple.engineering.modules.thermal import ThermalModule
from pple.engineering.modules.tribology import TribologyModule
from pple.engineering.modules.vibration import VibrationModule
from src.agents.specialist_agents import (
    DGAAgent,
    MCSAAgent,
    PDAgent,
    ThermalAgent,
    TribologyAgent,
    VibrationAgent,
)


class PplePackageImportTests(unittest.TestCase):
    def test_subpackages_import(self):
        import pple
        import pple.core
        import pple.core.exceptions
        import pple.engineering
        import pple.engineering.schemas
        import pple.engineering.base
        import pple.engineering.legacy_adapter
        import pple.engineering.registry
        import pple.engineering.manifest
        import pple.engineering.loader
        import pple.engineering.bootstrap
        import pple.engineering.modules.vibration
        import pple.engineering.modules.mcsa
        import pple.engineering.modules.dga
        import pple.engineering.modules.partial_discharge
        import pple.engineering.modules.tribology
        import pple.engineering.modules.thermal
        import pple.assets
        import pple.agents
        import pple.reliability
        import pple.database
        import pple.api
        import pple.cli  # noqa: F401 (import-only smoke test)


class EngineeringModuleContractTests(unittest.TestCase):
    def test_engineering_module_is_abstract(self):
        from pple.engineering.base import EngineeringModule

        with self.assertRaises(TypeError):
            EngineeringModule()


class _LegacyAdapterEquivalenceMixin:
    """Shared assertions for any EngineeringModule wrapping a BaseSpecialistAgent.

    Subclasses set: module_cls, agent_cls, defect_data, expected_severity,
    expected_module_id, one_applicable_equipment.
    """

    def setUp(self):
        self.module = self.module_cls()
        self.legacy = self.agent_cls()

    def test_module_metadata(self):
        self.assertEqual(self.module.id, self.expected_module_id)
        self.assertIn(self.one_applicable_equipment, self.module.applicable_equipment)

    def test_healthy_default_input(self):
        result = self.module.run("CWP 1A", {})
        self.assertEqual(result.equipment_id, "CWP 1A")
        self.assertEqual(result.module_id, self.expected_module_id)
        self.assertEqual(result.severity.value, "NORMAL")

    def test_defect_input_matches_legacy_agent(self):
        legacy = self.legacy.evaluate("CWP 1A", self.defect_data)

        result = self.module.run("CWP 1A", self.defect_data)

        # The adapter must not alter the underlying calculation.
        self.assertEqual(result.health_score, legacy["health_score"])
        self.assertEqual(result.confidence, legacy["confidence"])
        self.assertEqual(result.severity.value, self.expected_severity)
        self.assertEqual(
            sorted(r.text for r in result.recommendations),
            sorted(legacy["recommendation"]),
        )
        self.assertEqual(
            sorted(e.text for e in result.evidence),
            sorted(legacy["evidence"]),
        )


class VibrationModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = VibrationModule
    agent_cls = VibrationAgent
    defect_data = {"overall_rms": 5.2, "bpfo_amp": 1.2}
    expected_severity = "ALARM"  # legacy severity 3
    expected_module_id = "vibration"
    one_applicable_equipment = "MOTOR"


class MCSAModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = MCSAModule
    agent_cls = MCSAAgent
    defect_data = {"upper_sb": -44.0, "bearing_status": "Alarm"}
    expected_severity = "CRITICAL"  # legacy severity 4
    expected_module_id = "mcsa"
    one_applicable_equipment = "MOTOR"


class DGAModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = DGAModule
    agent_cls = DGAAgent
    defect_data = {"c2h2": 15.0, "c2h4": 80.0, "ch4": 40.0}
    expected_severity = "CRITICAL"  # legacy severity 4 (C2H2 >= 5.0)
    expected_module_id = "dga"
    one_applicable_equipment = "TRANSFORMER"


class PartialDischargeModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = PartialDischargeModule
    agent_cls = PDAgent
    defect_data = {"pulse_magnitude_pc": 1800.0, "nqn": 120.0}
    expected_severity = "CRITICAL"  # legacy severity 4
    expected_module_id = "partial_discharge"
    one_applicable_equipment = "GENERATOR"


class TribologyModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = TribologyModule
    agent_cls = TribologyAgent
    defect_data = {"fe_ppm": 85.0, "water_ppm": 600.0}
    expected_severity = "CRITICAL"  # legacy severity 4
    expected_module_id = "tribology"
    one_applicable_equipment = "MOTOR"


class ThermalModuleAdapterTests(_LegacyAdapterEquivalenceMixin, unittest.TestCase):
    module_cls = ThermalModule
    agent_cls = ThermalAgent
    defect_data = {"bearing_temp": 88.0, "delta_t_phase": 18.0}
    expected_severity = "ALARM"  # legacy severity 3
    expected_module_id = "thermal"
    one_applicable_equipment = "MOTOR"


class ManifestLoaderTests(unittest.TestCase):
    def _write_manifest(self, tmpdir, filename, content):
        path = os.path.join(tmpdir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_real_manifests_all_load_active(self):
        from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

        registry, results = load_modules_from_manifests()

        self.assertEqual(len(results), 6)
        self.assertTrue(all(r.status == ModuleStatus.ACTIVE for r in results))
        self.assertEqual(
            {m.id for m in registry.list()},
            {"vibration", "mcsa", "dga", "partial_discharge", "tribology", "thermal"},
        )

    def test_disabled_manifest_is_not_registered(self):
        from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_manifest(tmpdir, "vibration.yaml", """
id: vibration
name: Vibration Analysis
version: 1.0.0
enabled: false
""")
            registry, results = load_modules_from_manifests(tmpdir)

            self.assertEqual(results[0].status, ModuleStatus.DISABLED)
            self.assertEqual(registry.list(), [])

    def test_malformed_yaml_does_not_crash_the_scan(self):
        from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_manifest(tmpdir, "broken.yaml", "id: [this is not: valid: yaml")
            self._write_manifest(tmpdir, "vibration.yaml", """
id: vibration
name: Vibration Analysis
version: 1.0.0
""")
            registry, results = load_modules_from_manifests(tmpdir)

            statuses = {r.module_id: r.status for r in results}
            self.assertEqual(statuses["broken.yaml"], ModuleStatus.ERROR)
            self.assertEqual(statuses["vibration"], ModuleStatus.ACTIVE)
            # The broken manifest must not prevent the valid one from loading.
            self.assertEqual({m.id for m in registry.list()}, {"vibration"})

    def test_manifest_missing_required_field_is_an_error(self):
        from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_manifest(tmpdir, "incomplete.yaml", "id: vibration\n")  # missing name/version
            registry, results = load_modules_from_manifests(tmpdir)

            self.assertEqual(results[0].status, ModuleStatus.ERROR)
            self.assertEqual(registry.list(), [])

    def test_unknown_module_id_is_incompatible(self):
        from pple.engineering.loader import ModuleStatus, load_modules_from_manifests

        with tempfile.TemporaryDirectory() as tmpdir:
            self._write_manifest(tmpdir, "future.yaml", """
id: boiler_tube_inspection
name: Boiler Tube Inspection
version: 0.1.0
""")
            registry, results = load_modules_from_manifests(tmpdir)

            self.assertEqual(results[0].status, ModuleStatus.INCOMPATIBLE)
            self.assertEqual(registry.list(), [])

    def test_nonexistent_manifest_dir_returns_empty_without_error(self):
        from pple.engineering.loader import load_modules_from_manifests

        registry, results = load_modules_from_manifests("/no/such/directory")

        self.assertEqual(registry.list(), [])
        self.assertEqual(results, [])


class ModuleRegistryTests(unittest.TestCase):
    def setUp(self):
        from pple.engineering.registry import ModuleRegistry

        self.registry = ModuleRegistry()
        for module_cls in (
            VibrationModule,
            MCSAModule,
            DGAModule,
            PartialDischargeModule,
            TribologyModule,
            ThermalModule,
        ):
            self.registry.register(module_cls())

    def test_get_registered_module(self):
        module = self.registry.get("vibration")
        self.assertEqual(module.id, "vibration")

    def test_get_missing_module_raises(self):
        from pple.core.exceptions import ModuleNotRegisteredError

        with self.assertRaises(ModuleNotRegisteredError):
            self.registry.get("does-not-exist")

    def test_get_for_equipment_filters_by_applicability(self):
        # vibration, mcsa, partial_discharge, tribology, thermal all declare MOTOR.
        self.assertEqual(len(self.registry.get_for_equipment("MOTOR")), 5)
        # dga, partial_discharge, thermal declare TRANSFORMER.
        self.assertEqual(len(self.registry.get_for_equipment("TRANSFORMER")), 3)
        self.assertEqual(len(self.registry.get_for_equipment("NONEXISTENT_TYPE")), 0)

    def test_list_returns_all_registered(self):
        self.assertEqual(len(self.registry.list()), 6)

    def test_unregister(self):
        self.registry.unregister("vibration")
        ids = {m.id for m in self.registry.list()}
        self.assertNotIn("vibration", ids)
        self.assertEqual(len(ids), 5)


if __name__ == "__main__":
    unittest.main()
