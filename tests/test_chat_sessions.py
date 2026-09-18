import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app
import src.agent_memory as agent_mem
from pple.api.routers.agents import generate_speech_summary


class TestChatSessionsAndVoice(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Paksa jalur rule-based: tanpa API key, baik PPLEMasterAgent maupun
        # endpoint /api/agent/chat tidak pernah memanggil provider LLM
        # (Gemini/Groq/...), sehingga test tidak menggantung di mesin tanpa
        # akses jaringan. Pola sama dengan
        # tests/test_master_agent.py::test_process_query_rule_fallback.
        for target in (
            "src.agents.master_agent.resolve_provider_key",
            "pple.api.routers.agents.resolve_provider_key",
        ):
            patcher = patch(target, return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_generate_speech_summary(self):
        markdown_text = """### Status CWP 1A: ALARM
- Suhu bearing: 85°C (tinggi)
- Nilai getaran: 4.5 mm/s sesuai ISO 10816-3.
| Param | Nilai |
| --- | --- |
| TDCG | 1200 ppm |
Rekomendasi tindak lanjut segera lakukan pemeriksaan pelumasan."""
        speech = generate_speech_summary(markdown_text, matched_equipment="CWP 1A")
        self.assertNotIn("###", speech)
        self.assertNotIn("|", speech)
        self.assertIn("milimeter per detik", speech)
        self.assertIn("derajat Celcius", speech)

    def test_chat_session_lifecycle(self):
        # 1. Create a new session
        create_res = self.client.post(
            "/api/agent/chat/sessions",
            json={"title": "Inspeksi Vibrasi BFP 1A", "session_type": "chat"},
        )
        self.assertEqual(create_res.status_code, 200)
        data = create_res.json()
        session_id = data["session_id"]
        self.assertTrue(session_id.startswith("ses-"))

        # 2. List sessions
        list_res = self.client.get("/api/agent/chat/sessions")
        self.assertEqual(list_res.status_code, 200)
        sessions = list_res.json().get("sessions", [])
        found = any(s["session_id"] == session_id for s in sessions)
        self.assertTrue(found)

        # 3. Send message within this session (via voice)
        chat_res = self.client.post(
            "/api/agent/chat",
            json={
                "message": "Status BFP 1A",
                "session_id": session_id,
                "source": "VOICE",
            },
        )
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertIn("reply", chat_data)
        self.assertIn("summary_for_speech", chat_data)
        self.assertEqual(chat_data["session_id"], session_id)

        # 4. Retrieve messages for this session
        msg_res = self.client.get(f"/api/agent/chat/sessions/{session_id}")
        self.assertEqual(msg_res.status_code, 200)
        messages = msg_res.json().get("messages", [])
        self.assertGreaterEqual(len(messages), 2)  # User + Assistant

        # 5. Delete session
        del_res = self.client.delete(f"/api/agent/chat/sessions/{session_id}")
        self.assertEqual(del_res.status_code, 200)

        # Confirm deletion
        msg_res_after = self.client.get(f"/api/agent/chat/sessions/{session_id}")
        self.assertEqual(msg_res_after.json().get("messages", []), [])

    def test_safety_guardrail_voice_interception(self):
        # High-risk command should be blocked and have safety speech warning
        chat_res = self.client.post(
            "/api/agent/chat",
            json={
                "message": "tolong trip boiler unit 1 sekarang juga",
                "source": "VOICE",
            },
        )
        self.assertEqual(chat_res.status_code, 200)
        data = chat_res.json()
        self.assertTrue(data.get("safety_blocked"))
        self.assertIn("Peringatan keselamatan", data.get("summary_for_speech", ""))


if __name__ == "__main__":
    unittest.main()

