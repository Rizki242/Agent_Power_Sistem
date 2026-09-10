"""Application Use Case for multi-agent CBM condition assessment reports."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, Optional

from pple.core.logging import log_report_generation
from src.agents.subagent_coordinator import SubAgentCoordinator


class GenerateAssessmentReportUseCase:
    """Orchestrates comprehensive multi-agent CBM condition assessment reports."""

    def __init__(self, coordinator: Optional[SubAgentCoordinator] = None):
        self.coordinator = coordinator or SubAgentCoordinator()

    def generate_report(self, equipment: str) -> Dict[str, Any]:
        """Generate a complete multi-modal condition assessment report for an asset."""
        t0 = time.perf_counter()
        collab = self.coordinator.run_collaborative_diagnosis(
            equipment=equipment,
            query=f"Laporan komprehensif assessment kondisi {equipment}",
        )

        rpt_no = f"CBM-RPT-{datetime.now().strftime('%Y%m')}-{abs(hash(equipment)) % 10000:04d}"
        duration_ms = (time.perf_counter() - t0) * 1000

        log_report_generation(
            report_id=rpt_no,
            equipment=equipment,
            report_type="CBM_ASSESSMENT",
            status="SUCCESS",
            duration_ms=round(duration_ms, 2),
            health_index=collab.get("consensus_health_index", 90.0),
            health_status=collab.get("consensus_health_status", "HEALTHY"),
        )

        return {
            "report_id": rpt_no,
            "equipment": equipment,
            "plant": "PLTU Jeranjang (3 × 25 MW)",
            "unit": collab.get("unit", "UNIT 1"),
            "system": collab.get("system", "Turbine & Boiler Auxiliaries"),
            "asset_type": collab.get("asset_type", "Medium Voltage Motor Drive"),
            "criticality": collab.get("criticality", "B"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WITA"),
            "assessment_summary": {
                "health_index": collab.get("consensus_health_index", 90.0),
                "health_status": collab.get("consensus_health_status", "HEALTHY"),
                "primary_failure_mode": collab.get("consensus_failure_mode", "Normal Operation"),
                "confidence_percent": round(collab.get("consensus_confidence", 0.95) * 100, 1),
                "estimated_rul_days": collab.get("predictive_rul", {}).get("estimated_rul_days", 90),
                "risk_level": collab.get("risk_assessment", {}).get("risk_level", "Low Risk (Acceptable)"),
                "fused_evidence": collab.get("fused_evidence", []),
            },
            "subagent_traces": collab.get("subagent_traces", []),
            "work_order_action": collab.get("maintenance_decision", {}),
            "safety_clearance": collab.get("safety_clearance", True),
            "signoff": {
                "prepared_by": "AI O&M Reliability Orchestrator (8 Sub-Agents)",
                "verified_by": "Predictive Maintenance Engineer (CBM Specialist)",
                "approved_by": "Chief Operation Engineer / Shift Supervisor CCR",
                "approval_status": "Awaiting Field Verification",
            },
        }
