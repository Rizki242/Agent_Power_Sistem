import unittest
from src.dga_data import (
    calculate_dga_diagnosis,
    calculate_duval_pentagon,
    calculate_rogers_ratios,
    calculate_key_gas_profile,
    calculate_gas_trend_prediction,
    get_dga_transformer_detail,
    get_dga_summary,
)


class TestDGAMultiMethods(unittest.TestCase):
    def test_duval_pentagon_pd(self):
        gases = {"H2": 500.0, "CH4": 20.0, "C2H6": 10.0, "C2H4": 5.0, "C2H2": 1.0}
        res = calculate_duval_pentagon(gases)
        self.assertEqual(res["zone"], "PD")
        self.assertIn("percentages", res)
        self.assertGreater(res["percentages"]["H2"], 80.0)

    def test_duval_pentagon_arcing_d2(self):
        gases = {"H2": 50.0, "CH4": 30.0, "C2H6": 10.0, "C2H4": 40.0, "C2H2": 200.0}
        res = calculate_duval_pentagon(gases)
        self.assertEqual(res["zone"], "D2")
        self.assertIn("D2", res["zone_label"])

    def test_duval_pentagon_thermal_t3(self):
        gases = {"H2": 20.0, "CH4": 30.0, "C2H6": 15.0, "C2H4": 300.0, "C2H2": 5.0}
        res = calculate_duval_pentagon(gases)
        self.assertEqual(res["zone"], "T3")

    def test_rogers_ratios_normal(self):
        gases = {"H2": 100.0, "CH4": 50.0, "C2H6": 60.0, "C2H4": 10.0, "C2H2": 0.2, "CO": 200.0, "CO2": 1800.0}
        res = calculate_rogers_ratios(gases)
        self.assertEqual(res["diagnosis"], "Normal Deterioration")
        self.assertEqual(res["severity"], "NORMAL")
        self.assertAlmostEqual(res["co2_co_ratio"], 9.0, places=1)

    def test_rogers_ratios_arcing(self):
        gases = {"H2": 80.0, "CH4": 40.0, "C2H6": 20.0, "C2H4": 30.0, "C2H2": 60.0, "CO": 200.0, "CO2": 1000.0}
        res = calculate_rogers_ratios(gases)
        self.assertIn(res["severity"], ["HIGH", "WARNING"])

    def test_key_gas_profile_thermal_oil(self):
        gases = {"H2": 15.0, "CH4": 40.0, "C2H6": 40.0, "C2H4": 200.0, "C2H2": 2.0, "CO": 50.0}
        res = calculate_key_gas_profile(gases)
        self.assertEqual(res["dominant_gas"], "C2H4")
        self.assertEqual(res["fault_type"], "Thermal Oil Degradation")

    def test_key_gas_profile_cellulose(self):
        gases = {"H2": 20.0, "CH4": 15.0, "C2H6": 10.0, "C2H4": 10.0, "C2H2": 0.5, "CO": 800.0}
        res = calculate_key_gas_profile(gases)
        self.assertEqual(res["dominant_gas"], "CO")
        self.assertEqual(res["fault_type"], "Thermal Cellulose / Paper Overheating")

    def test_gas_trend_prediction(self):
        history = [
            {"date": "2026-01-01", "tdcg": 100.0, "H2": 10.0, "CH4": 20.0, "C2H6": 10.0, "C2H4": 10.0, "C2H2": 0.0, "CO": 50.0, "CO2": 500.0},
            {"date": "2026-04-01", "tdcg": 190.0, "H2": 20.0, "CH4": 40.0, "C2H6": 20.0, "C2H4": 20.0, "C2H2": 0.5, "CO": 90.0, "CO2": 600.0},
        ]
        current_gases = {"H2": 20.0, "CH4": 40.0, "C2H6": 20.0, "C2H4": 20.0, "C2H2": 0.5, "CO": 90.0, "CO2": 600.0}
        res = calculate_gas_trend_prediction(history, current_gases)
        self.assertIn("forecast_3m", res)
        self.assertIn("forecast_6m", res)
        self.assertIn("forecast_12m", res)
        self.assertIn("rate_ppm_day", res)
        self.assertIn("rate_status", res)
        self.assertGreater(res["forecast_3m"]["TDCG"], current_gases["H2"])

    def test_transformer_detail_integration(self):
        d = get_dga_transformer_detail("TRF-001")
        self.assertIsNotNone(d)
        self.assertIn("diagnosis", d)
        self.assertIn("pentagon", d["diagnosis"])
        self.assertIn("rogers", d["diagnosis"])
        self.assertIn("key_gas", d["diagnosis"])
        self.assertIn("prediction", d)


if __name__ == "__main__":
    unittest.main()

