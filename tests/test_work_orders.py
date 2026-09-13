import unittest
import os
import tempfile
import json

from src.work_orders import (
    load_work_orders,
    save_work_orders,
    create_work_order,
    generate_cbm_work_order,
    update_work_order_status,
    get_work_order_by_number,
    delete_work_order,
)


class WorkOrdersTests(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for isolated test persistence
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        os.environ["WORK_ORDERS_FILE"] = self.temp_file.name

    def tearDown(self):
        os.environ.pop("WORK_ORDERS_FILE", None)
        if os.path.exists(self.temp_file.name):
            try:
                os.remove(self.temp_file.name)
            except OSError:
                pass

    def test_load_and_seed(self):
        orders = load_work_orders()
        self.assertIsInstance(orders, list)
        self.assertGreaterEqual(len(orders), 1)
        self.assertTrue(any("BC 10.1" in w.get("equipment", "") for w in orders))

    def test_create_manual_work_order(self):
        new_wo = create_work_order(
            equipment="BC 10.1",
            title="Greasing Bearing DE",
            priority="P3 - Medium",
            domain="Vibrasi",
            reason="Pemeriksaan pelumasan rutin",
            required_tools=["Grease Gun"],
            required_parts=["Shell Gadus S2"],
            required_manpower="1 Mekanik",
        )
        self.assertTrue(new_wo["wo_number"].startswith("WO-"))
        self.assertEqual(new_wo["equipment"], "BC 10.1")
        self.assertEqual(new_wo["domain"], "Vibrasi")
        self.assertIn("Shell Gadus S2", new_wo["required_parts"])

        # Check persistence
        fetched = get_work_order_by_number(new_wo["wo_number"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Greasing Bearing DE")

    def test_generate_cbm_work_order_critical(self):
        wo = generate_cbm_work_order(
            equipment="C3WP 1A",
            domain="Vibrasi",
            severity="CRITICAL",
            anomaly_desc="Vmax 7.8 mm/s di atas batas Zone D ISO 10816",
            recommendations=["Inspeksi unbalance impeller", "Cek alignment kopling"],
        )
        self.assertEqual(wo["priority"], "P1 - Critical")
        self.assertIn("C3WP 1A", wo["title"])
        self.assertIn("Laser Alignment Kit", wo["required_tools"])
        self.assertIn("PTW", str(wo["safety_checklist"]))

    def test_generate_cbm_work_order_warning(self):
        wo = generate_cbm_work_order(
            equipment="PA FAN 2A",
            domain="Thermal",
            severity="WARNING",
            anomaly_desc="Delta-T 18°C pada terminal R-S",
            recommendations=["Retorque sambungan baut"],
        )
        self.assertEqual(wo["priority"], "P2 - High")
        self.assertEqual(wo["domain"], "Thermal")

    def test_generate_cbm_duplicate_prevention(self):
        wo1 = generate_cbm_work_order(
            equipment="BFP 1A",
            domain="Tribology",
            severity="WARNING",
            anomaly_desc="Air 280 ppm",
        )
        wo2 = generate_cbm_work_order(
            equipment="BFP 1A",
            domain="Tribology",
            severity="WARNING",
            anomaly_desc="Air 280 ppm",
        )
        # Should return the same work order instead of creating a duplicate
        self.assertEqual(wo1["wo_number"], wo2["wo_number"])

    def test_status_transitions(self):
        wo = create_work_order(
            equipment="TEST-EQ",
            title="Test Task",
            priority="P2 - High",
        )
        num = wo["wo_number"]

        # Approve
        res_app = update_work_order_status(num, "Approve", actor="Supervisor Budi")
        self.assertIn("Approved", res_app["status"])

        # Progress
        res_prog = update_work_order_status(num, "Progress", actor="Teknisi Joko")
        self.assertIn("In Progress", res_prog["status"])

        # Complete
        res_comp = update_work_order_status(num, "Complete", actor="Supervisor Budi")
        self.assertIn("Completed", res_comp["status"])

    def test_delete_work_order(self):
        wo = create_work_order(
            equipment="TO-DELETE",
            title="Delete me",
        )
        num = wo["wo_number"]
        self.assertIsNotNone(get_work_order_by_number(num))

        deleted = delete_work_order(num)
        self.assertTrue(deleted)
        self.assertIsNone(get_work_order_by_number(num))


if __name__ == "__main__":
    unittest.main()

