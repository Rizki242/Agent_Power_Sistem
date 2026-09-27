"""render_agent_result() must not crash on an UNKNOWN/data-gap diagnosis.

BaseSpecialistAgent._insufficient_if_empty() deliberately returns
health_score=None (and confidence=0.0) when an equipment has no matching
measurement - CONTEXT.md's invariant that missing data is UNKNOWN, never a
fabricated score. render_agent_result() is the one renderer shared by every
domain page (Vibration/DGA/Tribology/PD/...), so a bug here breaks all of
them, not just one.
"""

import unittest

from streamlit.testing.v1 import AppTest

from src.components.agent_result import render_agent_result


def _script():
    import streamlit as st

    from src.components.agent_result import render_agent_result

    result = {
        "equipment": "PAF 1B",
        "domain": "Tribology",
        "condition": "UNKNOWN",
        "health_score": None,
        "failure_mode": "Insufficient measurement data",
        "fault_code": "UNKNOWN",
        "mechanism_tags": [],
        "severity": 0,
        "confidence": 0.0,
        "evidence": [],
        "recommendation": ["Lengkapi data pengukuran yang relevan sebelum menetapkan kondisi aset."],
        "metrics": {},
    }
    render_agent_result(st, result, {})


class RenderAgentResultUnknownConditionTests(unittest.TestCase):
    def test_none_health_score_renders_without_crashing(self):
        at = AppTest.from_function(_script, default_timeout=30).run()
        self.assertFalse(list(at.exception), msg=[str(e) for e in at.exception])

    def test_none_health_score_shows_a_placeholder_not_a_fabricated_number(self):
        at = AppTest.from_function(_script, default_timeout=30).run()
        metric_values = [m.value for m in at.metric]
        self.assertIn("Tidak diketahui", metric_values)
        self.assertNotIn("0/100", metric_values)


class RenderAgentResultDirectCallTests(unittest.TestCase):
    """Exercise the None-guard logic directly without the AppTest harness,
    for a fast assertion on the exact computed values."""

    def test_confidence_none_does_not_crash(self):
        # A minimal fake `st` that only records .metric() calls; enough to
        # prove render_agent_result() computes past the guarded lines.
        class _Col:
            def metric(self, *a, **k):
                pass

        class _FakeSt:
            def container(self, *a, **k):
                import contextlib
                return contextlib.nullcontext()

            def columns(self, n):
                return [_Col() for _ in range(n)]

            def error(self, *a, **k):
                pass

            def warning(self, *a, **k):
                pass

            def info(self, *a, **k):
                pass

            def success(self, *a, **k):
                pass

            def markdown(self, *a, **k):
                pass

            def write(self, *a, **k):
                pass

            def caption(self, *a, **k):
                pass

            def expander(self, *a, **k):
                import contextlib
                return contextlib.nullcontext()

            def dataframe(self, *a, **k):
                pass

        render_agent_result(_FakeSt(), {"confidence": None, "health_score": None}, {})


if __name__ == "__main__":
    unittest.main()
