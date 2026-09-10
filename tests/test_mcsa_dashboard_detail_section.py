import unittest
from unittest.mock import MagicMock
import pandas as pd

from src.components.mcsa_dashboard_detail_section import (
    _style_status_cell,
    render_equipment_detail_section,
)


class TestMCSADashboardDetailSection(unittest.TestCase):
    def test_style_status_cell_known_and_unknown(self):
        normal_style = _style_status_cell("Normal")
        self.assertIn("background-color:", normal_style)
        self.assertIn("color:", normal_style)

        alarm_style = _style_status_cell("Alarm")
        self.assertIn("background-color:", alarm_style)

        unknown_style = _style_status_cell("UnknownStatus")
        self.assertIn("background-color:", unknown_style)

    def test_render_empty_equipment_shows_warning(self):
        st = MagicMock()
        st.session_state = {}

        empty_df = pd.DataFrame(columns=["Equipment", "Unit_Name", "Voltage_Level"])

        render_equipment_detail_section(
            st=st,
            df=empty_df,
            df_latest=empty_df,
            df_latest_all=empty_df,
            sel_unit="All",
            sel_volt="All",
            sel_equipment=[],
            eq_master_df=pd.DataFrame(),
            master_norm_to_unit={},
            master_norm_to_volt={},
            status_by_norm={},
            date_start="2026-01-01",
            date_end="2026-09-01",
        )

        st.subheader.assert_called_with("Data Detail")
        st.warning.assert_called_with("Tidak ada equipment yang sesuai filter.")


if __name__ == "__main__":
    unittest.main()
