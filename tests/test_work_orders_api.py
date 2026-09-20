"""Unit tests for Work Orders API endpoints and lifecycle."""

import os
import unittest
from fastapi.testclient import TestClient

from api_server import app


class WorkOrdersApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_get_work_orders(self):
        resp = self.client.get("/api/workorders")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("work_orders", data)
        self.assertIn("count", data)
        self.assertGreaterEqual(data["count"], 1)

    def test_create_and_approve_work_order(self):
        # 1. Create WO
        create_payload = {
            "equipment": "TEST-PUMP-99",
            "title": "Uji Coba Laser Alignment & Bearing Inspection",
            "priority": "P2 - High",
            "domain": "Vibrasi",
            "reason": "Uji coba otomatisasi work order",
            "required_tools": ["Laser Alignment Kit", "Dial Indicator"],
            "required_parts": ["Shim 0.1mm"],
            "required_manpower": "2 Teknisi",
            "target_completion_date": "2026-10-01",
            "created_by": "Test Runner",
        }
        create_resp = self.client.post("/api/workorders", json=create_payload)
        self.assertEqual(create_resp.status_code, 200)
        created_wo = create_resp.json().get("work_order", {})
        wo_number = created_wo.get("wo_number")
        self.assertTrue(wo_number)
        self.assertEqual(created_wo.get("equipment"), "TEST-PUMP-99")

        # 2. Approve WO
        approve_payload = {
            "wo_number": wo_number,
            "approved_by": "Supervisor Uji Coba",
            "action": "Approve",
        }
        approve_resp = self.client.post("/api/workorders/approve", json=approve_payload)
        self.assertEqual(approve_resp.status_code, 200)
        approved_wo = approve_resp.json().get("work_order", {})
        self.assertIn("Approved by Supervisor Uji Coba", approved_wo.get("status", ""))

        # 3. Complete WO
        complete_payload = {
            "wo_number": wo_number,
            "approved_by": "Supervisor Uji Coba",
            "action": "Complete",
        }
        complete_resp = self.client.post("/api/workorders/approve", json=complete_payload)
        self.assertEqual(complete_resp.status_code, 200)
        completed_wo = complete_resp.json().get("work_order", {})
        self.assertIn("Completed", completed_wo.get("status", ""))

    def test_generate_cbm_work_order(self):
        cbm_payload = {
            "equipment": "CWP 1A",
            "domain": "Multi-Domain CBM",
            "severity": "WARNING",
            "anomaly_desc": "Indikasi deviasi getaran 2X dan unbalance",
            "recommendations": ["Inspeksi coupling", "Re-balancing rotor"],
            "created_by": "CBM Diagnostics Engine",
        }
        resp = self.client.post("/api/workorders/generate-cbm", json=cbm_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "success")
        wo = data.get("work_order", {})
        self.assertEqual(wo.get("equipment"), "CWP 1A")
        self.assertTrue(wo.get("wo_number", "").startswith("WO-"))
        self.assertIn("CBM", wo.get("domain", ""))


if __name__ == "__main__":
    unittest.main()

