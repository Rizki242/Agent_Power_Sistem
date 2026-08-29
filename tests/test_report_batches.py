import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.report_batches import commit_batch, create_batch, load_batch_manifest, preview_batch


class UploadedFile(io.BytesIO):
    def __init__(self, name, payload=b"word-data"):
        super().__init__(payload)
        self.name = name

    def getbuffer(self):
        return memoryview(self.getvalue())


def parsed_rows(equipment="PUMP1", value="10"):
    return [{
        "Equipment": equipment, "Parameter": "Current 1", "Date": "2026-08-01",
        "Raw_Value": value, "Value": float(value), "Unit": "A", "Limit": "",
        "Status": "Normal", "Unit_Name": "Unknown", "Voltage_Level": "Unknown",
        "Full_Name": equipment,
    }]


class ReportBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "Laporan"
        self.master = pd.DataFrame([{
            "Equipment": "PUMP1", "Unit_Name": "UNIT 1",
            "Voltage_Level": "380/400 V", "Full_Name": "Pump 1",
        }])

    def tearDown(self):
        self.temp.cleanup()

    def test_create_batch_keeps_duplicate_names_and_writes_checksums(self):
        path, manifest = create_batch(
            self.root,
            [UploadedFile("PUMP1_000.docx", b"a"), UploadedFile("PUMP1_000.docx", b"b")],
            now=datetime(2026, 8, 14, 9, 30, 0),
        )
        self.assertEqual(path.relative_to(self.root).parts[:4], ("uploads", "2026", "08", "14"))
        self.assertEqual([item["stored_name"] for item in manifest["files"]], ["PUMP1_000.docx", "PUMP1_000-2.docx"])
        self.assertNotEqual(manifest["files"][0]["sha256"], manifest["files"][1]["sha256"])
        self.assertEqual(load_batch_manifest(path)["status"], "pending")
        self.assertEqual(manifest["audit_events"][0]["action"], "created")

    @patch("src.report_batches.parse_docx_report", return_value=parsed_rows())
    def test_preview_uses_master_metadata(self, _parse):
        path, _ = create_batch(self.root, [UploadedFile("PUMP1_000.docx")])
        frame, manifest = preview_batch(path, self.master)
        self.assertEqual(manifest["files"][0]["parse_status"], "valid")
        self.assertEqual(frame.iloc[0]["Unit_Name"], "UNIT 1")
        self.assertEqual(frame.iloc[0]["Voltage_Level"], "380/400 V")
        self.assertEqual(manifest["audit_events"][-1]["action"], "previewed")

    @patch("src.report_batches.parse_docx_report", return_value=parsed_rows("UNKNOWN1"))
    def test_preview_quarantines_unknown_equipment(self, _parse):
        path, _ = create_batch(self.root, [UploadedFile("UNKNOWN1_000.docx")])
        frame, manifest = preview_batch(path, self.master)
        self.assertTrue(frame.empty)
        self.assertEqual(manifest["files"][0]["parse_status"], "quarantined")

    @patch("src.report_batches.parse_docx_report", return_value=parsed_rows(value="25"))
    def test_commit_replaces_same_equipment_parameter_and_date(self, _parse):
        path, _ = create_batch(self.root, [UploadedFile("PUMP1_000.docx")])
        preview, _ = preview_batch(path, self.master)
        current = pd.DataFrame(parsed_rows(value="10"))
        saved = {}

        def fake_save(frame, _path):
            saved["frame"] = frame.copy()

        merged, manifest = commit_batch(path, preview, current, fake_save, "Report MCSA.xls")
        self.assertEqual(len(merged), 1)
        self.assertEqual(float(saved["frame"].iloc[0]["Value"]), 25.0)
        self.assertEqual(manifest["status"], "committed")
        self.assertEqual(manifest["audit_events"][-1]["action"], "committed")
        self.assertEqual(manifest["audit_events"][-1]["replaced_or_duplicate_rows"], 1)


if __name__ == "__main__":
    unittest.main()
