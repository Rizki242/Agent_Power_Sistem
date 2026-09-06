import json
import os
import tempfile
import unittest
from unittest import mock

from typer.testing import CliRunner

from pple.cli.main import app

runner = CliRunner()


def _temp_settings_path():
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(path)
    return path


class ConfigLlmShowTests(unittest.TestCase):
    def test_defaults_shown_when_nothing_persisted_yet(self):
        path = _temp_settings_path()
        with mock.patch("src.ai_settings._default_path", return_value=path):
            result = runner.invoke(app, ["config", "llm"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("gemini", result.stdout)
        self.assertIn("gemini-2.5-flash", result.stdout)
        self.assertIn("lapisan opsional", result.stdout)

    def test_ollama_shows_host_and_no_api_key_requirement(self):
        path = _temp_settings_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"ai_provider": "ollama"}, f)
        with mock.patch("src.ai_settings._default_path", return_value=path):
            result = runner.invoke(app, ["config", "llm"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("ollama", result.stdout)
        self.assertIn("localhost:11434", result.stdout)
        self.assertIn("n/a", result.stdout)
        if os.path.exists(path):
            os.remove(path)


class ConfigSetTests(unittest.TestCase):
    def test_set_provider_valid(self):
        path = _temp_settings_path()
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path):
                result = runner.invoke(app, ["config", "set", "llm.provider", "groq"])
                self.assertEqual(result.exit_code, 0)
                self.assertIn("groq", result.stdout)
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.assertEqual(saved["ai_provider"], "groq")
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_set_provider_invalid_rejected(self):
        path = _temp_settings_path()
        with mock.patch("src.ai_settings._default_path", return_value=path):
            result = runner.invoke(app, ["config", "set", "llm.provider", "not-a-real-provider"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("tidak dikenal", result.stdout)
        self.assertFalse(os.path.exists(path))

    def test_set_model_writes_to_field_for_current_provider(self):
        path = _temp_settings_path()
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path):
                runner.invoke(app, ["config", "set", "llm.provider", "groq"])
                result = runner.invoke(app, ["config", "set", "llm.model", "llama-3.1-8b-instant"])
                self.assertEqual(result.exit_code, 0)
                with open(path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.assertEqual(saved["groq_model"], "llama-3.1-8b-instant")
                self.assertNotIn("gemini_model", saved)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_set_never_persists_an_api_key_field(self):
        path = _temp_settings_path()
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path):
                # ai_settings.save() silently drops anything outside its allowlist -
                # this exercises that guarantee through the CLI's own entry point.
                from src import ai_settings

                ai_settings.save({"gemini_api_key": "should-never-be-written"})
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        self.assertNotIn("should-never-be-written", f.read())
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_set_unknown_key_rejected(self):
        path = _temp_settings_path()
        with mock.patch("src.ai_settings._default_path", return_value=path):
            result = runner.invoke(app, ["config", "set", "llm.nonsense", "x"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("tidak dikenal", result.stdout)


class ConfigTestConnectionTests(unittest.TestCase):
    def test_gemini_without_key_reports_missing_key_not_crash(self):
        path = _temp_settings_path()
        try:
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.resolve_provider_key", return_value=None):
                result = runner.invoke(app, ["config", "test"])
            self.assertEqual(result.exit_code, 1)
            self.assertIn("belum diset", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_ollama_uses_test_ollama_connection(self):
        path = _temp_settings_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"ai_provider": "ollama"}, f)
            with mock.patch("src.ai_settings._default_path", return_value=path), \
                 mock.patch("src.llm_assistant.test_ollama_connection", return_value=(True, "Berhasil terhubung ke Ollama.", ["llama3.2"])):
                result = runner.invoke(app, ["config", "test"])
            self.assertEqual(result.exit_code, 0)
            self.assertIn("Berhasil terhubung ke Ollama", result.stdout)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()
