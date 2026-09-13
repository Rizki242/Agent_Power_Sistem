import unittest
import pandas as pd

from src.chatbot import MCSAChatbot


class ChatbotMultiDomainTests(unittest.TestCase):
    def setUp(self):
        self.df_latest = pd.DataFrame([
            {"Equipment": "BC 10.1", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "BC 10.1", "Parameter": "Load", "Raw_Value": "78", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "C3WP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Date": "2026-05-01", "Unit_Name": "UNIT 3", "Voltage_Level": "6.3 KV"},
            {"Equipment": "C3WP 1A", "Parameter": "Load", "Raw_Value": "85", "Date": "2026-05-01", "Unit_Name": "UNIT 3", "Voltage_Level": "6.3 KV"},
        ])
        self.df_all = self.df_latest.copy()
        self.bot = MCSAChatbot(self.df_latest, df_all=self.df_all)

    def test_correlation_general(self):
        resp = self.bot.process_query("Korelasi vibrasi dan arus")
        self.assertIn("Korelasi Multi-Domain", resp)
        self.assertIn("Unbalance Mekanik", resp)
        self.assertIn("Air Gap Eccentricity", resp)

    def test_correlation_equipment(self):
        resp = self.bot.process_query("Korelasi vibrasi dan arus BC 10.1")
        self.assertIn("BC 10.1", resp)
        self.assertIn("Elektrikal (MCSA)", resp)
        self.assertIn("Mekanikal (Vibrasi)", resp)
        self.assertIn("Thermal (IRT)", resp)
        self.assertIn("Pelumas (Tribology)", resp)

    def test_domain_vibration_query(self):
        resp = self.bot.process_query("Vibrasi BC 10.1")
        self.assertIn("BC 10.1", resp)
        self.assertTrue("ISO 10816" in resp or "Vibrasi" in resp)

    def test_domain_thermal_query(self):
        resp = self.bot.process_query("Suhu dan thermography BC 10.1")
        self.assertIn("BC 10.1", resp)
        self.assertTrue("IRT" in resp or "Suhu" in resp)

    def test_domain_tribology_query(self):
        resp = self.bot.process_query("Status pelumas dan oli")
        # Tanpa equipment spesifik, tetap tidak error
        self.assertTrue(len(resp) > 20)

    def test_domain_dga_query(self):
        resp = self.bot.process_query("Standar DGA trafo")
        self.assertIn("IEEE C57.104", resp)
        self.assertIn("Duval Triangle", resp)
        self.assertIn("C2H2", resp)

    def test_vibration_alarm_list(self):
        resp = self.bot.get_vibration_alarm_list()
        self.assertTrue("Vibrasi" in resp or "Normal" in resp)

    def test_status_backward_compatibility(self):
        resp = self.bot.process_query("Status BC 10.1")
        self.assertIn("BC 10.1", resp)
        self.assertIn("NORMAL", resp)
        self.assertIn("78", resp)
        self.assertNotIn("nan", resp.lower())
        self.assertNotIn("none", resp.lower())


if __name__ == "__main__":
    unittest.main()

