import math

from src.utils import safe_float as _safe_float


def _diagnostic_validity(load_pct):
    load_pct = _safe_float(load_pct)
    if load_pct is None:
        return "Unknown"
    if load_pct < 20:
        return "Invalid (<20%)"
    if load_pct < 40:
        return "Monitoring Only (20-40%)"
    return "Valid Diagnosis (>=40%)"


def evaluate_rotorbar(params):
    upper = _safe_float(params.get("Upper Sideband"))
    lower = _safe_float(params.get("Lower Sideband"))
    rb_idx = _safe_float(params.get("Rotorbar Health"))
    level_pct = _safe_float(params.get("Rotorbar Level %"))
    load_pct = _safe_float(params.get("Load"))

    sb_values = [value for value in [upper, lower] if value is not None]
    max_sb = max(sb_values) if sb_values else None

    level = None
    if max_sb is not None:
        if max_sb >= -45:
            level = 4
        elif max_sb >= -54:
            level = 3
        elif max_sb >= -60:
            level = 2
        else:
            level = 1

    if rb_idx is not None:
        if rb_idx >= 3.0:
            level = 4 if level is None else max(level, 4)
        elif rb_idx >= 1.0:
            level = 3 if level is None else max(level, 3)
        elif rb_idx >= 0.1:
            level = 2 if level is None else max(level, 2)

    if level is None:
        status = "Normal"
        assessment = "Unknown"
    elif level >= 4:
        status = "High"
        assessment = "Poor"
    elif level == 3:
        status = "Alarm"
        assessment = "Fair"
    elif level == 2:
        status = "Normal"
        assessment = "Very Good"
    else:
        status = "Normal"
        assessment = "Excellent"

    if upper is not None and lower is not None:
        rbi = (abs(upper) + abs(lower)) / 2.0
    else:
        rbi = abs(max_sb) if max_sb is not None else None

    return {
        "Level": level,
        "Status": status,
        "Assessment": assessment,
        "Max Sideband": max_sb,
        "RB Index": rb_idx,
        "RBI": rbi,
        "RBI Corrected": rbi,
        "Rotorbar Health Index": math.exp(-0.08 * rbi) if rbi is not None else None,
        "Level %": level_pct,
        "Diagnostic Validity": _diagnostic_validity(load_pct),
    }
