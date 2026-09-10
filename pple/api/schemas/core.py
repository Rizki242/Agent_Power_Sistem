"""Pydantic response schemas for core MCSA, equipment, and agents endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    app: str
    uptime_seconds: Optional[float] = None
    version: Optional[str] = "2.0.0"
    active_domains: Optional[List[str]] = None
    cache_loaded: Optional[bool] = None



class MCSACounts(BaseModel):
    model_config = ConfigDict(extra="allow")

    Normal: int = 0
    Alarm: int = 0
    High: int = 0
    Standby: int = 0


class SummaryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_equipment: int
    counts: Dict[str, int]
    units: List[str]
    voltages: List[str]
    dates: List[str]


class EquipmentListItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    equipment: str
    unit: Optional[str] = ""
    voltage: Optional[str] = ""
    status: str
    condition: str
    rotorbar_status: Optional[str] = "Normal"
    bearing_status: Optional[str] = "Normal"
    last_date: Optional[str] = ""
    date: Optional[str] = ""


class EquipmentListResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    equipment: List[EquipmentListItem]
    count: int


class RotorBarCalculationResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    upper_sb: float
    lower_sb: float
    severity_level: int
    status: str
    assessment: str
    max_sideband: Optional[float] = None
    diagnostic_validity: Optional[str] = None


class SpecialistSubAgentItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_id: str
    name: str
    role: Optional[str] = None
    domain: str
    standards: List[str] = Field(default_factory=list)
    icon: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)


class SpecialistSubAgentsResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    specialists: List[SpecialistSubAgentItem]
    total_count: int
    status: str
