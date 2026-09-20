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

    def test_process_query_dga_explanation_not_fleet_dump(self):
        # "jelaskan"/"apa itu" pertanyaan definisi DGA harus menjawab rujukan
        # standar (IEEE C57.104 / Duval Triangle), bukan dump status 25 trafo.
        for query in ["jelaskan tentang DGA", "jelaskan tentang apa itu duval triangle"]:
            response = self.bot.process_query(query)
            self.assertIn("IEEE C57.104", response)
            self.assertNotIn("Armada Transformer", response)

    def test_process_query_knowledge_sop(self):
        response = self.bot.process_query("bagaimana SOP pengukuran ATPOL?")
        self.assertIn("Referensi", response)
        self.assertTrue(len(response) > 50)

    def test_process_query_natural_persona_non_technical(self):
        # 1. Greeting
        res_greet = self.bot.process_query("Halo selamat pagi!")
        self.assertIn("Agent CBM Learning PLTU Jeranjang", res_greet)
        self.assertIn("PLTU Jeranjang", res_greet)

        # 2. Identity / persona
        res_who = self.bot.process_query("Siapa kamu sebenarnya?")
        self.assertIn("Agent CBM Learning PLTU Jeranjang", res_who)
        self.assertIn("Condition-Based Maintenance", res_who)

        # 3. Small talk / how are you
        res_talk = self.bot.process_query("Lagi ngapain sekarang?")
        self.assertIn("Agent CBM Learning PLTU Jeranjang", res_talk)

        # 4. Gratitude
        res_thanks = self.bot.process_query("Terima kasih banyak mantap sekali!")
        self.assertIn("Agent CBM Learning PLTU Jeranjang", res_thanks)

        # 5. Casual off-topic (not an error message)
        res_casual = self.bot.process_query("Bisa ceritakan hal menarik?")
        self.assertIn("Agent CBM Learning PLTU Jeranjang", res_casual)
        self.assertNotIn("belum menemukan data spesifik", res_casual)

    def test_process_query_expert_conceptual_answers(self):
        # Misalignment
        res_mis = self.bot.process_query("jelaskan tentang misalignment pada poros mesin")
        self.assertIn("Misalignment", res_mis)
        self.assertIn("2\\times", res_mis)
        self.assertIn("ISO", res_mis)

        # Bearing defect
        res_brg = self.bot.process_query("apa saja tahapan kerusakan bearing?")
        self.assertIn("BPFO", res_brg)
        self.assertIn("BPFI", res_brg)
        self.assertIn("ISO 15243", res_brg)

        # Cavitation
        res_cav = self.bot.process_query("apa penyebab kavitasi pada pompa?")
        self.assertIn("Kavitasi", res_cav)
        self.assertIn("NPSH", res_cav)
        self.assertIn("BFP", res_cav)

        # Air Gap Eccentricity
        res_gap = self.bot.process_query("apa itu eksentrisitas celah udara?")
        self.assertIn("Air Gap Eccentricity", res_gap)
        self.assertIn("f_{ecc}", res_gap)

        # Mechanical looseness
        res_loos = self.bot.process_query("jelaskan tipe kelonggaran mekanikal looseness")
        self.assertIn("Mechanical Looseness", res_loos)
        self.assertIn("Tipe A", res_loos)

        # Thermal Delta-T
        res_therm = self.bot.process_query("bagaimana evaluasi delta-t pada inspeksi thermal?")
        self.assertIn("Delta-T", res_therm)
        self.assertIn("ISO 18434-1", res_therm)

        # RUL & Health Index
        res_rul = self.bot.process_query("apa itu health index dan bagaimana cara menghitung RUL?")
        self.assertIn("Health Index", res_rul)
        self.assertIn("RUL", res_rul)
        self.assertIn("Weibull", res_rul)

        # Rotor Bar & THD
        res_rb = self.bot.process_query("bagaimana cara deteksi broken rotor bar?")
        self.assertIn("Rotor Bar", res_rb)
        self.assertIn("EPRI", res_rb)

        res_thd = self.bot.process_query("apa batas standar THD tegangan?")
        self.assertIn("THD", res_thd)
        self.assertIn("IEEE 519", res_thd)


if __name__ == "__main__":
    unittest.main()
