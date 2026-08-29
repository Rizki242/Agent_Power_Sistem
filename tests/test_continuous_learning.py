"""
Unit tests for Power Plant Continuous Learning and Self-Improving Skills.
"""

import unittest
import tempfile
import os
from src.agents.continuous_learning import PowerPlantSkillLearner


class TestPowerPlantSkillLearner(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.learner = PowerPlantSkillLearner(storage_path=self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_initial_seed_skills(self):
        skills = self.learner.load_learned_skills()
        self.assertGreaterEqual(len(skills), 5)
        titles = [s["title"] for s in skills]
        self.assertTrue(any("BFP 1A" in t for t in titles))
        self.assertTrue(any("ID Fan" in t for t in titles))

    def test_teach_agent_new_skill(self):
        res = self.learner.teach_agent(
            equipment="CEP 1A",
            title="CEP 1A High Frequency Bearing Fluting due to VFD Inverter",
            system="Condensate System",
            category="MCSA_KELISTRIKAN",
            symptoms=["Bearing BPFO high frequency noise", "Harmonisa arus 5th/7th"],
            verified_root_cause="Fluting discharge current pada bantalan NDE akibat ketiadaan grounding brush pada motor VFD.",
            corrective_action_taken="Pemasangan shaft grounding brush dan ceramic insulated bearing pada sisi NDE.",
            lesson_learned="Motor VFD wajib dipasangi grounding ring shaft untuk membuang tegangan induksi poros dan mencegah bearing fluting.",
            author="Senior Electrical Engineer"
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("SKILL-PLTU-", res["skill"]["id"])
        
        # Verify query retrieval
        matches = self.learner.query_learned_knowledge("CEP 1A")
        self.assertTrue(any(m["equipment"] == "CEP 1A" for m in matches))

    def test_query_learned_knowledge(self):
        matches = self.learner.query_learned_knowledge("BC 41", "sideband rotor bar retak")
        self.assertGreater(len(matches), 0)
        self.assertTrue(any("BC 41" in m.get("equipment", "") or "Rotor Bar" in m.get("title", "") for m in matches))

    def test_run_benchmarks(self):
        bm = self.learner.run_benchmarks()
        self.assertEqual(bm["total_benchmarks"], 5)
        self.assertGreaterEqual(bm["diagnostic_accuracy_score"], 90.0)
        self.assertEqual(bm["rating"], "GRADE A - EXPERT SYSTEM")
        self.assertEqual(len(bm["benchmark_results"]), 5)


if __name__ == "__main__":
    unittest.main()
