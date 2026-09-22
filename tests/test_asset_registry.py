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

    def test_repeated_writes_never_corrupt_test_date_to_blank(self):
        """Regression test for a real bug: add_condition_record() used to
        append onto load_condition_history()'s datetime-coerced DataFrame,
        then save it back. Mixing freshly-formatted string dates with
        already-coerced Timestamp objects across repeated calls made pandas
        silently turn some earlier rows' test_date into NaT (blank on
        save) - reproduced with 3+ sequential calls. Also covers a second,
        related failure: once corrupted rows exist with a different date
        string format ("%Y-%m-%d %H:%M:%S" vs "%Y-%m-%d"), pandas >= 2's
        default to_datetime() infers ONE format from the column and NaTs
        every row that doesn't match it - fixed by format="mixed"."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(asset_registry, "get_data_path", side_effect=lambda *parts: str(root.joinpath(*parts))):
                for i in range(5):
                    asset_registry.upsert_asset({
                        "asset_id": f"AST-SEQ-{i}",
                        "name": f"Sequential Pump {i}",
                        "unit": "UNIT 1",
                        "monitoring_modules": ["VIBRASI"],
                    })
                for i in range(5):
                    asset_registry.add_condition_record({
                        "asset_id": f"AST-SEQ-{i}",
                        "module": "VIBRASI",
                        "test_date": "2026-07-01",
                        "condition": "Normal",
                        "summary": "test",
                    })
                history = asset_registry.load_condition_history()
                seq_rows = history[history["asset_id"].str.startswith("AST-SEQ-")]
                self.assertEqual(len(seq_rows), 5)
                self.assertEqual(seq_rows["test_date"].isna().sum(), 0,
                                  "no sequentially-written row should end up with a blank/NaT test_date")
                self.assertTrue((seq_rows["test_date"] == "2026-07-01").all())

                # Simulate a pre-existing row written by the old buggy code
                # path (Timestamp-formatted "%Y-%m-%d %H:%M:%S") to prove
                # load_condition_history() still parses the new plain-date
                # rows correctly alongside it, rather than NaT-ing them.
                raw = asset_registry._load_condition_history_raw()
                raw.loc[len(raw)] = {
                    "record_id": "COND-LEGACYFMT", "asset_id": "AST-SEQ-0", "asset_name": "Sequential Pump 0",
                    "module": "VIBRASI", "test_date": "2026-06-01 00:00:00", "condition": "Normal",
                    "summary": "legacy-format row", "source_file": "", "created_at": "2026-01-01T00:00:00",
                }
                raw.to_csv(asset_registry._condition_path(), index=False)

                reloaded = asset_registry.load_condition_history()
                self.assertEqual(reloaded["test_date"].isna().sum(), 0,
                                  "a legacy '%Y-%m-%d %H:%M:%S' row must not blank out the other rows' plain-date values")

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

