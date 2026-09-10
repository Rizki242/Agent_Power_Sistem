import os
import shutil
import tempfile
import unittest
import importlib
from unittest.mock import patch

from fastapi.testclient import TestClient

import api_server
import pple.api.router as pple_api_router
import pple.api.security as security
from pple.core import audit
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
        self.assertTrue(res.headers.get("X-Request-ID"))
        self.assertTrue(res.headers.get("X-Correlation-ID"))

    def test_error_envelope_and_correlation_id(self):
        res = self.client.get("/api/equipment/NON-EXISTENT-EQUIPMENT-XYZ")
        self.assertEqual(res.status_code, 404)
        payload = res.json()
        self.assertEqual(payload.get("detail"), "Equipment not found")
        self.assertIn("error", payload)
        self.assertEqual(payload["error"]["code"], 404)
        self.assertEqual(payload["error"]["message"], "Equipment not found")
        self.assertEqual(payload["error"]["correlation_id"], res.headers.get("X-Request-ID"))

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

    def test_equipment_detail(self):
        list_res = self.client.get("/api/equipment")
        self.assertEqual(list_res.status_code, 200)
        eq_name = list_res.json()["equipment"][0]["equipment"]
        res = self.client.get(f"/api/equipment/{eq_name}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("equipment"), eq_name)
        self.assertIn("condition", data)
        self.assertIn("parameters", data)
        self.assertIn("telemetry_groups", data)

    def test_equipment_router_modular_ownership(self):
        from pple.api.routers import equipment_router
        routes = [r.path for r in equipment_router.routes]
        self.assertIn("/api/equipment", routes)
        self.assertIn("/api/equipment/{equipment_name}", routes)

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

    def test_v2_reliability_health_known_equipment(self):
        listed = self.client.get("/api/v2/assets", params={"domain": "dga"}).json()["equipment"]
        sample_id = listed[0]["id"]

        res = self.client.get(f"/api/v2/reliability/{sample_id}")

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["equipment_id"], sample_id)
        self.assertTrue(any(c["module_id"] == "dga" for c in data["domain_contributions"]))
        self.assertIn(data["health_index_type"], {"calculated"})

    def test_v2_reliability_health_unknown_equipment_returns_404(self):
        res = self.client.get("/api/v2/reliability/DOES-NOT-EXIST")
        self.assertEqual(res.status_code, 404)

    def test_v2_agents_list_endpoint(self):
        res = self.client.get("/api/v2/agents")
        self.assertEqual(res.status_code, 200)
        agents = res.json()["agents"]
        self.assertEqual(len(agents), 8)
        vibration = next(a for a in agents if a["agent_id"] == "subagent-vib-01")
        self.assertEqual(vibration["status"], "ACTIVE")

    def test_v2_agents_get_unknown_returns_404(self):
        res = self.client.get("/api/v2/agents/does-not-exist")
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

        # PUT ikut menulis audit log (Phase 29) - arahkan ke berkas sementara
        # supaya data/MCSA/audit/ yang asli tidak ikut terisi oleh test.
        self._audit_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._audit_dir, True)
        audit_patcher = patch.object(
            audit, "default_log_path", lambda: os.path.join(self._audit_dir, "audit.jsonl")
        )
        audit_patcher.start()
        self.addCleanup(audit_patcher.stop)

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


class TestV2Audit(unittest.TestCase):
    """docs/final.md Phase 29 - /api/v2/audit plus the trail that PUT
    /api/v2/equipment/{id}/modules/{module} leaves behind. Both the override
    store and the audit log point at temp files, so no real config is touched."""

    def setUp(self):
        self.client = TestClient(app)
        self._tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._tmpdir, True)
        self.audit_path = os.path.join(self._tmpdir, "audit.jsonl")

        store_patcher = patch.object(
            pple_api_router,
            "_equipment_module_store",
            EquipmentModuleStore(os.path.join(self._tmpdir, "overrides.json")),
        )
        store_patcher.start()
        self.addCleanup(store_patcher.stop)

        audit_patcher = patch.object(audit, "default_log_path", lambda: self.audit_path)
        audit_patcher.start()
        self.addCleanup(audit_patcher.stop)

    def test_empty_audit_endpoint(self):
        res = self.client.get("/api/v2/audit")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"count": 0, "events": []})

    def test_disabling_a_module_is_audited_with_api_source(self):
        put = self.client.put("/api/v2/equipment/CWP-1A/modules/dga", json={"enabled": False})
        self.assertEqual(put.status_code, 200)

        res = self.client.get("/api/v2/audit")
        data = res.json()
        self.assertEqual(data["count"], 1)
        event = data["events"][0]
        self.assertEqual(event["entity"], "CWP-1A")
        self.assertEqual(event["field"], "module:dga")
        self.assertEqual(event["old_value"], "enabled")
        self.assertEqual(event["new_value"], "disabled")
        self.assertEqual(event["source"], "API")
        self.assertIn("CWP-1A", event["summary"])

    def test_x_actor_header_names_the_person(self):
        self.client.put(
            "/api/v2/equipment/CWP-1A/modules/dga",
            json={"enabled": False},
            headers={"X-Actor": "Engineer Rizki"},
        )
        event = self.client.get("/api/v2/audit").json()["events"][0]
        self.assertEqual(event["who"], "Engineer Rizki")

    def test_audit_filters(self):
        self.client.put("/api/v2/equipment/CWP-1A/modules/dga", json={"enabled": False})
        self.client.put("/api/v2/equipment/CWP-2B/modules/dga", json={"enabled": False})

        self.assertEqual(self.client.get("/api/v2/audit?entity=CWP-2B").json()["count"], 1)
        self.assertEqual(self.client.get("/api/v2/audit?source=API").json()["count"], 2)
        self.assertEqual(self.client.get("/api/v2/audit?limit=1").json()["count"], 1)

    def test_failed_put_leaves_no_audit_trail(self):
        res = self.client.put(
            "/api/v2/equipment/CWP-1A/modules/does-not-exist", json={"enabled": False}
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(self.client.get("/api/v2/audit").json()["count"], 0)

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


class TestSpecialistDomainRouterArchitecture(unittest.TestCase):
    """Characterization boundary for the first api_server.py extraction.

    The public paths remain legacy-compatible, while their ownership moves to
    a dedicated router so new specialist endpoints do not grow api_server.py.
    """

    EXPECTED_PATHS = {
        "/api/dga/summary",
        "/api/dga/transformers",
        "/api/dga/transformers/{transformer_id}",
        "/api/tribology/summary",
        "/api/tribology/samples",
        "/api/tribology/samples/{sample_id}",
        "/api/thermal/summary",
        "/api/thermal/inspections",
        "/api/pd/summary",
        "/api/pd/samples",
        "/api/pd/samples/{sample_id}",
        "/api/pd/samples/{sample_id}/assessment",
    }

    def setUp(self):
        self.client = TestClient(app)

    def test_routes_are_owned_by_dedicated_router(self):
        module = importlib.import_module("pple.api.specialist_router")
        paths = {route.path for route in module.router.routes}
        self.assertEqual(paths, self.EXPECTED_PATHS)

    def test_list_envelopes_remain_compatible(self):
        for path, collection_key in (
            ("/api/dga/transformers", "transformers"),
            ("/api/tribology/samples", "samples"),
            ("/api/thermal/inspections", "inspections"),
            ("/api/pd/samples", "samples"),
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertIn(collection_key, payload)
                self.assertEqual(payload["count"], len(payload[collection_key]))

    def test_routes_enforce_response_models(self):
        module = importlib.import_module("pple.api.specialist_router")
        for route in module.router.routes:
            with self.subTest(path=route.path):
                self.assertIsNotNone(
                    getattr(route, "response_model", None),
                    f"Route {route.path} must have a typed response_model",
                )

    def test_modular_routers_ownership(self):
        wo_mod = importlib.import_module("pple.api.routers.work_orders")
        wo_paths = {r.path for r in wo_mod.router.routes}
        self.assertEqual(wo_paths, {"/api/workorders", "/api/workorders/approve"})

        kn_mod = importlib.import_module("pple.api.routers.knowledge")
        kn_paths = {r.path for r in kn_mod.router.routes}
        self.assertEqual(kn_paths, {"/api/materi", "/api/materi/search"})

        vib_mod = importlib.import_module("pple.api.routers.vibration")
        vib_paths = {r.path for r in vib_mod.router.routes}
        self.assertEqual(
            vib_paths,
            {
                "/api/vibration/summary",
                "/api/vibration/equipment",
                "/api/vibration/equipment/{asset_id}",
                "/api/vibration/classes",
                "/api/vibration/tests",
            },
        )


class TestAPISecurity(unittest.TestCase):
    """CORS + API key opsional (pple/api/security.py).

    Middleware membaca PPLE_API_KEY per-request, jadi app yang sama bisa
    diuji dalam mode terbuka maupun terkunci tanpa membangun ulang app.
    """

    PROTECTED_PATH = "/api/summary"

    def setUp(self):
        self.client = TestClient(app)

    def _with_key(self, key):
        return patch.dict(os.environ, {security.API_KEY_ENV: key})

    def test_auth_disabled_by_default_keeps_api_open(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(security.API_KEY_ENV, None)
            self.assertFalse(security.auth_enabled())
            self.assertEqual(self.client.get(self.PROTECTED_PATH).status_code, 200)

    def test_request_without_key_is_rejected_when_enabled(self):
        with self._with_key("rahasia-123"):
            res = self.client.get(self.PROTECTED_PATH)
            self.assertEqual(res.status_code, 401)
            self.assertIn("X-API-Key", res.json()["detail"])

    def test_request_with_wrong_key_is_rejected(self):
        with self._with_key("rahasia-123"):
            res = self.client.get(self.PROTECTED_PATH, headers={"X-API-Key": "salah"})
            self.assertEqual(res.status_code, 401)

    def test_request_with_api_key_header_passes(self):
        with self._with_key("rahasia-123"):
            res = self.client.get(self.PROTECTED_PATH, headers={"X-API-Key": "rahasia-123"})
            self.assertEqual(res.status_code, 200)

    def test_request_with_bearer_token_passes(self):
        with self._with_key("rahasia-123"):
            res = self.client.get(
                self.PROTECTED_PATH, headers={"Authorization": "Bearer rahasia-123"}
            )
            self.assertEqual(res.status_code, 200)

    def test_health_stays_public_for_monitoring(self):
        with self._with_key("rahasia-123"):
            self.assertEqual(self.client.get("/api/health").status_code, 200)

    def test_v2_routes_are_protected_too(self):
        # Middleware, bukan Depends per-route: router v2 ikut terlindungi.
        with self._with_key("rahasia-123"):
            self.assertEqual(self.client.get("/api/v2/modules").status_code, 401)
            res = self.client.get("/api/v2/modules", headers={"X-API-Key": "rahasia-123"})
            self.assertEqual(res.status_code, 200)

    def test_default_cors_origins_are_localhost_only(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(security.CORS_ORIGINS_ENV, None)
            origins = security.resolve_cors_origins()
            self.assertNotIn("*", origins)
            self.assertIn("http://localhost:5173", origins)
            self.assertTrue(security.cors_allow_credentials(origins))

    def test_cors_origins_read_from_env(self):
        with patch.dict(
            os.environ,
            {security.CORS_ORIGINS_ENV: "https://pdm.pln.co.id/, https://ops.pln.co.id"},
        ):
            self.assertEqual(
                security.resolve_cors_origins(),
                ["https://pdm.pln.co.id", "https://ops.pln.co.id"],
            )

    def test_wildcard_origin_disables_credentials(self):
        # allow_origins=["*"] + allow_credentials=True ditolak browser.
        with patch.dict(os.environ, {security.CORS_ORIGINS_ENV: "*"}):
            origins = security.resolve_cors_origins()
            self.assertEqual(origins, ["*"])
            self.assertFalse(security.cors_allow_credentials(origins))


if __name__ == "__main__":
    unittest.main()
