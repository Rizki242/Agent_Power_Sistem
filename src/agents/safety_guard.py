"""
Safety Guardrail Agent for Power Plant AI Assistant.
Enforces safety policies, prevents autonomous destructive commands (Trip/Shutdown),
and mandates Human-in-the-Loop engineering approval.
"""

from typing import Dict, Any, List


class SafetyGuardrailAgent:
    """
    Safety Guardrail to validate AI responses and ensure dangerous plant actuation
    cannot be automatically performed without explicit engineer confirmation.
    """
    FORBIDDEN_AUTONOMOUS_ACTIONS = [
        "trip generator",
        "shutdown turbine",
        "shutdown turbin",
        "open breaker",
        "buka breaker",
        "close breaker",
        "tutup breaker",
        "trip motor",
        "trip boiler",
        "open safety valve",
        "buka safety valve",
        "change protection setting",
        "ubah setting proteksi",
        "override interlock",
        "bypass proteksi",
        "emergency stop"
    ]

    def check_safety(self, action_or_query: str) -> Dict[str, Any]:
        text_lower = str(action_or_query).lower()
        violated_actions = []

        for forbidden in self.FORBIDDEN_AUTONOMOUS_ACTIONS:
            if forbidden in text_lower:
                violated_actions.append(forbidden)

        if violated_actions:
            return {
                "safe": False,
                "violation_detected": True,
                "actions": violated_actions,
                "message": (
                    "⚠️ [SAFETY GUARDRAIL BLOCKED] AI Assistant tidak diizinkan melakukan eksekusi langsung "
                    f"perintah operasional berisiko tinggi ({', '.join(violated_actions).upper()}). "
                    "Seluruh rekomendasi tindakan darurat harus melalui verifikasi Standard Operating Procedure (SOP) "
                    "dan otorisasi resmi Shift Supervisor / Chief Engineer di Ruang Kontrol (CCR)."
                ),
                "required_approval": "Chief Operation Engineer / Shift Supervisor"
            }

        return {
            "safe": True,
            "violation_detected": False,
            "message": "Operasi aman dan memenuhi standar kepatuhan keselamatan pembangkit."
        }
