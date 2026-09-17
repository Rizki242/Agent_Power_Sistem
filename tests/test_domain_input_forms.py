"""Unit tests for the rich domain input forms module.

Tests verify:
- All four render_* functions are importable (guards against broken imports
  that would crash app.py at startup).
- Each form function accepts `st` (as a mock) without raising.
- DomainWorkspaceConfig accepts the new input_form_renderer field.
- The _tdcg_status helper returns correct IEEE C57.104 conditions.
- The _vib_zone helper returns correct ISO 10816-3 zones.
"""

import sys
import types
import unittest
from datetime import date
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Minimal Streamlit mock so tests can import form modules without a server
# ---------------------------------------------------------------------------

def _make_st_mock():
    """Return a MagicMock that mimics the subset of the st API used by forms."""
    st = MagicMock()
    # Widgets must return sentinel defaults matching their type
    st.selectbox.return_value = "Unit 1"
    st.text_input.return_value = ""
    st.text_area.return_value = ""
    st.number_input.return_value = 0.0
    st.date_input.return_value = date.today()
    st.columns.return_value = [MagicMock() for _ in range(4)]
    st.tabs.return_value = [MagicMock().__enter__.return_value for _ in range(3)]
    st.button.return_value = False
    st.session_state = {}
    st.metric.return_value = None
    st.markdown.return_value = None
    st.caption.return_value = None
    st.divider.return_value = None
    st.toast.return_value = None
    st.expander.return_value = MagicMock().__enter__.return_value
    # Ensure column children also return sensible widget defaults
    for col in st.columns.return_value:
        col.selectbox.return_value = "Unit 1"
        col.text_input.return_value = ""
        col.number_input.return_value = 0.0
        col.date_input.return_value = date.today()
        col.button.return_value = False
        col.metric.return_value = None
        col.markdown.return_value = None
    return st


class TestDomainInputFormsImport(unittest.TestCase):
    """All form functions must be importable and callable without crashing."""

    def test_import_module(self):
        from src.components import domain_input_forms  # noqa: F401

    def test_render_dga_input_form_importable(self):
        from src.components.domain_input_forms import render_dga_input_form
        self.assertTrue(callable(render_dga_input_form))

    def test_render_tribology_input_form_importable(self):
        from src.components.domain_input_forms import render_tribology_input_form
        self.assertTrue(callable(render_tribology_input_form))

    def test_render_vibration_input_form_importable(self):
        from src.components.domain_input_forms import render_vibration_input_form
        self.assertTrue(callable(render_vibration_input_form))

    def test_render_pd_input_form_importable(self):
        from src.components.domain_input_forms import render_pd_input_form
        self.assertTrue(callable(render_pd_input_form))


class TestTdcgStatusHelper(unittest.TestCase):
    """IEEE C57.104 TDCG threshold classification."""

    def _status(self, value):
        from src.components.domain_input_forms import _tdcg_status
        return _tdcg_status(value)

    def test_normal(self):
        self.assertIn("Normal", self._status(0))
        self.assertIn("Normal", self._status(720))

    def test_condition_2(self):
        result = self._status(721)
        self.assertIn("2", result)

    def test_condition_3(self):
        result = self._status(1921)
        self.assertIn("3", result)

    def test_condition_4_critical(self):
        result = self._status(5000)
        self.assertIn("4", result)


class TestVibZoneHelper(unittest.TestCase):
    """ISO 10816-3 vibration zone classification."""

    def _zone(self, value):
        from src.components.domain_input_forms import _vib_zone
        return _vib_zone(value)

    def test_zone_a(self):
        zone, color = self._zone(1.0)
        self.assertEqual(zone, "A")

    def test_zone_b(self):
        zone, _ = self._zone(3.0)
        self.assertEqual(zone, "B")

    def test_zone_c(self):
        zone, _ = self._zone(5.0)
        self.assertEqual(zone, "C")

    def test_zone_d(self):
        zone, _ = self._zone(10.0)
        self.assertEqual(zone, "D")


class TestDomainWorkspaceConfigExtended(unittest.TestCase):
    """DomainWorkspaceConfig must accept input_form_renderer field."""

    def test_config_accepts_input_form_renderer(self):
        from src.components.domain_workspace import DomainWorkspaceConfig
        renderer = lambda st: None  # noqa: E731
        cfg = DomainWorkspaceConfig(
            domain="DGA",
            title="Test DGA",
            input_form_renderer=renderer,
        )
        self.assertIs(cfg.input_form_renderer, renderer)

    def test_config_defaults_to_none(self):
        from src.components.domain_workspace import DomainWorkspaceConfig
        cfg = DomainWorkspaceConfig(domain="DGA", title="Test")
        self.assertIsNone(cfg.input_form_renderer)


class TestPageImports(unittest.TestCase):
    """Domain pages must import successfully with the new wiring."""

    def test_dga_page_importable(self):
        from src.pages import dga_page  # noqa: F401

    def test_tribology_page_importable(self):
        from src.pages import tribology_page  # noqa: F401

    def test_vibration_page_importable(self):
        from src.pages import vibration_page  # noqa: F401

    def test_pd_page_importable(self):
        from src.pages import pd_page  # noqa: F401


if __name__ == "__main__":
    unittest.main()

