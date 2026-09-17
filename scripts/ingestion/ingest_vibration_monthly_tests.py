"""Ingest periodic "Exsume Vibrasi <Bulan> <Tahun>.xlsx" monthly test reports
into the canonical VIBRASI measurement store and the central condition history.

src.vibration_data.load_vibration_monthly_tests() already parses this report's
SUMMARY sheet (per-equipment 1V..6A point readings, Vib Max, Status) but is
built around a single "current" file read on demand - it hardcodes test_date
to the original January 2026 file's date and nothing persists it, so a second
month's report just replaces the first in every live view instead of adding
to history. This script is the missing write path: it derives each report's
real month from its title cell, writes every equipment's readings as long-format
rows into data/domain/VIBRASI/measurements.csv (the store Tren & Riwayat and
Laporan already read for the other five domains), and adds one VIBRASI
condition-history record per equipment that matches a centrally registered
asset (by exact name or alias - about 2/3 of rows; the rest are spare/standby
units, like backup compressors, that were never registered as assets).

Idempotent: re-running skips any (equipment, test_date) already present in
measurements.csv and any (asset_id, test_date) already in condition_history.

Usage: python scripts/ingestion/ingest_vibration_monthly_tests.py "<path 1>" "<path 2>" ...
"""

import re
import sys
from pathlib import Path

import pandas as pd

from src.asset_registry import add_condition_record, list_assets, load_condition_history
from src.domain_measurements import append_measurements, load_measurements
from src.vibration_data import load_vibration_monthly_tests

_INDONESIAN_MONTHS = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
}

_POINT_KEYS = [f"{point}{axis}" for point in range(1, 7) for axis in ("V", "H", "A")]


def _extract_report_month(path: Path) -> str:
    """Read the report title ("... BULAN MEI 2026") off the SUMMARY sheet and
    return the first day of that month as YYYY-MM-01. Raises if not found -
    an unparseable date should stop the run, not silently backfill today."""
    title_rows = pd.read_excel(path, sheet_name="SUMMARY", header=None, nrows=6)
    for _, cell in title_rows.iloc[:, 0].items():
        text = str(cell or "")
        match = re.search(r"BULAN\s+([A-Za-z]+)\s+(\d{4})", text, re.IGNORECASE)
        if match:
            month = _INDONESIAN_MONTHS.get(match.group(1).strip().lower())
            if month:
                return f"{match.group(2)}-{month:02d}-01"
    raise ValueError(f"Tidak dapat menemukan judul 'BULAN <nama> <tahun>' pada {path}")


def _build_asset_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for asset in list_assets():
        lookup.setdefault(asset["name"].strip().upper(), asset["asset_id"])
        for alias in asset.get("aliases", []):
            lookup.setdefault(str(alias).strip().upper(), asset["asset_id"])
    return lookup


def ingest_file(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"Skip: file not found: {path}")
        return

    test_date = _extract_report_month(path)
    records = load_vibration_monthly_tests(str(path))
    if not records:
        print(f"Skip: no records parsed from {path}")
        return

    asset_lookup = _build_asset_lookup()
    existing_measurements = load_measurements("VIBRASI")
    existing_keys = set()
    if not existing_measurements.empty:
        existing_keys = {
            (str(row.equipment).strip().upper(), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in existing_measurements.itertuples()
        }

    existing_history = load_condition_history()
    existing_history_keys = set()
    if not existing_history.empty:
        vib = existing_history[existing_history["module"] == "VIBRASI"]
        existing_history_keys = {
            (str(row.asset_id), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in vib.itertuples()
        }

    rows = []
    skipped_no_reading, skipped_dup, cond_added, cond_skipped_dup, cond_skipped_no_asset = 0, 0, 0, 0, 0

    for record in records:
        equipment = record["equipment"].strip()
        key = (equipment.upper(), test_date)
        if key in existing_keys:
            skipped_dup += 1
        else:
            has_reading = bool(record["points"]) or record["velocity_max"] > 0
            if not has_reading:
                skipped_no_reading += 1
            else:
                identity = {
                    "equipment": equipment,
                    "asset_id": asset_lookup.get(equipment.upper(), ""),
                    "unit_name": record["unit"],
                    "test_date": test_date,
                    "condition": record["status"].title(),
                    "notes": f"ISO group {record['iso_group']}",
                    "source_file": path.name,
                }
                if record["velocity_max"] > 0:
                    rows.append({**identity, "parameter": "overall_rms", "value": record["velocity_max"],
                                 "raw_value": record["velocity_max"], "uom": "mm/s"})
                for point_key in _POINT_KEYS:
                    if point_key not in record["points"]:
                        continue
                    canonical_key = f"pt{point_key[0]}_{point_key[1].lower()}"
                    value = record["points"][point_key]
                    rows.append({**identity, "parameter": canonical_key, "value": value,
                                 "raw_value": value, "uom": "mm/s"})

        asset_id = asset_lookup.get(equipment.upper())
        if not asset_id:
            cond_skipped_no_asset += 1
            continue
        if (asset_id, test_date) in existing_history_keys:
            cond_skipped_dup += 1
            continue
        summary = (
            f"Uji vibrasi rutin bulan {test_date[:7]}: Vmax={record['velocity_max']} mm/s "
            f"({record['iso_group']}), status {record['status'].title()}."
        )
        try:
            add_condition_record({
                "asset_id": asset_id, "module": "VIBRASI", "test_date": test_date,
                "condition": record["status"].title(), "summary": summary, "source_file": path.name,
            })
            cond_added += 1
        except ValueError as exc:
            print(f"Condition record skipped for {equipment}: {exc}")

    if rows:
        result = append_measurements("VIBRASI", rows, batch_id=f"monthly-{test_date}")
        print(f"{path.name} ({test_date}): wrote {result['written']} measurement rows "
              f"(rejected {len(result['rejected'])}), skipped {skipped_dup} already-stored equipment, "
              f"{skipped_no_reading} standby/no-reading equipment.")
    else:
        print(f"{path.name} ({test_date}): no new measurement rows "
              f"(skipped {skipped_dup} already-stored, {skipped_no_reading} standby/no-reading).")
    print(f"  Condition history: +{cond_added} records, {cond_skipped_dup} duplicates, "
          f"{cond_skipped_no_asset} equipment with no matching registered asset.")


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python scripts/ingestion/ingest_vibration_monthly_tests.py <file1.xlsx> [file2.xlsx ...]")
        return
    for path_str in paths:
        ingest_file(path_str)


if __name__ == "__main__":
    main()
