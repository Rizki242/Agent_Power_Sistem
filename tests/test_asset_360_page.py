import unittest
from unittest.mock import MagicMock
import pandas as pd

from src.pages.asset_360_page import (
    _build_radar_chart,
    _score_from_status,
    render_asset_360_page,
)


class TestAsset360Page(unittest.TestCase):

    def test_score_from_status(self):
        self.assertEqual(_score_from_status("NORMAL"), 95.0)
        self.assertEqual(_score_from_status("HEALTHY"), 95.0)
        self.assertEqual(_score_from_status("WATCH"), 80.0)
        self.assertEqual(_score_from_status("PREWARNING"), 80.0)
        self.assertEqual(_score_from_status("ALARM"), 60.0)
        self.assertEqual(_score_from_status("WARNING"), 60.0)
        self.assertEqual(_score_from_status("HIGH"), 25.0)
        self.assertEqual(_score_from_status("CRITICAL"), 25.0)
        self.assertEqual(_score_from_status("UNKNOWN"), 75.0)

    def test_build_radar_chart(self):
        scores = {
            "⚡ MCSA (Listrik)": 95.0,
            "〰️ Vibrasi (Mekanik)": 80.0,
            "🌡️ Thermal (Suhu)": 90.0,
            "🛢️ Tribology (Oli)": 85.0,
            "🛡️ Stator & Bearing": 80.0,
        }
        fig = _build_radar_chart(scores, "TEST_EQUIPMENT")
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)
        # Verify closed loop (5 categories + 1 duplicate to close loop = 6 points)
        self.assertEqual(len(fig.data[0].r), 6)
        self.assertEqual(len(fig.data[0].theta), 6)

    def test_render_asset_360_page_smoke(self):
        mock_st = MagicMock()
        mock_st.columns.side_effect = lambda n, **kwargs: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
        mock_st.selectbox.side_effect = lambda label, options, **kwargs: options[0] if options else None

        df_latest_mock = pd.DataFrame([
            {
                "Equipment": "BC 10.1",
                "Status": "Normal",
                "Status_Category": "Normal",
                "Rotorbar": "Normal",
                "Dev Current": 1.5,
                "Dev Voltage": 0.8,
                "Bearing": "Normal",
                "Date": "2026-08-01",
            }
        ])

        # Should execute smoothly without raising exception
        render_asset_360_page(mock_st, df_latest_all=df_latest_mock)
        self.assertTrue(mock_st.subheader.called)


if __name__ == "__main__":
    unittest.main()
