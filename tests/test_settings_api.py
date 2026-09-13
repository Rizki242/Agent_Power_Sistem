import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api_server import app


class SettingsAPITests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.ai_settings.load", return_value={"ai_enabled": True, "ai_provider": "gemini", "gemini_model": "gemini-test"})
    @patch("pple.api.routers.settings.resolve_provider_key", side_effect=lambda provider: "secret-value" if provider == "gemini" else None)
    def test_overview_never_exposes_provider_keys(self, _resolve, _load):
        response = self.client.get("/api/settings/overview")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["providers"]["gemini"]["configured"])
        self.assertNotIn("secret-value", response.text)
        self.assertNotIn("api_key", response.text.lower())

    @patch("src.ai_settings.save", return_value={"ai_enabled": True, "ai_provider": "ollama", "ollama_model": "qwen2.5", "ollama_host": "http://localhost:11434"})
    def test_update_persists_only_safe_preferences(self, save):
        response = self.client.put("/api/settings/ai", json={
            "ai_enabled": True,
            "ai_provider": "ollama",
            "model": "qwen2.5",
            "ollama_host": "http://localhost:11434",
        })

        self.assertEqual(response.status_code, 200)
        saved = save.call_args.args[0]
        self.assertEqual(saved["ollama_model"], "qwen2.5")
        self.assertNotIn("api_key", saved)

    def test_update_rejects_unknown_provider(self):
        response = self.client.put("/api/settings/ai", json={
            "ai_enabled": True, "ai_provider": "unknown", "model": "x",
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
