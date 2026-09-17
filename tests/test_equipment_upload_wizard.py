"""Unit tests for the bulk asset registration helpers in equipment_upload_wizard.

Covers: header-alias mapping for CSV/XLSX bulk uploads, monitoring_modules
token parsing, and row-to-upsert_asset-payload conversion. These are the
pure functions behind the "Registrasi Massal" (bulk CSV/Excel) section of
the equipment upload wizard, kept free of Streamlit so they can be tested
directly.
"""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.components.equipment_upload_wizard import (
    _bulk_sample_csv,
    _bulk_template_csv,
    _parse_monitoring_modules,
    _row_to_asset_payload,
    parse_bulk_asset_file,
)


class TestParseBulkAssetFile(unittest.TestCase):
    def test_recognises_aliased_headers_and_ignores_unknown_columns(self):
        content = (
            b"Asset ID,Equipment Name,Category,Manufacturer,Model,"
            b"Rated Power (kW),Voltage,RPM,Unit,Location,Install Date,"
            b"Monitoring Modules,KKS,Notes,Unrelated Column\n"
            b",ID Fan Motor 2A,Motor,ABB,M3BP 315 SMB,750,6600,1485,"
            b'UNIT 2,Unit 2 - ID Fan Area,2026-09-17,"VIBRASI,MCSA,THERMAL",-,test,ignored\n'
        )
        df = parse_bulk_asset_file("assets.csv", content)
        self.assertEqual(len(df), 1)
        row = df.iloc[0]
        self.assertEqual(row["name"], "ID Fan Motor 2A")
        self.assertEqual(row["equipment_type"], "Motor")
        self.assertEqual(row["monitoring_modules"], "VIBRASI,MCSA,THERMAL")
        self.assertNotIn("unrelated_column", df.columns)

    def test_missing_optional_column_comes_back_empty_not_missing(self):
        content = b"name,unit\nMotor A,UNIT 1\n"
        df = parse_bulk_asset_file("assets.csv", content)
        self.assertIn("kks", df.columns)
        self.assertEqual(df.iloc[0]["kks"], "")

    def test_invalid_file_raises_value_error(self):
        with self.assertRaises(ValueError):
            parse_bulk_asset_file("assets.txt", b"not a real spreadsheet")


class TestParseMonitoringModules(unittest.TestCase):
    def test_comma_and_semicolon_separators(self):
        self.assertEqual(_parse_monitoring_modules("VIBRASI,MCSA;THERMAL"), ["VIBRASI", "MCSA", "THERMAL"])

    def test_aliases_normalise_to_canonical_tokens(self):
        self.assertEqual(_parse_monitoring_modules("Vibration, pd online"), ["VIBRASI", "PD"])

    def test_unknown_token_is_dropped(self):
        self.assertEqual(_parse_monitoring_modules("VIBRASI,NOT_A_MODULE"), ["VIBRASI"])

    def test_blank_or_nan_returns_empty_list(self):
        self.assertEqual(_parse_monitoring_modules(""), [])
        self.assertEqual(_parse_monitoring_modules(float("nan")), [])
        self.assertEqual(_parse_monitoring_modules(None), [])


class TestRowToAssetPayload(unittest.TestCase):
    def test_full_row_maps_onto_upsert_asset_fields(self):
        row = {
            "asset_id": "AST-001", "name": "Transformer TR1", "equipment_type": "Transformer",
            "manufacturer": "Siemens", "model": "TR-500", "rated_power_kw": "500",
            "rpm": "", "voltage_level": "20000", "unit": "UNIT 1",
            "location": "Switchyard", "install_date": "2020-01-01",
            "monitoring_modules": "DGA;PD", "kks": "KKS1", "notes": "note",
        }
        payload = _row_to_asset_payload(row)
        self.assertEqual(payload["asset_id"], "AST-001")
        self.assertEqual(payload["name"], "Transformer TR1")
        self.assertEqual(payload["monitoring_modules"], ["DGA", "PD"])
        self.assertEqual(payload["specs"]["c1_type_mfg"], "Siemens / TR-500")
        self.assertNotIn("c1_speed", payload["specs"])  # blank rpm omitted

    def test_blank_asset_id_becomes_none_so_upsert_asset_generates_one(self):
        payload = _row_to_asset_payload({"name": "Motor X"})
        self.assertIsNone(payload["asset_id"])

    def test_blank_name_row_is_left_for_caller_to_skip(self):
        payload = _row_to_asset_payload({"asset_id": "AST-002"})
        self.assertEqual(payload["name"], "")


class TestBulkTemplateCsv(unittest.TestCase):
    def test_template_round_trips_through_the_parser(self):
        template = _bulk_template_csv()
        df = parse_bulk_asset_file("templat_registrasi_aset.csv", template)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["name"], "ID Fan Motor 2A")
        self.assertEqual(_parse_monitoring_modules(df.iloc[0]["monitoring_modules"]), ["VIBRASI", "MCSA", "THERMAL"])


class TestBulkSampleCsv(unittest.TestCase):
    def test_sample_has_multiple_rows_across_equipment_types(self):
        sample = _bulk_sample_csv()
        df = parse_bulk_asset_file("contoh_registrasi_aset.csv", sample)
        self.assertGreaterEqual(len(df), 3)
        self.assertGreaterEqual(df["equipment_type"].nunique(), 3)

    def test_sample_rows_all_convert_to_valid_payloads(self):
        sample = _bulk_sample_csv()
        df = parse_bulk_asset_file("contoh_registrasi_aset.csv", sample)
        for _, row in df.iterrows():
            payload = _row_to_asset_payload(row.to_dict())
            self.assertTrue(payload["name"])
            self.assertTrue(payload["monitoring_modules"])


def _run_wizard():
    def script():
        import streamlit as st

        from src.components.equipment_upload_wizard import render_equipment_upload_wizard

        render_equipment_upload_wizard(st, edit_mode=True)

    return AppTest.from_function(script, default_timeout=30).run()


class TestSingleAssetFormPersistsToRegistry(unittest.TestCase):
    """The single-asset form used to be a UI mock (its Submit button only
    showed a success message without calling upsert_asset). Verifies it now
    actually registers the asset, same as the bulk-upload path.

    src.data_loader.get_data_path() resolves its data root once at import
    time, so MCSA_DATA_DIR set after that has no effect - patch
    asset_registry.get_data_path directly instead (same approach
    tests/test_streamlit_app.py's _isolated_registry() uses)."""

    def setUp(self):
        import src.asset_registry as asset_registry

        self._temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp_dir.cleanup)
        root = Path(self._temp_dir.name)
        patcher = mock.patch.object(asset_registry, "get_data_path", side_effect=lambda *p: str(root.joinpath(*p)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_submit_creates_the_asset(self):
        from src.asset_registry import list_assets

        at = _run_wizard()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

        for widget in at.text_input:
            if widget.label == "EQUIPMENT NAME":
                widget.set_value("Single Form Test Motor")
        for widget in at.selectbox:
            if widget.label == "UNIT":
                widget.set_value("UNIT 2")
        for button in at.button:
            if button.label == "Submit & Register":
                button.click()
        at.run(timeout=30)
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

        assets = list_assets()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["name"], "Single Form Test Motor")
        self.assertEqual(assets[0]["unit"], "UNIT 2")
        self.assertIn("VIBRASI", assets[0]["monitoring_modules"])
        self.assertIn("MCSA", assets[0]["monitoring_modules"])

    def test_blank_equipment_name_is_rejected(self):
        from src.asset_registry import list_assets

        at = _run_wizard()
        for button in at.button:
            if button.label == "Submit & Register":
                button.click()
        at.run(timeout=30)
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.error), "expected a validation error for the blank name")
        self.assertEqual(len(list_assets()), 0)


if __name__ == "__main__":
    unittest.main()
