"""Standard diagnostic output schema shared by every EngineeringModule (docs/final.md Phase 9)."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    ALARM = "ALARM"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_legacy_level(cls, level: int) -> "Severity":
        """Map the existing specialist agents' 1-4 int severity to this enum."""
        return {1: cls.NORMAL, 2: cls.WATCH, 3: cls.ALARM, 4: cls.CRITICAL}.get(level, cls.NORMAL)


class Evidence(BaseModel):
    text: str


class FaultHypothesis(BaseModel):
    name: str
    confidence: float | None = None


class Recommendation(BaseModel):
    text: str


class StandardReference(BaseModel):
    name: str


class Finding(BaseModel):
    text: str


class DiagnosticResult(BaseModel):
    equipment_id: str
    module_id: str
    timestamp: datetime

    health_score: float | None = None
    severity: Severity
    confidence: float | None = None

    findings: list[Finding] = Field(default_factory=list)
    faults: list[FaultHypothesis] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    standards: list[StandardReference] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)
