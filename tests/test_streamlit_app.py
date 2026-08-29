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


class TestPlaceholderPage(unittest.TestCase):
    def test_placeholder_page_renders(self):
        def _script():
            import streamlit as st

            from src.pages.placeholder_page import render_placeholder_page

            render_placeholder_page(st, "Reliability", "Belum tersedia.")

        at = AppTest.from_function(_script, default_timeout=30).run()
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


if __name__ == "__main__":
    unittest.main()
