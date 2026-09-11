import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app


class AutomationAPITests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.env = patch.dict(os.environ, {"PPLE_AUTOMATION_DIR": self.tempdir.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.client = TestClient(app)

    def test_create_list_and_queue_approval(self):
        payload = {
            "name": "Belajar kondisi aset",
            "action": "learning_cycle",
            "interval_minutes": 60,
            "approval_required": True,
        }
        created = self.client.post("/api/automations/workflows", json=payload)
        self.assertEqual(created.status_code, 201)
        workflow_id = created.json()["workflow"]["id"]

        listed = self.client.get("/api/automations/workflows")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["count"], 1)

        run = self.client.post(f"/api/automations/workflows/{workflow_id}/run")
        self.assertEqual(run.status_code, 202)
        self.assertEqual(run.json()["run"]["status"], "WAITING_APPROVAL")

    @patch("src.automations.dispatch_action", return_value={"status": "success"})
    def test_approve_executes_allowed_action(self, dispatch):
        created = self.client.post("/api/automations/workflows", json={
            "name": "Learning cycle", "action": "learning_cycle",
            "interval_minutes": 30, "approval_required": True,
        }).json()["workflow"]
        run = self.client.post(f"/api/automations/workflows/{created['id']}/run").json()["run"]

        approved = self.client.post(
            f"/api/automations/runs/{run['id']}/approve", json={"approved_by": "Engineer"},
        )
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["run"]["status"], "SUCCESS")
        dispatch.assert_called_once_with("learning_cycle")

    def test_due_workflow_executes_once_until_next_interval(self):
        from src.automations import create_workflow, run_due_workflows

        workflow = create_workflow("Health terjadwal", "knowledge_health_check", 60, False)
        with patch("src.automations.dispatch_action", return_value={"status": "success"}) as dispatch:
            first = run_due_workflows(datetime.now(timezone.utc))
            second = run_due_workflows(datetime.now(timezone.utc))

        self.assertEqual(first[0]["workflow_id"], workflow["id"])
        self.assertEqual(first[0]["status"], "SUCCESS")
        self.assertEqual(second, [])
        dispatch.assert_called_once_with("knowledge_health_check")

    def test_due_approval_workflow_does_not_duplicate_pending_run(self):
        from src.automations import create_workflow, run_due_workflows

        create_workflow("Belajar dengan approval", "learning_cycle", 15, True)
        first = run_due_workflows(datetime.now(timezone.utc))
        second = run_due_workflows(datetime.now(timezone.utc))

        self.assertEqual(first[0]["status"], "WAITING_APPROVAL")
        self.assertEqual(second, [])


if __name__ == "__main__":
    unittest.main()
