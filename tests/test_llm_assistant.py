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
        # Ensure cross-provider fallback also fails to test terminal rule fallback
        assistant._try_cross_provider_fallback = lambda prompt: (None, None, None)
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Alarm"}])

        answer = assistant.enhance_answer("analisa BC101", "Jawaban Rule Fallback", df)
        self.assertEqual(answer, "Jawaban Rule Fallback")
        self.assertIn("gagal menjawab", assistant.last_error)
        self.assertEqual(assistant.resilience_info["effective_provider"], "rule_based")

    def test_cross_provider_failover(self):
        class BrokenClient:
            def generate(self, *args, **kwargs):
                raise ConnectionError("Primary provider connection refused")

        assistant = MCSALLMAssistant(enabled=True, provider="groq", client=BrokenClient(), model="llama-3.3-70b-versatile")
        # Simulate successful cross-provider failover
        assistant._try_cross_provider_fallback = lambda prompt: ("Jawaban Failover dari Gemini", "gemini", "gemini-3.1-flash-lite")
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Alarm"}])

        answer = assistant.enhance_answer("analisa BC101", "Jawaban Rule Fallback", df)
        self.assertEqual(answer, "Jawaban Failover dari Gemini")
        self.assertEqual(assistant.resilience_info["effective_provider"], "gemini")
        self.assertTrue(assistant.resilience_info["failover_occurred"])

    def test_groq_model_fallback_on_rate_limit(self):
        class CascadeClient:
            def __init__(self):
                self.attempted_models = []

            def generate(self, model, prompt, system=None):
                self.attempted_models.append(model)
                if model == "llama-3.3-70b-versatile":
                    raise ValueError("HTTP 429: Rate limit reached")
                return f"Jawaban sukses dari model cadangan: {model}"

        cascade_client = CascadeClient()
        assistant = MCSALLMAssistant(
            enabled=True,
            provider="groq",
            client=cascade_client,
            model="llama-3.3-70b-versatile",
        )
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Alarm"}])

        answer = assistant.enhance_answer("analisa BC101", "Jawaban Rule Fallback", df)
        self.assertIn("Jawaban sukses dari model cadangan", answer)
        self.assertIn("llama-3.3-70b-versatile", cascade_client.attempted_models)
        self.assertTrue(len(cascade_client.attempted_models) >= 2)
        self.assertNotEqual(assistant.model, "llama-3.3-70b-versatile")

    def test_opencode_model_fallback(self):
        class OpenCodeFallbackClient:
            def __init__(self):
                self.attempted_models = []

            def generate(self, model, prompt, system=None):
                self.attempted_models.append(model)
                if model == "gpt-4o-mini":
                    raise ConnectionError("Timeout on gpt-4o-mini")
                return f"Jawaban OpenCode dari: {model}"

        client = OpenCodeFallbackClient()
        assistant = MCSALLMAssistant(
            enabled=True,
            provider="opencode",
            client=client,
            model="gpt-4o-mini",
        )
        df = pd.DataFrame([{"Equipment": "BC101", "Parameter": "Kondisi", "Raw_Value": "Normal"}])

        answer = assistant.enhance_answer("status BC101", "Rule normal", df)
        self.assertIn("Jawaban OpenCode dari", answer)
        self.assertIn("gpt-4o-mini", client.attempted_models)
        self.assertEqual(assistant.resilience_info["effective_provider"], "opencode")


if __name__ == "__main__":
    unittest.main()
