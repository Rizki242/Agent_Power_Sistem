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
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs
from api_server import app
from pple.api.routers.work_orders import (
    _get_work_orders_store_path,
    _load_work_orders,
    _save_work_orders,
)
from pple.api.schemas.reliability import FusionDiagnosisResponse


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
        self.assertEqual(v_res["fault_code"], "BEARING_OUTER_RACE")
        self.assertIn("BEARING_DEGRADATION", v_res["mechanism_tags"])
        self.assertGreaterEqual(v_res["severity"], 3)

        # 2. MCSA Agent
        mcsa = MCSAAgent()
        m_res = mcsa.evaluate("CWP 1A", {"upper_sb": -44.0, "bearing_status": "Alarm"})
        self.assertEqual(m_res["domain"], "MCSA")
        self.assertEqual(m_res["condition"], "CRITICAL")
        self.assertIn("BEARING_DEGRADATION", m_res["mechanism_tags"])

        # 3. DGA Agent
        dga = DGAAgent()
        d_res = dga.evaluate("Main Transformer 1", {"c2h2": 15.0, "c2h4": 80.0, "ch4": 40.0})
        self.assertEqual(d_res["domain"], "DGA")
        self.assertIn("D2", d_res["failure_mode"])
        self.assertEqual(d_res["fault_code"], "DGA_HIGH_ENERGY_DISCHARGE")

        # 4. PD Agent
        pd_ag = PDAgent()
        p_res = pd_ag.evaluate("Generator 1", {"pulse_magnitude_pc": 1800.0, "nqn": 120.0})
        self.assertEqual(p_res["condition"], "CRITICAL")
        self.assertEqual(p_res["fault_code"], "PARTIAL_DISCHARGE_ACTIVE")

        # 5. Tribology Agent
        tribo = TribologyAgent()
        t_res = tribo.evaluate("BFP 1A", {"fe_ppm": 85.0, "water_ppm": 600.0})
        self.assertEqual(t_res["condition"], "CRITICAL")
        self.assertEqual(t_res["fault_code"], "BEARING_WEAR")

        # 6. Thermal Agent
        therm = ThermalAgent()
        th_res = therm.evaluate("IDF 1A", {"bearing_temp": 88.0, "delta_t_phase": 18.0})
        self.assertGreaterEqual(th_res["severity"], 3)
        self.assertEqual(th_res["fault_code"], "ELECTRICAL_HOTSPOT")
        self.assertIn("BEARING_DEGRADATION", th_res["mechanism_tags"])

    def test_direct_specialists_do_not_treat_empty_payload_as_healthy(self):
        agents = [
            VibrationAgent(), MCSAAgent(), DGAAgent(), PDAgent(),
            TribologyAgent(), ThermalAgent(),
        ]

        for agent in agents:
            with self.subTest(domain=agent.domain_name):
                result = agent.evaluate("ASSET-1", {})
                self.assertEqual(result["condition"], "UNKNOWN")
                self.assertIsNone(result["health_score"])
                self.assertEqual(result["severity"], 0)
                self.assertEqual(result["confidence"], 0.0)
                self.assertEqual(result["data_quality"]["status"], "insufficient_data")
                self.assertEqual(result["fault_code"], "UNKNOWN")
                self.assertEqual(result["mechanism_tags"], [])

    def test_unknown_tribology_is_a_data_gap_not_a_fusion_score(self):
        result = self.fusion.run_full_fusion("TEST-PARTIAL-OIL", oil_data={"water_ppm": 0})
        self.assertEqual(result["health_status"], "UNKNOWN")
        self.assertIsNone(result["health_index"])
        self.assertIsNone(result["maintenance_decision"]["work_order"])
        self.assertIn("Tribology", result["data_quality"]["excluded_domains"])

    def test_partial_tribology_alarm_preserves_partial_quality_in_fusion(self):
        result = self.fusion.run_full_fusion("TEST-PARTIAL-OIL", oil_data={"fe_ppm": 85})
        self.assertEqual(result["health_status"], "CRITICAL")
        self.assertEqual(result["data_quality"]["status"], "partial")
        self.assertEqual(result["data_quality"]["excluded_domains"], {})

    def test_unknown_tribology_does_not_change_measured_vibration_fusion(self):
        baseline = self.fusion.run_full_fusion("TEST-PARTIAL-OIL", vibration_data={"overall_rms": 5.2})
        result = self.fusion.run_full_fusion(
            "TEST-PARTIAL-OIL", vibration_data={"overall_rms": 5.2}, oil_data={"iso_cleanliness": "22/19/13"},
        )
        self.assertEqual(result["health_index"], baseline["health_index"])
        self.assertNotIn("Tribology", result["specialist_evaluations"])
        self.assertIn("Tribology", result["data_quality"]["excluded_domains"])

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
        hypothesis = fusion_res["failure_mode_diagnosis"]["ranked_hypotheses"][0]
        self.assertEqual(hypothesis["fault_code"], "BEARING_DEGRADATION")
        self.assertEqual(len(hypothesis["supporting_evidence"]), 4)
        self.assertIn("physical_mechanism", hypothesis)
        self.assertIn("confidence_rationale", hypothesis)
        self.assertIn("required_confirmation", hypothesis)

    def test_bearing_fusion_uses_structured_taxonomy_not_failure_mode_text(self):
        specialist_results = {
            "Vibration": {
                "failure_mode": "teks bebas tanpa kata kunci",
                "fault_code": "BEARING_OUTER_RACE",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "metrics": {"bpfo_amp": 1.2},
            },
            "Tribology": {
                "failure_mode": "deskripsi lokal",
                "fault_code": "BEARING_WEAR",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "metrics": {"fe_ppm": 50.0},
            },
            "Thermal": {
                "failure_mode": "kondisi temperatur normal",
                "fault_code": "NORMAL",
                "mechanism_tags": [],
                "severity": 1,
                "metrics": {"bearing_temp_c": 60.0},
            },
        }

        diagnosis = FailureModeDiagnosisAgent().diagnose(specialist_results)

        self.assertIn("Bearing", diagnosis["primary_failure_mode"])
        hypothesis = diagnosis["ranked_hypotheses"][0]
        self.assertEqual(hypothesis["fault_code"], "BEARING_DEGRADATION")
        self.assertEqual(len(hypothesis["supporting_evidence"]), 2)
        self.assertTrue(hypothesis["contradicting_evidence"])
        self.assertIn("MCSA", hypothesis["missing_evidence"])

    def test_other_fusion_rules_use_structured_fault_codes(self):
        cases = [
            (
                {"MCSA": {
                    "failure_mode": "narasi bebas",
                    "fault_code": "ROTOR_BAR_DEGRADATION",
                    "mechanism_tags": ["ROTOR_ELECTRICAL_DEGRADATION"],
                    "severity": 3,
                    "confidence": 0.88,
                    "evidence": ["sideband terukur"],
                    "metrics": {},
                }},
                "ROTOR_BAR_DEGRADATION",
            ),
            (
                {"Vibration": {
                    "failure_mode": "narasi bebas",
                    "fault_code": "SHAFT_MISALIGNMENT",
                    "mechanism_tags": ["SHAFT_ALIGNMENT"],
                    "severity": 3,
                    "evidence": ["2X dan axial"],
                    "metrics": {},
                }},
                "SHAFT_MISALIGNMENT",
            ),
            (
                {
                    "DGA": {
                        "failure_mode": "narasi bebas",
                        "fault_code": "DGA_HIGH_ENERGY_DISCHARGE",
                        "mechanism_tags": ["ELECTRICAL_DISCHARGE"],
                        "severity": 4,
                        "confidence": 0.92,
                        "evidence": ["C2H2 meningkat"],
                        "metrics": {},
                    },
                    "Partial Discharge": {
                        "failure_mode": "narasi lokal",
                        "fault_code": "PARTIAL_DISCHARGE_ACTIVE",
                        "mechanism_tags": ["ELECTRICAL_DISCHARGE"],
                        "severity": 3,
                        "evidence": ["PRPD aktif"],
                        "metrics": {},
                    },
                },
                "DGA_HIGH_ENERGY_DISCHARGE",
            ),
            (
                {"Partial Discharge": {
                    "failure_mode": "narasi bebas",
                    "fault_code": "PARTIAL_DISCHARGE_ACTIVE",
                    "mechanism_tags": ["INSULATION_DEGRADATION"],
                    "severity": 3,
                    "confidence": 0.87,
                    "evidence": ["PRPD aktif"],
                    "metrics": {},
                }},
                "PARTIAL_DISCHARGE_ACTIVE",
            ),
        ]

        for results, expected_code in cases:
            with self.subTest(expected_code=expected_code):
                diagnosis = FailureModeDiagnosisAgent().diagnose(results)
                self.assertEqual(diagnosis["ranked_hypotheses"][0]["fault_code"], expected_code)

    def test_fusion_hypothesis_is_validated_by_api_schema(self):
        payload = self.fusion.run_full_fusion(
            equipment="CWP 2A",
            vibration_data={"overall_rms": 5.4, "bpfo_amp": 1.4},
            oil_data={"fe_ppm": 55.0},
        )

        response = FusionDiagnosisResponse(**payload)
        hypothesis = response.failure_mode_diagnosis.ranked_hypotheses[0]
        self.assertEqual(hypothesis.fault_code, "BEARING_DEGRADATION")

    def test_fusion_v2_ranks_multiple_simultaneous_hypotheses(self):
        results = {
            "Vibration": {
                "failure_mode": "bearing race defect",
                "fault_code": "BEARING_OUTER_RACE",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "evidence": ["BPFO tinggi"],
                "metrics": {"bpfo_amp": 1.3},
            },
            "Tribology": {
                "failure_mode": "active wear",
                "fault_code": "BEARING_WEAR",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "evidence": ["Fe meningkat"],
                "metrics": {"fe_ppm": 55.0},
            },
            "MCSA": {
                "failure_mode": "rotor asymmetry",
                "fault_code": "ROTOR_BAR_DEGRADATION",
                "mechanism_tags": ["ROTOR_ELECTRICAL_DEGRADATION"],
                "severity": 3,
                "evidence": ["sideband meningkat"],
                "metrics": {"bearing_status": "Normal"},
            },
        }

        diagnosis = FailureModeDiagnosisAgent().diagnose(results)
        hypotheses = diagnosis["ranked_hypotheses"]

        self.assertGreaterEqual(len(hypotheses), 2)
        self.assertEqual(
            {item["fault_code"] for item in hypotheses[:2]},
            {"BEARING_DEGRADATION", "ROTOR_BAR_DEGRADATION"},
        )
        self.assertGreaterEqual(hypotheses[0]["ranking_score"], hypotheses[1]["ranking_score"])
        self.assertEqual([item["rank"] for item in hypotheses], list(range(1, len(hypotheses) + 1)))
        self.assertIn(hypotheses[0]["status"], {"PROBABLE", "POSSIBLE", "INCONCLUSIVE"})
        self.assertEqual(diagnosis["primary_failure_mode"], hypotheses[0]["failure_mode"])
        self.assertEqual(diagnosis["diagnosis_status"], hypotheses[0]["status"])

    def test_fusion_v2_penalizes_missing_and_contradicting_evidence(self):
        diagnosis = FailureModeDiagnosisAgent().diagnose({
            "Vibration": {
                "failure_mode": "bearing race defect",
                "fault_code": "BEARING_OUTER_RACE",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "metrics": {"bpfo_amp": 1.3},
            },
            "Tribology": {
                "failure_mode": "active wear",
                "fault_code": "BEARING_WEAR",
                "mechanism_tags": ["BEARING_DEGRADATION"],
                "severity": 3,
                "metrics": {"fe_ppm": 55.0},
            },
            "Thermal": {
                "failure_mode": "normal",
                "fault_code": "NORMAL",
                "mechanism_tags": [],
                "severity": 1,
                "metrics": {"bearing_temp_c": 60.0},
            },
        })

        hypothesis = diagnosis["ranked_hypotheses"][0]
        self.assertLess(hypothesis["ranking_score"], hypothesis["confidence"])
        self.assertIn("MCSA", hypothesis["missing_evidence"])
        self.assertTrue(hypothesis["contradicting_evidence"])

    def test_reliability_fusion_without_measurements_is_unknown(self):
        result = self.fusion.run_full_fusion(equipment="CWP 2A")

        self.assertIsNone(result["health_index"])
        self.assertEqual(result["health_status"], "UNKNOWN")
        self.assertEqual(result["specialist_evaluations"], {})
        self.assertEqual(result["predictive_rul"]["status"], "unavailable")
        self.assertIsNone(result["predictive_rul"]["estimated_rul_days"])
        self.assertIsNone(result["risk_assessment"]["risk_index"])

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

        inputs = extract_mcsa_fusion_inputs(eq_data)

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
