"""Tes memori percakapan chat: konteks giliran sebelumnya, carry-over aset, dan
pengayaan kata kunci retrieval untuk pertanyaan lanjutan.

Semua tes di sini murni lokal (SQLite memori agent + fungsi rule-based), tidak
memanggil provider LLM mana pun.
"""

import unittest

from pple.api.routers.agents import build_conversation_context, is_follow_up_question
from src.agent_memory import create_chat_session, delete_chat_session, save_session_message
from src.llm_assistant import MCSALLMAssistant, build_retrieval_query


class ChatContextTests(unittest.TestCase):
    def setUp(self):
        self.session_id = create_chat_session(title="Tes Konteks", session_type="chat")

    def tearDown(self):
        try:
            delete_chat_session(self.session_id)
        except Exception:
            pass

    def test_context_kosong_tanpa_sesi(self):
        context, equipment = build_conversation_context(None)
        self.assertEqual(context, "")
        self.assertIsNone(equipment)

    def test_context_merangkum_giliran_dan_membawa_aset(self):
        save_session_message(self.session_id, "user", "Bagaimana kondisi motor CWP 1A?")
        save_session_message(
            self.session_id,
            "assistant",
            "Sideband rotor bar CWP 1A berada pada -48 dB (alert).",
            payload={"matched_equipment": "CWP 1A"},
        )

        context, equipment = build_conversation_context(self.session_id)

        self.assertIn("User: Bagaimana kondisi motor CWP 1A?", context)
        self.assertIn("Agent: Sideband rotor bar CWP 1A", context)
        self.assertEqual(equipment, "CWP 1A")

    def test_context_dibatasi_jumlah_giliran(self):
        for i in range(20):
            save_session_message(self.session_id, "user", f"pertanyaan ke-{i}")
            save_session_message(self.session_id, "assistant", f"jawaban ke-{i}")

        context, _ = build_conversation_context(self.session_id)

        self.assertNotIn("pertanyaan ke-0", context)
        self.assertIn("pertanyaan ke-19", context)

    def test_deteksi_pertanyaan_lanjutan(self):
        self.assertTrue(is_follow_up_question("kenapa bisa begitu?"))
        self.assertTrue(is_follow_up_question("bagaimana trennya?"))
        self.assertTrue(is_follow_up_question("kondisinya sekarang"))
        self.assertFalse(is_follow_up_question(""))
        self.assertFalse(
            is_follow_up_question(
                "Tampilkan seluruh daftar peralatan berstatus alarm pada Unit 1 beserta "
                "nilai sideband, unbalance arus, dan rekomendasi pemeliharaan lengkapnya"
            )
        )


class RetrievalQueryTests(unittest.TestCase):
    def test_pertanyaan_pendek_diperkaya_konteks(self):
        query = build_retrieval_query(
            "kenapa?",
            "User: Bagaimana kondisi rotor bar BFP 1A?\nAgent: Sideband -45 dB kategori kritis.",
        )
        self.assertIn("kenapa?", query)
        self.assertIn("rotor bar BFP 1A", query)

    def test_pertanyaan_panjang_tidak_diubah(self):
        question = (
            "Jelaskan batas evaluasi sideband rotor bar menurut EPRI beserta dampaknya "
            "pada motor 6.3 kV di PLTU Jeranjang"
        )
        self.assertEqual(build_retrieval_query(question, "User: halo\nAgent: halo"), question)

    def test_tanpa_konteks_query_apa_adanya(self):
        self.assertEqual(build_retrieval_query("kenapa?", ""), "kenapa?")


class FollowUpPromptTests(unittest.TestCase):
    """Pertanyaan lanjutan pendek harus mewarisi mode teknis dari percakapan."""

    def setUp(self):
        self.assistant = MCSALLMAssistant(enabled=False, provider="gemini", api_key=None)

    def _prompt(self, question, conversation_context=""):
        return self.assistant._build_rag_prompt(
            question=question,
            rule_answer="",
            mcsa_context="",
            history_context="",
            knowledge_context="",
            conversation_context=conversation_context,
        )

    def test_lanjutan_teknis_memakai_prompt_engineer(self):
        prompt = self._prompt(
            "kenapa bisa begitu?",
            "User: Bagaimana sideband rotor bar BFP 1A?\nAgent: Nilainya -45 dB (kritis).",
        )
        self.assertIn("Reliability Engineer", prompt)
        self.assertIn("RIWAYAT PERCAKAPAN SESI INI", prompt)

    def test_sapaan_tetap_memakai_prompt_natural(self):
        prompt = self._prompt("halo", "")
        self.assertIn("NATURAL", prompt.upper())

    def test_konteks_disisipkan_pada_prompt_natural(self):
        prompt = self._prompt("terima kasih", "User: halo\nAgent: Halo, ada yang bisa dibantu?")
        self.assertIn("RIWAYAT PERCAKAPAN SEBELUMNYA", prompt)


if __name__ == "__main__":
    unittest.main()
