import os
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from pple.cli.main import app
from pple.core import audit
from pple.engineering.equipment_modules import EquipmentModuleStore
from pple.engineering.loader import load_modules_from_manifests

runner = CliRunner()


def _isolate_audit_log(testcase):
    """Arahkan audit log ke berkas sementara.

    Mengubah override modul sekarang ikut menulis lewat pple/core/audit.py,
    jadi tanpa ini test akan menumpuk event di data/MCSA/audit/ yang asli.
    """
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.remove(path)
    patcher = patch.object(audit, "default_log_path", lambda: path)
    patcher.start()
    testcase.addCleanup(patcher.stop)
    testcase.addCleanup(lambda: os.path.exists(path) and os.remove(path))
    return path


class EquipmentModuleStoreTests(unittest.TestCase):
    def setUp(self):
        _isolate_audit_log(self)
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)  # store must tolerate a missing file
        self.store = EquipmentModuleStore(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_unconfigured_equipment_defaults_every_module_enabled(self):
        registry, _ = load_modules_from_manifests()
        results = self.store.list_for_equipment("CWP-1A", registry)
        self.assertEqual(len(results), len(registry.list()))
        self.assertTrue(all(enabled for _, enabled in results))
        self.assertTrue(self.store.is_enabled("CWP-1A", "vibration"))

    def test_remove_then_add_round_trips(self):
        self.store.remove_module("CWP-1A", "dga")
        self.assertFalse(self.store.is_enabled("CWP-1A", "dga"))
        # Unrelated equipment/module are untouched.
        self.assertTrue(self.store.is_enabled("CWP-1A", "vibration"))
        self.assertTrue(self.store.is_enabled("CWP-1B", "dga"))

        self.store.add_module("CWP-1A", "dga")
        self.assertTrue(self.store.is_enabled("CWP-1A", "dga"))

    def test_disable_persists_across_store_instances(self):
        self.store.remove_module("CWP-1A", "tribology")
        reloaded = EquipmentModuleStore(self.path)
        self.assertFalse(reloaded.is_enabled("CWP-1A", "tribology"))

    def test_re_enabling_last_override_removes_equipment_entry(self):
        self.store.remove_module("CWP-1A", "dga")
        self.store.add_module("CWP-1A", "dga")
        self.assertEqual(self.store.overrides_for("CWP-1A"), {})

    def test_corrupt_store_file_is_treated_as_empty(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not valid json")
        self.assertEqual(self.store.overrides_for("CWP-1A"), {})


class EquipmentCLITests(unittest.TestCase):
    """CLI tests patch the store's default path so they never touch the real
    data/MCSA/config/pple_equipment_modules.json file."""

    def setUp(self):
        _isolate_audit_log(self)
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self._patcher = patch(
            "pple.engineering.equipment_modules._default_store_path", return_value=self.path
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_modules_lists_all_six_enabled_by_default(self):
        result = runner.invoke(app, ["equipment", "modules", "CWP-1A"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CWP-1A", result.stdout)
        for name in (
            "Vibration Analysis",
            "Motor Current Signature Analysis",
            "Dissolved Gas Analysis",
            "Tribology & Oil Condition",
            "Thermography & RTD Monitoring",
        ):
            self.assertIn(name, result.stdout)

    def test_module_add_unknown_id_exits_nonzero(self):
        result = runner.invoke(app, ["equipment", "module-add", "CWP-1A", "does-not-exist"])
        self.assertEqual(result.exit_code, 1)

    def test_module_remove_unknown_id_exits_nonzero(self):
        result = runner.invoke(app, ["equipment", "module-remove", "CWP-1A", "does-not-exist"])
        self.assertEqual(result.exit_code, 1)

    def test_module_remove_and_add_round_trip_via_cli(self):
        store = EquipmentModuleStore(self.path)

        remove_result = runner.invoke(app, ["equipment", "module-remove", "CWP-1A", "dga"])
        self.assertEqual(remove_result.exit_code, 0)
        self.assertIn("Disabled", remove_result.stdout)
        self.assertFalse(store.is_enabled("CWP-1A", "dga"))

        list_result = runner.invoke(app, ["equipment", "modules", "CWP-1A"])
        self.assertIn("✗", list_result.stdout)

        add_result = runner.invoke(app, ["equipment", "module-add", "CWP-1A", "dga"])
        self.assertEqual(add_result.exit_code, 0)
        self.assertIn("Enabled", add_result.stdout)
        self.assertTrue(store.is_enabled("CWP-1A", "dga"))


class EquipmentModuleWiringTests(unittest.TestCase):
    """Follow-up to Phase 8: EquipmentModuleStore must actually gate
    SubAgentCoordinator and ReliabilityFusionAgent, not just the CLI. Both
    agents build their own EquipmentModuleStore() at construction time, so
    patching the store's default path before constructing them is enough."""

    def setUp(self):
        _isolate_audit_log(self)
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self._patcher = patch(
            "pple.engineering.equipment_modules._default_store_path", return_value=self.path
        )
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_fusion_excludes_disabled_module_from_health_index(self):
        from src.agents.fusion_engine import ReliabilityFusionAgent

        EquipmentModuleStore(self.path).remove_module("CWP-1A", "tribology")
        fusion = ReliabilityFusionAgent()

        # Same alarming oil reading, disabled equipment vs. an untouched one.
        disabled_result = fusion.run_full_fusion(equipment="CWP-1A", oil_data={"fe_ppm": 999.0})
        unaffected_result = fusion.run_full_fusion(equipment="CWP-1B", oil_data={"fe_ppm": 999.0})

        self.assertIsNone(disabled_result["health_index"])
        self.assertEqual(disabled_result["health_status"], "UNKNOWN")
        self.assertLess(unaffected_result["health_index"], 90.0)

    def test_coordinator_omits_disabled_module_trace(self):
        from src.agents.subagent_coordinator import SubAgentCoordinator

        EquipmentModuleStore(self.path).remove_module("BFP 1A", "thermal")
        coordinator = SubAgentCoordinator()

        res = coordinator.run_collaborative_diagnosis(
            equipment="BFP 1A",
            custom_telemetry={"vibration": {"overall_rms": 2.2}, "mcsa": {}, "oil": {}},
        )
        domains = [t["subagent"]["domain"] for t in res["subagent_traces"]]
        self.assertNotIn("Thermal", domains)
        self.assertIn("Vibration", domains)

    def test_unconfigured_equipment_behaves_exactly_as_before(self):
        from src.agents.fusion_engine import ReliabilityFusionAgent

        fusion = ReliabilityFusionAgent()
        result = fusion.run_full_fusion(equipment="CWP-1A", vibration_data={"overall_rms": 2.6})
        self.assertIn("health_index", result)
        self.assertGreaterEqual(result["health_index"], 90.0)


if __name__ == "__main__":
    unittest.main()
