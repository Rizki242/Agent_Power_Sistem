"""Unit tests for Technology Examination (TE) report generation and workflows."""

from __future__ import annotations

import io
import unittest

from src.te_generator import build_te_report_data, export_te_docx


class TestTechnologyExamination(unittest.TestCase):
    def test_build_te_transformer(self):
        data = build_te_report_data(
            equipment="TRANSFORMATOR UAT UNIT 3",
            technology="DGA",
            finding="Kenaikan gas indikasi thermal fault",
            status="Kuning",
        )
        self.assertIn("TE/CBM/UJPJRJ", data["doc_number"])
        self.assertEqual(data["status"], "Kuning")
        self.assertIn("specifications", data)
        self.assertEqual(data["specifications"]["component_2"], "TRANSFORMATOR")
        self.assertIn("dga_data", data)
        self.assertIn("sign_off", data)
        self.assertEqual(data["sign_off"]["location"], "JERANJANG")

    def test_build_te_rotating_machine(self):
        data = build_te_report_data(
            equipment="CWP 1 UNIT 1",
            technology="Vibrasi dan Tribology",
            finding="Vibrasi tinggi 1X radial",
            status="Merah",
        )
        self.assertEqual(data["status"], "Merah")
        self.assertIn("specifications", data)
        self.assertIn("motor", data["specifications"])
        self.assertIn("driven", data["specifications"])
        self.assertIn("vibration_data", data)
        self.assertIn("points", data["vibration_data"])
        self.assertIn("1V", data["vibration_data"]["points"])
        self.assertIn("recommendations", data)
        self.assertTrue(len(data["recommendations"]) > 0)

    def test_export_te_docx(self):
        data = build_te_report_data(
            equipment="BOILER FEEDWATER PUMP 2 UNIT 3",
            technology="Vibrasi dan Tribology",
            finding="Vibrasi tinggi bearing 3 & 4",
            status="Kuning",
        )
        buffer = export_te_docx(data)
        self.assertIsInstance(buffer, io.BytesIO)
        byte_data = buffer.getvalue()
        # Ensure it is a valid zip/docx archive (starts with PK header)
        self.assertTrue(byte_data.startswith(b"PK\x03\x04"))
        self.assertGreater(len(byte_data), 10000)

    def test_work_orders_page_import(self):
        import src.pages.work_orders_page as wop
        self.assertTrue(hasattr(wop, "render_work_orders_page"))


if __name__ == "__main__":
    unittest.main()

