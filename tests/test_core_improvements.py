import unittest

import pandas as pd

from src.analytics import build_risk_summary, calculate_equipment_health_score, detect_equipment_anomalies, summarize_word_report_quality
from src.metadata import enrich_equipment_metadata
from src.standards import (
    calculate_rotorbar_severity,
    generate_esa_mcsa_quick_recommendations,
)


class MetadataEnrichmentTests(unittest.TestCase):
    def test_enrich_equipment_metadata_prefers_master_then_folder_metadata(self):
        df = pd.DataFrame(
            [
                {"Equipment": "BC101", "Unit_Name": "Unknown", "Voltage_Level": "Unknown", "Full_Name": "BC101"},
                {"Equipment": "CTF3A", "Unit_Name": "", "Voltage_Level": "", "Full_Name": ""},
            ]
        )
        master_df = pd.DataFrame(
            [
                {"Equipment": "BC101", "Unit_Name": "UNIT COMMON", "Voltage_Level": "380/400 V", "Full_Name": "BC 10.1"},
            ]
        )
        folder_meta = {
            "CTF3A": {"Unit": "UNIT 3", "Voltage": "380/400 V", "Full_Name": "CTF 3A"},
        }

        enriched = enrich_equipment_metadata(df, master_df=master_df, folder_metadata=folder_meta)

        bc101 = enriched[enriched["Equipment"] == "BC101"].iloc[0]
        self.assertEqual(bc101["Unit_Name"], "UNIT COMMON")
        self.assertEqual(bc101["Voltage_Level"], "380/400 V")
        self.assertEqual(bc101["Full_Name"], "BC 10.1")

        ctf3a = enriched[enriched["Equipment"] == "CTF3A"].iloc[0]
        self.assertEqual(ctf3a["Unit_Name"], "UNIT 3")
        self.assertEqual(ctf3a["Voltage_Level"], "380/400 V")
        self.assertEqual(ctf3a["Full_Name"], "CTF 3A")


class RotorbarSeverityTests(unittest.TestCase):
    def test_rotorbar_uses_shared_thresholds_for_high_severity(self):
        result = calculate_rotorbar_severity(
            {
                "Upper Sideband": -35.0,
                "Lower Sideband": -35.0,
                "Rotorbar Health": None,
            }
        )

        self.assertEqual(result["Level"], 4)
        self.assertEqual(result["Status"], "High")

    def test_rotorbar_low_load_does_not_inflate_severity(self):
        result = calculate_rotorbar_severity(
            {
                "Upper Sideband": -60.0,
                "Lower Sideband": -60.0,
                "Load": 30.0,
            }
        )

        self.assertEqual(result["Level"], 2)
        self.assertEqual(result["Status"], "Normal")
        self.assertEqual(result["Diagnostic Validity"], "Monitoring Only (20-40%)")


class EsaMcsaQuickRecommendationsTests(unittest.TestCase):
    def _latest_df(self, rows):
        return pd.DataFrame(
            [
                {"Parameter": k, "Value": v, "Raw_Value": "" if v is None else str(v)}
                for k, v in rows.items()
            ]
        )

    def test_high_overall_when_any_indicator_high(self):
        result = generate_esa_mcsa_quick_recommendations(
            self._latest_df(
                {
                    "Load": 75,
                    "Dev Voltage": 3.0,
                    "Dev Current": 12.0,
                    "THD Voltage %": 9.0,
                }
            )
        )
        self.assertEqual(result["overall"], "High")
        self.assertEqual(result["statuses"]["Unbalance Voltage"], "High")
        self.assertEqual(result["statuses"]["Unbalance Current"], "High")
        self.assertEqual(result["statuses"]["THD Voltage"], "High")
        self.assertEqual(result["statuses"]["Load Quality"], "Valid")
        self.assertTrue(result["recommendations"])

    def test_alarm_overall_when_indicators_warning_only(self):
        result = generate_esa_mcsa_quick_recommendations(
            self._latest_df(
                {
                    "Load": 65,
                    "Dev Voltage": 1.5,
                    "Dev Current": 6.0,
                    "THD Voltage %": 6.0,
                }
            )
        )
        self.assertEqual(result["overall"], "Alarm")
        self.assertEqual(result["statuses"]["Unbalance Voltage"], "Alarm")
        self.assertEqual(result["statuses"]["THD Voltage"], "Alarm")
        self.assertEqual(result["statuses"]["Load Quality"], "Valid")

    def test_normal_overall_within_limits(self):
        result = generate_esa_mcsa_quick_recommendations(
            self._latest_df(
                {
                    "Load": 80,
                    "Dev Voltage": 0.5,
                    "Dev Current": 2.0,
                    "THD Voltage %": 3.0,
                }
            )
        )
        self.assertEqual(result["overall"], "Normal")
        self.assertEqual(result["statuses"]["Unbalance Voltage"], "Normal")
        self.assertEqual(result["statuses"]["THD Voltage"], "Normal")
        self.assertEqual(result["statuses"]["Load Quality"], "Valid")

    def test_load_quality_classification(self):
        for load, expected in [(10.0, "Invalid"), (30.0, "Monitoring"), (60.0, "Valid")]:
            with self.subTest(load=load):
                result = generate_esa_mcsa_quick_recommendations(
                    self._latest_df({"Load": load})
                )
                self.assertEqual(result["statuses"]["Load Quality"], expected)

    def test_bearing_text_maps_to_status(self):
        result = generate_esa_mcsa_quick_recommendations(
            self._latest_df({"Load": 80, "Bearing": "Bad bearing"})
        )
        self.assertEqual(result["statuses"]["Bearing"], "High")
        self.assertEqual(result["overall"], "High")


class AnalyticsTests(unittest.TestCase):
    def test_health_score_penalizes_multiple_risk_drivers(self):
        score = calculate_equipment_health_score(
            {
                "Rotorbar": "High",
                "THD Voltage %": 6.2,
                "Dev Current": 11.0,
                "Bearing": "Alarm",
                "Load": 85.0,
            }
        )

        self.assertLess(score["score"], 60)
        self.assertIn("Rotorbar", score["drivers"])
        self.assertIn("Dev Current", score["drivers"])

    def test_detect_equipment_anomalies_compares_latest_vs_previous_samples(self):
        history = pd.DataFrame(
            [
                {"Equipment": "BC101", "Parameter": "THD Voltage %", "Date": "2026-01-01", "Value": 2.0, "Raw_Value": "2.0"},
                {"Equipment": "BC101", "Parameter": "THD Voltage %", "Date": "2026-02-01", "Value": 2.1, "Raw_Value": "2.1"},
                {"Equipment": "BC101", "Parameter": "THD Voltage %", "Date": "2026-03-01", "Value": 2.0, "Raw_Value": "2.0"},
                {"Equipment": "BC101", "Parameter": "THD Voltage %", "Date": "2026-04-01", "Value": 3.0, "Raw_Value": "3.0"},
            ]
        )

        anomalies = detect_equipment_anomalies(history)

        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies[0]["Equipment"], "BC101")
        self.assertEqual(anomalies[0]["Parameter"], "THD Voltage %")

    def test_quality_summary_reports_missing_params_and_bad_dates(self):
        df_word = pd.DataFrame(
            [
                {"Equipment": "BC101", "Parameter": "Load", "Date": "2030-01-01", "Value": 20, "Raw_Value": "20", "Unit_Name": "Unknown", "Voltage_Level": "Unknown"},
                {"Equipment": "BC101", "Parameter": "THD Voltage %", "Date": "2030-01-01", "Value": 99, "Raw_Value": "99", "Unit_Name": "Unknown", "Voltage_Level": "Unknown"},
            ]
        )
        report = {"failures": [{"file": "bad.docx", "error": "parse error"}]}

        summary = summarize_word_report_quality(
            df_word,
            report,
            required_params=["Load", "THD Voltage %", "Bearing"],
            max_future_days=30,
        )

        self.assertEqual(summary["failed_files_count"], 1)
        self.assertEqual(len(summary["missing_parameter_rows"]), 1)
        self.assertEqual(len(summary["weird_date_rows"]), 2)
        self.assertEqual(len(summary["numeric_flag_rows"]), 1)
        self.assertEqual(len(summary["missing_metadata_rows"]), 2)

    def test_build_risk_summary_sorts_lowest_health_score_first(self):
        df_latest = pd.DataFrame(
            [
                {"Equipment": "BC101", "Parameter": "Rotorbar", "Raw_Value": "High", "Value": None},
                {"Equipment": "BC101", "Parameter": "Dev Current", "Raw_Value": "11", "Value": 11.0},
                {"Equipment": "BC102", "Parameter": "Rotorbar", "Raw_Value": "Normal", "Value": None},
                {"Equipment": "BC102", "Parameter": "Dev Current", "Raw_Value": "2", "Value": 2.0},
            ]
        )

        summary = build_risk_summary(df_latest, top_n=2)

        self.assertEqual(summary[0]["Equipment"], "BC101")
        self.assertLess(summary[0]["Health Score"], summary[1]["Health Score"])


if __name__ == "__main__":
    unittest.main()
