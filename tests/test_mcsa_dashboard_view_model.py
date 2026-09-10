import unittest

import pandas as pd


class MCSADashboardViewModelTests(unittest.TestCase):
    def setUp(self):
        self.latest = pd.DataFrame(
            [
                {
                    "Equipment": "PUMP-A",
                    "Full_Name": "PUMP-A",
                    "Unit_Name": "Unknown",
                    "Voltage_Level": "Unknown",
                    "Parameter": "Load",
                    "Raw_Value": "60",
                    "Value": 60.0,
                    "Unit": "%",
                    "Status": "Normal",
                    "Status_Category": "Normal",
                    "Date": "2026-09-01",
                },
                {
                    "Equipment": "PUMP-B",
                    "Full_Name": "Pump B",
                    "Unit_Name": "UNIT 2",
                    "Voltage_Level": "380/400 V",
                    "Parameter": "Load",
                    "Raw_Value": "45",
                    "Value": 45.0,
                    "Unit": "%",
                    "Status": "Normal",
                    "Status_Category": "Normal",
                    "Date": "2026-09-01",
                },
            ]
        )
        self.master = pd.DataFrame(
            [
                {
                    "Equipment": "PUMP A",
                    "Full_Name": "Main Cooling Pump A",
                    "Unit_Name": "Unit 1",
                    "Voltage_Level": "6.3 kV",
                }
            ]
        )

    def test_selection_model_uses_master_mapping_for_filter_and_label(self):
        from src.components.mcsa_dashboard_view_model import build_equipment_selection_model

        model = build_equipment_selection_model(
            self.latest,
            selected_unit="UNIT 1",
            selected_voltage="6.3 KV",
            selected_equipment=[],
            equipment_master=self.master,
            master_norm_to_unit={"PUMPA": "UNIT 1"},
            master_norm_to_voltage={"PUMPA": "6.3 KV"},
        )

        self.assertEqual(model.detail_df["Equipment"].unique().tolist(), ["PUMP-A"])
        self.assertEqual(model.display_map, {"Main Cooling Pump A (PUMP-A)": "PUMP-A"})
        self.assertEqual(model.master_by_norm["PUMPA"]["Unit_Name"], "Unit 1")

    def test_detail_model_adds_latest_missing_thd_and_resolves_metadata(self):
        from src.components.mcsa_dashboard_view_model import (
            build_equipment_detail_model,
            build_equipment_selection_model,
        )

        history = pd.concat(
            [
                self.latest,
                pd.DataFrame(
                    [
                        {
                            "Equipment": "PUMP-A",
                            "Full_Name": "PUMP-A",
                            "Unit_Name": "Unknown",
                            "Voltage_Level": "Unknown",
                            "Parameter": "THD Voltage %",
                            "Raw_Value": "4.5",
                            "Value": 4.5,
                            "Unit": "%",
                            "Status": "Normal",
                            "Status_Category": "Normal",
                            "Date": "2026-08-01",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        selection = build_equipment_selection_model(
            self.latest,
            selected_unit="All",
            selected_voltage="All",
            selected_equipment=[],
            equipment_master=self.master,
            master_norm_to_unit={"PUMPA": "UNIT 1"},
            master_norm_to_voltage={"PUMPA": "6.3 KV"},
        )

        model = build_equipment_detail_model(
            history=history,
            detail_df=selection.detail_df,
            selected_equipment="PUMP-A",
            master_by_norm=selection.master_by_norm,
            master_norm_to_unit={"PUMPA": "UNIT 1"},
            master_norm_to_voltage={"PUMPA": "6.3 KV"},
            status_by_norm={"PUMPA": "Normal"},
        )

        self.assertEqual(model.full_name, "Main Cooling Pump A")
        self.assertEqual(model.unit_name, "UNIT 1")
        self.assertEqual(model.voltage_level, "6.3 KV")
        thd_row = model.table_df[model.table_df["Parameter"] == "THD Voltage %"].iloc[0]
        self.assertEqual(thd_row["Nilai"], "4.5")
        self.assertEqual(thd_row["Unit"], "%")
        self.assertIn("score", model.health_summary)
        self.assertEqual(model.condition_class, "unknown")


if __name__ == "__main__":
    unittest.main()
