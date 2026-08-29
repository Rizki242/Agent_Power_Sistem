import os
import tempfile
import unittest
from unittest.mock import patch

import src.pd_data as pd_data
from src.pd_data import (
    DEFAULT_PD_SAMPLES,
    get_pd_sample_detail,
    save_pd_sample,
    search_pd_samples,
)
from src.domain_overrides import DomainOverrideStore


class PDDataTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._store_path = os.path.join(self._tmpdir.name, "pd_overrides.json")
        self._patcher = patch.object(
            pd_data, "_override_store", return_value=DomainOverrideStore(self._store_path)
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_status_thresholds_match_pdagent(self):
        # Same thresholds PDAgent.evaluate() uses: >=1500 pC or >=100 NQN -> HIGH,
        # >=500 -> WARNING, >=250 -> PREWARNING, else NORMAL.
        self.assertEqual(pd_data._pd_status(100.0, 5.0), "NORMAL")
        self.assertEqual(pd_data._pd_status(250.0, 5.0), "PREWARNING")
        self.assertEqual(pd_data._pd_status(500.0, 5.0), "WARNING")
        self.assertEqual(pd_data._pd_status(1500.0, 5.0), "HIGH")
        self.assertEqual(pd_data._pd_status(10.0, 100.0), "HIGH")

    def test_no_overrides_returns_default_samples_unchanged(self):
        results = search_pd_samples()
        self.assertEqual(len(results), len(DEFAULT_PD_SAMPLES))

    def test_every_default_sample_has_a_status(self):
        for r in search_pd_samples():
            self.assertIn(r["status"], {"NORMAL", "PREWARNING", "WARNING", "HIGH"})

    def test_editing_existing_sample_replaces_its_fields(self):
        save_pd_sample("PD-001", {
            "equipment": "Generator Stator Winding Unit 1",
            "unit": "UNIT 1",
            "test_date": "2026-08-01",
            "method": "PRPD Online Monitoring",
            "pulse_magnitude_pc": 1600.0,
            "pd_type": "Internal Void",
            "phase_clustering_deg": 42.0,
            "nqn": 120.0,
        })
        detail = get_pd_sample_detail("PD-001")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["status"], "HIGH")
        self.assertEqual(len(search_pd_samples()), len(DEFAULT_PD_SAMPLES))

    def test_adding_new_sample_id_increases_count(self):
        save_pd_sample("PD-TEST-NEW", {
            "equipment": "Test Equipment",
            "unit": "UNIT 1",
            "test_date": "2026-08-01",
            "method": "PRPD Online Monitoring",
            "pulse_magnitude_pc": 50.0,
            "pd_type": "Corona",
            "phase_clustering_deg": 10.0,
            "nqn": 1.0,
        })
        self.assertEqual(len(search_pd_samples()), len(DEFAULT_PD_SAMPLES) + 1)
        self.assertIsNotNone(get_pd_sample_detail("PD-TEST-NEW"))

    def test_other_samples_unaffected_by_an_edit(self):
        original = next(s for s in DEFAULT_PD_SAMPLES if s["sample_id"] == "PD-002")
        save_pd_sample("PD-001", {**DEFAULT_PD_SAMPLES[0], "pulse_magnitude_pc": 1600.0, "nqn": 120.0})
        detail = get_pd_sample_detail("PD-002")
        self.assertEqual(detail["pulse_magnitude_pc"], original["pulse_magnitude_pc"])


if __name__ == "__main__":
    unittest.main()
