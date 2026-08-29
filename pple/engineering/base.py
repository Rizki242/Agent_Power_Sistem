"""EngineeringModule interface (docs/final.md Phase 5).

Every engineering domain (Vibration, MCSA, DGA, Tribology, PD, Thermal, and
future modules) implements this contract instead of being special-cased in
an if/elif dispatch. run() orchestrates the four required steps and packages
the result as a standard DiagnosticResult (schemas.py).

Phase 1 scope: modules are thin adapters over the existing agents in
src/agents/specialist_agents.py - no business logic is duplicated or moved.
"""

from abc import ABC, abstractmethod
from typing import Any

from pple.engineering.schemas import DiagnosticResult


class EngineeringModule(ABC):
    id: str
    name: str
    version: str
    applicable_equipment: list[str] = []

    @abstractmethod
    def validate(self, data: dict[str, Any]) -> None:
        """Raise pple.core.exceptions.ModuleValidationError if data is unusable."""

    @abstractmethod
    def analyze(self, data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Run the underlying analysis and return a raw result dict."""

    @abstractmethod
    def diagnose(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Derive severity/health/confidence from an analyze() result."""

    @abstractmethod
    def recommend(self, diagnostic: dict[str, Any]) -> list[str]:
        """Derive recommendation strings from a diagnose() result."""

    def run(
        self,
        equipment_id: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> DiagnosticResult:
        """validate -> analyze -> diagnose -> recommend -> DiagnosticResult."""
        context = dict(context or {})
        context.setdefault("equipment_id", equipment_id)

        self.validate(data)
        analysis = self.analyze(data, context)
        diagnostic = self.diagnose(analysis)
        recommendations = self.recommend(diagnostic)

        return self._build_result(equipment_id, diagnostic, recommendations)

    def _build_result(
        self,
        equipment_id: str,
        diagnostic: dict[str, Any],
        recommendations: list[str],
    ) -> DiagnosticResult:
        from datetime import datetime, timezone

        from pple.engineering.schemas import (
            DiagnosticResult,
            Evidence,
            Finding,
            Recommendation,
            Severity,
        )

        return DiagnosticResult(
            equipment_id=equipment_id,
            module_id=self.id,
            timestamp=datetime.now(timezone.utc),
            health_score=diagnostic.get("health_score"),
            severity=diagnostic.get("severity", Severity.NORMAL),
            confidence=diagnostic.get("confidence"),
            findings=[Finding(text=t) for t in diagnostic.get("findings", [])],
            evidence=[Evidence(text=t) for t in diagnostic.get("evidence", [])],
            recommendations=[Recommendation(text=t) for t in recommendations],
            metadata=diagnostic.get("metadata", {}),
        )
