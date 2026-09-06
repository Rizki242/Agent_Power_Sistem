import unittest
from unittest import mock

from typer.testing import CliRunner

from pple.cli.main import app
from pple.cli.nl import parse_intent
from pple.cli.safety import RiskTier, check_high_risk, classify_command

runner = CliRunner()


class SafetyClassificationTests(unittest.TestCase):
    def test_read_commands_classified_read(self):
        for cmd in ("status", "doctor", "assets list", "reliability health", "analyze"):
            self.assertEqual(classify_command(cmd), RiskTier.READ)

    def test_write_commands_classified_write(self):
        for cmd in ("equipment module-add", "equipment module-remove"):
            self.assertEqual(classify_command(cmd), RiskTier.WRITE)

    def test_unknown_command_defaults_read(self):
        self.assertEqual(classify_command("something-made-up"), RiskTier.READ)

    def test_high_risk_text_blocked(self):
        result = check_high_risk("tolong trip generator sekarang")
        self.assertTrue(result["violation_detected"])
        self.assertIn("SAFETY GUARDRAIL", result["message"])

    def test_safe_text_not_blocked(self):
        result = check_high_risk("cek CWP-1A")
        self.assertFalse(result["violation_detected"])


class ParseIntentTests(unittest.TestCase):
    def test_module_enable(self):
        intent = parse_intent("aktifkan modul vibration untuk CWP-1A")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "MODULE_ENABLE")
        self.assertEqual(intent.command, "equipment module-add")
        self.assertEqual(intent.params, {"module_id": "vibration", "equipment": "CWP-1A"})
        self.assertEqual(intent.risk, RiskTier.WRITE)

    def test_module_disable(self):
        intent = parse_intent("matikan modul tribology dari CWP-1A")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "MODULE_DISABLE")
        self.assertEqual(intent.command, "equipment module-remove")
        self.assertEqual(intent.risk, RiskTier.WRITE)

    def test_equipment_health_check(self):
        intent = parse_intent("cek CWP-1A")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.name, "EQUIPMENT_HEALTH")
        self.assertEqual(intent.command, "reliability health")
        self.assertEqual(intent.params["equipment"], "CWP-1A")
        self.assertEqual(intent.risk, RiskTier.READ)

    def test_asset_list(self):
        intent = parse_intent("daftar aset di UNIT 1")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.command, "assets list")
        self.assertEqual(intent.params["unit"], "UNIT 1")

    def test_status(self):
        intent = parse_intent("status")
        self.assertIsNotNone(intent)
        self.assertEqual(intent.command, "status")

    def test_unrecognized_text_returns_none(self):
        self.assertIsNone(parse_intent("tambahkan Unit 4"))
        self.assertIsNone(parse_intent("blah blah nonsense"))


class AskCommandTests(unittest.TestCase):
    def test_high_risk_text_blocked_before_parsing(self):
        result = runner.invoke(app, ["ask", "trip generator sekarang"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("SAFETY GUARDRAIL BLOCKED", result.stdout)

    def test_unrecognized_text_rejected_not_guessed(self):
        result = runner.invoke(app, ["ask", "tambahkan Unit 4"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("tidak dikenali", result.stdout)

    def test_read_intent_runs_without_confirmation(self):
        from pple.assets import AssetRegistry

        sample = AssetRegistry().list_equipment(domain="dga")[0]
        result = runner.invoke(app, ["ask", f"cek {sample.id}"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("RELIABILITY FUSION", result.stdout)

    def test_write_intent_declined_without_yes_makes_no_change(self):
        with mock.patch("pple.engineering.equipment_modules._default_store_path") as mocked_path, \
             mock.patch("typer.confirm", return_value=False):
            import tempfile
            import os

            fd, path = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            os.remove(path)
            mocked_path.return_value = path

            result = runner.invoke(app, ["ask", "aktifkan modul vibration untuk CWP-1A"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Dibatalkan", result.stdout)
            self.assertFalse(os.path.exists(path))

    def test_write_intent_with_yes_flag_skips_confirmation(self):
        with mock.patch("pple.engineering.equipment_modules._default_store_path") as mocked_path:
            import tempfile
            import os

            fd, path = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            os.remove(path)
            mocked_path.return_value = path

            result = runner.invoke(app, ["ask", "aktifkan modul vibration untuk CWP-1A", "--yes"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Enabled", result.stdout)

            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
