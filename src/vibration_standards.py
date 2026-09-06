"""ISO 10816-3 zone limits and SPM shock-pulse thresholds for Vibrasi.

The existing VibrationAgent evaluates overall RMS against one hardcoded set
of limits (ISO 10816-3 Group 1 rigid: 2.3 / 4.5 / 7.1 mm/s). The asset
register actually carries four different equipment classes, and the plant's
own DETAIL REPORT VIBRASI form prints the A/B/C/D limit row for the class
the machine belongs to - so a Group 2 machine judged against Group 1 limits
is judged too leniently.

This module holds those per-class limits, plus the shock-pulse thresholds
the report's second page documents, as plain data with one lookup function
each. Rule-based and standalone: no LLM, no I/O, so both the report
generator and the UI can call it without pulling in anything heavier.

Sources for the numbers: ISO 10816-3 Table A.1 zone boundaries, and the
limits printed on the plant's own form (FORM.JRG.F.05.001), which the
Group 1 rigid row matches exactly (2.3 / 4.5 / 7.1).
"""

from __future__ import annotations

import re
from typing import Any, Optional

# Zone boundaries in mm/s RMS: (A|B, B|C, C|D).
# Zone A - new-machine condition, B - acceptable for long-term operation,
# C - unsatisfactory for long-term operation, D - damaging.
ISO_10816_3_ZONES: dict[str, tuple[float, float, float]] = {
    "GROUP 1 RIGID": (2.3, 4.5, 7.1),
    "GROUP 1 FLEXIBLE": (3.5, 7.1, 11.0),
    "GROUP 2 RIGID": (1.4, 2.8, 4.5),
    "GROUP 2 FLEXIBLE": (2.3, 4.5, 7.1),
}

# Fallback when a class string names no recognisable group. Group 2 rigid is
# the strictest of the four, so an unknown machine is never judged more
# leniently than it might deserve.
_DEFAULT_GROUP = "GROUP 2 RIGID"

ZONE_CONDITION = {
    "A": "Sangat halus (kondisi mesin baru)",
    "B": "Dapat diterima untuk operasi jangka panjang",
    "C": "Tidak memuaskan untuk operasi jangka panjang",
    "D": "Berpotensi merusak mesin",
}

ZONE_STATUS = {"A": "NORMAL", "B": "NORMAL", "C": "PREWARNING", "D": "ALARM"}


def canon_equipment_class(equipment_class: Any) -> str:
    """Normalise a class string from the asset register to a zone-table key.

    Accepts the forms actually present in the register, e.g.
    "ISO 10816-3 (GROUP 1 RIGID)", "ISO 10816-2 (GROUP 2 RIGID)", or a bare
    "ISO 10816-2" with no group at all.
    """
    text = str(equipment_class or "").upper()
    match = re.search(r"GROUP\s*([12])\s*(RIGID|FLEXIBLE)", text)
    if match:
        return f"GROUP {match.group(1)} {match.group(2)}"
    return _DEFAULT_GROUP


def zone_limits(equipment_class: Any) -> tuple[float, float, float]:
    """(A|B, B|C, C|D) boundaries in mm/s for this equipment class."""
    return ISO_10816_3_ZONES[canon_equipment_class(equipment_class)]


def evaluate_overall(velocity_mm_s: float, equipment_class: Any) -> dict[str, Any]:
    """Classify one overall RMS reading into an ISO 10816-3 zone."""
    a_b, b_c, c_d = zone_limits(equipment_class)
    value = float(velocity_mm_s)

    if value < a_b:
        zone = "A"
    elif value < b_c:
        zone = "B"
    elif value < c_d:
        zone = "C"
    else:
        zone = "D"

    return {
        "zone": zone,
        "status": ZONE_STATUS[zone],
        "condition": ZONE_CONDITION[zone],
        "value": value,
        "limits": {"A": 0.0, "B": a_b, "C": b_c, "D": c_d},
        "equipment_class": canon_equipment_class(equipment_class),
    }


# --- Shock pulse (SPM) ------------------------------------------------------
# Thresholds as documented on page 2 of the plant's report form.
SHOCK_PULSE_CARPET_WARNING = 10.0
SHOCK_PULSE_CARPET_ALARM = 15.0
SHOCK_PULSE_MAX_WARNING = 25.0
SHOCK_PULSE_MAX_ALARM = 35.0
SHOCK_PULSE_DELTA_IDEAL = 10.0


def evaluate_shock_pulse(max_db: Optional[float], carpet_db: Optional[float]) -> dict[str, Any]:
    """Evaluate one bearing's shock-pulse pair.

    delta = max - carpet, which is how the plant's own form computes it
    (verified against its printed example: max -24, carpet -31, delta 7).
    Lubrication reading follows the form's note: delta below the ideal means
    over-greasing, above it means under-greasing.
    """
    result: dict[str, Any] = {
        "max_db": None if max_db is None else float(max_db),
        "carpet_db": None if carpet_db is None else float(carpet_db),
        "delta": None,
        "status": "TIDAK ADA DATA",
        "carpet_status": "TIDAK ADA DATA",
        "max_status": "TIDAK ADA DATA",
        "lubrication": "-",
    }
    if max_db is None or carpet_db is None:
        return result

    max_value = float(max_db)
    carpet_value = float(carpet_db)
    delta = max_value - carpet_value
    result["delta"] = delta

    if carpet_value >= SHOCK_PULSE_CARPET_ALARM:
        result["carpet_status"] = "ALARM"
    elif carpet_value >= SHOCK_PULSE_CARPET_WARNING:
        result["carpet_status"] = "WARNING"
    else:
        result["carpet_status"] = "NORMAL"

    if max_value >= SHOCK_PULSE_MAX_ALARM:
        result["max_status"] = "ALARM"
    elif max_value >= SHOCK_PULSE_MAX_WARNING:
        result["max_status"] = "WARNING"
    else:
        result["max_status"] = "NORMAL"

    severity_order = {"NORMAL": 0, "WARNING": 1, "ALARM": 2}
    result["status"] = max(
        (result["carpet_status"], result["max_status"]),
        key=lambda name: severity_order[name],
    )

    if delta < SHOCK_PULSE_DELTA_IDEAL:
        result["lubrication"] = "Kelebihan greasing"
    elif delta > SHOCK_PULSE_DELTA_IDEAL:
        result["lubrication"] = "Kekurangan greasing"
    else:
        result["lubrication"] = "Greasing ideal"

    return result
