"""Unit tests for Predictive Maintenance Scheduling & Outage Planning Engine."""

import unittest
from datetime import datetime
import pandas as pd

from src.outage_planner import (
    DEFAULT_OUTAGE_SCHEDULE,
    generate_outage_turnaround_package,
    parse_rul_lower_bound,
    plan_outage_maintenance,
)


class TestOutagePlanner(unittest.TestCase):
    def test_parse_rul_lower_bound(self):
        self.assertEqual(parse_rul_lower_bound("14–45 hari"), 14)
        self.assertEqual(parse_rul_lower_bound("45-90 days"), 45)
        self.assertEqual(parse_rul_lower_bound(30), 30)
        self.assertEqual(parse_rul_lower_bound(60.5), 60)
        self.assertEqual(parse_rul_lower_bound(None), 180)
        self.assertEqual(parse_rul_lower_bound("invalid"), 180)

    def test_empty_fleet_matrix_returns_valid_structure(self):
        plan = plan_outage_maintenance([])
        self.assertEqual(plan["total_bundled_count"], 0)
        self.assertEqual(plan["saved_downtime_hours"], 0)
        self.assertEqual(plan["categorized_assets"], [])
        self.assertEqual(plan["pre_outage_critical"], [])
        self.assertIn("UNIT 1", plan["bundled_by_unit"])
        self.assertIn("outage_schedules", plan)

    def test_outage_urgency_classification(self):
        fixed_now = datetime(2026, 6, 1, 10, 0, 0)
        # Unit 1 outage is in 45 days
        fleet = [
            # 1. RUL 14 days < 45 days -> Pre-Outage Critical Trip Risk
            {
                "equipment": "CWP 1A",
                "unit": "UNIT 1",
                "health_index": 35.0,
                "health_status": "CRITICAL",
                "criticality": "A",
                "rul_days": "14–30 hari",
                "primary_failure_mode": "Severe Bearing Wear",
            },
            # 2. RUL 50 days (near 45 days) -> Optimal Outage Scope
            {
                "equipment": "PA FAN 1A",
                "unit": "UNIT 1",
                "health_index": 65.0,
                "health_status": "WARNING",
                "criticality": "B",
                "rul_days": "45–90 hari",
                "primary_failure_mode": "Motor Dynamic Eccentricity",
            },
            # 3. RUL 300 days -> Post-Outage Safe
            {
                "equipment": "ID FAN 1A",
                "unit": "UNIT 1",
                "health_index": 92.0,
                "health_status": "HEALTHY",
                "criticality": "A",
                "rul_days": "180–365 hari",
                "primary_failure_mode": "Normal",
            },
        ]

        plan = plan_outage_maintenance(fleet, base_date=fixed_now)

        self.assertEqual(len(plan["categorized_assets"]), 3)

        # Asset 1 (CWP 1A)
        cwp = next(a for a in plan["categorized_assets"] if a["equipment"] == "CWP 1A")
        self.assertEqual(cwp["urgency"], "PRE_OUTAGE_CRITICAL")
        self.assertIn("Risiko Trip", cwp["urgency_label"])

        # Asset 2 (PA FAN 1A)
        paf = next(a for a in plan["categorized_assets"] if a["equipment"] == "PA FAN 1A")
        self.assertEqual(paf["urgency"], "OPTIMAL_OUTAGE_SCOPE")
        self.assertIn("Paket Ideal", paf["urgency_label"])

        # Asset 3 (ID FAN 1A)
        idf = next(a for a in plan["categorized_assets"] if a["equipment"] == "ID FAN 1A")
        self.assertEqual(idf["urgency"], "POST_OUTAGE_SAFE")

        # Bundled count in UNIT 1 should be 2 (CWP 1A and PA FAN 1A)
        self.assertEqual(len(plan["bundled_by_unit"]["UNIT 1"]), 2)
        # Saved downtime hours = (2 - 1) * 16 = 16 hours
        self.assertEqual(plan["saved_downtime_hours"], 16)

        # Pre-outage critical list
        self.assertEqual(len(plan["pre_outage_critical"]), 1)
        self.assertEqual(plan["pre_outage_critical"][0]["equipment"], "CWP 1A")

        # Gantt data
        self.assertFalse(plan["gantt_data"].empty)
        self.assertIn("Task", plan["gantt_data"].columns)

    def test_generate_outage_turnaround_package(self):
        bundled = [
            {
                "equipment": "CWP 1A",
                "criticality": "A",
                "rul_lower_bound_days": 14,
                "primary_failure_mode": "Bearing Outer Race Fault",
                "health_status": "CRITICAL",
            },
            {
                "equipment": "PA FAN 1A",
                "criticality": "B",
                "rul_lower_bound_days": 45,
                "primary_failure_mode": "Rotor Bar Broken Bar",
                "health_status": "WARNING",
            },
        ]
        pkg = generate_outage_turnaround_package("UNIT 1", bundled)

        self.assertIn("TOP-UNIT1", pkg["package_id"])
        self.assertEqual(pkg["total_equipment"], 2)
        self.assertEqual(len(pkg["scope_items"]), 2)
        self.assertTrue(pkg["loto_required"])
        # Check required parts inferred from failure modes
        parts_text = " ".join(pkg["required_parts"])
        self.assertIn("Bearing", parts_text)
        self.assertIn("Winding", parts_text)


if __name__ == "__main__":
    unittest.main()

