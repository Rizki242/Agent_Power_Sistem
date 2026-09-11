import unittest
import pandas as pd

from src.llm_assistant import (
    MCSALLMAssistant,
    OpenAICompatibleClient,
    GroqClient,
    OllamaClient,
    build_history_summary_context,
    build_mcsa_context,
    resolve_api_key,
    resolve_provider_key,
    is_any_ai_configured,
)


class FakeGenericClient:
    def __init__(self):
        self.calls = []

    def generate(self, model, prompt, system=None):
        self.calls.append({"model": model, "prompt": prompt})
        return f"Jawaban dari provider model {model}"


class LlmAssistantTests(unittest.TestCase):
    def test_build_context_limits_rows_and_includes_relevant_fields(self):
        df = pd.DataFrame(
            [
                {
                    "Equipment": "BC101",
                    "Parameter": "Kondisi",
                    "Raw_Value": "Alarm",
                    "Value": None,
                    "Unit": "",
                    "Date": "2026-05-01",
                    "Unit_Name": "UNIT 1",
                    "Voltage_Level": "380/400 V",
                }
            ]
        )

        context = build_mcsa_context(df, max_rows=1)
        self.assertIn("BC101", context)
        self.assertIn("Alarm", context)

    def test_enhance_answer_calls_groq(self):
        fake_client = FakeGenericClient()
        assistant = MCSALLMAssistant(enabled=True, provider="groq", client=fake_client, model="llama-3.3-70b-versatile")
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Alarm"}])

        answer = assistant.enhance_answer("analisa BC101", "BC101 Alarm", df)
        self.assertIn("llama-3.3-70b-versatile", answer)
        self.assertEqual(len(fake_client.calls), 1)

    def test_enhance_answer_calls_opencode(self):
        fake_client = FakeGenericClient()
        assistant = MCSALLMAssistant(enabled=True, provider="opencode", client=fake_client, model="gpt-4o-mini")
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Normal"}])

        answer = assistant.enhance_answer("status BC101", "BC101 Normal", df)
        self.assertIn("gpt-4o-mini", answer)

    def test_resolve_provider_key(self):
        key = resolve_provider_key("groq", "gsk_test123")
        self.assertEqual(key, "gsk_test123")

    def test_enhance_answer_falls_back_on_exception(self):
        class BrokenClient:
            def generate(self, *args, **kwargs):
                raise ConnectionError("API connection timed out")

        assistant = MCSALLMAssistant(enabled=True, provider="groq", client=BrokenClient(), model="llama-3.3-70b-versatile")
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Alarm"}])

        answer = assistant.enhance_answer("analisa BC101", "Jawaban Rule Fallback", df)
        self.assertEqual(answer, "Jawaban Rule Fallback")
        self.assertIn("gagal menjawab", assistant.last_error)


if __name__ == "__main__":
    unittest.main()
