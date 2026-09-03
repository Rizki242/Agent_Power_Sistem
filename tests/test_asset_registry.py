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

