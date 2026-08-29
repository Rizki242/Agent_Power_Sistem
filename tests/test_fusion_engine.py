import unittest
import os
import tempfile
from fastapi.testclient import TestClient

from src.agents.specialist_agents import (
    VibrationAgent, MCSAAgent, DGAAgent, PDAgent, TribologyAgent, ThermalAgent
)
from src.agents.fusion_engine import (
    ReliabilityFusionAgent, FailureModeDiagnosisAgent, RULPredictor, RiskEngine, MaintenanceDecisionAgent
)
from src.agents.safety_guard import SafetyGuardrailAgent
from src.agents.asset_graph import AssetKnowledgeGraph
from api_server import (
    app,
    _extract_mcsa_fusion_inputs,
    _get_work_orders_store_path,
    _load_work_orders,
    _save_work_orders,
)


class TestReliabilityFusionSystem(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.fusion = ReliabilityFusionAgent()
        self.safety = SafetyGuardrailAgent()
        self.graph = AssetKnowledgeGraph()

    def test_specialist_agents(self):
        # 1. Vibration Agent
        vib = VibrationAgent()
        v_res = vib.evaluate("CWP 1A", {"overall_rms": 5.2, "bpfo_amp": 1.2})
        self.assertEqual(v_res["domain"], "Vibration")
        self.assertIn("Bearing", v_res["failure_mode"])
        self.assertGreaterEqual(v_res["severity"], 3)

        # 2. MCSA Agent
        mcsa = MCSAAgent()
        m_res = mcsa.evaluate("CWP 1A", {"upper_sb": -44.0, "bearing_status": "Alarm"})
        self.assertEqual(m_res["domain"], "MCSA")
        self.assertEqual(m_res["condition"], "CRITICAL")

        # 3. DGA Agent
        dga = DGAAgent()
        d_res = dga.evaluate("Main Transformer 1", {"c2h2": 15.0, "c2h4": 80.0, "ch4": 40.0})
        self.assertEqual(d_res["domain"], "DGA")
        self.assertIn("D2", d_res["failure_mode"])

        # 4. PD Agent
        pd_ag = PDAgent()
        p_res = pd_ag.evaluate("Generator 1", {"pulse_magnitude_pc": 1800.0, "nqn": 120.0})
        self.assertEqual(p_res["condition"], "CRITICAL")

        # 5. Tribology Agent
        tribo = TribologyAgent()
        t_res = tribo.evaluate("BFP 1A", {"fe_ppm": 85.0, "water_ppm": 600.0})
        self.assertEqual(t_res["condition"], "CRITICAL")

        # 6. Thermal Agent
        therm = ThermalAgent()
        th_res = therm.evaluate("IDF 1A", {"bearing_temp": 88.0, "delta_t_phase": 18.0})
        self.assertGreaterEqual(th_res["severity"], 3)

    def test_reliability_fusion_correlation(self):
        # Test Multi-Modal Bearing Evidence Correlation
        fusion_res = self.fusion.run_full_fusion(
            equipment="CWP 2A",
            asset_type="Electric Motor-Pump",
            criticality="A",
            vibration_data={"overall_rms": 5.4, "bpfo_amp": 1.4},
            mcsa_data={"upper_sb": -52.0, "bearing_status": "Alarm"},
            oil_data={"fe_ppm": 55.0},
            thermal_data={"bearing_temp": 82.0}
        )

        self.assertIn("Bearing", fusion_res["failure_mode_diagnosis"]["primary_failure_mode"])
        self.assertGreaterEqual(fusion_res["failure_mode_diagnosis"]["confidence"], 0.90)
        self.assertIn("fused_evidence", fusion_res["failure_mode_diagnosis"])
        self.assertIn("predictive_rul", fusion_res)
        self.assertIn("estimated_rul_days", fusion_res["predictive_rul"])
        self.assertIn("risk_assessment", fusion_res)
        self.assertIn("work_order", fusion_res["maintenance_decision"])

    def test_safety_guardrail(self):
        blocked = self.safety.check_safety("Tolong shutdown turbine sekarang juga")
        self.assertFalse(blocked["safe"])
        self.assertTrue(blocked["violation_detected"])
        self.assertIn("SAFETY GUARDRAIL BLOCKED", blocked["message"])

        safe_query = self.safety.check_safety("Berapa getaran motor CWP 1A?")
        self.assertTrue(safe_query["safe"])
        self.assertFalse(safe_query["violation_detected"])

    def test_asset_knowledge_graph(self):
        node = self.graph.get_equipment_node("BFP 1A")
        self.assertEqual(node["unit"], "UNIT 1")
        self.assertEqual(node["criticality"], "A")
        self.assertIn("Feedwater", node["system"])

    def test_api_reliability_endpoints(self):
        # 1. Fleet summary
        fleet_res = self.client.get("/api/reliability/fleet")
        self.assertEqual(fleet_res.status_code, 200)
        data = fleet_res.json()
        self.assertIn("total_assets", data)
        self.assertIn("asset_matrix", data)

        # 2. Equipment fusion detail
        eq_res = self.client.get("/api/reliability/fusion/BC%2010.1")
        self.assertEqual(eq_res.status_code, 200)
        fusion_data = eq_res.json()
        self.assertIn("health_index", fusion_data)
        self.assertIn("failure_mode_diagnosis", fusion_data)

        # 3. Work orders
        wo_res = self.client.get("/api/workorders")
        self.assertEqual(wo_res.status_code, 200)
        self.assertGreaterEqual(wo_res.json()["count"], 1)

    def test_mcsa_fusion_inputs_do_not_invent_missing_modalities(self):
        import pandas as pd

        eq_data = pd.DataFrame([
            {"Equipment": "CWP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Value": None},
            {"Equipment": "CWP 1A", "Parameter": "Upper Sideband", "Raw_Value": "-52.5", "Value": -52.5},
            {"Equipment": "CWP 1A", "Parameter": "Dev Current", "Raw_Value": "6.1", "Value": 6.1},
        ])

        inputs = _extract_mcsa_fusion_inputs(eq_data)

        self.assertEqual(
            set(inputs.keys()),
            {"mcsa_data"},
            "Reliability fusion should not fabricate vibration, thermal, or oil inputs from MCSA status alone.",
        )
        self.assertEqual(inputs["mcsa_data"]["upper_sb"], -52.5)
        self.assertEqual(inputs["mcsa_data"]["dev_current"], 6.1)
        self.assertEqual(inputs["mcsa_data"]["bearing_status"], "Alarm")

    def test_work_order_approval_is_persisted_to_configured_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store_path = os.path.join(tmpdir, "work_orders.json")
            old_path = os.environ.get("WORK_ORDERS_FILE")
            os.environ["WORK_ORDERS_FILE"] = store_path
            try:
                orders = [{
                    "wo_number": "WO-TEST-0001",
                    "equipment": "CWP 1A",
                    "title": "Test WO",
                    "priority": "P3 - Medium",
                    "reason": "Regression test",
                    "required_tools": [],
                    "required_parts": [],
                    "required_manpower": "1 Technician",
                    "target_completion_date": "2026-08-30",
                    "status": "Draft - Awaiting Approval",
                }]
                _save_work_orders(orders)
                self.assertEqual(_get_work_orders_store_path(), store_path)

                res = self.client.post("/api/workorders/approve", json={
                    "wo_number": "WO-TEST-0001",
                    "approved_by": "Engineer Test",
                    "action": "Approve",
                })

                self.assertEqual(res.status_code, 200)
                persisted = _load_work_orders()
                self.assertEqual(persisted[0]["status"], "Approved by Engineer Test - In Progress")
            finally:
                if old_path is None:
                    os.environ.pop("WORK_ORDERS_FILE", None)
                else:
                    os.environ["WORK_ORDERS_FILE"] = old_path


if __name__ == "__main__":
    unittest.main()
