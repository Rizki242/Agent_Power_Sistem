"""Tests for speech summary generation, CBM diagnostic verbal synthesis, and plant phonetic expansions."""

import unittest
from pple.api.routers.agents import generate_speech_summary


class TestSpeechSummary(unittest.TestCase):
    def test_structured_cbm_diagnostic_extraction(self):
        diagnostic_text = (
            "### 📋 Evaluasi CBM Multi-Disiplin: **BFP 1A**\n"
            "- **Unit & Sistem**: Unit 1 | Boiler Feed System\n"
            "- **Consolidated Health Index**: **88.5/100** (HEALTHY)\n"
            "- **Primary Failure Mode**: Unbalance & Ketidaksejajaran Sudu Fan\n"
            "- **Prediksi Sisa Umur (RUL)**: **210 hari**\n"
            "- **Rekomendasi CBM**: Jadwalkan re-balancing rotor dan periksa kelonggaran baut pondasi.\n"
        )
        summary = generate_speech_summary(diagnostic_text, matched_equipment="BFP 1A")
        self.assertIn("Laporan CBM untuk BFP 1A", summary)
        self.assertIn("Indeks kesehatan 88.5", summary)
        self.assertIn("HEALTHY", summary)
        self.assertIn("Unbalance", summary)
        self.assertIn("re-balancing rotor", summary)

    def test_latex_math_cleaning(self):
        latex_text = (
            "Hasil inspeksi termal menunjukkan kenaikan suhu \\Delta T = 15.4 degC, "
            "dengan deviasi \\pm 2.1%. Nilai ini \\le batas toleransi \\times 1.5."
        )
        summary = generate_speech_summary(latex_text)
        self.assertNotIn("\\Delta", summary)
        self.assertNotIn("\\pm", summary)
        self.assertNotIn("\\le", summary)
        self.assertIn("Delta T", summary)
        self.assertIn("plus minus", summary)
        self.assertIn("kurang dari sama dengan", summary)

    def test_plant_acronym_phonetic_expansion(self):
        acronym_text = (
            "Pemantauan getaran BFP Unit 1 menghasilkan 4.2 mm/s. "
            "Evaluasi MCSA motor 6.3 kV dan uji DGA trafo menunjukkan kondisi stabil di PLTU Jeranjang."
        )
        summary = generate_speech_summary(acronym_text)
        self.assertIn("milimeter per detik", summary)
        self.assertIn("kilo Volt", summary)
        self.assertIn("Boiler Feed Pump", summary)
        self.assertIn("P L T U", summary)

    def test_empty_input_handling(self):
        self.assertEqual(generate_speech_summary(""), "")
        self.assertEqual(generate_speech_summary(None), "")


if __name__ == "__main__":
    unittest.main()
