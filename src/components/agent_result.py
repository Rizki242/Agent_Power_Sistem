"""Shared renderer for src.agents.specialist_agents.*Agent.evaluate() output.

Moved verbatim out of src/pages/condition_control_page.py so the
Vibration/DGA/Tribology dashboard pages can reuse the exact same
result rendering (metrics, severity callout, evidence, recommendations,
raw-parameter expander, SOP disclaimer) instead of copy-pasting it a
third/fourth time. Behavior is unchanged from the original.
"""

from typing import Any, Dict

import pandas as pd


def render_agent_result(st, result: Dict[str, Any], metric_labels: Dict[str, str]) -> None:
    """Render a standard specialist-agent result without unsafe actuation."""
    severity = int(result.get("severity", 1))
    condition = str(result.get("condition", "HEALTHY"))
    # `result.get(key, default)` only substitutes the default when the key is
    # ABSENT, not when its value is explicitly None - and BaseSpecialistAgent
    # ._insufficient_if_empty() deliberately returns health_score=None for an
    # UNKNOWN/data-gap condition (CONTEXT.md invariant: missing data is
    # UNKNOWN, never a fabricated score). `float(None)` raised here, crashing
    # every domain page the moment an equipment had no matching measurement.
    confidence_raw = result.get("confidence")
    confidence = float(confidence_raw) if confidence_raw is not None else 0.0
    health_score_raw = result.get("health_score")
    health_score = float(health_score_raw) if health_score_raw is not None else None

    with st.container(border=True):
        metric_cols = st.columns(3)
        metric_cols[0].metric("Status", condition)
        health_score_label = f"{health_score:.0f}/100" if health_score is not None else "Tidak diketahui"
        metric_cols[1].metric("Health score", health_score_label)
        metric_cols[2].metric("Confidence", f"{confidence:.0%}")
        if severity >= 4:
            st.error(f"Severity {severity}: {result.get('failure_mode', '-')}")
        elif severity >= 3:
            st.warning(f"Severity {severity}: {result.get('failure_mode', '-')}")
        elif severity >= 2:
            st.info(f"Severity {severity}: {result.get('failure_mode', '-')}")
        else:
            st.success(f"Severity {severity}: {result.get('failure_mode', '-')}")
        evidence = result.get("evidence") or []
        if evidence:
            st.markdown("**Bukti rule-based**")
            for item in evidence:
                st.write(f"- {item}")
        recommendations = result.get("recommendation") or []
        if recommendations:
            st.markdown("**Rekomendasi tindak lanjut**")
            for item in recommendations:
                st.write(f"- {item}")
        with st.expander("Parameter yang dianalisis", expanded=False):
            # "Nilai" mixes numbers with qualitative readings ("Normal
            # In-Service", an ISO 4406 code, ...). Left as-is, Arrow fails to
            # infer a column type and Streamlit falls back with a noisy
            # traceback in the logs, so render every value as text - the same
            # .astype(str) treatment src/pages/dashboard_page.py already
            # applies to its own mixed "Nilai" column.
            rows = [
                {
                    "Parameter": metric_labels.get(key, key),
                    # pd.isna (not `value is None`) so a float NaN metric -
                    # e.g. a ratio computed from a zero denominator - blanks
                    # out too, instead of stringifying to the literal "nan".
                    "Nilai": "" if isinstance(value, float) and pd.isna(value) else ("" if value is None else str(value)),
                }
                for key, value in (result.get("metrics") or {}).items()
            ]
            st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Hasil adalah screening rule-based. Keputusan operasi, trip, shutdown, atau perubahan proteksi wajib melalui SOP dan otorisasi engineer.")
