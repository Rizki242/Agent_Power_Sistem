"""Unit and characterization tests for agent_dashboard_page Streamlit presenter."""

import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from src.pages.agent_dashboard_page import (
    _render_health_chips,
    _render_fleet_table,
    _render_roster,
    _run_equipment_diagnosis,
)


class TestAgentDashboardPage(unittest.TestCase):
    def test_run_equipment_diagnosis_delegates_to_use_case(self):
        mock_coordinator = MagicMock()
        mock_coordinator.safety_guard.check_safety.return_value = {"safe": True, "message": "OK"}
        mock_coordinator.fusion_agent.run_full_fusion.return_value = {
            "equipment": "BFP 1A",
            "health_index": 90.0,
            "overall_status": "HEALTHY",
        }
        mock_coordinator.asset_graph.get_equipment_node.return_value = {
            "equipment": "BFP 1A",
            "asset_type": "Electric Motor-Pump",
            "criticality": "A",
        }

        df_latest = pd.DataFrame(
            [{"Equipment": "BFP 1A", "Parameter": "Rotorbar", "Raw_Value": "-45.0 dB", "Status": "Normal"}]
        )

        res = _run_equipment_diagnosis(mock_coordinator, df_latest, "BFP 1A")
        self.assertIn("fusion", res)
        self.assertIn("safety", res)
        self.assertIn("data_sources", res)
        self.assertEqual(res["fusion"]["equipment"], "BFP 1A")
        self.assertTrue(res["safety"]["safe"])

    def test_render_health_chips(self):
        mock_st = MagicMock()
        summary = {"HEALTHY": 5, "WATCH": 2, "WARNING": 1, "ALERT": 0, "CRITICAL": 0}
        _render_health_chips(mock_st, summary)
        mock_st.markdown.assert_called_once()
        html_arg = mock_st.markdown.call_args[0][0]
        self.assertIn("HEALTHY: 5", html_arg)
        self.assertIn("WARNING: 1", html_arg)

    def test_render_fleet_table_empty(self):
        mock_st = MagicMock()
        _render_fleet_table(mock_st, [])
        mock_st.info.assert_called_once_with("Tidak ada aset pada status WARNING/ALERT/CRITICAL.")

    def test_render_fleet_table_with_records(self):
        mock_st = MagicMock()
        assets = [
            {
                "equipment": "BFP 1A",
                "unit": "UNIT 1",
                "system": "Condensate",
                "criticality": "A",
                "health_index": 85.0,
                "health_status": "HEALTHY",
                "primary_failure_mode": "Normal",
                "severity": "Normal",
                "rul_days": 180,
                "risk_level": "Low",
            }
        ]
        _render_fleet_table(mock_st, assets)
        mock_st.dataframe.assert_called_once()

    def test_render_roster(self):
        mock_st = MagicMock()
        specialists = [
            {"name": "Vibration Specialist", "icon": "📳", "domain": "Vibration", "role": "Analyzer", "status": "Ready"}
        ]
        _render_roster(mock_st, specialists)
        mock_st.dataframe.assert_called_once()


if __name__ == "__main__":
    unittest.main()
