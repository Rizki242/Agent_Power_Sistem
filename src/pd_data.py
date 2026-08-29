"""
Partial Discharge (PD) data loader.

Unlike every other domain in this repo, there is no source file of any kind
for PD today - no Excel export, no SQLite register (confirmed: this module
did not exist before docs/final.md's Manajemen Data multi-module work).
DEFAULT_PD_SAMPLES is therefore a hardcoded example list, same as DGA's
DEFAULT_TRANSFORMERS - pages built on this module MUST show
render_data_disclaimer_banner. Because this schema is being designed from
scratch (nothing pre-existing to match), its fields are chosen to map
directly onto src.agents.specialist_agents.PDAgent.evaluate()'s input
(pulse_magnitude_pc, pd_type, phase_clustering_deg, nqn) - so, unlike
Thermal, the Rekomendasi view for PD calls PDAgent for real.
"""

from typing import Dict, Any, List, Optional

from src.data_loader import get_data_path
from src.domain_overrides import DomainOverrideStore

DEFAULT_PD_SAMPLES = [
    {
        "sample_id": "PD-001",
        "equipment": "Generator Stator Winding Unit 1",
        "unit": "UNIT 1",
        "test_date": "2026-07-20",
        "method": "PRPD Online Monitoring",
        "pulse_magnitude_pc": 120.0,
        "pd_type": "Internal Void",
        "phase_clustering_deg": 42.0,
        "nqn": 12.0,
    },
    {
        "sample_id": "PD-002",
        "equipment": "Generator Stator Winding Unit 2",
        "unit": "UNIT 2",
        "test_date": "2026-07-22",
        "method": "PRPD Online Monitoring",
        "pulse_magnitude_pc": 310.0,
        "pd_type": "Surface Discharge",
        "phase_clustering_deg": 55.0,
        "nqn": 28.0,
    },
    {
        "sample_id": "PD-003",
        "equipment": "Generator Stator Winding Unit 3",
        "unit": "UNIT 3",
        "test_date": "2026-07-23",
        "method": "PRPD Online Monitoring",
        "pulse_magnitude_pc": 680.0,
        "pd_type": "Slot Discharge",
        "phase_clustering_deg": 61.0,
        "nqn": 45.0,
    },
    {
        "sample_id": "PD-004",
        "equipment": "MV Switchgear Feeder Cable Unit 1",
        "unit": "UNIT 1",
        "test_date": "2026-06-28",
        "method": "Offline HFCT",
        "pulse_magnitude_pc": 95.0,
        "pd_type": "Corona",
        "phase_clustering_deg": 30.0,
        "nqn": 8.0,
    },
    {
        "sample_id": "PD-005",
        "equipment": "Station Service Transformer (SST) Bushing",
        "unit": "COMMON",
        "test_date": "2026-07-05",
        "method": "UHF Sensor",
        "pulse_magnitude_pc": 1620.0,
        "pd_type": "Internal Void",
        "phase_clustering_deg": 78.0,
        "nqn": 110.0,
    },
]


def _pd_status(pulse_magnitude_pc: float, nqn: float) -> str:
    """Same thresholds PDAgent.evaluate() itself uses (1500/500/250 pC, 100
    NQN) so a sample's badge status always agrees with the score its
    Rekomendasi tab computes - not a separate/looser classification."""
    if pulse_magnitude_pc >= 1500.0 or nqn >= 100.0:
        return "HIGH"
    if pulse_magnitude_pc >= 500.0:
        return "WARNING"
    if pulse_magnitude_pc >= 250.0:
        return "PREWARNING"
    return "NORMAL"


def _override_store() -> DomainOverrideStore:
    return DomainOverrideStore(get_data_path('config', 'pd_overrides.json'))


def _merged_samples() -> List[Dict[str, Any]]:
    """DEFAULT_PD_SAMPLES with any recorded overrides applied on top - an
    override whose sample_id matches an existing entry replaces it, a new
    sample_id adds a new sample."""
    overrides = _override_store().all()
    known_ids = {s['sample_id'] for s in DEFAULT_PD_SAMPLES}
    merged = [dict(overrides.get(s['sample_id'], s)) for s in DEFAULT_PD_SAMPLES]
    merged.extend(dict(record) for sid, record in overrides.items() if sid not in known_ids)
    return merged


def save_pd_sample(sample_id: str, fields: Dict[str, Any]) -> None:
    """Add a new PD sample or edit an existing one."""
    record = dict(fields)
    record['sample_id'] = sample_id
    _override_store().set(sample_id, record)


def get_pd_summary() -> Dict[str, Any]:
    """Returns summary stats for the PD sample fleet."""
    samples = _merged_samples()
    by_unit = {}
    by_status = {"NORMAL": 0, "PREWARNING": 0, "WARNING": 0, "HIGH": 0}
    for s in samples:
        u = s["unit"]
        by_unit[u] = by_unit.get(u, 0) + 1
        status = _pd_status(float(s.get("pulse_magnitude_pc", 0)), float(s.get("nqn", 0)))
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "total_samples": len(samples),
        "by_unit": by_unit,
        "by_status": by_status,
    }


def search_pd_samples(unit: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns filtered PD sample list with status attached."""
    results = []
    for s in _merged_samples():
        if unit and unit.upper() != "ALL" and s.get("unit", "").upper() != unit.upper():
            continue
        if search and search.strip():
            q = search.lower().strip()
            if q not in s.get("equipment", "").lower() and q not in s.get("sample_id", "").lower():
                continue
        s_status = _pd_status(float(s.get("pulse_magnitude_pc", 0)), float(s.get("nqn", 0)))
        if status and status.upper() != "ALL" and s_status != status.upper():
            continue
        s_copy = dict(s)
        s_copy["status"] = s_status
        results.append(s_copy)
    return results


def get_pd_sample_detail(sample_id: str) -> Optional[Dict[str, Any]]:
    """Returns one PD sample plus its status - the Rekomendasi tab computes
    the full PDAgent score itself from this record's raw fields."""
    for s in _merged_samples():
        if str(s.get("sample_id", "")).upper() == sample_id.upper():
            detail = dict(s)
            detail["status"] = _pd_status(float(detail.get("pulse_magnitude_pc", 0)), float(detail.get("nqn", 0)))
            return detail
    return None
