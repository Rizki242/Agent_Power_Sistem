import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from src.data_loader import _configured_backup_limit, filter_mcsa_data
from src.analytics import build_word_qc_export
from src.report_batches import commit_batch, create_batch, preview_batch
from src.rotorbar import evaluate_rotorbar


class UploadedFile(io.BytesIO):
    def __init__(self, name, payload=b"word-data"):
        super().__init__(payload)
        self.name = name

    def getbuffer(self):
        return memoryview(self.getvalue())


def report_row(parameter, value, report_date="2026-08-01"):
    return {
        "Equipment": "PUMP1", "Parameter": parameter, "Date": report_date,
        "Raw_Value": str(value), "Value": float(value), "Unit": "", "Limit": "",
        "Status": "Normal", "Unit_Name": "Unknown", "Voltage_Level": "Unknown",
        "Full_Name": "PUMP1",
    }


class RotorbarRegressionTests(unittest.TestCase):
    def test_rotorbar_sideband_thresholds_produce_expected_level_and_status(self):
        cases = [
            (-60.01, 1, "Normal"),
            (-60.00, 2, "Normal"),
            (-54.00, 3, "Alarm"),
            (-45.00, 4, "High"),
        ]
        for sideband, expected_level, expected_status in cases:
            with self.subTest(sideband=sideband):
                result = evaluate_rotorbar({"Upper Sideband": sideband, "Lower Sideband": sideband})
                self.assertEqual(result["Level"], expected_level)
                self.assertEqual(result["Status"], expected_status)

    def test_rotorbar_health_escalates_a_safe_sideband_result(self):
        result = evaluate_rotorbar({
            "Upper Sideband": -65.0,
            "Lower Sideband": -66.0,
            "Rotorbar Health": 3.0,
        })
        self.assertEqual(result["Level"], 4)
        self.assertEqual(result["Status"], "High")


class DataFilterRegressionTests(unittest.TestCase):
    def test_date_and_equipment_filters_are_inclusive_and_composable(self):
        df = pd.DataFrame([
            report_row("Current 1", 10, "2026-07-31"),
            report_row("Current 1", 11, "2026-08-01"),
            {**report_row("Current 1", 12, "2026-08-15"), "Equipment": "PUMP2"},
            report_row("Current 1", 13, "2026-08-31"),
            report_row("Current 1", 14, "2026-09-01"),
        ])

        actual = filter_mcsa_data(
            df,
            date_start=date(2026, 8, 1),
            date_end=date(2026, 8, 31),
            equipment=["PUMP1"],
        )

        self.assertEqual(actual["Raw_Value"].tolist(), ["11", "13"])
        self.assertTrue((actual["Equipment"] == "PUMP1").all())


class ReportRevisionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "Laporan"
        self.master = pd.DataFrame([{
            "Equipment": "PUMP1", "Unit_Name": "UNIT 1",
            "Voltage_Level": "380/400 V", "Full_Name": "Pump 1",
        }])

    def tearDown(self):
        self.temp.cleanup()

    @patch("src.report_batches.parse_docx_report")
    def test_same_date_revision_replaces_only_matching_parameter(self, parse_report):
        parse_report.return_value = [report_row("Current 1", 25)]
        batch, _ = create_batch(self.root, [UploadedFile("PUMP1_000.docx")])
        preview, _ = preview_batch(batch, self.master)
        current = pd.DataFrame([
            report_row("Current 1", 10),
            report_row("Voltage 1", 400),
        ])
        saved = {}

        def save(frame, _path):
            saved["frame"] = frame.copy()

        merged, manifest = commit_batch(batch, preview, current, save, "Report MCSA.xls")

        self.assertEqual(manifest["status"], "committed")
        self.assertEqual(len(merged), 2)
        values = merged.set_index("Parameter")["Value"].to_dict()
        self.assertEqual(values, {"Current 1": 25.0, "Voltage 1": 400.0})
        self.assertEqual(len(saved["frame"]), 2)


class QualityCheckExportTests(unittest.TestCase):
    def test_qc_export_includes_failure_reason_and_summary_counts(self):
        summary = {
            "failed_files_count": 1,
            "failed_files": [{"file": "PUMP1_000.docx", "error": "Equipment PUMP1 tidak ditemukan"}],
            "missing_parameter_rows": [], "numeric_flag_rows": [], "duplicate_rows": [],
            "weird_date_rows": [], "missing_metadata_rows": [],
        }
        export = build_word_qc_export(summary, {"total_files": 2, "parsed_files": 1})

        failure = export[export["Kategori"] == "Gagal diproses"].iloc[0]
        self.assertEqual(failure["Item"], "PUMP1_000.docx")
        self.assertEqual(failure["Alasan"], "Equipment PUMP1 tidak ditemukan")
        self.assertEqual(export.iloc[0]["Jumlah"], 2)


class OperationalConfigurationTests(unittest.TestCase):
    def test_backup_retention_uses_environment_and_enforces_minimum(self):
        with patch.dict("os.environ", {"MCSA_MAX_BACKUPS": "10"}, clear=False):
            self.assertEqual(_configured_backup_limit(), 10)
        with patch.dict("os.environ", {"MCSA_MAX_BACKUPS": "0"}, clear=False):
            self.assertEqual(_configured_backup_limit(), 1)


if __name__ == "__main__":
    unittest.main()
