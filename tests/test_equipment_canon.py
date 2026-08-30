import json
import os
import tempfile
import unittest

import pandas as pd

from src.equipment_canon import (
    build_master_norm_maps,
    canon_unit_name,
    canon_voltage_level,
    compute_overall_status_from_rows,
    load_equipment_master,
    norm_equipment,
    safe_float,
)


class TestCanonHelpers(unittest.TestCase):
    def test_norm_equipment_strips_punctuation_and_uppercases(self):
        self.assertEqual(norm_equipment("BFP-1A"), "BFP1A")
        self.assertEqual(norm_equipment(" CWP 1A "), "CWP1A")
        self.assertEqual(norm_equipment(None), "")

    def test_canon_unit_name_variants(self):
        self.assertEqual(canon_unit_name("Unit1"), "UNIT 1")
        self.assertEqual(canon_unit_name("unit common"), "UNIT COMMON")
        self.assertEqual(canon_unit_name(""), "Unknown")

    def test_canon_voltage_level_variants(self):
        self.assertEqual(canon_voltage_level("6.3 kv"), "6.3 KV")
        self.assertEqual(canon_voltage_level("400V"), "380/400 V")
        self.assertEqual(canon_voltage_level("unknown"), "Unknown")
        self.assertEqual(canon_voltage_level(""), "Unknown")

    def test_safe_float_edge_cases(self):
        self.assertIsNone(safe_float(None))
        self.assertIsNone(safe_float(""))
        self.assertIsNone(safe_float("nan"))
        self.assertIsNone(safe_float(float("nan")))
        self.assertIsNone(safe_float("not-a-number"))
        self.assertEqual(safe_float("3.5"), 3.5)
        self.assertEqual(safe_float(2), 2.0)

    def test_compute_overall_status_from_rows(self):
        rows = pd.DataFrame([
            {"Parameter": "Dev Voltage", "Value": 1.0, "Raw_Value": "1.0"},
            {"Parameter": "Dev Current", "Value": 2.0, "Raw_Value": "2.0"},
            {"Parameter": "Kondisi", "Value": None, "Raw_Value": "Normal"},
        ])
        status = compute_overall_status_from_rows(rows)
        self.assertIn(status, {"Normal", "Alarm", "High", "Standby", "Unknown"})

    def test_compute_overall_status_from_empty_rows(self):
        self.assertEqual(compute_overall_status_from_rows(None), "Unknown")
        self.assertEqual(compute_overall_status_from_rows(pd.DataFrame()), "Unknown")


class TestEquipmentMaster(unittest.TestCase):
    def test_load_equipment_master_from_json(self):
        payload = [{"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV"}]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "equipment_master.json")
            with open(path, "w", encoding="utf-8") as fp:
                json.dump(payload, fp)
            master_df = load_equipment_master(path)
        self.assertFalse(master_df.empty)
        self.assertEqual(master_df.iloc[0]["Equipment"], "BFP 1A")
        for col in ("Equipment", "Unit_Name", "Voltage_Level", "Full_Name"):
            self.assertIn(col, master_df.columns)

    def test_load_equipment_master_missing_file_returns_empty(self):
        self.assertTrue(load_equipment_master(os.path.join("nonexistent", "master.json")).empty)

    def test_build_master_norm_maps_canonicalizes_and_dedupes(self):
        master_df = pd.DataFrame([
            {"Equipment": "BFP 1A", "Unit_Name": "UNIT1", "Voltage_Level": "6.3 kv"},
            {"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV"},
        ])
        unit_map, volt_map = build_master_norm_maps(master_df)
        self.assertEqual(unit_map, {"BFP1A": "UNIT 1"})
        self.assertEqual(volt_map, {"BFP1A": "6.3 KV"})

    def test_build_master_norm_maps_empty_frame(self):
        unit_map, volt_map = build_master_norm_maps(pd.DataFrame())
        self.assertEqual(unit_map, {})
        self.assertEqual(volt_map, {})


if __name__ == "__main__":
    unittest.main()
