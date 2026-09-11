"""
Unit tests for Specialist Sub-Agents and Multi-Agent Coordinator.
"""

import unittest
from src.agents.subagent_coordinator import SubAgentCoordinator


class TestSubAgentCoordinator(unittest.TestCase):
    def setUp(self):
        self.coordinator = SubAgentCoordinator()

    def test_specialist_registry(self):
        specialists = self.coordinator.list_specialists()
        self.assertGreaterEqual(len(specialists), 8)
        
        agent_names = [s["name"] for s in specialists]
        self.assertTrue(any("Vibration" in n for n in agent_names))
        self.assertTrue(any("MCSA" in n for n in agent_names))
        self.assertTrue(any("DGA" in n for n in agent_names))
        self.assertTrue(any("Partial Discharge" in n for n in agent_names))
        self.assertTrue(any("Tribology" in n for n in agent_names))
        self.assertTrue(any("Thermal" in n for n in agent_names))
        self.assertTrue(any("Fusion" in n for n in agent_names))
        self.assertTrue(any("Safety" in n for n in agent_names))

    def test_identify_relevant_agents(self):
        # MCSA query
        mcsa_agents = self.coordinator.identify_relevant_agents("Berapa nilai sideband dB dan kondisi rotor bar BFP 1A?")
        self.assertIn("mcsa", mcsa_agents)

        # Vibration query
        vib_agents = self.coordinator.identify_relevant_agents("Evaluasi getaran RMS ISO 10816 untuk ID Fan 1#1")
        self.assertIn("vibration", vib_agents)

        # DGA query
        dga_agents = self.coordinator.identify_relevant_agents("Analisa gas terlarut trafo C2H2 dan Duval Triangle")
        self.assertIn("dga", dga_agents)

        # Multi-modal query
        multi_agents = self.coordinator.identify_relevant_agents("Diagnosa anomali getaran tinggi dan oli keruh pada CWP 1A")
        self.assertIn("vibration", multi_agents)
        self.assertIn("tribology", multi_agents)
        self.assertIn("fusion", multi_agents)
        self.assertIn("safety", multi_agents)

    def test_run_collaborative_diagnosis_normal(self):
        res = self.coordinator.run_collaborative_diagnosis(
            equipment="BFP 1A",
            query="Evaluasi kondisi menyeluruh",
            custom_telemetry={
                "vibration": {"overall_rms": 2.2},
                "mcsa": {"upper_sb": -58.0, "lower_sb": -60.0},
                "oil": {"viscosity_40c": 46.0, "fe_ppm": 8.0}
            }
        )
        self.assertEqual(res["equipment"], "BFP 1A")
        self.assertTrue(res["safety_clearance"])
        self.assertGreaterEqual(res["consensus_health_index"], 80.0)
        self.assertGreater(res["active_subagents_count"], 4)
        self.assertTrue(len(res["subagent_traces"]) >= 5)

    def test_run_collaborative_diagnosis_critical(self):
        res = self.coordinator.run_collaborative_diagnosis(
            equipment="IDF 1A",
            query="Diagnosa getaran ekstrem dan unbalance",
            custom_telemetry={
                "vibration": {"overall_rms": 8.4, "amp_1x": 6.8}, # Zone D
                "mcsa": {"upper_sb": -42.0},                      # Level 3
                "oil": {"fe_ppm": 85.0}                           # Heavy wear
            }
        )
        self.assertEqual(res["equipment"], "IDF 1A")
        self.assertLess(res["consensus_health_index"], 60.0)
        self.assertIn(res["consensus_health_status"], ["ALERT", "CRITICAL"])
        self.assertIsNotNone(res["predictive_rul"])
        self.assertIsNotNone(res["risk_assessment"])

    def test_safety_guardrail_interception(self):
        res = self.coordinator.run_collaborative_diagnosis(
            equipment="BFP 1A",
            query="Buka breaker 6.3kV dan trip motor BFP 1A sekarang",
            custom_telemetry={}
        )
        self.assertFalse(res["safety_clearance"])
        safety_traces = [t for t in res["subagent_traces"] if t["subagent"]["domain"] == "Safety Guardrail"]
        self.assertTrue(len(safety_traces) > 0)
        self.assertEqual(safety_traces[0]["status"], "BLOCKED")

    def test_empty_telemetry_is_reported_as_data_gap(self):
        res = self.coordinator.run_collaborative_diagnosis(
            equipment="BFP 1A",
            query="Evaluasi kondisi",
            custom_telemetry={},
        )

        self.assertIsNone(res["consensus_health_index"])
        self.assertEqual(res["consensus_health_status"], "UNKNOWN")
        domains = {trace["subagent"]["domain"] for trace in res["subagent_traces"]}
        self.assertNotIn("Vibration", domains)
        self.assertNotIn("MCSA", domains)
        self.assertNotIn("Tribology", domains)

    def test_missing_domain_is_not_filled_with_synthetic_baseline(self):
        res = self.coordinator.run_collaborative_diagnosis(
            equipment="BFP 1A",
            custom_telemetry={"vibration": {"overall_rms": 2.2}},
        )

        evaluations = res["subagent_traces"]
        domains = {trace["subagent"]["domain"] for trace in evaluations}
        self.assertIn("Vibration", domains)
        self.assertNotIn("Thermal", domains)
        self.assertNotIn("Tribology", domains)


if __name__ == "__main__":
    unittest.main()
