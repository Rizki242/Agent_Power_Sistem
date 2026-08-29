import unittest

from pple.engineering.modules.mcsa import MCSAModule
from pple.engineering.modules.vibration import VibrationModule
from src.agents.specialist_agents import MCSAAgent, VibrationAgent


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


class ModuleRegistryTests(unittest.TestCase):
    def setUp(self):
        from pple.engineering.registry import ModuleRegistry

        self.registry = ModuleRegistry()
        self.registry.register(VibrationModule())
        self.registry.register(MCSAModule())

    def test_get_registered_module(self):
        module = self.registry.get("vibration")
        self.assertEqual(module.id, "vibration")

    def test_get_missing_module_raises(self):
        from pple.core.exceptions import ModuleNotRegisteredError

        with self.assertRaises(ModuleNotRegisteredError):
            self.registry.get("does-not-exist")

    def test_get_for_equipment_filters_by_applicability(self):
        # Both vibration and mcsa declare MOTOR as applicable.
        self.assertEqual(len(self.registry.get_for_equipment("MOTOR")), 2)
        self.assertEqual(len(self.registry.get_for_equipment("TRANSFORMER")), 0)
        # Only vibration declares TURBINE.
        self.assertEqual(len(self.registry.get_for_equipment("TURBINE")), 1)

    def test_list_returns_all_registered(self):
        self.assertEqual(len(self.registry.list()), 2)

    def test_unregister(self):
        self.registry.unregister("vibration")
        self.assertEqual({m.id for m in self.registry.list()}, {"mcsa"})


if __name__ == "__main__":
    unittest.main()
