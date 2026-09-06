import os
import shutil
import tempfile
import unittest
from datetime import date
from unittest import mock

from streamlit.testing.v1 import AppTest

from src import domain_measurements as dm
from src.components.domain_workspace import (
    PERIOD_PRESETS,
    DomainWorkspaceConfig,
    render_domain_workspace,
    resolve_preset_range,
)


class WorkspaceTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="pple_ws_")
        self._env = mock.patch.dict(os.environ, {"MCSA_DATA_DIR": self.root})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        shutil.rmtree(self.root, ignore_errors=True)

    def _seed(self):
        dm.append_measurements("DGA", [
            {"equipment": "TRF-1", "unit_name": "UNIT 1", "test_date": "2026-02-01", "parameter": "h2", "value": 20, "uom": "ppm"},
            {"equipment": "TRF-1", "unit_name": "UNIT 1", "test_date": "2026-04-01", "parameter": "h2", "value": 90, "uom": "ppm"},
        ])


class PresetRangeTests(WorkspaceTestCase):
    def test_mingguan_is_a_rolling_seven_day_window_on_the_latest_data(self):
        start, end = resolve_preset_range("Mingguan", date(2026, 1, 1), date(2026, 4, 10))
        self.assertEqual(end, date(2026, 4, 10))
        self.assertEqual(start, date(2026, 4, 4))

    def test_presets_are_anchored_on_data_not_today(self):
        # "Kondisi saat Ini" must mean the month of the newest reading, so a
        # dataset that ends months ago still resolves to a non-empty window.
        start, end = resolve_preset_range("Kondisi saat Ini", date(2024, 1, 1), date(2026, 4, 10))
        self.assertEqual(start, date(2026, 4, 1))
        self.assertEqual(end, date(2026, 4, 10))

    def test_every_offered_preset_resolves_inside_the_data_range(self):
        min_date, max_date = date(2024, 1, 10), date(2026, 4, 20)
        for preset in PERIOD_PRESETS:
            if preset == "Kustom":
                continue
            start, end = resolve_preset_range(preset, min_date, max_date)
            self.assertGreaterEqual(start, min_date, preset)
            self.assertLessEqual(end, max_date, preset)
            self.assertLessEqual(start, end, preset)

    def test_semua_covers_the_whole_range(self):
        self.assertEqual(
            resolve_preset_range("Semua", date(2024, 1, 10), date(2026, 4, 20)),
            (date(2024, 1, 10), date(2026, 4, 20)),
        )


def _run_workspace(domain="DGA", title="DGA"):
    """Render the workspace headlessly for one domain."""
    def script():
        import streamlit as st

        from src.agents.specialist_agents import DGAAgent
        from src.components.domain_workspace import DomainWorkspaceConfig, render_domain_workspace

        render_domain_workspace(st, DomainWorkspaceConfig(
            domain="DGA", title="DGA", subtitle="uji", agent_factory=DGAAgent,
        ))

    return AppTest.from_function(script, default_timeout=30).run()


class WorkspaceRenderTests(WorkspaceTestCase):
    def test_renders_five_tabs_without_error_on_empty_store(self):
        app = _run_workspace()
        self.assertFalse(app.exception, getattr(app, "exception", None))
        labels = [tab.label for tab in app.tabs] if hasattr(app, "tabs") else []
        for expected in ("Ringkasan", "Data & Upload", "Tren & Riwayat", "Diagnosa", "Laporan"):
            self.assertIn(expected, labels)

    def test_empty_store_guides_user_to_upload_instead_of_crashing(self):
        app = _run_workspace()
        self.assertFalse(app.exception)
        info_text = " ".join(item.value for item in app.info)
        self.assertIn("Data & Upload", info_text)

    def test_template_download_button_is_offered(self):
        app = _run_workspace()
        self.assertFalse(app.exception)
        labels = [button.label for button in app.get("download_button")]
        self.assertIn("Unduh template CSV", labels)

    def test_renders_with_data_present(self):
        self._seed()
        app = _run_workspace()
        self.assertFalse(app.exception, getattr(app, "exception", None))
        metric_labels = [metric.label for metric in app.get("metric")]
        self.assertIn("Record tersimpan", metric_labels)


class WorkspaceConfigTests(WorkspaceTestCase):
    def test_config_defaults_are_safe(self):
        config = DomainWorkspaceConfig(domain="PD", title="Partial Discharge")
        self.assertIsNone(config.agent_factory)
        self.assertEqual(config.metric_labels, {})
        self.assertEqual(config.disclaimer, "")


class AllDomainPagesUseTheWorkspaceTests(WorkspaceTestCase):
    """Every domain page must route through the shared workspace, otherwise
    that domain silently loses upload / period filter / reports again."""

    PAGES = {
        "VIBRASI": ("src.pages.vibration_page", "render_vibration_page"),
        "DGA": ("src.pages.dga_page", "render_dga_page"),
        "TRIBOLOGY": ("src.pages.tribology_page", "render_tribology_page"),
        "THERMAL": ("src.pages.thermal_page", "render_thermal_page"),
        "PD": ("src.pages.pd_page", "render_pd_page"),
    }

    def _captured_config(self, module_name, function_name):
        import importlib

        module = importlib.import_module(module_name)
        captured = {}

        def fake_render(st, config):
            captured["config"] = config

        original = module.render_domain_workspace
        module.render_domain_workspace = fake_render
        try:
            getattr(module, function_name)(object())
        finally:
            module.render_domain_workspace = original
        return captured["config"]

    def test_every_domain_page_renders_the_workspace(self):
        for domain, (module_name, function_name) in self.PAGES.items():
            config = self._captured_config(module_name, function_name)
            self.assertEqual(config.domain, domain, module_name)
            self.assertTrue(config.title, module_name)

    def test_every_domain_page_supplies_an_agent_and_labels(self):
        for domain, (module_name, function_name) in self.PAGES.items():
            config = self._captured_config(module_name, function_name)
            self.assertIsNotNone(config.agent_factory, f"{domain} tanpa agent")
            self.assertTrue(config.metric_labels, f"{domain} tanpa metric_labels")

    def test_metric_labels_match_what_the_agent_actually_returns(self):
        # render_agent_result maps result["metrics"] keys through these
        # labels; a mismatch shows raw keys to the engineer instead of a
        # readable parameter name.
        probes = {
            "VIBRASI": {"overall_rms": 3.0},
            "DGA": {"h2": 40, "ch4": 30, "c2h2": 2, "c2h4": 20, "c2h6": 15, "co": 300, "co2": 2500},
            "TRIBOLOGY": {"viscosity_40c": 44, "tan": 0.3, "water_ppm": 120, "fe_ppm": 30, "cu_ppm": 8},
            "THERMAL": {"bearing_temp": 78, "winding_temp": 95, "ambient_temp": 33, "delta_t_phase": 12},
            "PD": {"pulse_magnitude_pc": 800, "nqn": 40, "pd_type": "Internal Void", "phase_clustering_deg": 45},
        }
        for domain, (module_name, function_name) in self.PAGES.items():
            config = self._captured_config(module_name, function_name)
            result = config.agent_factory().evaluate("X", probes[domain])
            unlabelled = set(result["metrics"]) - set(config.metric_labels)
            self.assertEqual(unlabelled, set(), f"{domain}: metrik tanpa label {unlabelled}")

    def test_every_domain_page_preserves_its_legacy_summary_view(self):
        for domain, (module_name, function_name) in self.PAGES.items():
            config = self._captured_config(module_name, function_name)
            self.assertIsNotNone(config.summary_renderer, f"{domain} kehilangan tampilan lama")

    def test_synthetic_data_domains_keep_their_disclaimer(self):
        # DGA/Tribology/PD run on example data; that warning must not be lost
        # in the move to the shared shell.
        for domain in ("DGA", "TRIBOLOGY", "PD"):
            module_name, function_name = self.PAGES[domain]
            config = self._captured_config(module_name, function_name)
            self.assertIn("Data Contoh", config.disclaimer, domain)


if __name__ == "__main__":
    unittest.main()
