import unittest

from src.agents.specialist_agents import VibrationAgent


class PplePackageImportTests(unittest.TestCase):
    def test_subpackages_import(self):
        import pple
        import pple.core
        import pple.core.exceptions
        import pple.engineering
        import pple.engineering.schemas
        import pple.engineering.base
        import pple.engineering.registry
        import pple.engineering.modules.vibration
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


class VibrationModuleAdapterTests(unittest.TestCase):
    def setUp(self):
        from pple.engineering.modules.vibration import VibrationModule

        self.module = VibrationModule()
        self.legacy = VibrationAgent()

    def test_healthy_default_input(self):
        result = self.module.run("CWP 1A", {})
        self.assertEqual(result.equipment_id, "CWP 1A")
        self.assertEqual(result.module_id, "vibration")
        self.assertEqual(result.severity.value, "NORMAL")
        self.assertGreaterEqual(result.health_score, 90.0)

    def test_bearing_defect_matches_legacy_agent(self):
        data = {"overall_rms": 5.2, "bpfo_amp": 1.2}
        legacy = self.legacy.evaluate("CWP 1A", data)

        result = self.module.run("CWP 1A", data)

        # The adapter must not alter the underlying calculation.
        self.assertEqual(result.health_score, legacy["health_score"])
        self.assertEqual(result.confidence, legacy["confidence"])
        self.assertEqual(result.severity.value, "ALARM")  # legacy severity 3
        self.assertEqual(
            sorted(r.text for r in result.recommendations),
            sorted(legacy["recommendation"]),
        )
        self.assertEqual(
            sorted(e.text for e in result.evidence),
            sorted(legacy["evidence"]),
        )

    def test_module_metadata(self):
        self.assertEqual(self.module.id, "vibration")
        self.assertIn("MOTOR", self.module.applicable_equipment)


class ModuleRegistryTests(unittest.TestCase):
    def setUp(self):
        from pple.engineering.modules.vibration import VibrationModule
        from pple.engineering.registry import ModuleRegistry

        self.registry = ModuleRegistry()
        self.registry.register(VibrationModule())

    def test_get_registered_module(self):
        module = self.registry.get("vibration")
        self.assertEqual(module.id, "vibration")

    def test_get_missing_module_raises(self):
        from pple.core.exceptions import ModuleNotRegisteredError

        with self.assertRaises(ModuleNotRegisteredError):
            self.registry.get("does-not-exist")

    def test_get_for_equipment_filters_by_applicability(self):
        self.assertEqual(len(self.registry.get_for_equipment("MOTOR")), 1)
        self.assertEqual(len(self.registry.get_for_equipment("TRANSFORMER")), 0)

    def test_list_returns_all_registered(self):
        self.assertEqual(len(self.registry.list()), 1)

    def test_unregister(self):
        self.registry.unregister("vibration")
        self.assertEqual(self.registry.list(), [])


if __name__ == "__main__":
    unittest.main()
