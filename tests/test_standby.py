import unittest
from datetime import date

import pandas as pd

from src.standby import compute_standby


def _sample_df():
    rows = [
        {"Equipment": "BFP 1A", "Parameter": "Kondisi", "Raw_Value": "Normal", "Value": None,
         "Date": "2026-08-10", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV"},
        {"Equipment": "BFP 1A", "Parameter": "Dev Current", "Raw_Value": "6.1", "Value": 6.1,
         "Date": "2026-08-10", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV"},
    ]
    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def _sample_master():
    return pd.DataFrame([
        {"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV", "Full_Name": "Boiler Feed Pump 1A"},
        {"Equipment": "CWP 1B", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V", "Full_Name": "Circulating Water Pump 1B"},
    ])


class TestComputeStandby(unittest.TestCase):
    def test_missing_equipment_marked_standby(self):
        df = _sample_df()
        df_latest = df.copy()

        augmented, report, df_month, meta_df = compute_standby(
            df, df_latest, df_latest, _sample_master(), {}, {},
            date(2026, 8, 31), "Semua Unit (abaikan filter Unit)", "All", "All", ["Kondisi"],
        )

        self.assertIn("BFP 1A", report["eq_present"])
        self.assertIn("CWP 1B", report["eq_missing"])
        self.assertEqual(report["month_start"].strftime("%Y-%m"), "2026-08")
        standby_rows = augmented[augmented["Raw_Value"] == "Standby"]
        self.assertEqual(len(standby_rows), 1)
        self.assertEqual(standby_rows.iloc[0]["Equipment"], "CWP 1B")
        self.assertEqual(standby_rows.iloc[0]["Status"], "Standby")
        self.assertFalse(df_month.empty)
        self.assertFalse(meta_df.empty)

    def test_all_equipment_present_has_no_standby_rows(self):
        master = pd.DataFrame([
            {"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV", "Full_Name": "BFP 1A"},
        ])
        df = _sample_df()
        df_latest = df.copy()

        augmented, report, df_month, meta_df = compute_standby(
            df, df_latest, df_latest, master, {}, {},
            date(2026, 8, 31), "Semua Unit (abaikan filter Unit)", "All", "All", ["Kondisi"],
        )

        self.assertEqual(report["eq_missing"], [])
        self.assertTrue((augmented["Raw_Value"] != "Standby").all())
        self.assertEqual(len(augmented), len(df_latest))

    def test_per_unit_scope_filters_universe(self):
        master = pd.DataFrame([
            {"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV", "Full_Name": "BFP 1A"},
            {"Equipment": "CWP 2A", "Unit_Name": "UNIT 2", "Voltage_Level": "6.3 KV", "Full_Name": "CWP 2A"},
        ])
        df = _sample_df()
        df_latest = df.copy()

        augmented, report, df_month, meta_df = compute_standby(
            df, df_latest, df_latest, master, {}, {},
            date(2026, 8, 31), "Per Unit (mengikuti filter Unit/Voltage)", "UNIT 1", "All", ["Kondisi"],
        )

        self.assertIn("BFP 1A", report["eq_universe"])
        self.assertNotIn("CWP 2A", report["eq_universe"])
        self.assertEqual(report["sel_unit"], "UNIT 1")

    def test_reference_month_filters_rows(self):
        df = _sample_df()
        extra = pd.DataFrame([
            {"Equipment": "BFP 1A", "Parameter": "Kondisi", "Raw_Value": "High", "Value": None,
             "Date": "2026-07-05", "Unit_Name": "UNIT 1", "Voltage_Level": "6.3 KV"},
        ])
        extra["Date"] = pd.to_datetime(extra["Date"])
        df = pd.concat([df, extra], ignore_index=True)
        df_latest = df.copy()

        augmented, report, df_month, meta_df = compute_standby(
            df, df_latest, df_latest, _sample_master(), {}, {},
            date(2026, 8, 31), "Semua Unit (abaikan filter Unit)", "All", "All", ["Kondisi"],
        )

        self.assertTrue((df_month["Date"].dt.strftime("%Y-%m") == "2026-08").all())
        self.assertIn("BFP 1A", report["eq_present"])


if __name__ == "__main__":
    unittest.main()
