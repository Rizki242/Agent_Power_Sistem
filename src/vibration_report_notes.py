"""Engineer-editable narrative for one Vibrasi report.

The plant's DETAIL REPORT VIBRASI form carries three free-text fields that
no measurement can produce on its own: KETERANGAN on page 1, and ANALISA /
REKOMENDASI on page 2. VibrationAgent can draft all three from the readings,
but an engineer must be able to correct or extend them with field context
the numbers do not carry - so the draft is a starting point, never the last
word.

Notes are keyed by (equipment, test_date) because that pair is what one
printed report covers. Storage follows the same atomic-write JSON pattern as
src.ai_settings and pple.engineering.equipment_modules; measurements
themselves stay in src.domain_measurements, so editing a narrative can never
alter a reading.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any, Optional

import pandas as pd

_LOCK = Lock()
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

FIELDS = ("keterangan", "analisa", "rekomendasi")


def _data_root() -> Path:
    configured = os.environ.get("MCSA_DATA_DIR")
    root = Path(configured).expanduser() if configured else _PROJECT_ROOT / "data"
    return root.resolve()


def _store_path() -> Path:
    return _data_root() / "domain" / "VIBRASI" / "report_notes.json"


def make_key(equipment: str, test_date: Any) -> str:
    """Stable key for one report: '<equipment>|<YYYY-MM-DD>'."""
    parsed = pd.to_datetime(test_date, errors="coerce")
    stamp = "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")
    return f"{str(equipment or '').strip()}|{stamp}"


def _load_all() -> dict[str, dict[str, str]]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def get_notes(equipment: str, test_date: Any) -> dict[str, str]:
    """Saved narrative for this report, or empty strings when none exists."""
    stored = _load_all().get(make_key(equipment, test_date), {})
    return {field: str(stored.get(field, "") or "") for field in FIELDS}


def save_notes(equipment: str, test_date: Any, notes: dict[str, Any]) -> dict[str, str]:
    """Persist the narrative for one report, keeping only the known fields."""
    key = make_key(equipment, test_date)
    cleaned = {field: str(notes.get(field, "") or "").strip() for field in FIELDS}

    with _LOCK:
        everything = _load_all()
        everything[key] = cleaned
        path = _store_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = str(path) + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(everything, handle, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    return cleaned


def draft_notes(
    equipment: str,
    equipment_class: Any,
    readings: dict[str, float],
    shock_pulse: Optional[list[dict[str, Any]]] = None,
) -> dict[str, str]:
    """Rule-based first draft of the three narrative fields.

    Written to read like the plant's own wording, and stating only what the
    readings support: the worst point and its ISO zone, a monitoring
    recommendation whose urgency follows that zone, and a greasing check
    only for bearings whose shock-pulse readings are actually elevated.
    Never invents a cause the numbers do not show.
    """
    from src.vibration_standards import evaluate_overall

    point_values = {key: value for key, value in (readings or {}).items()
                    if key.startswith("pt") and isinstance(value, (int, float))}
    if not point_values:
        return {field: "" for field in FIELDS}

    worst_key = max(point_values, key=lambda key: point_values[key])
    worst_value = float(point_values[worst_key])
    verdict = evaluate_overall(worst_value, equipment_class)
    worst_label = _point_label(worst_key)

    keterangan = f"- Nilai vibrasi secara overall lebih dominan pada {worst_label}"

    analisa = (
        f"Secara overall nilai vibrasi {equipment} masuk level {verdict['status']} "
        f"(level {verdict['zone']}) dengan keterangan kondisi {verdict['condition'].lower()}, "
        f"berdasarkan {str(equipment_class or '-')}. "
        f"Nilai vibrasi overall tertinggi {_id_number(worst_value)} mm/s pada {worst_label}."
    )

    rekomendasi_lines = []
    if verdict["zone"] in {"A", "B"}:
        rekomendasi_lines.append("- Lakukan monitoring vibrasi secara rutin dan berkala")
    elif verdict["zone"] == "C":
        rekomendasi_lines.append("- Perketat interval monitoring vibrasi pada titik dengan nilai tertinggi")
        rekomendasi_lines.append("- Jadwalkan pemeriksaan alignment dan kondisi bearing pada kesempatan outage terdekat")
    else:
        rekomendasi_lines.append("- Tingkatkan frekuensi monitoring dan siapkan rencana perbaikan")
        rekomendasi_lines.append(
            "- Koordinasikan dengan Operasi untuk evaluasi lanjutan; keputusan penghentian unit "
            "tetap mengikuti SOP dan otorisasi engineer"
        )

    # Greasing is raised only when the bearing's own shock-pulse readings are
    # elevated. A delta away from the ideal on a bearing whose Max and Carpet
    # are both far below warning says little on its own - the plant's own
    # reports do not raise it either, and listing it per bearing would bury
    # the one recommendation that matters under four that do not.
    for entry in shock_pulse or []:
        if entry.get("status") in {"WARNING", "ALARM"}:
            rekomendasi_lines.append(
                f"- Periksa pelumasan bearing {entry.get('bearing')} "
                f"({str(entry.get('lubrication', '-')).lower()}, shock pulse {entry.get('status')})"
            )

    return {
        "keterangan": keterangan,
        "analisa": analisa,
        "rekomendasi": "\n".join(rekomendasi_lines),
    }


def _id_number(value: float) -> str:
    """Format a reading the way the plant writes it: comma as the decimal."""
    return f"{float(value):.2f}".replace(".", ",")


def _point_label(key: str) -> str:
    """'pt3_a' -> 'bearing 3 axial', matching how the plant writes it."""
    axis_names = {"v": "vertikal", "h": "horizontal", "a": "axial"}
    try:
        point, axis = key.replace("pt", "").split("_")
        return f"bearing {point} arah {axis_names.get(axis, axis)}"
    except ValueError:
        return key
