"""Ingest periodic "EKSUM IRT <Bulan> <Tahun>.xlsx" IR thermography reports
into the canonical THERMAL measurement store and the central condition
history.

src.thermal_data.load_thermal_irt_tests() already reads this report's
SUMMARY sheet, but that sheet only carries a pre-computed per-equipment
status (see that module's get_thermal_record_detail() docstring: it
deliberately does not call ThermalAgent because the SUMMARY sheet has no
numeric readings). The REKOMENDASI sheet is a different, more granular
source: one row per measurement point (Cover winding motor / Bearing N
motor|pump|fan|Fluid Coupling / Conection Phasa R|S|T) with a real measured
value (degC) and, for the phase points, an already-computed "T rise" (delta
over ambient). This script parses THAT sheet and writes into
data/domain/THERMAL/measurements.csv using exactly the parameter keys
ThermalAgent.evaluate() reads (src.agents.specialist_agents.ThermalAgent):
bearing_temp, winding_temp, delta_t_phase. ambient_temp and hotspot_temp are
never present in this report and are deliberately left out rather than
guessed - ThermalAgent already defaults them sensibly when absent.

Sheet layout (REKOMENDASI, data rows from index 5): each equipment starts a
new block where column 0 (Unit) is non-null; every row after that in the
block (until the next Unit cell) is one measurement point for the same
equipment, sharing its Unit/No. KKS/Description via merged cells (blank in
the source file, so this script forward-fills them). A block where the
equipment was in standby has "STD BY" text in the Data column instead of a
number for every point - those blocks get a condition-history entry but no
measurement rows (there is nothing measured to store).

Idempotent: re-running skips any (equipment, test_date) already present in
measurements.csv and any (asset_id, test_date) already in condition_history.

Usage: python -m scripts.ingestion.ingest_thermal_irt_tests "<path 1>" "<path 2>" ...
"""

import re
import sys
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from src.asset_registry import add_condition_record, list_assets, load_condition_history
from src.domain_measurements import append_measurements, load_measurements

# REKOMENDASI sheet column positions (0-based), fixed by the report template.
COL_UNIT = 0
COL_KKS = 1
COL_DESC = 2
COL_POINT = 3
COL_STATUS_POINT = 7
COL_STATUS_OVERALL = 8
COL_T_RISE = 9
COL_DATE = 11
COL_DATA = 12

_BEARING_RE = re.compile(r"^bearing\b", re.IGNORECASE)
_WINDING_RE = re.compile(r"cover\s+winding", re.IGNORECASE)
_PHASE_RE = re.compile(r"connection|conection", re.IGNORECASE)


def _norm_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).replace("\xa0", " ")).strip().upper()


# Many Thermal equipment descriptions spell out the registry abbreviation in
# parentheses right before the unit number, e.g. "CIRCULATING WATER PUMP
# (CWP) 1A" - "CWP" + "1A" is exactly how the asset is registered ("CWP
# 1A"). Same narrow, deliberately bounded pattern as
# scripts/ingestion/ingest_tribology_monthly_status.py's _abbreviation_guess
# (letters-only abbreviation, single digit 1-3 + optional A/B, word-bounded)
# so it can never grab a capacity/voltage number by accident - e.g.
# "GENERATOR TRANSFORMER (GT) 34.5 MVA 150/6.3 KV UNIT 1" must NOT match
# "GT 3" (34.5's leading digit). Verified against the full report: this
# raises condition-history asset matches from 4/110 to 30/110 with zero
# false positives; the remaining 80 equipment (turbines, transformers named
# by rating, belt conveyors, ...) are not in this abbreviated style and are
# left unmatched rather than guessed.
_ABBREVIATION_RE = re.compile(r"\(([A-Za-z0-9]+)\)\s*([1-3][AB]?)\b")


def _abbreviation_guess(equipment: str) -> Optional[str]:
    match = _ABBREVIATION_RE.search(equipment)
    if not match:
        return None
    return _norm_name(f"{match.group(1)} {match.group(2)}")


def _build_asset_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for asset in list_assets():
        lookup.setdefault(_norm_name(asset["name"]), asset["asset_id"])
        for alias in asset.get("aliases", []):
            lookup.setdefault(_norm_name(alias), asset["asset_id"])
    return lookup


def _status_to_condition(raw: str) -> str:
    """Same taxonomy as src.thermal_data.load_thermal_irt_tests() - kept
    identical deliberately so the SUMMARY-sheet view (per-equipment overall
    status) and this REKOMENDASI-sheet ingest never disagree on wording for
    the same underlying report."""
    s = str(raw or "").upper()
    if "STD" in s or "STAND" in s:
        return "STANDBY"
    if "LOW" in s:
        return "NORMAL"
    if "MED" in s or "PRE" in s:
        return "PREWARNING"
    if "HIGH" in s:
        return "WARNING"
    if "CRIT" in s or "ALARM" in s:
        return "HIGH"
    return "NORMAL"


def _parse_blocks(path: Path) -> list[dict[str, Any]]:
    """Groups REKOMENDASI's flat, merged-cell rows into one dict per
    equipment block: identity fields + every point's (type, value, date)."""
    raw = pd.read_excel(path, sheet_name="REKOMENDASI", header=None)
    blocks: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None

    for _, row in raw.iloc[5:].iterrows():
        unit_cell = row[COL_UNIT]
        if pd.notna(unit_cell):
            desc = row[COL_DESC]
            if pd.isna(desc) or not str(desc).strip():
                current = None
                continue
            current = {
                "unit": f"UNIT {int(unit_cell)}" if str(unit_cell).replace(".0", "").isdigit() else str(unit_cell),
                "kks": str(row[COL_KKS]) if pd.notna(row[COL_KKS]) else "",
                "equipment": str(desc).replace("EQUIPMENT-", "").strip(),
                "overall_status": row[COL_STATUS_OVERALL] if pd.notna(row[COL_STATUS_OVERALL]) else row[COL_STATUS_POINT],
                "points": [],
            }
            blocks.append(current)
        if current is None:
            continue

        point_name = row[COL_POINT]
        if pd.isna(point_name):
            continue
        data_val = row[COL_DATA]
        t_rise = row[COL_T_RISE]
        date_val = row[COL_DATE]
        current["points"].append({
            "name": str(point_name).strip(),
            "data": data_val,
            "t_rise": t_rise,
            "date": date_val,
        })

    return blocks


def _numeric_or_none(value: Any) -> Optional[float]:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f


def _block_test_date(block: dict[str, Any]) -> Optional[str]:
    for point in block["points"]:
        ts = pd.to_datetime(point["date"], errors="coerce")
        if pd.notna(ts):
            return ts.strftime("%Y-%m-%d")
    return None


def ingest_file(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"Skip: file not found: {path}")
        return

    blocks = _parse_blocks(path)
    if not blocks:
        print(f"Skip: no equipment blocks parsed from {path}")
        return

    asset_lookup = _build_asset_lookup()
    existing_measurements = load_measurements("THERMAL")
    existing_keys = set()
    if not existing_measurements.empty:
        existing_keys = {
            (str(row.equipment).strip().upper(), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in existing_measurements.itertuples()
        }

    existing_history = load_condition_history()
    existing_history_keys = set()
    if not existing_history.empty:
        thm = existing_history[existing_history["module"] == "THERMAL"]
        existing_history_keys = {
            (str(row.asset_id), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in thm.itertuples()
        }

    rows = []
    cond_added, cond_skipped_dup, cond_skipped_no_asset = 0, 0, 0
    skipped_dup, skipped_standby = 0, 0

    for block in blocks:
        equipment = block["equipment"]
        test_date = _block_test_date(block)
        condition = _status_to_condition(block["overall_status"])
        key = (equipment.upper(), test_date or "")
        resolved_asset_id = asset_lookup.get(_norm_name(equipment))
        if not resolved_asset_id:
            guess = _abbreviation_guess(equipment)
            if guess:
                resolved_asset_id = asset_lookup.get(guess)

        if condition == "STANDBY" or not test_date:
            skipped_standby += 1
        elif key in existing_keys:
            skipped_dup += 1
        else:
            bearing_vals, phase_rises, winding_val = [], [], None
            for point in block["points"]:
                value = _numeric_or_none(point["data"])
                if value is None:
                    continue
                if _WINDING_RE.search(point["name"]):
                    winding_val = value
                elif _BEARING_RE.search(point["name"]):
                    bearing_vals.append(value)
                elif _PHASE_RE.search(point["name"]):
                    rise = _numeric_or_none(point["t_rise"])
                    if rise is not None:
                        phase_rises.append(rise)

            identity = {
                "equipment": equipment,
                "asset_id": resolved_asset_id or "",
                "unit_name": block["unit"],
                "test_date": test_date,
                "condition": condition.title(),
                "notes": f"KKS {block['kks']}" if block["kks"] else "",
                "source_file": path.name,
            }
            if winding_val is not None:
                rows.append({**identity, "parameter": "winding_temp", "value": winding_val,
                             "raw_value": winding_val, "uom": "degC"})
            if bearing_vals:
                # Worst-case (highest) reading among this equipment's
                # bearing points - ThermalAgent takes a single bearing_temp,
                # and the highest bearing temperature is the conservative,
                # safety-relevant choice rather than an average that could
                # mask one overheating bearing among several normal ones.
                worst = max(bearing_vals)
                rows.append({**identity, "parameter": "bearing_temp", "value": worst,
                             "raw_value": worst, "uom": "degC"})
            if phase_rises:
                worst_rise = max(phase_rises)
                rows.append({**identity, "parameter": "delta_t_phase", "value": worst_rise,
                             "raw_value": worst_rise, "uom": "K"})

        asset_id = resolved_asset_id
        if not asset_id:
            cond_skipped_no_asset += 1
            continue
        history_date = test_date or _block_test_date(block) or ""
        if not history_date or (asset_id, history_date) in existing_history_keys:
            cond_skipped_dup += 1
            continue
        summary = f"Inspeksi IR Thermography bulan {history_date[:7]}: status {condition.title()}."
        try:
            add_condition_record({
                "asset_id": asset_id, "module": "THERMAL", "test_date": history_date,
                "condition": condition.title(), "summary": summary, "source_file": path.name,
            })
            cond_added += 1
        except ValueError as exc:
            print(f"Condition record skipped for {equipment}: {exc}")

    if rows:
        batch_tag = rows[0]["test_date"][:7] if rows else "unknown"
        result = append_measurements("THERMAL", rows, batch_id=f"monthly-{batch_tag}")
        print(f"{path.name}: wrote {result['written']} measurement rows (rejected {len(result['rejected'])}), "
              f"skipped {skipped_dup} already-stored equipment, {skipped_standby} standby/undated equipment.")
    else:
        print(f"{path.name}: no new measurement rows (skipped {skipped_dup} already-stored, "
              f"{skipped_standby} standby/undated).")
    print(f"  Condition history: +{cond_added} records, {cond_skipped_dup} duplicates, "
          f"{cond_skipped_no_asset} equipment with no matching registered asset.")


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python -m scripts.ingestion.ingest_thermal_irt_tests <file1.xlsx> [file2.xlsx ...]")
        return
    for path_str in paths:
        ingest_file(path_str)


if __name__ == "__main__":
    main()
