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
import hashlib
import json

from pple.core.exceptions import ModuleValidationError
from pple.engineering.base import EngineeringModule
from pple.engineering.schemas import Severity


class LegacyAgentAdapterModule(EngineeringModule):
    agent_cls: type

    _MEASUREMENT_FIELDS = {
        "vibration": {"overall_rms", "rms", "bpfo_amp", "bpfo", "bpfi_amp", "bpfi", "amp_1x", "1x", "amp_2x", "2x", "axial_1x"},
        "mcsa": {"upper_sb", "lower_sb", "bearing_status", "i_unbalance", "v_unbalance", "thd_i", "thd_v", "load_pct"},
        "dga": {"h2", "ch4", "c2h2", "c2h4", "c2h6", "co", "co2", "tdcg"},
        "partial_discharge": {"pulse_magnitude_pc", "magnitude_pc", "nqn", "repetition_rate", "phase_position", "pattern"},
        "tribology": {"fe_ppm", "cu_ppm", "water_ppm", "viscosity_cst", "viscosity_change_pct", "tan", "iso_code"},
        "thermal": {"bearing_temp", "temp", "winding_temp", "ambient_temp", "delta_t_phase", "hotspot_temp"},
    }
    _REQUIRED_CONTEXT = {
        "vibration": ("timestamp", "speed_rpm", "sensor_position", "direction", "unit"),
        "mcsa": ("timestamp", "load_pct", "line_frequency_hz", "sample_rate_hz"),
        "dga": ("timestamp", "sample_source", "laboratory", "unit"),
        "partial_discharge": ("timestamp", "sensor_position", "acquisition_method", "noise_rejection"),
        "tribology": ("timestamp", "sample_point", "lubricant_id", "service_hours"),
        "thermal": ("timestamp", "load_pct", "ambient_temp", "emissivity"),
    }

    def __init__(self) -> None:
        self._agent = self.agent_cls()

    def validate(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            raise ModuleValidationError(f"{self.name} data must be a dict of measurement fields.")
        normalized_keys = {str(key).lower(): key for key in data}
        usable = {
            key for key in self._MEASUREMENT_FIELDS.get(self.id, set())
            if key in normalized_keys
            and data[normalized_keys[key]] is not None
            and str(data[normalized_keys[key]]).strip() != ""
        }
        if not usable:
            raise ModuleValidationError(
                f"{self.name} requires at least one recognized, non-empty measurement field; "
                "missing data must not be interpreted as a healthy condition."
            )

    def analyze(self, data: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        equipment_id = context.get("equipment_id", "UNKNOWN")
        # Domain source files are not consistent about key casing (DGA uses
        # H2/CH4 while the legacy rule engine expects h2/ch4). Normalize only
        # at this boundary and retain the original payload for traceability.
        normalized_data = {str(key).lower(): value for key, value in data.items()}
        analysis = self._agent.evaluate(equipment_id, normalized_data)
        analysis["_input_data"] = data
        analysis["_context"] = context
        return analysis

    def diagnose(self, analysis: dict[str, Any]) -> dict[str, Any]:
        input_data = analysis.get("_input_data", {})
        context = analysis.get("_context", {})
        normalized_input = {str(key).lower(): value for key, value in input_data.items()}
        observed = sorted(
            key for key in self._MEASUREMENT_FIELDS.get(self.id, set())
            if key in normalized_input
            and normalized_input[key] is not None
            and str(normalized_input[key]).strip() != ""
        )
        missing_context = [
            key for key in self._REQUIRED_CONTEXT.get(self.id, ())
            if context.get(key) in (None, "") and input_data.get(key) in (None, "")
        ]
        limitations = []
        if missing_context:
            limitations.append("Konteks pengukuran belum lengkap; confidence bukan probabilitas terkalibrasi.")
        input_hash = hashlib.sha256(
            json.dumps(input_data, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")
        ).hexdigest()
        return {
            "severity": Severity.from_legacy_level(analysis.get("severity", 1)),
            "health_score": analysis.get("health_score"),
            "confidence": analysis.get("confidence"),
            "evidence": list(analysis.get("evidence", [])),
            "findings": [analysis.get("condition", ""), analysis.get("failure_mode", "")],
            "metadata": dict(analysis.get("metrics", {})),
            "data_quality": {
                "status": "partial" if missing_context else "valid",
                "observed_fields": observed,
                "missing_context": missing_context,
                "limitations": limitations,
            },
            "source_trace": {
                "source_id": context.get("source_id"),
                "input_hash": input_hash,
                "rule_set_version": self.version,
            },
            "required_confirmation": list(analysis.get("required_confirmation", [])),
            "_analysis": analysis,
        }

    def recommend(self, diagnostic: dict[str, Any]) -> list[str]:
        return list(diagnostic["_analysis"].get("recommendation", []))
