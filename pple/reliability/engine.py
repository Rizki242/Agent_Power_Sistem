"""Reliability Fusion V2 (docs/final.md Phase 11/17).

Consumes DiagnosticResult[] (the standard output every pple.engineering
module produces, see pple/engineering/schemas.py) rather than domain-
specific objects - a caller can fuse evidence from any current or future
module without this engine knowing its shape.

Deliberately reuses the existing, calibrated RUL/Risk formulas from
src.agents.fusion_engine (RULPredictor, RiskEngine) instead of inventing new
ones: docs/final.md explicitly warns against fabricating a RUL formula where
no model/data backs it, and CLAUDE.md's own principle is to improve existing
rule-based logic rather than replace it. What IS new here is the health-index
aggregation itself: the legacy ReliabilityFusionAgent takes a fixed set of
named domain scores (vibration/mcsa/dga/tribology); this engine
confidence-weights an arbitrary list of DiagnosticResults, so adding a new
engineering module needs no change here.
"""

from typing import Optional

from pple.engineering.schemas import DiagnosticResult, Severity
from pple.reliability.schemas import DomainContribution, FusionResult

# Severity.CRITICAL is worse than ALARM is worse than WATCH is worse than NORMAL.
_SEVERITY_RANK = {
    Severity.NORMAL: 1,
    Severity.WATCH: 2,
    Severity.ALARM: 3,
    Severity.CRITICAL: 4,
}
_DEFAULT_CONFIDENCE = 0.5  # weight used when a module doesn't report one


class ReliabilityFusionEngine:
    def __init__(self):
        # Deferred import: src.agents.fusion_engine pulls in the specialist
        # agents module, which pple.engineering.legacy_adapter already
        # depends on - importing at module load time risks a cycle.
        from src.agents.fusion_engine import RiskEngine, RULPredictor

        self._rul_predictor = RULPredictor()
        self._risk_engine = RiskEngine()

    def fuse(self, results: list[DiagnosticResult], criticality: str = "B") -> FusionResult:
        """Fuse one equipment's DiagnosticResults into a single reliability
        picture. Raises ValueError if `results` is empty or mixes more than
        one equipment_id (fusing across equipment has no defined meaning)."""
        if not results:
            raise ValueError("fuse() requires at least one DiagnosticResult.")
        equipment_ids = {r.equipment_id for r in results}
        if len(equipment_ids) > 1:
            raise ValueError(f"fuse() got results for multiple equipment: {sorted(equipment_ids)}")
        equipment_id = results[0].equipment_id

        weighted_sum = 0.0
        weight_total = 0.0
        contributions = []
        for r in results:
            score = r.health_score if r.health_score is not None else 50.0
            weight = r.confidence if r.confidence is not None else _DEFAULT_CONFIDENCE
            weighted_sum += score * weight
            weight_total += weight
            contributions.append(DomainContribution(
                module_id=r.module_id, health_score=r.health_score,
                severity=r.severity, confidence=r.confidence,
            ))
        health_index = round(weighted_sum / weight_total, 1) if weight_total else 50.0

        worst = max(results, key=lambda r: _SEVERITY_RANK[r.severity])
        # ISO 13374 / MIMOSA bottleneck rule (same bound as the legacy V1
        # engine): one domain in ALARM/CRITICAL caps the fused index even if
        # every other domain looks healthy - a single bad bearing sinks the
        # equipment's health regardless of how good its oil looks.
        if worst.severity == Severity.CRITICAL:
            health_index = min(health_index, 45.0)
        elif worst.severity == Severity.ALARM:
            health_index = min(health_index, 65.0)

        rul_info = self._rul_predictor.predict(health_index, _SEVERITY_RANK[worst.severity])
        risk_info = self._risk_engine.calculate_risk(rul_info["failure_probability_30d"], criticality)

        return FusionResult(
            equipment_id=equipment_id,
            health_index=health_index,
            severity=worst.severity,
            domain_contributions=contributions,
            risk_level=risk_info["risk_level"],
            risk_index=risk_info["risk_index"],
            failure_probability_30d=rul_info["failure_probability_30d"],
            estimated_rul_days=rul_info["estimated_rul_days"],
            rul_min_days=rul_info["rul_min_days"],
            rul_max_days=rul_info["rul_max_days"],
            recommended_window=rul_info["recommended_window"],
        )

    def fuse_equipment(self, equipment_id: str, criticality: str = "B") -> FusionResult:
        """Source DiagnosticResult[] for `equipment_id` from real measurement
        data (DGA gas readings, vibration monthly-test records) via
        pple.assets.AssetRegistry + pple.engineering's module registry, then
        fuse(). A domain pple/assets says applies to this equipment but that
        has no matching real measurement is skipped and recorded in
        FusionResult.notes - never given a fabricated score (same principle
        CLAUDE.md documents for the equipment-module registry)."""
        from pple.assets import AssetRegistry
        from pple.engineering.loader import load_modules_from_manifests

        registry, _ = load_modules_from_manifests()
        assets = AssetRegistry()
        results: list[DiagnosticResult] = []
        notes: list[str] = []

        dga_eq = assets.get_equipment(equipment_id, domain="dga")
        if dga_eq is not None:
            gases = self._latest_dga_gases(equipment_id)
            if gases is not None:
                results.append(registry.get("dga").run(equipment_id, gases))
            else:
                notes.append("dga: tidak ada data gas terlarut untuk equipment ini")

        vib_eq = assets.get_equipment(equipment_id, domain="vibration")
        if vib_eq is not None:
            payload = self._latest_vibration_input(vib_eq.name)
            if payload is not None:
                results.append(registry.get("vibration").run(equipment_id, payload))
            else:
                notes.append("vibration: tidak ada data pengujian bulanan yang cocok untuk equipment ini")

        if not results:
            raise ValueError(
                f"Tidak ada data diagnostik yang tersedia untuk equipment '{equipment_id}' "
                f"(domain terdaftar: {', '.join(AssetRegistry.available_domains())})."
            )

        result = self.fuse(results, criticality=criticality)
        result.notes.extend(notes)
        return result

    @staticmethod
    def _latest_dga_gases(equipment_id: str) -> Optional[dict]:
        from src.dga_data import search_dga_transformers

        match = next((t for t in search_dga_transformers() if t.get("transformer_id") == equipment_id), None)
        return match.get("gases") if match else None

    @staticmethod
    def _latest_vibration_input(equipment_name: str) -> Optional[dict]:
        from src.vibration_data import (
            build_vibration_agent_input,
            load_vibration_monthly_tests,
            match_monthly_test_by_equipment,
        )

        record = match_monthly_test_by_equipment(equipment_name, load_vibration_monthly_tests())
        return build_vibration_agent_input(record) if record else None
