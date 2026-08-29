import os
import tempfile
import unittest
from unittest.mock import patch

import src.dga_data as dga_data
from src.dga_data import (
    DEFAULT_TRANSFORMERS,
    get_dga_transformer_detail,
    save_dga_transformer,
    search_dga_transformers,
)
from src.domain_overrides import DomainOverrideStore


class DGAOverrideTests(unittest.TestCase):
    """Uses a temp-file-backed store so these tests never touch the real
    data/config/dga_overrides.json (avoids leaving a stray tracked-looking
    file in the repo working tree)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._store_path = os.path.join(self._tmpdir.name, "dga_overrides.json")
        self._patcher = patch.object(
            dga_data, "_override_store", return_value=DomainOverrideStore(self._store_path)
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()
        self._tmpdir.cleanup()

    def test_no_overrides_returns_default_transformers_unchanged(self):
        results = search_dga_transformers()
        self.assertEqual(len(results), len(DEFAULT_TRANSFORMERS))
        ids = {r["transformer_id"] for r in results}
        self.assertEqual(ids, {t["transformer_id"] for t in DEFAULT_TRANSFORMERS})

    def test_editing_existing_transformer_replaces_its_gases(self):
        new_gases = {"H2": 999.0, "CH4": 1.0, "C2H6": 1.0, "C2H4": 1.0, "C2H2": 1.0, "CO": 1.0, "CO2": 1.0, "H2O": 1.0}
        save_dga_transformer("TRF-001", {
            "name": "Generator Step-Up Transformer 1 (GT 1)",
            "unit": "UNIT 1",
            "voltage_ratio": "10.5 / 150 kV",
            "rated_capacity": "31.25 MVA",
            "oil_type": "Mineral Oil (IEC 60296)",
            "oil_volume": "14,500 L",
            "sampling_date": "2026-08-01",
            "gases": new_gases,
            "status": "NORMAL",
        })
        detail = get_dga_transformer_detail("TRF-001")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["gases"]["H2"], 999.0)
        # Total count unchanged - this was an edit, not an add.
        self.assertEqual(len(search_dga_transformers()), len(DEFAULT_TRANSFORMERS))

    def test_adding_new_transformer_id_increases_count(self):
        save_dga_transformer("TRF-999", {
            "name": "Test Transformer",
            "unit": "UNIT 1",
            "voltage_ratio": "10.5 / 150 kV",
            "rated_capacity": "1.0 MVA",
            "oil_type": "Mineral Oil",
            "oil_volume": "100 L",
            "sampling_date": "2026-08-01",
            "gases": {"H2": 1.0, "CH4": 1.0, "C2H6": 1.0, "C2H4": 1.0, "C2H2": 0.0, "CO": 1.0, "CO2": 1.0, "H2O": 1.0},
            "status": "NORMAL",
        })
        results = search_dga_transformers()
        self.assertEqual(len(results), len(DEFAULT_TRANSFORMERS) + 1)
        self.assertIsNotNone(get_dga_transformer_detail("TRF-999"))

    def test_other_transformers_unaffected_by_an_edit(self):
        save_dga_transformer("TRF-001", {
            "name": "Generator Step-Up Transformer 1 (GT 1)",
            "unit": "UNIT 1",
            "voltage_ratio": "10.5 / 150 kV",
            "rated_capacity": "31.25 MVA",
            "oil_type": "Mineral Oil (IEC 60296)",
            "oil_volume": "14,500 L",
            "sampling_date": "2026-08-01",
            "gases": {"H2": 999.0, "CH4": 1.0, "C2H6": 1.0, "C2H4": 1.0, "C2H2": 1.0, "CO": 1.0, "CO2": 1.0, "H2O": 1.0},
            "status": "NORMAL",
        })
        original_trf002 = next(t for t in DEFAULT_TRANSFORMERS if t["transformer_id"] == "TRF-002")
        detail = get_dga_transformer_detail("TRF-002")
        self.assertEqual(detail["gases"]["H2"], original_trf002["gases"]["H2"])


if __name__ == "__main__":
    unittest.main()
