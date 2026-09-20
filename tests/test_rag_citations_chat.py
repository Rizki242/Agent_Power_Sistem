import unittest
from fastapi.testclient import TestClient
from api_server import app


class TestRAGChatCitations(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_agent_chat_returns_rag_citations_for_concept_query(self):
        response = self.client.post(
            "/api/agent/chat",
            json={
                "message": "bagaimana evaluasi delta-t pada inspeksi thermal?",
                "provider": "groq",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("reply", data)
        self.assertIn("citations", data)
        self.assertIsInstance(data["citations"], list)
        self.assertGreater(len(data["citations"]), 0)

        first_cit = data["citations"][0]
        self.assertIn("source", first_cit)
        self.assertIn("title", first_cit)
        self.assertIn("heading", first_cit)

    def test_agent_chat_citations_persisted_in_session(self):
        # Create session
        s_res = self.client.post("/api/agent/chat/sessions", json={"title": "Test RAG Citations"})
        self.assertEqual(s_res.status_code, 200)
        session_id = s_res.json()["session_id"]

        # Send chat message with session_id
        chat_res = self.client.post(
            "/api/agent/chat",
            json={
                "message": "jelaskan standar getaran ISO 10816-3",
                "session_id": session_id,
                "provider": "groq",
            },
        )
        self.assertEqual(chat_res.status_code, 200)
        chat_data = chat_res.json()
        self.assertIn("citations", chat_data)
        self.assertGreater(len(chat_data["citations"]), 0)

        # Retrieve session messages
        sess_get = self.client.get(f"/api/agent/chat/sessions/{session_id}")
        self.assertEqual(sess_get.status_code, 200)
        messages = sess_get.json()["messages"]
        self.assertGreaterEqual(len(messages), 2)  # user + bot

        bot_msg = [m for m in messages if m["role"] == "assistant"][-1]
        self.assertIn("citations", bot_msg)
        self.assertIsInstance(bot_msg["citations"], list)
        self.assertGreater(len(bot_msg["citations"]), 0)
        self.assertEqual(bot_msg["citations"][0]["title"], chat_data["citations"][0]["title"])


if __name__ == "__main__":
    unittest.main()

