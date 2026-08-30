"""Shared equipment-status canonicalization and color palette.

canon_condition_status() is moved verbatim out of src/pages/dashboard_page.py
so the Vibration/DGA/Tribology dashboard pages (and any future one) can
reuse the exact same status vocabulary and colors instead of copy-pasting
it a third or fourth time. Behavior is unchanged from the original.
"""

from typing import Any


def canon_condition_status(x: Any) -> str:
    s = str(x or "").strip().lower()
    if any(k in s for k in ["high", "bad", "critical", "rusak", "damage", "trip"]):
        return "High"
    if any(k in s for k in ["alarm", "warning", "prewarning", "alert", "watch"]):
        return "Alarm"
    if "standby" in s:
        return "Standby"
    if any(k in s for k in ["normal", "ok", "good", "satisfactory"]):
        return "Normal"
    return "Unknown"


STATUS_PIE_COLORS = {
    "Normal": "#16a34a",
    "Alarm": "#facc15",
    "High": "#dc2626",
    "Standby": "#9ca3af",
    "Unknown": "#e5e7eb",
}

STATUS_BADGE_BG = {
    "Normal": "#dcfce7",
    "Alarm": "#fef9c3",
    "High": "#fee2e2",
    "Standby": "#e5e7eb",
    "Unknown": "#f3f4f6",
}

STATUS_BADGE_FG = {
    "Normal": "#166534",
    "Alarm": "#854d0e",
    "High": "#991b1b",
    "Standby": "#374151",
    "Unknown": "#374151",
}


def render_status_badge(st, label: str, status: str) -> None:
    """Same pill-badge HTML block dashboard_page.py renders for the selected equipment header."""
    bg = STATUS_BADGE_BG.get(status, STATUS_BADGE_BG["Unknown"])
    fg = STATUS_BADGE_FG.get(status, STATUS_BADGE_FG["Unknown"])
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:12px;">
          <h3 style="margin:0;">{label}</h3>
          <span style="padding:4px 10px; border-radius:999px; background:{bg}; color:{fg}; font-weight:700; border:1px solid rgba(0,0,0,0.08);">{status}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
