import unittest
from unittest.mock import MagicMock
import pandas as pd

from src.template_generator import (
    TEMPLATES,
    get_template_csv,
    validate_batch_dataframe,
)
from src.pages.data_ingestion_hub_page import (
    _render_live_chart,
    render_data_ingestion_hub_page,
)


class TestDataIngestionHub(unittest.TestCase):

    def test_get_template_csv_all_domains(self):
        domains = ["MCSA", "VIBRASI", "THERMAL", "TRIBOLOGY", "DGA"]
        for domain in domains:
            csv_str = get_template_csv(domain)
            self.assertIsInstance(csv_str, str)
            self.assertIn("Equipment", csv_str)
            self.assertIn("Date", csv_str)
            reqs = TEMPLATES[domain]["required"]
            for col in reqs:
                self.assertIn(col, csv_str)

    def test_validate_batch_dataframe_valid(self):
        df_valid_vib = pd.DataFrame([
            {"Equipment": "BC 10.1", "Date": "2026-08-01", "Velocity_RMS": 2.5}
        ])
        res = validate_batch_dataframe("VIBRASI", df_valid_vib)
        self.assertTrue(res["valid"])
        self.assertEqual(len(res["missing_columns"]), 0)
        self.assertEqual(res["row_count"], 1)

    def test_validate_batch_dataframe_missing_column(self):
        df_invalid = pd.DataFrame([
            {"Equipment": "BC 10.1", "Date": "2026-08-01"}
        ])
        # VIBRASI requires Velocity_RMS
        res = validate_batch_dataframe("VIBRASI", df_invalid)
        self.assertFalse(res["valid"])
        self.assertIn("Velocity_RMS", res["missing_columns"])

    def test_render_live_chart(self):
        records = [
            {"time": "10:00:01", "val": 2.1, "status": "Normal"},
            {"time": "10:00:02", "val": 4.8, "status": "Alarm"},
            {"time": "10:00:03", "val": 7.5, "status": "High"},
        ]
        fig = _render_live_chart(records, "Velocity RMS (mm/s)")
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(len(fig.data[0].x), 3)

    def test_render_data_ingestion_hub_page_smoke(self):
        mock_st = MagicMock()
        mock_st.tabs.return_value = [MagicMock(), MagicMock()]
        mock_st.columns.side_effect = lambda n, **kw: [MagicMock() for _ in range(n if isinstance(n, int) else len(n))]
        mock_st.selectbox.side_effect = lambda label, options, **kw: options[0] if options else None
        mock_st.session_state = {}

        render_data_ingestion_hub_page(mock_st)
        self.assertTrue(mock_st.subheader.called)


if __name__ == "__main__":
    unittest.main()
