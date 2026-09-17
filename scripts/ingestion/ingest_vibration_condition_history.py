"""Backfill VIBRASI condition-history records from the vibration asset
workbook (data/vibrasi/asset/database_aset_vibrasi_PLTU_Jeranjang_dengan_unit.xlsx).

The 68 assets in this workbook's Asset_Master sheet are already registered
in the central Asset Registry (via sync_assets_from_database_aset(), run
through the "Sinkronisasi Master" button on the Register Aset page) with
MCSA/VIBRASI/TRIBOLOGY/THERMAL monitoring modules already assigned. What was
missing was the actual vibration test results: the Report_Records sheet
carries one measurement per asset (Measurement Date, PM Week, Status
Vibrasi per ISO 10816-3) that had never been written into the central
condition history, so "Catat Riwayat Kondisi" / asset reports showed zero
VIBRASI records even though the workbook has them.

Idempotent: skips any (asset_id, module, test_date) already present in
condition_history.csv, so it is safe to re-run after the source workbook
is refreshed with new measurements.
"""

from pathlib import Path

import pandas as pd

from src.asset_registry import add_condition_record, get_asset, load_condition_history

_SOURCE_XLSX = Path("data/vibrasi/asset/database_aset_vibrasi_PLTU_Jeranjang_dengan_unit.xlsx")


def main() -> None:
    if not _SOURCE_XLSX.exists():
        print(f"Source workbook not found: {_SOURCE_XLSX}")
        return

    records = pd.read_excel(_SOURCE_XLSX, sheet_name="Report_Records")
    existing = load_condition_history()
    existing_keys = set()
    if not existing.empty:
        vib = existing[existing["module"] == "VIBRASI"]
        existing_keys = {
            (str(row.asset_id), str(row.test_date.date()) if pd.notna(row.test_date) else "")
            for row in vib.itertuples()
        }

    added, skipped_dup, skipped_no_asset = 0, 0, 0
    for _, row in records.iterrows():
        asset_id = str(row.get("Asset ID") or "").strip()
        if not asset_id or not get_asset(asset_id):
            skipped_no_asset += 1
            continue

        test_date = pd.to_datetime(row.get("Measurement Date"), errors="coerce")
        if pd.isna(test_date):
            continue
        test_date_str = test_date.strftime("%Y-%m-%d")

        if (asset_id, test_date_str) in existing_keys:
            skipped_dup += 1
            continue

        status = str(row.get("Status Vibrasi") or "Unknown").strip().title()
        pm_week = str(row.get("PM Week") or "-").strip()
        eq_class = str(row.get("Equipment Class (Normalized)") or "-").strip()

        summary = f"Hasil pengujian rutin vibrasi ({pm_week}), klasifikasi {eq_class}, status {status}."

        try:
            result = add_condition_record({
                "asset_id": asset_id,
                "module": "VIBRASI",
                "test_date": test_date_str,
                "condition": status,
                "summary": summary,
                "source_file": _SOURCE_XLSX.name,
            })
            print(f"Recorded: {result['record_id']} - {result['asset_name']} ({test_date_str}, {status})")
            added += 1
        except ValueError as exc:
            print(f"Skipped {asset_id} ({test_date_str}): {exc}")

    print(
        f"\nDone. Added {added} VIBRASI condition records "
        f"(skipped {skipped_dup} duplicates, {skipped_no_asset} rows with no matching registered asset)."
    )


if __name__ == "__main__":
    main()
