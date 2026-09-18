import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src import asset_registry


class AssetRegistryTests(unittest.TestCase):
    def test_asset_and_condition_history_are_persisted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset = asset_registry.upsert_asset({
                    "asset_id": "AST-PUMP-A",
                    "name": "Boiler Feed Pump A",
                    "unit": "UNIT 1",
                    "monitoring_modules": ["VIBRASI", "MCSA", "invalid"],
                })
                self.assertEqual(asset["monitoring_modules"], ["MCSA", "VIBRASI"])
                row = asset_registry.add_condition_record({
                    "asset_id": asset["asset_id"],
                    "module": "VIBRASI",
                    "test_date": date(2026, 8, 1),
                    "condition": "Alarm",
                    "summary": "Velocity RMS meningkat",
                })
                self.assertEqual(row["asset_name"], "Boiler Feed Pump A")
                history = asset_registry.load_condition_history()
                self.assertEqual(len(history), 1)
                self.assertEqual(history.iloc[0]["module"], "VIBRASI")

    def test_condition_requires_registered_asset_and_valid_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                with self.assertRaises(ValueError):
                    asset_registry.add_condition_record({"asset_id": "UNKNOWN", "module": "DGA"})

    def test_delete_asset_removes_record_and_returns_true(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-DEL-A", "name": "Delete Me", "unit": "UNIT 1"})
                self.assertIsNotNone(asset_registry.get_asset("AST-DEL-A"))

                deleted = asset_registry.delete_asset("AST-DEL-A")

                self.assertTrue(deleted)
                self.assertIsNone(asset_registry.get_asset("AST-DEL-A"))

    def test_delete_asset_unknown_id_returns_false(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                self.assertFalse(asset_registry.delete_asset("DOES-NOT-EXIST"))

    def test_delete_asset_cascades_condition_history(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-CASCADE-A", "name": "Cascade Pump", "unit": "UNIT 1"})
                asset_registry.upsert_asset({"asset_id": "AST-KEEP-A", "name": "Keep Pump", "unit": "UNIT 1"})
                asset_registry.add_condition_record({
                    "asset_id": "AST-CASCADE-A", "module": "VIBRASI",
                    "test_date": date(2026, 8, 1), "condition": "Alarm",
                })
                asset_registry.add_condition_record({
                    "asset_id": "AST-KEEP-A", "module": "MCSA",
                    "test_date": date(2026, 8, 2), "condition": "Normal",
                })
                self.assertEqual(asset_registry.count_condition_records("AST-CASCADE-A"), 1)

                asset_registry.delete_asset("AST-CASCADE-A")

                history = asset_registry.load_condition_history()
                self.assertEqual(len(history), 1)
                self.assertEqual(history.iloc[0]["asset_id"], "AST-KEEP-A")

    def test_update_condition_record_changes_fields_in_place(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-UPD-A", "name": "Update Pump", "unit": "UNIT 1"})
                row = asset_registry.add_condition_record({
                    "asset_id": "AST-UPD-A", "module": "VIBRASI",
                    "test_date": date(2026, 8, 1), "condition": "Alarm", "summary": "Awal",
                })

                updated = asset_registry.update_condition_record(row["record_id"], {
                    "module": "MCSA", "test_date": date(2026, 8, 5),
                    "condition": "Normal", "summary": "Direvisi",
                })

                self.assertEqual(updated["module"], "MCSA")
                self.assertEqual(updated["condition"], "Normal")
                self.assertEqual(updated["summary"], "Direvisi")
                history = asset_registry.load_condition_history()
                self.assertEqual(len(history), 1)
                self.assertEqual(history.iloc[0]["module"], "MCSA")

    def test_update_condition_record_rejects_invalid_module(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-BAD-A", "name": "Bad Pump", "unit": "UNIT 1"})
                row = asset_registry.add_condition_record({
                    "asset_id": "AST-BAD-A", "module": "VIBRASI", "test_date": date(2026, 8, 1), "condition": "Alarm",
                })
                with self.assertRaises(ValueError):
                    asset_registry.update_condition_record(row["record_id"], {"module": "NOT-A-MODULE"})

    def test_update_condition_record_unknown_id_raises(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                with self.assertRaises(ValueError):
                    asset_registry.update_condition_record("DOES-NOT-EXIST", {"module": "MCSA"})

    def test_delete_condition_record_removes_row_and_returns_true(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-RM-A", "name": "Remove Pump", "unit": "UNIT 1"})
                row = asset_registry.add_condition_record({
                    "asset_id": "AST-RM-A", "module": "VIBRASI", "test_date": date(2026, 8, 1), "condition": "Alarm",
                })

                deleted = asset_registry.delete_condition_record(row["record_id"])

                self.assertTrue(deleted)
                self.assertTrue(asset_registry.load_condition_history().empty)

    def test_delete_condition_record_unknown_id_returns_false(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                self.assertFalse(asset_registry.delete_condition_record("DOES-NOT-EXIST"))

    def test_get_condition_record_returns_dict_or_none(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                asset_registry.upsert_asset({"asset_id": "AST-GET-A", "name": "Get Pump", "unit": "UNIT 1"})
                row = asset_registry.add_condition_record({
                    "asset_id": "AST-GET-A", "module": "VIBRASI", "test_date": date(2026, 8, 1), "condition": "Alarm",
                })

                fetched = asset_registry.get_condition_record(row["record_id"])
                self.assertIsNotNone(fetched)
                self.assertEqual(fetched["asset_id"], "AST-GET-A")
                self.assertIsNone(asset_registry.get_condition_record("DOES-NOT-EXIST"))

    def test_find_asset_canonical_and_dga_sync(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                # Test sync from DGA
                added = asset_registry.sync_assets_from_dga()
                self.assertGreater(added, 0)

                # Test canonical lookup by exact name and alias
                asset = asset_registry.find_asset_canonical("GT 1")
                self.assertIsNotNone(asset)
                self.assertEqual(asset["equipment_type"], "Power Transformer")
                self.assertIn("DGA", asset["monitoring_modules"])

                # Lookup by partial code
                uat = asset_registry.find_asset_canonical("UAT 3")
                self.assertIsNotNone(uat)
                self.assertIn("UAT 3", uat["name"])

