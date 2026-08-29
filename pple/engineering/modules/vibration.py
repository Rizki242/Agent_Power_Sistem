"""Vibration EngineeringModule - Phase 1 MVP.

Adapter over src.agents.specialist_agents.VibrationAgent. The legacy agent
computes validation/analysis/diagnosis/recommendation in a single evaluate()
call, so this adapter runs it once in analyze() and slices the result across
diagnose()/recommend() to satisfy the EngineeringModule contract without
duplicating or moving the underlying ISO 10816-3 logic (per docs/final.md
Phase 1: "jangan pindahkan business logic sekaligus").
"""

from typing import Any

from pple.core.exceptions import ModuleValidationError
from pple.engineering.base import EngineeringModule
from pple.engineering.schemas import Severity
from src.agents.specialist_agents import VibrationAgent


class VibrationModule(EngineeringModule):
    id = "vibration"
    name = "Vibration Analysis"
    version = "1.0.0"
    applicable_equipment = ["MOTOR", "PUMP", "FAN", "TURBINE", "GENERATOR", "GEARBOX"]

    def __init__(self) -> None:
        self._agent = VibrationAgent()

    def validate(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ModuleValidationError("Vibration data must be a dict of measurement fields.")

    def analyze(self, data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        equipment_id = context.get("equipment_id", "UNKNOWN")
        return self._agent.evaluate(equipment_id, data)

    def diagnose(self, analysis: dict[str, Any]) -> dict[str, Any]:
        return {
            "severity": Severity.from_legacy_level(analysis.get("severity", 1)),
            "health_score": analysis.get("health_score"),
            "confidence": analysis.get("confidence"),
            "evidence": list(analysis.get("evidence", [])),
            "findings": [analysis.get("condition", ""), analysis.get("failure_mode", "")],
            "metadata": dict(analysis.get("metrics", {})),
            "_analysis": analysis,
        }

    def recommend(self, diagnostic: dict[str, Any]) -> list[str]:
        return list(diagnostic["_analysis"].get("recommendation", []))
