"""Tests for pple/reliability/ (docs/final.md Phase 11/17 - Reliability Fusion V2)."""

import unittest
from datetime import datetime

from pple.engineering.schemas import DiagnosticResult, Severity
from pple.reliability import ReliabilityFusionEngine


def _result(equipment_id="EQ-1", module_id="vibration", health_score=90.0, severity=Severity.NORMAL, confidence=0.9):
    return DiagnosticResult(
        equipment_id=equipment_id, module_id=module_id, timestamp=datetime.now(),
        health_score=health_score, severity=severity, confidence=confidence,
    )


class FuseTests(unittest.TestCase):
    def setUp(self):
        self.engine = ReliabilityFusionEngine()

    def test_fuse_requires_at_least_one_result(self):
        with self.assertRaises(ValueError):
            self.engine.fuse([])

    def test_fuse_rejects_mixed_equipment_ids(self):
        with self.assertRaises(ValueError):
            self.engine.fuse([_result(equipment_id="EQ-1"), _result(equipment_id="EQ-2")])

    def test_single_healthy_domain(self):
        result = self.engine.fuse([_result(health_score=95.0, severity=Severity.NORMAL, confidence=0.9)])
        self.assertEqual(result.equipment_id, "EQ-1")
        self.assertEqual(result.health_index, 95.0)
        self.assertEqual(result.severity, Severity.NORMAL)
        self.assertEqual(result.risk_level, "LOW RISK")
        self.assertEqual(len(result.domain_contributions), 1)

    def test_confidence_weighted_average(self):
        # (90*0.8 + 50*0.2) / 1.0 = 82.0
        result = self.engine.fuse([
            _result(module_id="vibration", health_score=90.0, confidence=0.8, severity=Severity.NORMAL),
            _result(module_id="mcsa", health_score=50.0, confidence=0.2, severity=Severity.NORMAL),
        ])
        self.assertEqual(result.health_index, 82.0)

    def test_missing_confidence_defaults_to_half_weight(self):
        result = self.engine.fuse([_result(health_score=80.0, confidence=None, severity=Severity.NORMAL)])
        self.assertEqual(result.health_index, 80.0)

    def test_critical_severity_caps_health_index_even_if_average_is_high(self):
        result = self.engine.fuse([
            _result(module_id="vibration", health_score=98.0, confidence=0.9, severity=Severity.NORMAL),
            _result(module_id="dga", health_score=95.0, confidence=0.9, severity=Severity.CRITICAL),
        ])
        self.assertLessEqual(result.health_index, 45.0)
        self.assertEqual(result.severity, Severity.CRITICAL)

    def test_alarm_severity_caps_health_index(self):
        result = self.engine.fuse([_result(health_score=99.0, confidence=0.9, severity=Severity.ALARM)])
        self.assertLessEqual(result.health_index, 65.0)

    def test_low_health_index_yields_high_risk_and_short_rul(self):
        result = self.engine.fuse([_result(health_score=20.0, confidence=0.9, severity=Severity.CRITICAL)], criticality="A")
        self.assertGreaterEqual(result.failure_probability_30d, 80.0)
        self.assertIn(result.risk_level, {"HIGH RISK", "CRITICAL RISK"})
        self.assertLessEqual(result.rul_max_days, 45)

    def test_value_types_are_labeled(self):
        result = self.engine.fuse([_result()])
        self.assertEqual(result.health_index_type.value, "calculated")
        self.assertEqual(result.risk_type.value, "rule_based")
        self.assertEqual(result.failure_probability_type.value, "rule_based")
        self.assertEqual(result.rul_type.value, "rule_based")
        self.assertEqual(result.domain_contributions[0].value_type.value, "measured")
        self.assertEqual(result.prognostic_status.value, "heuristic_unvalidated")
        self.assertIn("bukan prediksi ML", result.prognostic_disclaimer)


class FuseEquipmentTests(unittest.TestCase):
    """fuse_equipment() against the real DGA/vibration fixtures - same
    approach as tests/test_pple_assets.py."""

    def setUp(self):
        self.engine = ReliabilityFusionEngine()

    def test_fuse_equipment_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.engine.fuse_equipment("DOES-NOT-EXIST")

    def test_fuse_equipment_dga_transformer(self):
        from pple.assets import AssetRegistry

        sample = AssetRegistry().list_equipment(domain="dga")[0]

        result = self.engine.fuse_equipment(sample.id)

        self.assertEqual(result.equipment_id, sample.id)
        self.assertTrue(any(c.module_id == "dga" for c in result.domain_contributions))
        self.assertGreaterEqual(result.health_index, 0.0)
        self.assertLessEqual(result.health_index, 100.0)

    def test_fuse_equipment_notes_missing_vibration_data_instead_of_faking_it(self):
        from pple.assets import AssetRegistry

        # A DGA transformer has no vibration monthly-test counterpart, so
        # fuse_equipment() must not invent a vibration score for it.
        sample = AssetRegistry().list_equipment(domain="dga")[0]

        result = self.engine.fuse_equipment(sample.id)

        self.assertFalse(any(c.module_id == "vibration" for c in result.domain_contributions))


if __name__ == "__main__":
    unittest.main()
