import os
import tempfile
import unittest
from unittest.mock import patch

import src.tribology_data as tribology_data
from src.tribology_data import (
    get_tribology_sample_detail,
    load_tribology_monthly_tests,
    save_tribology_sample,
    search_tribology_samples,
)
from src.domain_overrides import DomainOverrideStore


class TribologyOverrideTests(unittest.TestCase):
    """Temp-file-backed store, same reasoning as tests/test_dga_data.py -
    never touch the real data/config/tribology_overrides.json."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._store_path = os.path.join(self._tmpdir.name, "tribology_overrides.json")
        self._patcher = patch.object(
            tribology_data, "_override_store", return_value=DomainOverrideStore(self._store_path)
        )
        self._patcher.start()
        self._base = load_tribology_monthly_tests()
        self.assertTrue(self._base, "expected at least one base tribology sample to exist")
        self._sample_id = self._base[0]["sample_id"]

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_no_overrides_returns_base_unchanged(self):
        self.assertEqual(len(search_tribology_samples()), len(self._base))

    def test_editing_existing_sample_replaces_its_fields(self):
        original = self._base[0]
        save_tribology_sample(self._sample_id, {**original, "wear_fe": 12345})
        detail = get_tribology_sample_detail(self._sample_id)
        self.assertIsNotNone(detail)
        self.assertEqual(detail["wear_fe"], 12345)
        self.assertEqual(len(search_tribology_samples()), len(self._base))

    def test_adding_new_sample_id_increases_count(self):
        save_tribology_sample("OIL-TEST-NEW", {
            "equipment": "Test Equipment",
            "unit": "UNIT 1",
            "oil_brand": "Test Oil",
            "oil_type": "ISO VG 46",
            "sampling_date": "2026-08-01",
            "viscosity_40c": 46.0,
            "tan": 0.1,
            "water_ppm": 10,
            "iso_cleanliness": "16/14/11",
            "wear_fe": 1,
            "wear_cu": 1,
            "flash_point": 220,
            "status": "NORMAL",
        })
        self.assertEqual(len(search_tribology_samples()), len(self._base) + 1)
        self.assertIsNotNone(get_tribology_sample_detail("OIL-TEST-NEW"))

    def test_other_samples_unaffected_by_an_edit(self):
        if len(self._base) < 2:
            self.skipTest("need at least 2 base samples for this check")
        other = self._base[1]
        original = self._base[0]
        save_tribology_sample(self._sample_id, {**original, "wear_fe": 99999})
        detail = get_tribology_sample_detail(other["sample_id"])
        self.assertEqual(detail["wear_fe"], other["wear_fe"])


if __name__ == "__main__":
    unittest.main()
