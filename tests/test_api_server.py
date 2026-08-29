import unittest
from fastapi.testclient import TestClient
from api_server import app

class TestAPIServer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get("status"), "ok")

    def test_summary(self):
        res = self.client.get("/api/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_equipment", data)
        self.assertIn("counts", data)

    def test_equipment_list(self):
        res = self.client.get("/api/equipment")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("equipment", data)
        self.assertGreater(len(data["equipment"]), 0)

    def test_rotorbar_calculate(self):
        res = self.client.post("/api/rotorbar/calculate", json={"upper_sb": -40.0, "lower_sb": -42.0})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "High")
        self.assertEqual(data.get("severity_level"), 4)

    def test_agent_chat(self):
        res = self.client.post("/api/agent/chat", json={"message": "List Alarm"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("reply", data)
        self.assertIn("Warning/Alarm", data.get("reply"))

    def test_specialist_subagents_endpoint(self):
        res = self.client.get("/api/agents/specialists")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("specialists", data)
        self.assertGreaterEqual(data["total_count"], 8)

    def test_collaborate_endpoint(self):
        res = self.client.post("/api/agents/collaborate", json={"equipment": "BFP 1A"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("equipment"), "BFP 1A")
        self.assertIn("consensus_health_index", data)
        self.assertIn("subagent_traces", data)

    def test_assessment_report_endpoint(self):
        res = self.client.get("/api/reports/assessment/BFP%201A")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("equipment"), "BFP 1A")
        self.assertIn("report_id", data)
        self.assertIn("assessment_summary", data)
        self.assertIn("signoff", data)

    def test_harness_status_endpoint(self):
        res = self.client.get("/api/learning/harness-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ACTIVE")
        self.assertIn("components", data)
        self.assertGreaterEqual(data.get("total_harness_components", 0), 3)

    def test_rigger_cycle_endpoint(self):
        res = self.client.post("/api/learning/rigger-cycle", json={"equipment": "BFP 1A"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "COMPLETED")
        self.assertIn("rigger_cycle", data)

    def test_evaluate_harness_endpoint(self):
        res = self.client.post("/api/learning/evaluate-harness")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "EVALUATED")
        self.assertIn("harness_score", data)
        self.assertIn("results", data)


if __name__ == "__main__":
    unittest.main()

