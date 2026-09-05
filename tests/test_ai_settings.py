import json
import os
import tempfile
import unittest

from src import ai_settings


class AISettingsTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.remove(self.path)  # save()/load() must both tolerate a missing file

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_load_missing_file_returns_empty_dict(self):
        self.assertEqual(ai_settings.load(self.path), {})

    def test_save_then_load_round_trips(self):
        ai_settings.save({"ai_provider": "groq", "groq_model": "llama-3.3-70b-versatile"}, self.path)

        loaded = ai_settings.load(self.path)

        self.assertEqual(loaded["ai_provider"], "groq")
        self.assertEqual(loaded["groq_model"], "llama-3.3-70b-versatile")

    def test_save_merges_rather_than_overwrites(self):
        ai_settings.save({"ai_provider": "gemini", "gemini_model": "gemini-2.5-flash"}, self.path)
        ai_settings.save({"gemini_model": "gemini-2.0-flash"}, self.path)

        loaded = ai_settings.load(self.path)

        self.assertEqual(loaded["ai_provider"], "gemini")
        self.assertEqual(loaded["gemini_model"], "gemini-2.0-flash")

    def test_save_silently_drops_unknown_and_key_shaped_fields(self):
        ai_settings.save({
            "ai_provider": "gemini",
            "gemini_api_key": "should-never-be-persisted",
            "groq_api_key": "AIzaSomeSecretLookingValue",
            "random_field": "whatever",
        }, self.path)

        loaded = ai_settings.load(self.path)

        self.assertEqual(loaded, {"ai_provider": "gemini"})
        with open(self.path, "r", encoding="utf-8") as f:
            raw = f.read()
        self.assertNotIn("should-never-be-persisted", raw)
        self.assertNotIn("AIzaSomeSecretLookingValue", raw)

    def test_load_ignores_unknown_fields_from_a_hand_edited_file(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"ai_provider": "ollama", "some_future_field": "x"}, f)

        loaded = ai_settings.load(self.path)

        self.assertEqual(loaded, {"ai_provider": "ollama"})

    def test_load_corrupt_file_returns_empty_dict(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("{not valid json")

        self.assertEqual(ai_settings.load(self.path), {})

    def test_default_path_uses_config_data_dir(self):
        path = ai_settings._default_path()
        self.assertTrue(path.replace("\\", "/").endswith("config/ai_settings.json"))


if __name__ == "__main__":
    unittest.main()
