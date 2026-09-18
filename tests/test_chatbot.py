import unittest
import warnings
import pandas as pd

warnings.filterwarnings("ignore", category=DeprecationWarning)

from src.chatbot import MCSAChatbot


class ChatbotTests(unittest.TestCase):
    def setUp(self):
        self.df_latest = pd.DataFrame([
            {"Equipment": "BC 10.1", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "BC 10.1", "Parameter": "Load", "Raw_Value": "75", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "C3WP 1A", "Parameter": "Kondisi", "Raw_Value": "Alarm", "Date": "2026-05-01", "Unit_Name": "UNIT 3", "Voltage_Level": "6.3 KV"},
            {"Equipment": "C3WP 1A", "Parameter": "THD Voltage %", "Raw_Value": "6.5", "Date": "2026-05-01", "Unit_Name": "UNIT 3", "Voltage_Level": "6.3 KV"},
            {"Equipment": "CRUSHER 1", "Parameter": "Kondisi", "Raw_Value": "High", "Date": "2026-05-01", "Unit_Name": "UNIT COMMON", "Voltage_Level": "380/400 V"},
        ])
        self.df_all = self.df_latest.copy()
        self.bot = MCSAChatbot(self.df_latest, df_all=self.df_all)

    def test_fuzzy_match_equipment(self):
        # Spacing / punctuation variations
        self.assertEqual(self.bot.match_equipment("status bc101"), "BC 10.1")
        self.assertEqual(self.bot.match_equipment("bagaimana motor BC 10.1 hari ini?"), "BC 10.1")
        self.assertEqual(self.bot.match_equipment("cek kondisi c3wp1a"), "C3WP 1A")
        self.assertEqual(self.bot.match_equipment("crusher 1 rusak"), "CRUSHER 1")

    def test_process_query_alarm_list(self):
        response = self.bot.process_query("List equipment yang alarm")
        self.assertIn("C3WP 1A", response)
        self.assertIn("CRUSHER 1", response)
        self.assertNotIn("BC 10.1", response)

    def test_process_query_specific_equipment(self):
        response = self.bot.process_query("Status BC 10.1")
        self.assertIn("BC 10.1", response)
        self.assertIn("NORMAL", response)
        self.assertIn("75", response)

    def test_process_query_hides_nan_values(self):
        df_latest = pd.DataFrame([
            {"Equipment": "BC 20.1", "Parameter": "Kondisi", "Raw_Value": "Normal", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "BC 20.1", "Parameter": "Load", "Raw_Value": "nan", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            {"Equipment": "BC 20.1", "Parameter": "Bearing", "Raw_Value": "Normal", "Date": "2026-05-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
        ])
        df_all = pd.concat([
            pd.DataFrame([
                {"Equipment": "BC 20.1", "Parameter": "Load", "Raw_Value": "nan", "Date": "2026-03-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
                {"Equipment": "BC 20.1", "Parameter": "Load", "Raw_Value": "None", "Date": "2026-04-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
                {"Equipment": "BC 20.1", "Parameter": "Bearing", "Raw_Value": "nan", "Date": "2026-03-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
                {"Equipment": "BC 20.1", "Parameter": "Bearing", "Raw_Value": "Normal", "Date": "2026-04-01", "Unit_Name": "UNIT 1", "Voltage_Level": "380/400 V"},
            ]),
            df_latest,
        ], ignore_index=True)

        response = MCSAChatbot(df_latest, df_all=df_all).process_query("Status BC 20.1")

        self.assertNotIn("nan", response.lower())
        self.assertNotIn("none", response.lower())
        # Parameter yang benar-benar terukur tetap tampil.
        self.assertIn("Bearing", response)

    def test_process_query_knowledge_sop(self):
        response = self.bot.process_query("bagaimana SOP pengukuran ATPOL?")
        self.assertIn("Referensi", response)
        self.assertTrue(len(response) > 50)


if __name__ == "__main__":
    unittest.main()
