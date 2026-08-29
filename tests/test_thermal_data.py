import os
import tempfile
import unittest
from unittest.mock import patch

import src.thermal_data as thermal_data
from src.thermal_data import (
    get_thermal_record_detail,
    load_thermal_irt_tests,
    save_thermal_record,
    search_thermal_records,
)
from src.domain_overrides import DomainOverrideStore


class ThermalOverrideTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._store_path = os.path.join(self._tmpdir.name, "thermal_overrides.json")
        self._patcher = patch.object(
            thermal_data, "_override_store", return_value=DomainOverrideStore(self._store_path)
        )
        self._patcher.start()
        self._base = load_thermal_irt_tests()
        self.assertTrue(self._base, "expected real thermal IRT records to exist")
        self._record_id = self._base[0]["id"]

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_no_overrides_returns_base_unchanged(self):
        self.assertEqual(len(search_thermal_records()), len(self._base))

    def test_editing_existing_record_replaces_its_status(self):
        original = self._base[0]
        save_thermal_record(self._record_id, {**original, "status": "HIGH"})
        detail = get_thermal_record_detail(self._record_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["status"], "HIGH")
        self.assertEqual(len(search_thermal_records()), len(self._base))

    def test_adding_new_record_id_increases_count(self):
        save_thermal_record("IRT-TEST-NEW", {
            "unit": "UNIT 1",
            "kks": "TEST-KKS",
            "equipment": "Test Equipment",
            "raw_status": "Low",
            "status": "NORMAL",
            "standard": "FLIR Thermal Camera / Delta-T Matrix",
            "test_date": "2026-08-01",
        })
        self.assertEqual(len(search_thermal_records()), len(self._base) + 1)
        self.assertIsNotNone(get_thermal_record_detail("IRT-TEST-NEW"))

    def test_recommendation_reflects_status_without_calling_thermal_agent(self):
        original = self._base[0]
        save_thermal_record(self._record_id, {**original, "status": "HIGH"})
        detail = get_thermal_record_detail(self._record_id)
        self.assertIn("segera", detail["recommendation"].lower())

        save_thermal_record(self._record_id, {**original, "status": "STANDBY"})
        detail = get_thermal_record_detail(self._record_id)
        self.assertIn("standby", detail["recommendation"].lower())

    def test_other_records_unaffected_by_an_edit(self):
        other = self._base[1]
        original = self._base[0]
        save_thermal_record(self._record_id, {**original, "status": "HIGH"})
        detail = get_thermal_record_detail(other["id"])
        self.assertEqual(detail["status"], other["status"])


if __name__ == "__main__":
    unittest.main()
