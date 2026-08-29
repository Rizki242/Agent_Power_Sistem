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
