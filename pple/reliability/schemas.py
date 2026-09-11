"""Reliability Fusion V2 output shapes (docs/final.md Phase 11/17).

docs/final.md requires the fusion output to distinguish where each number
came from - a raw sensor reading is not the same kind of fact as a rule-based
projection - so every derived field carries an explicit ValueType instead of
the caller having to guess.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from pple.engineering.schemas import Severity


class ValueType(str, Enum):
    MEASURED = "measured"
    CALCULATED = "calculated"
    RULE_BASED = "rule_based"
    ML_PREDICTION = "ML_prediction"
    LLM_INTERPRETATION = "LLM_interpretation"


class PrognosticStatus(str, Enum):
    HEURISTIC_UNVALIDATED = "heuristic_unvalidated"
    CALIBRATED_MODEL = "calibrated_model"


class DomainContribution(BaseModel):
    """One EngineeringModule's DiagnosticResult as it fed into the fusion."""
    module_id: str
    health_score: float | None = None
    severity: Severity
    confidence: float | None = None
    value_type: ValueType = ValueType.MEASURED


class FusionResult(BaseModel):
    equipment_id: str
    timestamp: datetime = Field(default_factory=datetime.now)

    health_index: float
    health_index_type: ValueType = ValueType.CALCULATED
    severity: Severity

    domain_contributions: list[DomainContribution] = Field(default_factory=list)

    risk_level: str
    risk_index: float
    risk_type: ValueType = ValueType.RULE_BASED

    failure_probability_30d: float
    failure_probability_type: ValueType = ValueType.RULE_BASED

    estimated_rul_days: str
    rul_min_days: int
    rul_max_days: int
    rul_type: ValueType = ValueType.RULE_BASED
    prognostic_status: PrognosticStatus = PrognosticStatus.HEURISTIC_UNVALIDATED
    prognostic_disclaimer: str = (
        "Estimasi berbasis bucket rule/health score; bukan prediksi ML dan belum dikalibrasi "
        "terhadap histori kegagalan aset."
    )

    recommended_window: str = ""

    # e.g. "vibration: tidak ada data pengujian bulanan yang cocok" - domains
    # that were applicable but skipped for lack of real data, never faked.
    notes: list[str] = Field(default_factory=list)
