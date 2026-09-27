import io
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import pandas as pd

from src import domain_ingest as ingest
from src import domain_measurements as dm


class IngestTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pple_ingest_")
        self._env = mock.patch.dict(os.environ, {"MCSA_DATA_DIR": self.root})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def _csv(self, frame: pd.DataFrame) -> bytes:
        return frame.to_csv(index=False).encode("utf-8")


class ProfileTests(IngestTestCase):
    def test_every_domain_has_a_profile(self):
        for domain in dm.DOMAINS:
            self.assertIn(domain, ingest.PROFILES)
            self.assertTrue(ingest.parameter_specs(domain))

    def test_parameter_keys_match_specialist_agent_inputs(self):
        # The whole point of the shared vocabulary: ingested data must be able
        # to drive the real agent. These keys are read by
        # src.agents.specialist_agents.<Agent>.evaluate().
        expected = {
            "VIBRASI": {"overall_rms", "amp_1x", "amp_2x", "axial_1x", "bpfo_amp", "bpfi_amp"},
            "DGA": {"h2", "ch4", "c2h2", "c2h4", "c2h6", "co", "co2"},
            "TRIBOLOGY": {"viscosity_40c", "tan", "water_ppm", "fe_ppm", "cu_ppm", "iso_cleanliness"},
            "THERMAL": {"bearing_temp", "winding_temp", "ambient_temp", "delta_t_phase", "hotspot_temp"},
            "PD": {"pulse_magnitude_pc", "nqn", "phase_clustering_deg", "pd_type"},
        }
        for domain, keys in expected.items():
            actual = {spec.key for spec in ingest.parameter_specs(domain)}
            self.assertTrue(keys.issubset(actual), f"{domain} kehilangan {keys - actual}")

    def test_template_csv_has_identity_and_parameter_columns(self):
        raw = ingest.template_csv("DGA")
        frame = pd.read_csv(io.BytesIO(raw))
        for column in ("equipment", "unit_name", "test_date", "h2", "co2", "condition"):
            self.assertIn(column, frame.columns)


class ColumnMappingTests(IngestTestCase):
    def test_maps_canonical_column_names(self):
        frame = pd.DataFrame(columns=["equipment", "test_date", "overall_rms", "amp_1x"])
        mapping = ingest.map_columns("VIBRASI", frame)
        self.assertEqual(mapping["equipment"], "equipment")
        self.assertEqual(mapping["overall_rms"], "overall_rms")

    def test_maps_indonesian_and_export_aliases(self):
        frame = pd.DataFrame(columns=["Peralatan", "Tanggal Uji", "Velocity Max", "Unit"])
        mapping = ingest.map_columns("VIBRASI", frame)
        self.assertEqual(mapping["Peralatan"], "equipment")
        self.assertEqual(mapping["Tanggal Uji"], "test_date")
        self.assertEqual(mapping["Velocity Max"], "overall_rms")
        self.assertEqual(mapping["Unit"], "unit_name")

    def test_mapping_is_case_and_separator_insensitive(self):
        frame = pd.DataFrame(columns=["EQUIPMENT_ID", "test date", "BPFO_amp_g"])
        mapping = ingest.map_columns("VIBRASI", frame)
        self.assertEqual(set(mapping.values()), {"equipment", "test_date", "bpfo_amp"})

    def test_unknown_columns_are_left_unmapped(self):
        frame = pd.DataFrame(columns=["equipment", "test_date", "kolom_asing"])
        mapping = ingest.map_columns("VIBRASI", frame)
        self.assertNotIn("kolom_asing", mapping)

    def test_maps_the_real_field_sheet_point_columns(self):
        # equipment/asset_id/unit_name/test_date/1V.../6A/kondisi/note - a
        # real inspection sheet template, not a synthetic example.
        columns = ["equipment", "asset_id", "unit_name", "test_date",
                   "1V", "1H", "1A", "6V", "6H", "6A", "kondisi ", "note"]
        mapping = ingest.map_columns("VIBRASI", pd.DataFrame(columns=columns))
        self.assertEqual(mapping["1V"], "pt1_v")
        self.assertEqual(mapping["1H"], "pt1_h")
        self.assertEqual(mapping["1A"], "pt1_a")
        self.assertEqual(mapping["6A"], "pt6_a")
        self.assertEqual(mapping["kondisi "], "condition")
        self.assertEqual(mapping["note"], "notes")
        self.assertEqual(mapping["asset_id"], "asset_id")

    def test_maps_the_gt_sampling_sheet_columns(self):
        """The GT#1..GT#3 transformer sheets carry TDCG and H2O columns whose
        keys are already in the store; both must map, not fall through."""
        frame = pd.DataFrame(columns=[
            "Equipment sumber", "Unit", "Tanggal", "TDCG", "H2", "CH4", "C2H6",
            "C2H4", "C2H2", "CO", "CO2", "H2O", "BDV", "Load MW", "Oil Temp",
            "Winding Temp",
        ])
        mapping = ingest.map_columns("DGA", frame)
        self.assertEqual(mapping["TDCG"], "tdcg")
        self.assertEqual(mapping["H2O"], "h2o")
        self.assertEqual(mapping["BDV"], "bdv_kv")
        self.assertEqual(mapping["Load MW"], "beban_mw")
        self.assertEqual(mapping["Oil Temp"], "temp_oil")
        self.assertEqual(mapping["Winding Temp"], "temp_winding")
        self.assertNotIn("H2O", {mapping[col] for col in mapping if col == "H2"})



class DelimiterDetectionTests(IngestTestCase):
    def test_tab_separated_csv_is_read_correctly(self):
        # Confirmed real-world case: a .csv exported from Excel that is
        # actually tab-separated. Reading it as comma-separated would parse
        # the entire header into a single unsplit column instead of raising,
        # which is worse than an error - nothing looks obviously wrong until
        # every column comes back unmapped.
        content = "equipment\ttest_date\t1V\tkondisi \tnote\nCWP 1A\t2026-05-01\t2.1\tNormal\tok\n".encode()
        preview = ingest.preview_upload("VIBRASI", "sheet.csv", content)
        self.assertEqual(preview["source_rows"], 1)
        self.assertEqual(len(preview["valid"]), 1)
        self.assertEqual(preview["valid"][0]["parameter"], "pt1_v")

    def test_semicolon_separated_csv_is_read_correctly(self):
        content = "equipment;test_date;overall_rms\nCWP 1A;2026-05-01;3.2\n".encode()
        preview = ingest.preview_upload("VIBRASI", "sheet.csv", content)
        self.assertEqual(len(preview["valid"]), 1)

    def test_comma_separated_csv_still_works(self):
        content = "equipment,test_date,overall_rms\nCWP 1A,2026-05-01,3.2\n".encode()
        preview = ingest.preview_upload("VIBRASI", "sheet.csv", content)
        self.assertEqual(len(preview["valid"]), 1)


class WideToLongTests(IngestTestCase):
    def test_one_wide_row_becomes_one_row_per_parameter(self):
        frame = pd.DataFrame([{
            "equipment": "CWP 1A", "unit_name": "UNIT 1", "test_date": "2026-05-01",
            "overall_rms": 3.2, "amp_1x": 1.1,
        }])
        rows = ingest.wide_to_long("VIBRASI", frame)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["parameter"] for row in rows}, {"overall_rms", "amp_1x"})
        self.assertTrue(all(row["equipment"] == "CWP 1A" for row in rows))

    def test_blank_parameter_cells_are_skipped_not_stored_as_zero(self):
        frame = pd.DataFrame([{
            "equipment": "CWP 1A", "test_date": "2026-05-01",
            "overall_rms": 3.2, "amp_1x": None, "amp_2x": "",
        }])
        rows = ingest.wide_to_long("VIBRASI", frame)
        self.assertEqual([row["parameter"] for row in rows], ["overall_rms"])

    def test_uom_is_attached_from_the_profile(self):
        frame = pd.DataFrame([{"equipment": "TRF-1", "test_date": "2026-05-01", "h2": 12}])
        rows = ingest.wide_to_long("DGA", frame)
        self.assertEqual(rows[0]["uom"], "ppm")


class PreviewTests(IngestTestCase):
    def test_preview_reports_valid_rejected_and_unmapped(self):
        frame = pd.DataFrame([
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "overall_rms": 3.2, "catatan_lain": "x"},
            {"equipment": "", "test_date": "2026-05-01", "overall_rms": 1.0, "catatan_lain": "y"},
        ])
        preview = ingest.preview_upload("VIBRASI", "uji.csv", self._csv(frame))

        self.assertEqual(preview["source_rows"], 2)
        self.assertEqual(len(preview["valid"]), 1)
        self.assertEqual(len(preview["rejected"]), 1)
        self.assertIn("catatan_lain", preview["unmapped_columns"])
        self.assertEqual(preview["parameters_found"], ["overall_rms"])

    def test_preview_writes_nothing_to_the_store(self):
        frame = pd.DataFrame([{"equipment": "CWP 1A", "test_date": "2026-05-01", "overall_rms": 3.2}])
        ingest.preview_upload("VIBRASI", "uji.csv", self._csv(frame))
        self.assertTrue(dm.load_measurements("VIBRASI").empty)

    def test_unsupported_extension_raises_readable_error(self):
        with self.assertRaises(ValueError) as ctx:
            ingest.preview_upload("VIBRASI", "laporan.docx", b"x")
        self.assertIn("tidak didukung", str(ctx.exception))

    def test_a_duplicate_aliased_column_is_reported_as_duplicate_not_unmapped(self):
        # Two columns both alias overall_rms (e.g. a copy-pasted template) -
        # the second is dropped, but the reason shown to the user must say
        # so, not claim the column was unrecognized.
        frame = pd.DataFrame([{"equipment": "CWP 1A", "test_date": "2026-05-01", "overall_rms": 3.2, "velocity_rms_mm_s": 3.5}])
        preview = ingest.preview_upload("VIBRASI", "uji.csv", self._csv(frame))
        self.assertIn("velocity_rms_mm_s", preview["duplicate_columns"])
        self.assertNotIn("velocity_rms_mm_s", preview["unmapped_columns"])

    def test_xlsx_upload_is_supported(self):
        frame = pd.DataFrame([{"equipment": "TRF-1", "test_date": "2026-05-01", "h2": 20}])
        buffer = io.BytesIO()
        frame.to_excel(buffer, index=False)
        preview = ingest.preview_upload("DGA", "dga.xlsx", buffer.getvalue())
        self.assertEqual(len(preview["valid"]), 1)


class BatchCommitTests(IngestTestCase):
    def _preview_and_commit(self, domain="VIBRASI"):
        frame = pd.DataFrame([
            {"equipment": "CWP 1A", "unit_name": "UNIT 1", "test_date": "2026-05-01", "overall_rms": 3.2},
            {"equipment": "CWP 1B", "unit_name": "UNIT 1", "test_date": "2026-05-01", "overall_rms": 6.9},
        ])
        content = self._csv(frame)
        preview = ingest.preview_upload(domain, "uji.csv", content)
        batch_path, _ = ingest.create_batch(domain, "uji.csv", content, preview)
        return batch_path, ingest.commit_batch(domain, batch_path, preview)

    def test_commit_writes_rows_into_the_canonical_store(self):
        _, result = self._preview_and_commit()
        self.assertEqual(result["written"], 2)
        stored = dm.load_measurements("VIBRASI")
        self.assertEqual(len(stored), 2)
        self.assertEqual(set(stored["equipment"]), {"CWP 1A", "CWP 1B"})

    def test_batch_archives_original_file_and_manifest(self):
        batch_path, _ = self._preview_and_commit()
        self.assertTrue((batch_path / "uji.csv").exists())
        manifest = json.loads((batch_path / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "committed")
        self.assertEqual(manifest["written_rows"], 2)
        self.assertEqual(manifest["domain"], "VIBRASI")

    def test_manifest_records_audit_events(self):
        batch_path, _ = self._preview_and_commit()
        manifest = ingest.load_manifest(batch_path)
        actions = [event["action"] for event in manifest["audit_events"]]
        self.assertEqual(actions, ["preview", "commit"])

    def test_committed_rows_carry_the_batch_id(self):
        _, result = self._preview_and_commit()
        stored = dm.load_measurements("VIBRASI")
        self.assertEqual(set(stored["batch_id"]), {result["batch_id"]})

    def test_list_recent_batches_returns_newest_first(self):
        self._preview_and_commit()
        self._preview_and_commit()
        batches = ingest.list_recent_batches("VIBRASI")
        self.assertEqual(len(batches), 2)
        self.assertGreaterEqual(batches[0]["uploaded_at"], batches[1]["uploaded_at"])

    def test_batches_are_isolated_per_domain(self):
        self._preview_and_commit("VIBRASI")
        self.assertEqual(ingest.list_recent_batches("DGA"), [])


class ManualEntryTests(IngestTestCase):
    def test_manual_entry_produces_storable_rows(self):
        rows = ingest.manual_entry_rows(
            "DGA",
            {"equipment": "TRF-1", "unit_name": "UNIT 1", "test_date": "2026-06-01", "condition": "Normal"},
            {"h2": 15, "ch4": 25, "c2h2": ""},
        )
        self.assertEqual(len(rows), 2)
        result = dm.append_measurements("DGA", rows)
        self.assertEqual(result["written"], 2)
        self.assertEqual(set(dm.load_measurements("DGA")["source_file"]), {"input-manual"})

    def test_manual_and_upload_land_in_the_same_store(self):
        frame = pd.DataFrame([{"equipment": "TRF-1", "test_date": "2026-06-01", "h2": 10}])
        preview = ingest.preview_upload("DGA", "a.csv", frame.to_csv(index=False).encode())
        path, _ = ingest.create_batch("DGA", "a.csv", frame.to_csv(index=False).encode(), preview)
        ingest.commit_batch("DGA", path, preview)
        dm.append_measurements("DGA", ingest.manual_entry_rows(
            "DGA", {"equipment": "TRF-2", "test_date": "2026-06-02"}, {"h2": 11},
        ))
        self.assertEqual(len(dm.load_measurements("DGA")), 2)


class AgentInputTests(IngestTestCase):
    def test_builds_agent_input_from_latest_readings(self):
        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "test_date": "2026-01-01", "parameter": "overall_rms", "value": 2.0},
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "overall_rms", "value": 5.5},
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "amp_1x", "value": 1.4},
        ])
        frame = dm.filter_measurements("VIBRASI", equipment="CWP 1A")
        payload = ingest.agent_input_from_measurements("VIBRASI", frame)
        self.assertEqual(payload["overall_rms"], 5.5)
        self.assertEqual(payload["amp_1x"], 1.4)

    def test_agent_input_feeds_the_real_specialist_agent(self):
        from src.agents.specialist_agents import VibrationAgent

        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "overall_rms", "value": 7.8},
        ])
        frame = dm.filter_measurements("VIBRASI", equipment="CWP 1A")
        payload = ingest.agent_input_from_measurements("VIBRASI", frame)
        result = VibrationAgent().evaluate("CWP 1A", payload)
        # 7.8 mm/s is well past ISO 10816-3 zone C, so the agent must not
        # report Normal - proving the ingested value really drove the verdict
        # instead of the agent's built-in 2.2 mm/s example default.
        self.assertEqual(result["metrics"]["overall_rms"], 7.8)
        self.assertNotEqual(result["condition"], "Normal")

    def test_a_missing_qualitative_reading_is_omitted_not_the_string_nan(self):
        # A qualitative parameter (numeric=False) with no raw text recorded
        # stores an empty raw_value, which comes back as float('nan') after
        # a CSV round-trip (pd.read_csv treats an empty cell as NaN). NaN is
        # truthy in Python, so a naive `raw_value or ""` would let it through
        # as the literal string "nan" instead of treating it as missing.
        dm.append_measurements("TRIBOLOGY", [
            {"equipment": "TRF-1", "test_date": "2026-05-01", "parameter": "iso_cleanliness", "value": float("nan"), "raw_value": ""},
        ])
        frame = dm.filter_measurements("TRIBOLOGY", equipment="TRF-1")
        payload = ingest.agent_input_from_measurements("TRIBOLOGY", frame)
        self.assertNotIn("iso_cleanliness", payload)

    def test_a_present_qualitative_reading_still_comes_through_as_text(self):
        dm.append_measurements("TRIBOLOGY", [
            {"equipment": "TRF-1", "test_date": "2026-05-01", "parameter": "iso_cleanliness", "value": float("nan"), "raw_value": "18/16/13"},
        ])
        frame = dm.filter_measurements("TRIBOLOGY", equipment="TRF-1")
        payload = ingest.agent_input_from_measurements("TRIBOLOGY", frame)
        self.assertEqual(payload["iso_cleanliness"], "18/16/13")

    def test_qualitative_reading_passes_through_as_text(self):
        dm.append_measurements("TRIBOLOGY", [
            {"equipment": "PMP-1", "test_date": "2026-05-01", "parameter": "iso_cleanliness", "value": "18/16/11"},
        ])
        frame = dm.filter_measurements("TRIBOLOGY", equipment="PMP-1")
        payload = ingest.agent_input_from_measurements("TRIBOLOGY", frame)
        self.assertEqual(payload["iso_cleanliness"], "18/16/11")

    def test_point_based_sheet_derives_overall_rms_as_the_worst_point(self):
        # Regression: a real field sheet (equipment/asset_id/unit_name/
        # test_date/1V.../6A/kondisi/note) has no "overall" column at all -
        # without a derived overall_rms, VibrationAgent would silently fall
        # back to its 2.2 mm/s example default and report Normal regardless
        # of what was actually measured.
        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "pt1_v", "value": 2.1},
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "pt3_v", "value": 7.9},
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "pt4_a", "value": 0.8},
        ])
        frame = dm.filter_measurements("VIBRASI", equipment="CWP 1A")
        payload = ingest.agent_input_from_measurements("VIBRASI", frame)
        self.assertEqual(payload["overall_rms"], 7.9)

    def test_explicit_overall_rms_column_is_never_overridden_by_points(self):
        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "overall_rms", "value": 3.0},
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "pt3_v", "value": 9.9},
        ])
        frame = dm.filter_measurements("VIBRASI", equipment="CWP 1A")
        payload = ingest.agent_input_from_measurements("VIBRASI", frame)
        self.assertEqual(payload["overall_rms"], 3.0)

    def test_no_points_and_no_overall_leaves_overall_rms_unset(self):
        dm.append_measurements("VIBRASI", [
            {"equipment": "CWP 1A", "test_date": "2026-05-01", "parameter": "temperature", "value": 55.0},
        ])
        frame = dm.filter_measurements("VIBRASI", equipment="CWP 1A")
        payload = ingest.agent_input_from_measurements("VIBRASI", frame)
        self.assertNotIn("overall_rms", payload)

    def test_empty_frame_yields_empty_payload(self):
        self.assertEqual(ingest.agent_input_from_measurements("PD", pd.DataFrame()), {})


if __name__ == "__main__":
    unittest.main()
