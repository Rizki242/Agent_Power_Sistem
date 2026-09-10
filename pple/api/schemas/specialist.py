"""Pydantic response schemas for specialist condition-monitoring domains.

Provides strict types and contracts for DGA, Tribology, Thermal, and PD endpoints
without modifying runtime values or breaking legacy compatibility with the
React frontend and CLI consumers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DGASummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_transformers: int
    by_unit: Dict[str, int]
    by_status: Dict[str, int]


class DGAItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    transformer_id: str
    name: Optional[str] = None
    equipment: Optional[str] = None
    unit: str
    voltage_ratio: Optional[str] = None
    rated_capacity: Optional[str] = None
    oil_type: Optional[str] = None
    oil_volume: Optional[str] = None
    sampling_date: Optional[str] = None
    gases: Optional[Dict[str, float]] = None
    status: str
    tdcg: Optional[float] = None
    duval_diag: Optional[str] = None
    diagnosis: Optional[Dict[str, Any]] = None


class DGAListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    transformers: List[DGAItem]
    count: int


class DGADetailResponse(DGAItem):
    model_config = ConfigDict(extra="allow")

    history: Optional[List[Dict[str, Any]]] = None
    recommendation: Optional[str] = None


class TribologySummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_samples: int
    by_unit: Dict[str, int]
    by_status: Dict[str, int]
    by_grade: Optional[Dict[str, int]] = None


class TribologyItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    sample_id: str
    unit: str
    equipment: str
    status: str
    oil_type: Optional[str] = None
    oil_brand: Optional[str] = None
    viscosity_40c: Optional[float] = None
    water_ppm: Optional[float] = None
    tan: Optional[float] = None
    iso_cleanliness: Optional[str] = None
    wear_fe: Optional[float] = None
    wear_cu: Optional[float] = None
    flash_point: Optional[float] = None
    sampling_date: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None


class TribologyListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    samples: List[TribologyItem]
    count: int


class TribologyDetailResponse(TribologyItem):
    model_config = ConfigDict(extra="allow")

    analysis: Optional[str] = None
    recommendation: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None


class ThermalSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_inspections: int
    by_unit: Dict[str, int]
    by_status: Dict[str, int]


class ThermalInspectionItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    unit: str
    kks: Optional[str] = ""
    equipment: str
    raw_status: Optional[str] = None
    status: str
    standard: Optional[str] = None
    test_date: Optional[str] = None


class ThermalListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    inspections: List[ThermalInspectionItem]
    count: int


class PDSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_samples: int
    by_unit: Dict[str, int]
    by_status: Dict[str, int]


class PDSampleItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    sample_id: str
    equipment: str
    unit: str
    test_date: Optional[str] = None
    method: Optional[str] = None
    pulse_magnitude_pc: Optional[float] = None
    pd_type: Optional[str] = None
    phase_clustering_deg: Optional[float] = None
    nqn: Optional[float] = None
    status: str


class PDListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    samples: List[PDSampleItem]
    count: int


class PDAssessmentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    equipment: str
    domain: str
    condition: str
    health_score: Optional[float] = None
    failure_mode: Optional[str] = None
    severity: int
    confidence: Optional[float] = None
    evidence: List[str] = Field(default_factory=list)
    recommendation: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
