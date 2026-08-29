import unittest

from src.components.status_colors import canon_condition_status


class CanonConditionStatusTests(unittest.TestCase):
    def test_normal_variants(self):
        for raw in ("NORMAL", "Normal", "ok", "Good"):
            self.assertEqual(canon_condition_status(raw), "Normal")

    def test_alarm_variants(self):
        for raw in ("ALARM", "WARNING", "PREWARNING"):
            self.assertEqual(canon_condition_status(raw), "Alarm")

    def test_high_variants(self):
        for raw in ("HIGH", "CRITICAL", "Rusak", "Damage", "Trip"):
            self.assertEqual(canon_condition_status(raw), "High")

    def test_standby(self):
        self.assertEqual(canon_condition_status("STANDBY"), "Standby")

    def test_unknown_for_empty_or_unrecognized(self):
        self.assertEqual(canon_condition_status(""), "Unknown")
        self.assertEqual(canon_condition_status(None), "Unknown")
        self.assertEqual(canon_condition_status("garbage"), "Unknown")


if __name__ == "__main__":
    unittest.main()
