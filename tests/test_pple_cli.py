import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from typer.testing import CliRunner

from pple.cli.main import app
from pple.core import audit

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


class CLIAuditCommandTests(unittest.TestCase):
    """`pple audit list` (Phase 29) membaca JSONL yang sama dengan API v2."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, True)
        self.path = os.path.join(self._tmpdir, "audit.jsonl")
        patcher = patch.object(audit, "default_log_path", lambda: self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_empty_log_reports_clearly(self):
        result = runner.invoke(app, ["audit", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Belum ada event audit", result.stdout)

    def test_recorded_change_is_listed(self):
        audit.record_change("CWP-1A", "module:dga", "enabled", "disabled",
                            actor="Engineer", source=audit.SOURCE_CLI, path=self.path)
        result = runner.invoke(app, ["audit", "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CWP-1A", result.stdout)
        self.assertIn("Engineer", result.stdout)
        self.assertIn("CLI", result.stdout)

    def test_entity_filter_excludes_others(self):
        audit.record_change("CWP-1A", "module:dga", "enabled", "disabled", path=self.path)
        audit.record_change("CWP-2B", "module:dga", "enabled", "disabled", path=self.path)
        result = runner.invoke(app, ["audit", "list", "--entity", "CWP-2B"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("CWP-2B", result.stdout)
        self.assertNotIn("CWP-1A", result.stdout)

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

    def test_analyze_rejects_missing_data_instead_of_assuming_healthy(self):
        result = runner.invoke(app, ["analyze", "vibration", "CWP 1A"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Data pengukuran tidak dapat dianalisis", result.stdout)
        self.assertIn("missing data", result.stdout)


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


class CLIReliabilityCommandTests(unittest.TestCase):
    def test_reliability_health_known_dga_equipment(self):
        from pple.assets import AssetRegistry

        sample = AssetRegistry().list_equipment(domain="dga")[0]
        result = runner.invoke(app, ["reliability", "health", sample.id])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("RELIABILITY FUSION", result.stdout)
        self.assertIn("Health Index", result.stdout)
        self.assertIn("(dga)", result.stdout)

    def test_reliability_health_unknown_equipment_exits_nonzero(self):
        result = runner.invoke(app, ["reliability", "health", "DOES-NOT-EXIST"])
        self.assertEqual(result.exit_code, 1)


class CLIAgentsCommandTests(unittest.TestCase):
    def test_agents_list_shows_all_eight_with_status(self):
        result = runner.invoke(app, ["agents", "list"])
        self.assertEqual(result.exit_code, 0)
        # Rich wraps long cell text across lines at this table's default
        # width, so assert on short column values rather than full agent names.
        for domain in ("Vibration", "MCSA", "DGA", "Tribology", "Thermal", "Safety Guardrail"):
            self.assertIn(domain, result.stdout)
        self.assertIn("ACTIVE", result.stdout)
        self.assertIn("ONLINE", result.stdout)


class CLIServeCommandTests(unittest.TestCase):
    @patch("pple.cli.main.subprocess.run")
    @patch("pple.cli.main._resolve_npm_command", return_value=r"C:\Program Files\nodejs\npm.cmd")
    def test_serve_frontend_uses_resolved_windows_npm_shim(self, resolve_npm, run):
        result = runner.invoke(app, ["serve", "frontend"])

        self.assertEqual(result.exit_code, 0)
        resolve_npm.assert_called_once_with()
        run.assert_called_once_with([
            r"C:\Program Files\nodejs\npm.cmd", "--prefix", "frontend", "run", "dev",
        ])


if __name__ == "__main__":
    unittest.main()
