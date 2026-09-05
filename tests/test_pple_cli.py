import json
import tempfile
import unittest

from typer.testing import CliRunner

from pple.cli.main import app

runner = CliRunner()


class CLIStatusDoctorTests(unittest.TestCase):
    def test_status_shows_modules_and_online(self):
        result = runner.invoke(app, ["status"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ONLINE", result.stdout)
        self.assertIn("6/6 modules ACTIVE", result.stdout)

    def test_doctor_reports_good_health_and_exits_zero(self):
        result = runner.invoke(app, ["doctor"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PPLE SYSTEM DOCTOR", result.stdout)
        self.assertIn("System health:", result.stdout)
        self.assertIn("GOOD", result.stdout)
        # All 6 built-in modules should report OK.
        for module_id in ("vibration", "mcsa", "dga", "partial_discharge", "tribology", "thermal"):
            self.assertIn(module_id, result.stdout)


class CLIModuleCommandTests(unittest.TestCase):
    def test_module_list_shows_all_six(self):
        result = runner.invoke(app, ["module", "list"])
        self.assertEqual(result.exit_code, 0)
        for module_id in ("vibration", "mcsa", "dga", "partial_discharge", "tribology", "thermal"):
            self.assertIn(module_id, result.stdout)

    def test_module_show_known_id(self):
        result = runner.invoke(app, ["module", "show", "vibration"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Vibration Analysis", result.stdout)
        self.assertIn("ACTIVE", result.stdout)

    def test_module_show_unknown_id_exits_nonzero(self):
        result = runner.invoke(app, ["module", "show", "does-not-exist"])
        self.assertEqual(result.exit_code, 1)


class CLIAnalyzeCommandTests(unittest.TestCase):
    def test_analyze_with_inline_data(self):
        result = runner.invoke(app, [
            "analyze", "vibration", "CWP 1A",
            "--data", json.dumps({"overall_rms": 5.2, "bpfo_amp": 1.2}),
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("VIBRATION ANALYSIS", result.stdout)
        self.assertIn("ALARM", result.stdout)
        self.assertIn("Bearing", result.stdout)

    def test_analyze_with_data_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"upper_sb": -44.0, "bearing_status": "Alarm"}, f)
            path = f.name

        result = runner.invoke(app, ["analyze", "mcsa", "CWP 1A", "--file", path])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CRITICAL", result.stdout)

    def test_analyze_rejects_both_data_and_file(self):
        result = runner.invoke(app, [
            "analyze", "vibration", "CWP 1A", "--data", "{}", "--file", "x.json",
        ])
        self.assertEqual(result.exit_code, 1)

    def test_analyze_unknown_module_exits_nonzero(self):
        result = runner.invoke(app, ["analyze", "does-not-exist", "CWP 1A"])
        self.assertEqual(result.exit_code, 1)

    def test_analyze_healthy_default_when_no_data_given(self):
        result = runner.invoke(app, ["analyze", "vibration", "CWP 1A"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("NORMAL", result.stdout)


class CLIAssetsCommandTests(unittest.TestCase):
    def test_assets_tree_shows_units_and_equipment(self):
        result = runner.invoke(app, ["assets", "tree"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PLTU Jeranjang", result.stdout)
        self.assertIn("UNIT 1", result.stdout)

    def test_assets_tree_domain_filter(self):
        result = runner.invoke(app, ["assets", "tree", "--domain", "dga"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("(dga)", result.stdout)
        self.assertNotIn("(vibration)", result.stdout)

    def test_assets_list_unit_filter(self):
        result = runner.invoke(app, ["assets", "list", "--unit", "UNIT 1"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("UNIT 1", result.stdout)
        self.assertNotIn("UNIT 2", result.stdout)

    def test_assets_show_known_equipment(self):
        from pple.assets import AssetRegistry

        sample = AssetRegistry().list_equipment(domain="dga")[0]
        result = runner.invoke(app, ["assets", "show", sample.id])
        self.assertEqual(result.exit_code, 0)
        self.assertIn(sample.name, result.stdout)
        self.assertIn("dga", result.stdout)

    def test_assets_show_unknown_equipment_exits_nonzero(self):
        result = runner.invoke(app, ["assets", "show", "DOES-NOT-EXIST"])
        self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
