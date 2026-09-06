import json
import os
import tempfile
import unittest
from unittest import mock

from typer.testing import CliRunner

from pple.cli.main import app

runner = CliRunner()


def _temp_settings_path(initial=None):
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    if initial is not None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(initial, f)
    else:
        os.remove(path)
    return path


class OfflineConfigTestGateTests(unittest.TestCase):
    def test_offline_blocks_cloud_provider_connection_test(self):
        path = _temp_settings_path({"ai_provider": "gemini"})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path):
                result = runner.invoke(app, ["--offline", "config", "test"])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("offline", result.stdout.lower())
            self.assertIn("gemini", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_offline_still_allows_local_ollama_connection_test(self):
        path = _temp_settings_path({"ai_provider": "ollama"})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.test_ollama_connection", return_value=(True, "Berhasil terhubung ke Ollama.", ["llama3.2"])):
                result = runner.invoke(app, ["--offline", "config", "test"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Berhasil terhubung ke Ollama", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_without_offline_cloud_provider_test_is_not_blocked_by_the_offline_gate(self):
        path = _temp_settings_path({"ai_provider": "gemini"})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.resolve_provider_key", return_value="fake-key"), \
                 mock.patch("src.llm_assistant.test_gemini_connection", return_value=(True, "Berhasil terhubung ke Gemini.")):
                result = runner.invoke(app, ["config", "test"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Berhasil terhubung ke Gemini", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)


class ChatCommandTests(unittest.TestCase):
    def test_chat_always_returns_a_rule_based_answer(self):
        path = _temp_settings_path({"ai_enabled": False})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path):
                result = runner.invoke(app, ["chat", "halo"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("MCSA AI Virtual Assistant", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_chat_offline_never_constructs_an_llm_client_for_cloud_provider(self):
        path = _temp_settings_path({"ai_provider": "gemini", "ai_enabled": True})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.resolve_provider_key", return_value="fake-key") as mocked_resolve, \
                 mock.patch("src.llm_assistant.MCSALLMAssistant") as mocked_llm:
                result = runner.invoke(app, ["--offline", "chat", "halo"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("MCSA AI Virtual Assistant", result.stdout)
            mocked_llm.assert_not_called()
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_chat_without_offline_and_no_api_key_falls_back_to_rule_based(self):
        path = _temp_settings_path({"ai_provider": "gemini", "ai_enabled": True})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.resolve_provider_key", return_value=None):
                result = runner.invoke(app, ["chat", "halo"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("MCSA AI Virtual Assistant", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_chat_enriches_with_llm_when_online_and_key_available(self):
        path = _temp_settings_path({"ai_provider": "gemini", "ai_enabled": True})
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.resolve_provider_key", return_value="fake-key"), \
                 mock.patch("src.llm_assistant.MCSALLMAssistant") as mocked_llm_cls:
                mocked_llm_cls.return_value.enhance_answer.return_value = "Jawaban yang sudah diperkaya LLM."
                result = runner.invoke(app, ["chat", "halo"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Jawaban yang sudah diperkaya LLM.", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
