import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

from src import domain_measurements as dm


class DomainMeasurementsTestCase(unittest.TestCase):
    """Every test runs against a throwaway data root so the real data/ tree is
    never touched (MCSA_DATA_DIR is what src.data_loader.get_data_path honors)."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pple_dm_")
        self._env = mock.patch.dict(os.environ, {"MCSA_DATA_DIR": self.root})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def _rows(self, count=2, equipment="CWP 1A", parameter="overall_rms"):
        return [
            {
                "equipment": equipment,
                "unit_name": "UNIT 1",
                "test_date": f"2026-0{index + 1}-15",
                "parameter": parameter,
                "value": 2.0 + index,
                "uom": "mm/s",
                "condition": "Normal",
            }
            for index in range(count)
        ]


class DomainValidationTests(DomainMeasurementsTestCase):
    def test_unknown_domain_rejected(self):
        with self.assertRaises(dm.UnknownDomainError):
            dm.canon_domain("NOT-A-DOMAIN")

    def test_canon_domain_is_case_insensitive(self):
        self.assertEqual(dm.canon_domain("vibrasi"), "VIBRASI")

    def test_mcsa_is_not_served_by_this_store(self):
        # MCSA keeps its own mcsa_updated.csv - see the module docstring.
        with self.assertRaises(dm.UnknownDomainError):
            dm.canon_domain("MCSA")


class LoadAndAppendTests(DomainMeasurementsTestCase):
    def test_load_empty_returns_canonical_columns(self):
        frame = dm.load_measurements("VIBRASI")
        self.assertTrue(frame.empty)
        self.assertEqual(list(frame.columns), dm.COLUMNS)

    def test_append_then_load_roundtrip(self):
        result = dm.append_measurements("VIBRASI", self._rows(2), batch_id="BATCH-1")
        self.assertEqual(result["written"], 2)
        self.assertEqual(result["rejected"], [])

        frame = dm.load_measurements("VIBRASI")
        self.assertEqual(len(frame), 2)
        self.assertEqual(set(frame["batch_id"]), {"BATCH-1"})
        self.assertTrue(frame["record_id"].str.startswith("VIBR").all())
        self.assertEqual(frame["value"].max(), 3.0)

    def test_append_is_additive_not_overwriting(self):
        dm.append_measurements("VIBRASI", self._rows(2))
        dm.append_measurements("VIBRASI", self._rows(1, equipment="CWP 1B"))
        frame = dm.load_measurements("VIBRASI")
        self.assertEqual(len(frame), 3)
        self.assertEqual(set(frame["equipment"]), {"CWP 1A", "CWP 1B"})

    def test_domains_are_isolated_from_each_other(self):
        dm.append_measurements("VIBRASI", self._rows(2))
        self.assertEqual(len(dm.load_measurements("DGA")), 0)

    def test_rows_missing_required_fields_are_rejected_not_written(self):
        rows = self._rows(1) + [{"equipment": "", "test_date": "2026-01-01", "parameter": "x"}]
        result = dm.append_measurements("VIBRASI", rows)
        self.assertEqual(result["written"], 1)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertIn("equipment", result["rejected"][0]["_reason"])

    def test_unparseable_date_is_rejected_with_reason(self):
        rows = [{"equipment": "CWP 1A", "test_date": "bukan-tanggal", "parameter": "overall_rms", "value": 1}]
        result = dm.append_measurements("VIBRASI", rows)
        self.assertEqual(result["written"], 0)
        self.assertIn("Tanggal", result["rejected"][0]["_reason"])

    def test_qualitative_reading_keeps_raw_value_with_nan_value(self):
        rows = [{"equipment": "TRF-1", "test_date": "2026-03-01", "parameter": "iso_cleanliness", "value": "18/16/11 (NAS 8)"}]
        result = dm.append_measurements("TRIBOLOGY", rows)
        self.assertEqual(result["written"], 1)
        frame = dm.load_measurements("TRIBOLOGY")
        self.assertTrue(pd.isna(frame.iloc[0]["value"]))
        self.assertEqual(frame.iloc[0]["raw_value"], "18/16/11 (NAS 8)")

    def test_blank_cell_read_as_nan_is_rejected_not_stored_as_text_nan(self):
        # Regression: an empty CSV cell arrives as float('nan'), and str(nan)
        # is the truthy string 'nan' - it used to pass the required-field
        # check and get stored as equipment literally named "nan".
        rows = [{"equipment": float("nan"), "test_date": "2026-01-01", "parameter": "overall_rms", "value": 1.0}]
        result = dm.append_measurements("VIBRASI", rows)
        self.assertEqual(result["written"], 0)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertNotIn("nan", set(dm.load_measurements("VIBRASI")["equipment"].astype(str)))

    def test_nat_test_date_is_rejected(self):
        rows = [{"equipment": "CWP 1A", "test_date": pd.NaT, "parameter": "overall_rms", "value": 1.0}]
        self.assertEqual(dm.append_measurements("VIBRASI", rows)["written"], 0)

    def test_empty_input_writes_nothing_and_does_not_create_file(self):
        result = dm.append_measurements("DGA", [])
        self.assertEqual(result["written"], 0)
        self.assertFalse(dm.measurements_path("DGA").exists())


class BackupTests(DomainMeasurementsTestCase):
    def test_second_write_creates_a_backup(self):
        dm.append_measurements("VIBRASI", self._rows(1))
        backup_dir = dm.measurements_path("VIBRASI").parent / "backup"
        self.assertFalse(backup_dir.exists(), "first write has nothing to back up yet")

        dm.append_measurements("VIBRASI", self._rows(1, equipment="CWP 1B"))
        self.assertTrue(backup_dir.exists())
        self.assertEqual(len(list(backup_dir.glob("measurements_*.csv"))), 1)

    def test_backup_rotation_honors_mcsa_max_backups(self):
        with mock.patch.dict(os.environ, {"MCSA_MAX_BACKUPS": "2"}):
            for index in range(5):
                dm.append_measurements("VIBRASI", self._rows(1, equipment=f"EQ-{index}"))
            backup_dir = dm.measurements_path("VIBRASI").parent / "backup"
            self.assertLessEqual(len(list(backup_dir.glob("measurements_*.csv"))), 2)


class FilterTests(DomainMeasurementsTestCase):
    def setUp(self):
        super().setUp()
        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "unit_name": "UNIT 1", "test_date": "2026-01-10", "parameter": "overall_rms", "value": 2.0},
            {"equipment": "CWP 1A", "unit_name": "UNIT 1", "test_date": "2026-03-10", "parameter": "overall_rms", "value": 4.5},
            {"equipment": "CWP 2B", "unit_name": "UNIT 2", "test_date": "2026-02-10", "parameter": "overall_rms", "value": 1.2},
            {"equipment": "CWP 2B", "unit_name": "UNIT 2", "test_date": "2026-02-10", "parameter": "temperature", "value": 55.0},
        ])

    def test_no_filters_returns_everything(self):
        self.assertEqual(len(dm.filter_measurements("VIBRASI")), 4)

    def test_period_filter_is_inclusive_on_both_ends(self):
        frame = dm.filter_measurements("VIBRASI", date_start="2026-02-10", date_end="2026-03-10")
        self.assertEqual(len(frame), 3)

    def test_period_filter_excludes_outside_range(self):
        frame = dm.filter_measurements("VIBRASI", date_start="2026-03-01", date_end="2026-03-31")
        self.assertEqual(len(frame), 1)
        self.assertEqual(frame.iloc[0]["value"], 4.5)

    def test_equipment_filter_is_case_insensitive(self):
        self.assertEqual(len(dm.filter_measurements("VIBRASI", equipment="cwp 1a")), 2)

    def test_unit_and_parameter_filters(self):
        self.assertEqual(len(dm.filter_measurements("VIBRASI", unit_name="UNIT 2")), 2)
        self.assertEqual(len(dm.filter_measurements("VIBRASI", parameters=["temperature"])), 1)

    def test_latest_per_equipment_takes_newest_reading_only(self):
        latest = dm.latest_per_equipment("VIBRASI", parameters=["overall_rms"])
        self.assertEqual(len(latest), 2)
        cwp1a = latest[latest["equipment"] == "CWP 1A"].iloc[0]
        self.assertEqual(cwp1a["value"], 4.5)

    def test_available_period_reflects_stored_rows(self):
        earliest, latest = dm.available_period("VIBRASI")
        self.assertEqual(earliest.strftime("%Y-%m-%d"), "2026-01-10")
        self.assertEqual(latest.strftime("%Y-%m-%d"), "2026-03-10")

    def test_available_period_is_none_when_empty(self):
        self.assertEqual(dm.available_period("THERMAL"), (None, None))

    def test_summarise_counts(self):
        summary = dm.summarise("VIBRASI")
        self.assertEqual(summary["records"], 4)
        self.assertEqual(summary["equipment_count"], 2)
        self.assertEqual(summary["parameters"], ["overall_rms", "temperature"])


class DeleteTests(DomainMeasurementsTestCase):
    def test_delete_removes_only_named_records(self):
        dm.append_measurements("DGA", [
            {"equipment": "TRF-1", "test_date": "2026-01-01", "parameter": "h2", "value": 10},
            {"equipment": "TRF-2", "test_date": "2026-01-01", "parameter": "h2", "value": 20},
        ])
        frame = dm.load_measurements("DGA")
        target = frame.iloc[0]["record_id"]

        removed = dm.delete_measurements("DGA", [target])
        self.assertEqual(removed, 1)
        remaining = dm.load_measurements("DGA")
        self.assertEqual(len(remaining), 1)
        self.assertNotIn(target, set(remaining["record_id"]))

    def test_delete_unknown_id_removes_nothing(self):
        dm.append_measurements("DGA", [{"equipment": "TRF-1", "test_date": "2026-01-01", "parameter": "h2", "value": 10}])
        self.assertEqual(dm.delete_measurements("DGA", ["NOPE"]), 0)
        self.assertEqual(len(dm.load_measurements("DGA")), 1)


class UnicodeSpaceTests(DomainMeasurementsTestCase):
    """Excel exports smuggle U+00A0 into names; the store must not keep it."""

    NBSP = chr(0x00A0)

    def test_nbsp_in_equipment_name_is_stored_as_plain_space(self):
        dm.append_measurements("VIBRASI", [{
            "equipment": "ROLLER" + self.NBSP + "SCREEN" + self.NBSP + "1",
            "test_date": "2026-07-01",
            "parameter": "overall_rms",
            "value": 8.21,
        }])
        frame = dm.load_measurements("VIBRASI")
        self.assertEqual(frame.loc[0, "equipment"], "ROLLER SCREEN 1")

    def test_equipment_filter_matches_the_plain_space_name(self):
        dm.append_measurements("VIBRASI", [{
            "equipment": "Fire" + self.NBSP + "Fighting" + self.NBSP + "Jockey" + self.NBSP + "Pump" + self.NBSP + "1",
            "test_date": "2026-07-01",
            "parameter": "overall_rms",
            "value": 0.93,
        }])
        found = dm.filter_measurements("VIBRASI", equipment="Fire Fighting Jockey Pump 1")
        self.assertEqual(len(found), 1)

    def test_internal_whitespace_runs_are_collapsed(self):
        dm.append_measurements("VIBRASI", [{
            "equipment": "BC  10.1 ",
            "test_date": "2026-07-01",
            "parameter": "overall_rms",
            "value": 3.47,
        }])
        self.assertEqual(dm.load_measurements("VIBRASI").loc[0, "equipment"], "BC 10.1")


class CorruptFileTests(DomainMeasurementsTestCase):
    def test_unreadable_csv_degrades_to_empty_not_crash(self):
        path = dm.measurements_path("THERMAL")
        path.parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(b"\x00\x01\x02 not really a csv")
        frame = dm.load_measurements("THERMAL")
        self.assertEqual(list(frame.columns), dm.COLUMNS)


if __name__ == "__main__":
    unittest.main()
