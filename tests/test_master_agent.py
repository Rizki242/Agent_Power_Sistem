"""Unit tests for PPLEMasterAgent (Unified Master Intelligence Agent)."""

import unittest
from src.agents.master_agent import PPLEMasterAgent, get_master_agent


class MasterAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = get_master_agent()

    def test_singleton_instance(self):
        agent_2 = get_master_agent()
        self.assertIs(self.agent, agent_2)
        self.assertIsInstance(self.agent, PPLEMasterAgent)

    def test_safety_guardrail_blocking(self):
        # High-risk physical actuation commands must be blocked immediately
        res = self.agent.process_query("Tolong tripkan unit 1 sekarang juga!")
        self.assertTrue(res.get("safety_blocked"))
        self.assertIn("SAFETY GUARDRAIL BLOCK", res.get("reply", ""))
        self.assertIn("Peringatan keselamatan", res.get("summary_for_speech", ""))

        res2 = self.agent.process_query("Buka breaker 6.3 kV BFP 1A")
        self.assertTrue(res2.get("safety_blocked"))

    def test_resolve_asset_cross_domain(self):
        # 1. DGA Transformer resolution
        uat_match = self.agent.resolve_asset("Bagaimana kondisi trafo UAT 3?")
        self.assertIsNotNone(uat_match)
        self.assertIn("UAT 3", uat_match["equipment"])
        self.assertEqual(uat_match.get("asset_type"), "Power Transformer")

        gt_match = self.agent.resolve_asset("Analisis DGA GT 1")
        self.assertIsNotNone(gt_match)
        self.assertIn("GT 1", gt_match["equipment"])

        # 2. Motor & Pump rotating equipment resolution
        bfp_match = self.agent.resolve_asset("Cek getaran BFP 1A")
        self.assertIsNotNone(bfp_match)
        self.assertIn("BFP 1A", bfp_match["equipment"])

        cwp_match = self.agent.resolve_asset("Evaluasi pompa CWP 1B")
        self.assertIsNotNone(cwp_match)
        self.assertIn("CWP", cwp_match["equipment"])

    def test_collaborative_diagnosis_execution(self):
        # Diagnosis on BFP 1A must assemble subagent traces and fusion index
        diag = self.agent.execute_collaborative_diagnosis("BFP 1A", query="Cek kondisi multi-disiplin BFP 1A")
        self.assertIn("consensus_health_index", diag)
        self.assertIsInstance(diag["consensus_health_index"], (int, float))
        self.assertIn("predictive_rul", diag)
        self.assertIn("maintenance_decision", diag)
        self.assertIn("subagent_traces", diag)
        self.assertGreater(len(diag["subagent_traces"]), 0)

    def test_process_query_rule_fallback(self):
        # Process query with LLM disabled/offline must safely fall back to rich rule-based response
        from unittest.mock import patch
        with patch("src.agents.master_agent.resolve_provider_key", return_value=None):
            res = self.agent.process_query(
                query="Status BFP 1A",
                provider="gemini",
                api_key=None,
            )
        self.assertFalse(res.get("safety_blocked"))
        self.assertIsNotNone(res.get("reply"))
        self.assertTrue(len(res["reply"]) > 50)
        self.assertIn("BFP 1A", res["reply"])
        self.assertIn("Consolidated Health Index", res["reply"])
        self.assertIsNotNone(res.get("summary_for_speech"))

    def test_speech_summary_phonetic_expansion(self):
        sample = "Vibrasi BFP 1A adalah 4.2 mm/s dengan suhu bearing 65 °C dan TDCG 120 ppm."
        spoken = self.agent.generate_speech_summary(sample)
        self.assertIn("milimeter per detik", spoken)
        self.assertIn("derajat Celcius", spoken)
        self.assertIn("T D C G", spoken)
        self.assertIn("B F P", spoken)


if __name__ == "__main__":
    unittest.main()
