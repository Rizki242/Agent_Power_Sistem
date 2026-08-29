import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import pple.api.router as pple_api_router
from api_server import app
from pple.engineering.equipment_modules import EquipmentModuleStore

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

    def test_v2_list_modules_endpoint(self):
        res = self.client.get("/api/v2/modules")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        module_ids = {m["id"] for m in data["modules"]}
        self.assertEqual(
            module_ids,
            {"vibration", "mcsa", "dga", "partial_discharge", "tribology", "thermal"},
        )

    def test_v2_get_module_endpoint(self):
        res = self.client.get("/api/v2/modules/vibration")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], "vibration")
        self.assertIn("MOTOR", data["applicable_equipment"])

    def test_v2_get_unknown_module_returns_404(self):
        res = self.client.get("/api/v2/modules/does-not-exist")
        self.assertEqual(res.status_code, 404)

    def test_v2_module_load_report_endpoint(self):
        res = self.client.get("/api/v2/module-load-report")
        self.assertEqual(res.status_code, 200)
        results = res.json()["results"]
        self.assertEqual(len(results), 6)
        self.assertTrue(all(r["status"] == "ACTIVE" for r in results))

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


class TestV2EquipmentModules(unittest.TestCase):
    """docs/final.md Phase 8 API surface. Patches the router's module-level
    _equipment_module_store so these tests never touch the real config file."""

    def setUp(self):
        self.client = TestClient(app)
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)
        self._patcher = patch.object(pple_api_router, "_equipment_module_store", EquipmentModuleStore(self.path))
        self._patcher.start()
        self.addCleanup(self._patcher.stop)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_list_defaults_all_six_enabled(self):
        res = self.client.get("/api/v2/equipment/CWP-1A/modules")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["equipment_id"], "CWP-1A")
        self.assertEqual(len(data["modules"]), 6)
        self.assertTrue(all(m["enabled"] for m in data["modules"]))

    def test_put_disable_then_list_reflects_it(self):
        put_res = self.client.put("/api/v2/equipment/CWP-1A/modules/dga", json={"enabled": False})
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.json(), {"equipment_id": "CWP-1A", "module_id": "dga", "enabled": False})

        list_res = self.client.get("/api/v2/equipment/CWP-1A/modules")
        by_id = {m["module_id"]: m["enabled"] for m in list_res.json()["modules"]}
        self.assertFalse(by_id["dga"])
        self.assertTrue(by_id["vibration"])  # unaffected

    def test_put_unknown_module_returns_404(self):
        res = self.client.put("/api/v2/equipment/CWP-1A/modules/does-not-exist", json={"enabled": False})
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()

