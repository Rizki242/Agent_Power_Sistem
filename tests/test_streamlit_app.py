"""Streamlit UI smoke tests using streamlit.testing.v1.AppTest.

There was previously no automated coverage at all for the Streamlit layer
(app.py, src/pages/, src/components/). These tests don't assert on visual
layout, just that the entrypoint and the newly-added pages (settings,
placeholder) execute without raising.
"""

import os
import unittest

from streamlit.testing.v1 import AppTest

_APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")


class TestAppEntrypoint(unittest.TestCase):
    def test_app_loads_default_page_without_exception(self):
        at = AppTest.from_file(_APP_PATH, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])


class TestSettingsPage(unittest.TestCase):
    def _run_category(self, category):
        def _script():
            import streamlit as st

            from src.pages.settings_page import render_settings_page

            st.session_state["_settings_category_quick"] = None
            st.session_state["_settings_category_more"] = "-"
            render_settings_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        return at

    def test_general_category_renders(self):
        self._run_category("General")

    def test_engineering_modules_category_renders(self):
        def _script():
            import streamlit as st

            from src.pages.settings_page import render_settings_page

            st.session_state["_settings_category_quick"] = "Engineering Modules"
            render_settings_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_engineering_modules_equipment_override_renders(self):
        def _script():
            import streamlit as st

            from src.pages.settings_page import render_settings_page

            st.session_state["_settings_category_quick"] = "Engineering Modules"
            st.session_state["_settings_eq_module_id"] = "TEST-EQUIPMENT-1"
            render_settings_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.checkbox), "expected at least one per-module checkbox for the equipment override table")

    def test_placeholder_category_renders(self):
        def _script():
            import streamlit as st

            from src.pages.settings_page import render_settings_page

            st.session_state["_settings_category_more"] = "Database"
            render_settings_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_ai_llm_category_renders(self):
        import tempfile
        from unittest.mock import patch

        from src import ai_settings

        def _script():
            import streamlit as st

            from src.pages.settings_page import render_settings_page

            st.session_state["_settings_category_quick"] = "AI & LLM"
            render_settings_page(st)

        # _render_ai_llm() persists the provider/model choice on every render
        # (src/ai_settings.py) - isolate it from the real
        # data/MCSA/config/ai_settings.json, same as TestAISettingsPersistence.
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        patcher = patch.object(ai_settings, "_default_path", return_value=path)
        patcher.start()
        self.addCleanup(patcher.stop)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])


class TestAISettingsPersistence(unittest.TestCase):
    """Settings > AI & LLM used to keep the provider/model choice only in
    st.session_state, resetting on every fresh session - src/ai_settings.py
    now persists it to disk (API keys excluded)."""

    def _isolated_path(self):
        import tempfile
        from unittest.mock import patch

        from src import ai_settings

        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(path)
        self.addCleanup(lambda: os.path.exists(path) and os.remove(path))
        patcher = patch.object(ai_settings, "_default_path", return_value=path)
        patcher.start()
        self.addCleanup(patcher.stop)
        return path

    @staticmethod
    def _script():
        import streamlit as st

        from src.pages.settings_page import render_settings_page

        st.session_state["_settings_category_quick"] = "AI & LLM"
        render_settings_page(st)

    def test_provider_choice_persists_across_sessions(self):
        from src import ai_settings

        self._isolated_path()

        at = AppTest.from_function(self._script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        provider_select = next(w for w in at.selectbox if w.key == "_llm_provider_sel")
        provider_select.set_value("Groq (Ultra-Fast Cloud)")
        at.run(timeout=30)
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

        self.assertEqual(ai_settings.load().get("ai_provider"), "groq")

        # A brand-new AppTest run simulates a fresh browser session with an
        # empty st.session_state - the persisted choice should seed it.
        at_fresh = AppTest.from_function(self._script, default_timeout=30).run()
        self.assertFalse(list(at_fresh.exception), msg=[str(e) for e in at_fresh.exception])
        fresh_provider_select = next(w for w in at_fresh.selectbox if w.key == "_llm_provider_sel")
        self.assertEqual(fresh_provider_select.value, "Groq (Ultra-Fast Cloud)")

    def test_persisted_file_never_contains_api_keys(self):
        import json

        path = self._isolated_path()

        at = AppTest.from_function(self._script, default_timeout=30).run()
        key_widget = next(w for w in at.text_input if w.label == "Gemini API Key")
        key_widget.set_value("AIzaSuperSecretTestKeyDoNotPersist")
        at.run(timeout=30)
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("AIzaSuperSecretTestKeyDoNotPersist", raw)
        saved = json.loads(raw)
        self.assertNotIn("gemini_api_key", saved)


class TestPlaceholderPage(unittest.TestCase):
    def test_placeholder_page_renders(self):
        def _script():
            import streamlit as st

            from src.pages.placeholder_page import render_placeholder_page

            render_placeholder_page(st, "Reliability", "Belum tersedia.")

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])


class TestAgentDashboardPage(unittest.TestCase):
    """Default landing page: agent roster + fleet overview + drill-down diagnosis."""

    @staticmethod
    def _script():
        import pandas as pd
        import streamlit as st

        from src.pages.agent_dashboard_page import render_agent_dashboard_page

        df_latest_all = pd.DataFrame([
            {"Equipment": "CWP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Value": None,
             "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "CWP 1A", "Parameter": "Upper Sideband", "Raw_Value": "-52.5", "Value": -52.5,
             "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
        ])
        render_agent_dashboard_page(st, df_latest_all=df_latest_all)

    def test_agent_dashboard_overview_renders(self):
        at = AppTest.from_function(self._script, default_timeout=60).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.metric), "expected fleet overview metrics to render")

    def test_agent_dashboard_drilldown_diagnosis_renders(self):
        at = AppTest.from_function(self._script, default_timeout=60).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(any(sb.key == "agent_diag_equipment" for sb in at.selectbox),
                        "expected the drill-down equipment selectbox to render")
        self.assertTrue(list(at.success), "expected the safety-clearance banner to render")


class TestMCSADashboardPage(unittest.TestCase):
    """The legacy Command Center dashboard, now living under Engineering > MCSA."""

    def test_mcsa_dashboard_page_renders_with_real_data(self):
        def _script():
            import pandas as pd
            import streamlit as st

            from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
            from src.equipment_canon import build_master_norm_maps, load_equipment_master
            from src.pages.dashboard_page import render_dashboard_page

            df = load_mcsa_data(get_data_path("Report MCSA.xls"))
            df["Date"] = pd.to_datetime(df.get("Date", pd.NaT), errors="coerce")
            df_latest_all = get_latest_data(df)
            eq_master_df = load_equipment_master(get_data_path("config", "equipment_master.json"))
            unit_map, volt_map = build_master_norm_maps(eq_master_df)
            render_dashboard_page(
                st,
                df=df,
                df_latest=df_latest_all,
                df_latest_all=df_latest_all,
                filtered_df=df_latest_all,
                df_month=None,
                date_start=df["Date"].min().date(),
                date_end=df["Date"].max().date(),
                sel_unit="All",
                sel_volt="All",
                sel_equipment=[],
                standby_enabled=False,
                standby_report=None,
                eq_master_df=eq_master_df,
                master_norm_to_unit=unit_map,
                master_norm_to_volt=volt_map,
            )

        at = AppTest.from_function(_script, default_timeout=120).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])


class TestDomainDashboards(unittest.TestCase):
    """Vibrasi/DGA/Tribology - ported from feature/domain-dashboards (see docs/agents plan)."""

    def test_vibration_page_renders(self):
        def _script():
            import streamlit as st

            from src.pages.vibration_page import render_vibration_page

            render_vibration_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_vibration_page_rekomendasi_tab_renders(self):
        def _script():
            import streamlit as st

            from src.pages.vibration_page import render_vibration_page

            st.session_state["vibration_detail_view"] = "Rekomendasi"
            render_vibration_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_dga_page_renders_with_disclaimer(self):
        def _script():
            import streamlit as st

            from src.pages.dga_page import render_dga_page

            render_dga_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.warning), "expected the data disclaimer banner to render")

    def test_dga_page_rekomendasi_tab_renders(self):
        def _script():
            import streamlit as st

            from src.pages.dga_page import render_dga_page

            st.session_state["dga_detail_view"] = "Rekomendasi"
            render_dga_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_tribology_page_renders_with_disclaimer(self):
        def _script():
            import streamlit as st

            from src.pages.tribology_page import render_tribology_page

            render_tribology_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.warning), "expected the data disclaimer banner to render")

    def test_tribology_page_rekomendasi_tab_renders(self):
        def _script():
            import streamlit as st

            from src.pages.tribology_page import render_tribology_page

            st.session_state["tribology_detail_view"] = "Rekomendasi"
            render_tribology_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_thermal_page_renders_without_disclaimer(self):
        def _script():
            import streamlit as st

            from src.pages.thermal_page import render_thermal_page

            render_thermal_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertFalse(list(at.warning), "Thermal data is real (parsed Excel) - it should not show the disclaimer banner")

    def test_thermal_page_rekomendasi_tab_renders(self):
        def _script():
            import streamlit as st

            from src.pages.thermal_page import render_thermal_page

            st.session_state["thermal_detail_view"] = "Rekomendasi"
            render_thermal_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_pd_page_renders_with_disclaimer(self):
        def _script():
            import streamlit as st

            from src.pages.pd_page import render_pd_page

            render_pd_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.warning), "expected the data disclaimer banner to render")

    def test_pd_page_rekomendasi_tab_renders(self):
        def _script():
            import streamlit as st

            from src.pages.pd_page import render_pd_page

            st.session_state["pd_detail_view"] = "Rekomendasi"
            render_pd_page(st)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])


class TestAssetRegistryPage(unittest.TestCase):
    """Cross-domain asset register (src/asset_registry.py) + its two pages -
    Register Aset (write side) and Laporan Kondisi (read side)."""

    def _isolated_registry(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        import src.asset_registry as asset_registry

        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        patcher = patch.object(asset_registry, "get_data_path", side_effect=lambda *p: str(root.joinpath(*p)))
        patcher.start()
        self.addCleanup(patcher.stop)
        return asset_registry

    def test_registry_page_renders_empty(self):
        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        self._isolated_registry()
        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_registry_page_warns_when_edit_mode_off(self):
        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=False)

        self._isolated_registry()
        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(list(at.warning), "expected the edit-mode-off warning to render")

    def test_new_asset_form_persists_to_registry(self):
        registry = self._isolated_registry()

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        for widget in at.text_input:
            if widget.label == "Nama Aset":
                widget.set_value("Boiler Feed Pump Test")
        for widget in at.multiselect:
            if widget.label == "Modul Monitoring yang Berlaku":
                widget.set_value(["MCSA", "VIBRASI"])
        for button in at.button:
            if button.label == "Simpan Aset":
                button.click()
        at.run(timeout=30)
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

        assets = registry.list_assets()
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0]["name"], "Boiler Feed Pump Test")
        self.assertEqual(assets[0]["monitoring_modules"], ["MCSA", "VIBRASI"])

    def test_condition_form_only_offers_assets_own_modules(self):
        registry = self._isolated_registry()
        registry.upsert_asset({"name": "Boiler Feed Pump A", "unit": "UNIT 1", "monitoring_modules": ["VIBRASI"]})

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        module_select = next(w for w in at.selectbox if w.label == "Modul Pengujian")
        self.assertEqual(list(module_select.options), ["VIBRASI"])

    def test_delete_asset_requires_confirmation_checkbox(self):
        registry = self._isolated_registry()
        asset = registry.upsert_asset({"asset_id": "AST-DEL-UI", "name": "Delete UI Pump", "unit": "UNIT 1"})

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        next(w for w in at.selectbox if w.key == "asset_registry_select").set_value(asset["asset_id"])
        at.run(timeout=30)

        delete_button = next(b for b in at.button if b.label == "Hapus Permanen")
        self.assertTrue(delete_button.disabled, "delete button must stay disabled until the confirmation checkbox is checked")

    def test_delete_asset_removes_it_and_cascades_history(self):
        registry = self._isolated_registry()
        asset = registry.upsert_asset({"asset_id": "AST-DEL-UI2", "name": "Delete UI Pump 2", "unit": "UNIT 1", "monitoring_modules": ["VIBRASI"]})
        registry.add_condition_record({"asset_id": asset["asset_id"], "module": "VIBRASI", "condition": "Alarm"})

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        next(w for w in at.selectbox if w.key == "asset_registry_select").set_value(asset["asset_id"])
        at.run(timeout=30)
        next(c for c in at.checkbox if c.key == "_confirm_delete_asset").set_value(True)
        at.run(timeout=30)
        next(b for b in at.button if b.label == "Hapus Permanen").click()
        at.run(timeout=30)

        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertIsNone(registry.get_asset(asset["asset_id"]))
        self.assertTrue(registry.load_condition_history().empty)

    def test_edit_condition_record_prefills_and_updates(self):
        registry = self._isolated_registry()
        asset = registry.upsert_asset({"asset_id": "AST-EDIT-UI", "name": "Edit UI Pump", "unit": "UNIT 1", "monitoring_modules": ["VIBRASI", "MCSA"]})
        record = registry.add_condition_record({
            "asset_id": asset["asset_id"], "module": "VIBRASI", "condition": "Alarm", "summary": "Awal",
        })

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        next(w for w in at.selectbox if w.key == "asset_condition_select").set_value(asset["asset_id"])
        at.run(timeout=30)
        next(w for w in at.selectbox if w.key == "asset_condition_record_select").set_value(record["record_id"])
        at.run(timeout=30)

        summary_widget = next(w for w in at.text_area if w.label == "Ringkasan Temuan")
        self.assertEqual(summary_widget.value, "Awal")

        summary_widget.set_value("Direvisi lewat UI")
        next(b for b in at.button if b.label == "Simpan Perubahan").click()
        at.run(timeout=30)

        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        updated = registry.get_condition_record(record["record_id"])
        self.assertEqual(updated["summary"], "Direvisi lewat UI")

    def test_delete_condition_record_removes_it(self):
        registry = self._isolated_registry()
        asset = registry.upsert_asset({"asset_id": "AST-DELREC-UI", "name": "Del Record UI Pump", "unit": "UNIT 1", "monitoring_modules": ["VIBRASI"]})
        record = registry.add_condition_record({"asset_id": asset["asset_id"], "module": "VIBRASI", "condition": "Alarm"})

        def _script():
            import streamlit as st

            from src.pages.asset_registry_page import render_asset_registry_page

            render_asset_registry_page(st, edit_mode=True)

        at = AppTest.from_function(_script, default_timeout=30).run()
        next(w for w in at.selectbox if w.key == "asset_condition_select").set_value(asset["asset_id"])
        at.run(timeout=30)
        next(w for w in at.selectbox if w.key == "asset_condition_record_select").set_value(record["record_id"])
        at.run(timeout=30)
        next(b for b in at.button if b.label == "Hapus Catatan Ini").click()
        at.run(timeout=30)

        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])
        self.assertTrue(registry.load_condition_history().empty)

    def test_reports_page_shows_empty_state_then_recorded_history(self):
        registry = self._isolated_registry()

        def _script():
            import streamlit as st

            from src.pages.asset_reports_page import render_asset_reports_page

            render_asset_reports_page(st)

        at_empty = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at_empty.exception), msg=[str(e) for e in at_empty.exception])
        self.assertTrue(list(at_empty.info), "expected the no-history-yet message")

        asset = registry.upsert_asset({"name": "Boiler Feed Pump A", "unit": "UNIT 1", "monitoring_modules": ["VIBRASI"]})
        registry.add_condition_record({
            "asset_id": asset["asset_id"], "module": "VIBRASI", "condition": "Alarm", "summary": "test",
        })

        at_filled = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at_filled.exception), msg=[str(e) for e in at_filled.exception])


if __name__ == "__main__":
    unittest.main()
