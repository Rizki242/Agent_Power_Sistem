import unittest

import pandas as pd

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs, numeric_param, status_from_equipment_rows
from src.fleet_reliability import build_fleet_reliability


class TestFusionInputs(unittest.TestCase):
    def test_status_from_equipment_rows(self):
        df = pd.DataFrame([{"Parameter": "Kondisi", "Raw_Value": "alarm"}])
        self.assertEqual(status_from_equipment_rows(df), "Alarm")
        self.assertEqual(status_from_equipment_rows(pd.DataFrame()), "Normal")
        self.assertEqual(status_from_equipment_rows(None), "Normal")

    def test_numeric_param_prefers_value_then_raw(self):
        df = pd.DataFrame([
            {"Parameter": "Dev Current", "Value": 6.1, "Raw_Value": "6.1"},
            {"Parameter": "Bearing", "Value": None, "Raw_Value": "Normal"},
        ])
        self.assertEqual(numeric_param(df, "Dev Current"), 6.1)
        self.assertIsNone(numeric_param(df, "Bearing"))
        self.assertIsNone(numeric_param(df, "Missing Param"))
        self.assertIsNone(numeric_param(pd.DataFrame(), "Dev Current"))


class TestBuildFleetReliability(unittest.TestCase):
    def setUp(self):
        self.fusion_agent = ReliabilityFusionAgent()
        self.asset_graph = AssetKnowledgeGraph()

    def test_empty_dataframe_returns_zero_assets(self):
        result = build_fleet_reliability(pd.DataFrame(), self.fusion_agent, self.asset_graph)
        self.assertEqual(result["total_assets"], 0)
        self.assertEqual(result["asset_matrix"], [])
        self.assertEqual(result["health_summary"], {})

    def test_fleet_matrix_from_measured_rows(self):
        df_latest = pd.DataFrame([
            {"Equipment": "CWP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Value": None},
            {"Equipment": "CWP 1A", "Parameter": "Upper Sideband", "Raw_Value": "-52.5", "Value": -52.5},
        ])

        result = build_fleet_reliability(df_latest, self.fusion_agent, self.asset_graph)

        self.assertEqual(result["total_assets"], 1)
        entry = result["asset_matrix"][0]
        for key in ("equipment", "unit", "system", "criticality", "health_index", "health_status",
                    "health_color", "primary_failure_mode", "severity", "confidence",
                    "rul_days", "risk_level"):
            self.assertIn(key, entry)
        self.assertEqual(entry["equipment"], "CWP 1A")
        self.assertGreaterEqual(result["fleet_health_average"], 0)
        self.assertLessEqual(result["fleet_health_average"], 100)
        self.assertIn(result["health_summary"].get("HEALTHY", 0) + result["health_summary"].get("WATCH", 0)
                      + result["health_summary"].get("WARNING", 0) + result["health_summary"].get("ALERT", 0)
                      + result["health_summary"].get("CRITICAL", 0), (0, 1))

    def test_matrix_sorted_by_health_index_ascending(self):
        rows = []
        for eq, kondisi in (("AAA 1", "Normal"), ("BBB 2", "High"), ("CCC 3", "Alarm")):
            rows.append({"Equipment": eq, "Parameter": "Kondisi", "Raw_Value": kondisi, "Value": None})
        df_latest = pd.DataFrame(rows)

        result = build_fleet_reliability(df_latest, self.fusion_agent, self.asset_graph)

        health_values = [a["health_index"] for a in result["asset_matrix"]]
        self.assertEqual(health_values, sorted(health_values))
        self.assertEqual(result["total_assets"], 3)


if __name__ == "__main__":
    unittest.main()
