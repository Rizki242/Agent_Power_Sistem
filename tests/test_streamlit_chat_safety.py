import unittest

from streamlit.testing.v1 import AppTest

from src.pages.chatbot_page import _build_conversation_context


def _render_chat():
    import pandas as pd
    import streamlit as st
    from types import SimpleNamespace
    from unittest.mock import Mock, patch
    from src.pages import chatbot_page as page

    files = []
    for index, text in enumerate(st.session_state.get("test_files", [])):
        files.append(SimpleNamespace(name=f"lampiran-{index}.txt", getvalue=lambda text=text: text.encode("utf-8")))
    submission = SimpleNamespace(text=st.session_state["test_prompt"], files=files)
    bot = Mock(last_matched_equipment=None, last_export=None)
    bot.process_query.return_value = "Jawaban rule-based."
    llm = Mock(last_citations=[], last_error=None)
    llm.enhance_answer.side_effect = lambda **kwargs: kwargs["rule_answer"]
    with patch.object(page, "MCSAChatbot", return_value=bot), patch.object(
        page, "MCSALLMAssistant", return_value=llm
    ) as factory, patch.object(page, "resolve_provider_key", return_value=None), patch.object(
        st, "chat_input", return_value=submission
    ):
        page.render_chatbot_page(st, pd.DataFrame(), pd.DataFrame())
    st.session_state["test_rule_calls"] = bot.process_query.call_count
    st.session_state["test_llm_calls"] = factory.call_count
    st.session_state["test_enhance_calls"] = llm.enhance_answer.call_count
    if llm.enhance_answer.called:
        st.session_state["test_context"] = llm.enhance_answer.call_args.kwargs


class StreamlitChatSafetyTests(unittest.TestCase):
    def make_app(self, prompt, files=None):
        app = AppTest.from_function(_render_chat, default_timeout=30)
        app.session_state["test_prompt"] = prompt
        app.session_state["test_files"] = files or []
        return app

    def assert_blocked(self, app):
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_rule_calls"], 0)
        self.assertEqual(app.session_state["test_llm_calls"], 0)
        self.assertEqual(app.session_state["test_enhance_calls"], 0)
        messages = app.session_state["messages"]
        self.assertTrue(messages[-2]["safety_blocked"])
        self.assertTrue(messages[-1]["safety_blocked"])
        self.assertIn("SAFETY GUARDRAIL BLOCKED", messages[-1]["content"])
        self.assertEqual(messages[-1]["citations"], [])

    def test_risky_prompts_block_before_rule_and_llm(self):
        for prompt in ("trip unit sekarang", "buka breaker", "override interlock"):
            for enabled in (False, True):
                with self.subTest(prompt=prompt, enabled=enabled):
                    app = self.make_app(prompt)
                    app.session_state["ai_enabled"] = enabled
                    self.assert_blocked(app)

    def test_second_attachment_is_checked(self):
        self.assert_blocked(self.make_app("Ringkas lampiran", ["Data oli normal", "shutdown turbine sekarang"]))

    def test_persisted_attachment_is_checked(self):
        app = self.make_app("Apa kondisi motor?")
        app.session_state["_chat_file_context"] = "bypass proteksi"
        self.assert_blocked(app)

    def test_safe_followup_after_rejection(self):
        app = self.make_app("trip unit")
        self.assert_blocked(app)
        app.session_state["test_prompt"] = "Apa itu MCSA?"
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_rule_calls"], 1)
        self.assertEqual(app.session_state["test_enhance_calls"], 1)
        self.assertEqual(app.session_state["test_context"]["conversation_context"], "")
        self.assertEqual(app.session_state["messages"][-1]["content"], "Jawaban rule-based.")

    def test_safe_attachment_keeps_existing_context(self):
        app = self.make_app("Ringkas data oli", ["Viskositas 32 cSt"])
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_rule_calls"], 1)
        self.assertIn("Viskositas 32 cSt", app.session_state["test_context"]["extra_file_context"])

    def test_rejected_turns_are_excluded_from_context(self):
        context = _build_conversation_context([
            {"role": "user", "content": "Data oli", "safety_blocked": False},
            {"role": "user", "content": "trip unit", "safety_blocked": True},
            {"role": "assistant", "content": "Penolakan", "safety_blocked": True},
        ])
        self.assertEqual(context, "User: Data oli")
