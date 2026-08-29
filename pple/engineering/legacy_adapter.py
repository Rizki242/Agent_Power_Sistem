"""Shared base for EngineeringModules that wrap a src.agents.specialist_agents
BaseSpecialistAgent as-is (Phase 1 migration strategy - see docs/final.md
Phase 1: "jangan pindahkan business logic sekaligus").

Every legacy specialist agent exposes the same evaluate(equipment, data) ->
dict shape (condition, health_score, failure_mode, severity, confidence,
evidence, recommendation, metrics), so a single adapter base can drive
validate/analyze/diagnose/recommend for all of them. A module only needs to
declare its id/name/version/applicable_equipment and which agent class to
wrap.
"""

from typing import Any

from pple.core.exceptions import ModuleValidationError
from pple.engineering.base import EngineeringModule
from pple.engineering.schemas import Severity


class LegacyAgentAdapterModule(EngineeringModule):
    agent_cls: type

    def __init__(self) -> None:
        self._agent = self.agent_cls()

    def validate(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ModuleValidationError(f"{self.name} data must be a dict of measurement fields.")

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
