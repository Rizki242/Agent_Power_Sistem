"""Unit tests for pple.application use cases."""

import unittest
from unittest.mock import MagicMock
import pandas as pd

from pple.application import (
    DiagnoseEquipmentUseCase,
    FleetReliabilityUseCase,
    GenerateAssessmentReportUseCase,
)


class TestApplicationUseCases(unittest.TestCase):
    def test_diagnose_equipment_use_case_from_inputs(self):
        mock_fusion = MagicMock()
        mock_fusion.run_full_fusion.return_value = {
            "equipment": "BFP 1A",
            "health_index": 92.0,
            "health_status": "HEALTHY",
        }
        mock_graph = MagicMock()

        use_case = DiagnoseEquipmentUseCase(fusion_agent=mock_fusion, asset_graph=mock_graph)
        res = use_case.diagnose_from_inputs(
            equipment="BFP 1A",
            asset_type="Motor-Pump",
            criticality="A",
            vibration={"overall": 1.2},
        )

        mock_fusion.run_full_fusion.assert_called_once()
        self.assertEqual(res["equipment"], "BFP 1A")
        self.assertEqual(res["health_index"], 92.0)

    def test_diagnose_equipment_use_case_from_mcsa_dataset(self):
        mock_fusion = MagicMock()
        mock_fusion.run_full_fusion.return_value = {
            "equipment": "BFP 1A",
            "health_index": 90.0,
        }
        mock_graph = MagicMock()
        mock_graph.get_equipment_node.return_value = {
            "equipment": "BFP 1A",
            "asset_type": "Electric Motor-Pump",
            "criticality": "A",
        }

        df_latest = pd.DataFrame(
            [
                {"Equipment": "BFP 1A", "Parameter": "Rotorbar", "Raw_Value": "-45.0 dB", "Status": "Normal"},
            ]
        )

        use_case = DiagnoseEquipmentUseCase(fusion_agent=mock_fusion, asset_graph=mock_graph)
        res = use_case.diagnose_from_mcsa_dataset("BFP 1A", df_latest)

        self.assertIn("asset_node", res)
        self.assertIn("data_sources", res)
        self.assertEqual(res["asset_node"]["equipment"], "BFP 1A")

    def test_fleet_reliability_use_case(self):
        mock_fusion = MagicMock()
        mock_graph = MagicMock()

        use_case = FleetReliabilityUseCase(fusion_agent=mock_fusion, asset_graph=mock_graph)
        df_latest = pd.DataFrame(
            [
                {"Equipment": "BFP 1A", "Unit_Name": "UNIT 1", "Parameter": "Kondisi", "Raw_Value": "Normal", "Status": "Normal"},
            ]
        )

        res = use_case.get_fleet_summary(df_latest)
        self.assertIn("total_assets", res)
        self.assertIn("health_summary", res)

    def test_generate_assessment_report_use_case(self):
        mock_coordinator = MagicMock()
        mock_coordinator.run_collaborative_diagnosis.return_value = {
            "equipment": "BFP 1A",
            "unit": "UNIT 1",
            "system": "Feedwater & Condensate",
            "asset_type": "Medium Voltage Motor Drive",
            "criticality": "A",
            "consensus_health_index": 95.0,
            "consensus_health_status": "HEALTHY",
            "consensus_failure_mode": "Normal Operation",
            "consensus_confidence": 0.98,
            "predictive_rul": {"estimated_rul_days": 180},
            "risk_assessment": {"risk_level": "Low Risk (Acceptable)"},
            "fused_evidence": ["No anomalous frequency signatures detected."],
            "subagent_traces": [],
            "maintenance_decision": {"action": "Continue Routine Monitoring"},
            "safety_clearance": True,
        }

        use_case = GenerateAssessmentReportUseCase(coordinator=mock_coordinator)
        report = use_case.generate_report("BFP 1A")

        self.assertEqual(report["equipment"], "BFP 1A")
        self.assertTrue(report["report_id"].startswith("CBM-RPT-"))
        self.assertIn("assessment_summary", report)
        self.assertEqual(report["assessment_summary"]["health_index"], 95.0)
        self.assertTrue(report["safety_clearance"])
        self.assertIn("signoff", report)


if __name__ == "__main__":
    unittest.main()
