"""
Unit tests for the Recursive Self-Improvement Engine.
Verifies: real benchmark evaluation, never-regress hill climbing,
prediction-vs-outcome learning, and data-driven history mining.
"""

import os
import tempfile
import unittest

import pandas as pd

from src.agents.continuous_learning import PowerPlantSkillLearner
from src.agents.self_improvement import RecursiveSelfImprover


class SelfImprovementTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.learner = PowerPlantSkillLearner(
            storage_path=os.path.join(self.tmpdir, "learned_skills.json")
        )
        self.improver = RecursiveSelfImprover(
            state_dir=self.tmpdir, learner=self.learner, max_depth=4
        )

    def tearDown(self):
        for fn in os.listdir(self.tmpdir):
            os.remove(os.path.join(self.tmpdir, fn))
        os.rmdir(self.tmpdir)

    def test_real_benchmark_evaluation(self):
        """Benchmarks must be evaluated by the REAL rule-based agents, not simulated."""
        res = self.improver.evaluate_benchmarks()
        self.assertEqual(res["total_benchmarks"], 5)
        self.assertGreaterEqual(res["severity_pass_count"], 4)
        self.assertGreaterEqual(res["diagnostic_score"], 80.0)
        # Observed failure modes come from actual agent evaluation
        for r in res["benchmark_results"]:
            self.assertIn("observed_failure_mode", r)
            self.assertIn(r["status"], ("PASSED", "PARTIAL", "FAILED"))
        # Weak areas are reported honestly for further learning
        self.assertIsInstance(res["weak_areas"], list)

    def test_legacy_run_benchmarks_schema(self):
        """continuous_learning.run_benchmarks() keeps its schema but is now real."""
        bm = self.learner.run_benchmarks()
        self.assertEqual(bm["total_benchmarks"], 5)
        self.assertEqual(bm["evaluation_mode"], "REAL_RULE_BASED")
        self.assertGreaterEqual(bm["diagnostic_accuracy_score"], 90.0)
        self.assertEqual(len(bm["benchmark_results"]), 5)

    def test_retrieval_evaluation_range(self):
        res = self.improver.evaluate_retrieval()
        self.assertGreaterEqual(res["retrieval_score"], 0.0)
        self.assertLessEqual(res["retrieval_score"], 100.0)
        self.assertEqual(res["total"], 5)

    def test_prediction_log_hit_and_miss(self):
        p1 = self.improver.record_prediction("BC 41", "Multiple Broken Rotor Bars", 4, 0.9)
        p2 = self.improver.record_prediction("CWP 1A", "Water Contamination", 3, 0.8)

        r1 = self.improver.record_outcome(
            prediction_id=p1["id"], actual_mode="Broken Rotor Bars severe", actual_severity=4
        )
        self.assertEqual(r1["result"], "HIT")

        r2 = self.improver.record_outcome(
            prediction_id=p2["id"], actual_mode="Bearing wear", actual_severity=1
        )
        self.assertEqual(r2["result"], "MISS")

        pred = self.improver.evaluate_predictions()
        self.assertEqual(pred["prediction_score"], 50.0)
        self.assertEqual(pred["resolved"], 2)

    def test_improvement_cycle_never_regresses(self):
        """Guardrail: the retained best score must never decrease across cycles."""
        first = self.improver.run_improvement_cycle(max_iterations=3)
        self.assertEqual(first["status"], "success")
        self.assertGreaterEqual(first["generation"], 1)
        self.assertTrue(os.path.exists(self.improver.state_path))

        second = self.improver.run_improvement_cycle(max_iterations=3)
        self.assertGreaterEqual(second["best_score"], first["best_score"] - 1e-6)
        self.assertGreaterEqual(second["generation"], first["generation"] + 1)

    def test_improvement_cycle_logs_history(self):
        self.improver.run_improvement_cycle(max_iterations=2)
        status = self.improver.get_status()
        self.assertEqual(status["learning_engine"], "RECURSIVE_SELF_IMPROVEMENT_ACTIVE")
        self.assertEqual(status["total_cycles"], 1)
        self.assertIn("category_weights", status)
        self.assertGreaterEqual(len(status["recent_cycles"]), 1)

    def test_learn_from_history_mines_precursors(self):
        rows = []
        # Equipment that degrades: Normal for 2 periods then Alarm (Load rising)
        for date, kondisi, load in [
            ("2026-01-10", "Normal", 60),
            ("2026-02-10", "Normal", 72),
            ("2026-03-10", "Alarm", 85),
        ]:
            rows.append({"Equipment": "TESTPUMP 1A", "Parameter": "Kondisi", "Raw_Value": kondisi, "Date": date, "Unit": ""})
            rows.append({"Equipment": "TESTPUMP 1A", "Parameter": "Load", "Raw_Value": str(load), "Date": date, "Unit": "%"})
        # Healthy equipment: no transition, must be ignored
        for date in ("2026-01-10", "2026-02-10"):
            rows.append({"Equipment": "OKFAN 2B", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": date, "Unit": ""})

        df = pd.DataFrame(rows)
        res = self.improver.learn_from_history(df)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["lessons_created"], 1)

        skills = self.learner.load_learned_skills()
        auto = [s for s in skills if s.get("source") == "auto_mined"]
        self.assertEqual(len(auto), 1)
        self.assertTrue(auto[0].get("needs_verification"))
        self.assertEqual(auto[0].get("equipment"), "TESTPUMP 1A")
        self.assertTrue(any("Load" in sym for sym in auto[0].get("symptoms", [])))

    def test_learn_from_history_no_transitions(self):
        df = pd.DataFrame([
            {"Equipment": "OKFAN 2B", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": "2026-01-10", "Unit": ""},
            {"Equipment": "OKFAN 2B", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": "2026-02-10", "Unit": ""},
        ])
        res = self.improver.learn_from_history(df)
        self.assertEqual(res["lessons_created"], 0)

    def test_learn_from_history_skips_duplicates(self):
        rows = []
        for date, kondisi, load in [
            ("2026-01-10", "Normal", 60),
            ("2026-02-10", "Normal", 72),
            ("2026-03-10", "Alarm", 85),
        ]:
            rows.append({"Equipment": "TESTPUMP 1A", "Parameter": "Kondisi", "Raw_Value": kondisi, "Date": date, "Unit": ""})
            rows.append({"Equipment": "TESTPUMP 1A", "Parameter": "Load", "Raw_Value": str(load), "Date": date, "Unit": "%"})
        df = pd.DataFrame(rows)
        first = self.improver.learn_from_history(df)
        self.assertEqual(first["lessons_created"], 1)
        # Second run on identical data must not create a duplicate lesson
        second = self.improver.learn_from_history(df)
        self.assertEqual(second["lessons_created"], 0)


if __name__ == "__main__":
    unittest.main()
