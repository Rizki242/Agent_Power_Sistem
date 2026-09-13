"""Unit tests for Executive Fleet Reliability Dashboard and Risk Matrix features."""

import unittest
import pandas as pd

from pple.application.fleet import FleetReliabilityUseCase
from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.fleet_reliability import build_fleet_reliability, _normalize_unit


class TestExecutiveFleetReliability(unittest.TestCase):
    def setUp(self):
        self.fusion_agent = ReliabilityFusionAgent()
        self.asset_graph = AssetKnowledgeGraph()
        self.use_case = FleetReliabilityUseCase(
            fusion_agent=self.fusion_agent,
            asset_graph=self.asset_graph,
        )

    def test_normalize_unit(self):
        self.assertEqual(_normalize_unit("UNIT 1"), "UNIT 1")
        self.assertEqual(_normalize_unit("PLTU Jeranjang Unit 1"), "UNIT 1")
        self.assertEqual(_normalize_unit("Unit_2"), "UNIT 2")
        self.assertEqual(_normalize_unit("Unit 3 Boiler"), "UNIT 3")
        self.assertEqual(_normalize_unit("BOP Common System"), "COMMON")
        self.assertEqual(_normalize_unit(""), "COMMON")
        self.assertEqual(_normalize_unit(None), "COMMON")

    def test_empty_dataframe_has_executive_keys(self):
        result = build_fleet_reliability(pd.DataFrame(), self.fusion_agent, self.asset_graph)
        self.assertEqual(result["total_assets"], 0)
        self.assertIn("unit_summary", result)
        self.assertIn("risk_matrix", result)
        self.assertIn("risk_matrix_assets", result)
        self.assertIn("risk_grid", result)
        self.assertIn("bad_actors", result)
        self.assertEqual(result["bad_actors"], [])

    def test_unit_summary_and_risk_matrix(self):
        rows = [
            {"Equipment": "CWP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Value": None},
            {"Equipment": "CWP 2A", "Parameter": "Kondisi", "Raw_Value": "Normal", "Value": None},
            {"Equipment": "PA FAN 3A", "Parameter": "Kondisi", "Raw_Value": "Normal", "Value": None},
        ]
        df_latest = pd.DataFrame(rows)

        result = self.use_case.execute(df_latest, limit=10, include_multi_domain=False)

        self.assertEqual(result["total_assets"], 3)
        self.assertIn("unit_summary", result)
        self.assertIn("risk_matrix", result)
        self.assertIn("risk_grid", result)

        # Verify risk_grid structure
        grid = result["risk_grid"]
        self.assertIn("x", grid)
        self.assertIn("y", grid)
        self.assertIn("z", grid)
        self.assertIn("text", grid)
        self.assertIn("hover", grid)
        self.assertEqual(len(grid["x"]), 3)  # Class C, B, A
        self.assertEqual(len(grid["y"]), 4)  # CRITICAL, ALERT, WARNING, HEALTHY / WATCH

        # Verify bad_actors is sorted descending by composite_risk_score
        bad_actors = result["bad_actors"]
        self.assertLessEqual(len(bad_actors), 10)
        for i in range(len(bad_actors) - 1):
            self.assertGreaterEqual(
                bad_actors[i]["composite_risk_score"],
                bad_actors[i + 1]["composite_risk_score"],
            )

        # Verify domain_alerts keys exist
        for item in result["asset_matrix"]:
            self.assertIn("domain_alerts", item)
            for d in ("mcsa", "vibration", "thermal", "tribology"):
                self.assertIn(d, item["domain_alerts"])

    def test_use_case_execute_alias(self):
        df_latest = pd.DataFrame([
            {"Equipment": "CWP 1A", "Parameter": "Kondisi", "Raw_Value": "Normal", "Value": None}
        ])
        res1 = self.use_case.get_fleet_summary(df_latest, limit=5, include_multi_domain=False)
        res2 = self.use_case.execute(df_latest, limit=5, include_multi_domain=False)
        self.assertEqual(res1["total_assets"], res2["total_assets"])
        self.assertEqual(res1["fleet_health_average"], res2["fleet_health_average"])


if __name__ == "__main__":
    unittest.main()

