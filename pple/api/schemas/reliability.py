"""Pydantic schemas for Fleet Reliability and Condition Assessment Reports."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FleetWatchlistItem(BaseModel):
    equipment: str
    unit: str
    system: Optional[str] = None
    criticality: Optional[str] = "B"
    health_index: float
    health_status: str
    health_color: Optional[str] = None
    primary_failure_mode: Optional[str] = None
    severity: Optional[int] = None
    confidence: Optional[float] = None
    rul_days: Optional[Any] = None
    risk_level: Optional[str] = None


class FleetReliabilityResponse(BaseModel):
    total_assets: int
    fleet_health_average: float
    health_summary: Dict[str, int] = Field(
        default_factory=lambda: {
            "HEALTHY": 0,
            "WATCH": 0,
            "WARNING": 0,
            "ALERT": 0,
            "CRITICAL": 0,
        }
    )
    critical_watchlist: List[Dict[str, Any]] = Field(default_factory=list)
    asset_matrix: List[Dict[str, Any]] = Field(default_factory=list)


class FusionDiagnosisResponse(BaseModel):
    equipment: str
    asset_type: str = "Electric Motor-Pump"
    timestamp: Optional[str] = None
    health_index: float
    health_status: str
    health_color: Optional[str] = None
    specialist_evaluations: Optional[Dict[str, Any]] = Field(default_factory=dict)
    failure_mode_diagnosis: Optional[Dict[str, Any]] = Field(default_factory=dict)
    predictive_rul: Optional[Dict[str, Any]] = Field(default_factory=dict)
    risk_assessment: Optional[Dict[str, Any]] = Field(default_factory=dict)
    maintenance_decision: Optional[Dict[str, Any]] = Field(default_factory=dict)
    asset_node: Optional[Dict[str, Any]] = None
    data_sources: Optional[List[str]] = Field(default_factory=list)


class AssessmentSummaryModel(BaseModel):
    health_index: float
    health_status: str
    primary_failure_mode: str
    confidence_percent: float
    estimated_rul_days: Any
    risk_level: str
    fused_evidence: List[str] = Field(default_factory=list)


class AssessmentReportResponse(BaseModel):
    report_id: str
    equipment: str
    plant: str = "PLTU Jeranjang (3 × 25 MW)"
    unit: str = "UNIT 1"
    system: str = "Turbine & Boiler Auxiliaries"
    asset_type: str = "Medium Voltage Motor Drive"
    criticality: str = "B"
    generated_at: str
    assessment_summary: AssessmentSummaryModel
    subagent_traces: List[Dict[str, Any]] = Field(default_factory=list)
    work_order_action: Dict[str, Any] = Field(default_factory=dict)
    safety_clearance: bool = True
    signoff: Dict[str, str] = Field(default_factory=dict)


class UploadResponse(BaseModel):
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
