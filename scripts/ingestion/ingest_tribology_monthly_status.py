"""Ingest periodic "EXSUM TRIBOLOGY BULAN <Bulan> <Tahun>.xlsx" reports into the
central condition history (src.asset_registry), status only.

Unlike the Vibrasi and Thermal monthly reports, this report's RESUM ALL sheet
carries NO numeric physicochemical values (viscosity, TAN, water content,
wear metals) - only a per-equipment PDM status per domain and a free-text
Indonesian analysis/recommendation. src.tribology_data.load_tribology_monthly_tests()
already reads it correctly (after fixing a bug where it read the Vibrasi
status column and labelled it Tribology) and returns those None for the
missing numeric fields rather than a fabricated placeholder - see that
module's docstring.

Because there is nothing numeric to store, this script deliberately does NOT
write to src.domain_measurements (data/domain/TRIBOLOGY/measurements.csv
stays empty - an empty store is the honest representation of "no measured
data available", not a reason to invent rows). It only adds one condition
history record per equipment that matches a centrally registered asset,
mirroring the Vibrasi/Thermal scripts' asset-lookup and idempotency pattern.

Idempotent: re-running skips any (asset_id, test_date) already present in
condition_history.

Usage: python -m scripts.ingestion.ingest_tribology_monthly_status "<path 1>" "<path 2>" ...
"""

import re
import sys
from pathlib import Path

from src.asset_registry import add_condition_record, list_assets, load_condition_history
from src.tribology_data import load_tribology_monthly_tests

import pandas as pd


def _norm_name(name: str) -> str:
    """Uppercase + collapse whitespace, including non-breaking spaces (\\xa0) -
    matches the normalisation used by the Vibrasi/Thermal ingest scripts so
    the same asset-alias lookup behaves consistently across all three."""
    return re.sub(r"\s+", " ", str(name).replace("\xa0", " ")).strip().upper()


# This report's Unit 1/3 rows spell out the equipment's own registry
# abbreviation in parentheses right before the unit number, e.g.
# "Induce Draught Fan (Idf) 1A New" - "Idf" + "1A" is exactly how the asset
# is registered ("IDF 1A"). Deliberately narrow (letters-only abbreviation,
# a single digit 1-3 + optional A/B, word-bounded) so it can never grab a
# capacity/voltage number by accident - e.g. "Generator Transformer (Gt)
# 34.5 Mva ... Unit 2" must NOT match "GT 3" (34.5's leading digit), which
# would misattribute this equipment's tribology data to the wrong asset.
# Unit 2 rows use a different, unparenthesised style ("Primary Air Fan 1
# Unit 2") this pattern deliberately does not match - falling through to
# "no matching asset" rather than guessing.
_ABBREVIATION_RE = re.compile(r"\(([A-Za-z]+)\)\s*([1-3][AB]?)\b")


def _abbreviation_guess(equipment: str) -> str | None:
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


def ingest_file(path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        print(f"Skip: file not found: {path}")
        return

    records = load_tribology_monthly_tests(str(path))
    if not records:
        print(f"Skip: no records parsed from {path}")
        return

    asset_lookup = _build_asset_lookup()
    existing_history = load_condition_history()
    existing_keys = set()
    if not existing_history.empty:
        trb = existing_history[existing_history["module"] == "TRIBOLOGY"]
        existing_keys = {
            (str(row.asset_id), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in trb.itertuples()
        }

    added, skipped_dup, skipped_no_asset = 0, 0, 0
    for record in records:
        equipment = record["equipment"].strip()
        test_date = record["sampling_date"]
        asset_id = asset_lookup.get(_norm_name(equipment))
        if not asset_id:
            guess = _abbreviation_guess(equipment)
            if guess:
                asset_id = asset_lookup.get(guess)
        if not asset_id:
            skipped_no_asset += 1
            continue
        if (asset_id, test_date) in existing_keys:
            skipped_dup += 1
            continue
        summary = (
            f"Inspeksi Tribology bulan {test_date[:7]}: status {record['status'].title()}. "
            f"{record.get('analysis', '').strip()[:280]}"
        ).strip()
        try:
            add_condition_record({
                "asset_id": asset_id, "module": "TRIBOLOGY", "test_date": test_date,
                "condition": record["status"].title(), "summary": summary, "source_file": path.name,
            })
            added += 1
        except ValueError as exc:
            print(f"Condition record skipped for {equipment}: {exc}")

    print(f"{path.name}: +{added} condition history records, {skipped_dup} duplicates, "
          f"{skipped_no_asset} equipment with no matching registered asset "
          f"(numeric measurements: none written - not present in this report).")


def main() -> None:
    paths = sys.argv[1:]
    if not paths:
        print("Usage: python -m scripts.ingestion.ingest_tribology_monthly_status <file1.xlsx> [file2.xlsx ...]")
        return
    for path_str in paths:
        ingest_file(path_str)


if __name__ == "__main__":
    main()
