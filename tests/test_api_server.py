import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import api_server
import pple.api.router as pple_api_router
from api_server import app
from pple.engineering.equipment_modules import EquipmentModuleStore
from src.agents.continuous_learning import PowerPlantSkillLearner
from src.agents.env_harness import EnvRigger

class TestAPIServer(unittest.TestCase):
    """Patches the module-level plant_skill_learner/env_rigger singletons so
    the /api/learning/* tests never write to the real data/learning/ tree
    (see api_server.py's plant_skill_learner = PowerPlantSkillLearner() and
    env_rigger = EnvRigger(), both instantiated with the real default paths)."""

    def setUp(self):
        self.client = TestClient(app)
        self._tmpdir = tempfile.mkdtemp()
        self._learner_patcher = patch.object(
            api_server,
            "plant_skill_learner",
            PowerPlantSkillLearner(storage_path=os.path.join(self._tmpdir, "learned_skills.json")),
        )
        self._rigger_patcher = patch.object(
            api_server,
            "env_rigger",
            EnvRigger(storage_dir=os.path.join(self._tmpdir, "env_harness")),
        )
        self._learner_patcher.start()
        self._rigger_patcher.start()
        self.addCleanup(self._learner_patcher.stop)
        self.addCleanup(self._rigger_patcher.stop)
        self.addCleanup(shutil.rmtree, self._tmpdir, True)

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

    def test_v2_assets_tree_endpoint(self):
        res = self.client.get("/api/v2/assets/tree")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        unit_names = {u["name"] for u in data["units"]}
        self.assertEqual(unit_names, {"UNIT 1", "UNIT 2", "UNIT 3", "COMMON"})

    def test_v2_assets_tree_domain_filter(self):
        res = self.client.get("/api/v2/assets/tree", params={"domain": "vibration"})
        self.assertEqual(res.status_code, 200)
        domains = {e["domain"] for u in res.json()["units"] for e in u["equipment"]}
        self.assertEqual(domains, {"vibration"})

    def test_v2_assets_list_endpoint(self):
        res = self.client.get("/api/v2/assets", params={"unit": "UNIT 1"})
        self.assertEqual(res.status_code, 200)
        equipment = res.json()["equipment"]
        self.assertGreater(len(equipment), 0)
        self.assertTrue(all(e["unit"] == "UNIT 1" for e in equipment))

    def test_v2_assets_get_endpoint(self):
        listed = self.client.get("/api/v2/assets", params={"domain": "dga"}).json()["equipment"]
        sample_id = listed[0]["id"]

        res = self.client.get(f"/api/v2/assets/{sample_id}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["id"], sample_id)

    def test_v2_assets_get_unknown_returns_404(self):
        res = self.client.get("/api/v2/assets/DOES-NOT-EXIST")
        self.assertEqual(res.status_code, 404)

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


class TestPartialDischargeEndpoints(unittest.TestCase):
    """PD was the only domain with no HTTP surface at all (docs/final.md's
    'Migrate PD' step), so these cover the whole route family."""

    def setUp(self):
        self.client = TestClient(app)

    def test_summary_shape(self):
        res = self.client.get("/api/pd/summary")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_samples", data)
        self.assertIn("by_unit", data)
        self.assertIn("by_status", data)

    def test_samples_list(self):
        res = self.client.get("/api/pd/samples")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], len(data["samples"]))
        self.assertGreater(data["count"], 0)
        # every row must carry the fields the sidebar tree reads
        for sample in data["samples"]:
            self.assertIn("sample_id", sample)
            self.assertIn("equipment", sample)
            self.assertIn("unit", sample)
            self.assertIn("status", sample)

    def test_samples_filters(self):
        unit_res = self.client.get("/api/pd/samples", params={"unit": "UNIT 1"})
        self.assertEqual(unit_res.status_code, 200)
        self.assertTrue(all(s["unit"] == "UNIT 1" for s in unit_res.json()["samples"]))

        status_res = self.client.get("/api/pd/samples", params={"status": "HIGH"})
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(all(s["status"] == "HIGH" for s in status_res.json()["samples"]))

        search_res = self.client.get("/api/pd/samples", params={"search": "switchgear"})
        self.assertEqual(search_res.status_code, 200)
        self.assertTrue(
            all("switchgear" in s["equipment"].lower() for s in search_res.json()["samples"])
        )

    def test_sample_detail_and_404(self):
        res = self.client.get("/api/pd/samples/PD-001")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["sample_id"], "PD-001")
        self.assertIn("pulse_magnitude_pc", data)
        self.assertIn("status", data)

        missing = self.client.get("/api/pd/samples/NOT-A-SAMPLE")
        self.assertEqual(missing.status_code, 404)

    def test_assessment_runs_agent_and_agrees_with_status(self):
        res = self.client.get("/api/pd/samples/PD-005/assessment")
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["domain"], "Partial Discharge")
        self.assertIn("recommendation", result)
        self.assertIn("evidence", result)

        # PD-005 is the HIGH sample; pd_data._pd_status and PDAgent share
        # thresholds, so the badge must not contradict the agent's verdict.
        detail = self.client.get("/api/pd/samples/PD-005").json()
        self.assertEqual(detail["status"], "HIGH")
        self.assertEqual(result["condition"], "CRITICAL")
        self.assertEqual(result["severity"], 4)

    def test_assessment_404_for_unknown_sample(self):
        res = self.client.get("/api/pd/samples/NOT-A-SAMPLE/assessment")
        self.assertEqual(res.status_code, 404)


if __name__ == "__main__":
    unittest.main()

