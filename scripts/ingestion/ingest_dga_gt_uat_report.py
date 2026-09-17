"""Ingest the "Detail Report DGA GT#1,GT#3 DAN UAT#3" workbook (sheets GT#1,
GT#2, GT#3, UAT) into DGA storage.

Each sheet is a per-transformer historical DGA log (2015-2024) with its own
column layout (GT#1 has extra load/temperature columns the others don't;
UAT's columns are all shifted one to the left) - handled here by scanning
each sheet's own header row for column names instead of hardcoding indices.

The 4 transformers already exist in the central Asset Registry (as
Main Transformer Unit 1/2/3 and UAT 3, from the CI19048 ingestion earlier),
which also seeded a handful of rows in the legacy dga_history_cbmai.csv
store (data/DGA - what src.dga_data's per-transformer search/detail views
read) for 2017-2019 only. This workbook has far more history per
transformer, so this script:

1. Appends every new (Equipment, Date) row to dga_history_cbmai.csv.
2. Appends the same readings as long-format rows to
   data/domain/DGA/measurements.csv (the canonical store the DGA page's
   Tren & Riwayat / Laporan tabs read).
3. Adds one VIBRASI-equivalent condition-history record per reading, using
   the sheet's own CONDITION column (IEEE C57.104 classification already
   computed by the plant) rather than recomputing it.

Idempotent on (Equipment, Date) for both stores; safe to re-run.
"""

import re
from pathlib import Path

import pandas as pd

from src.asset_registry import add_condition_record, load_condition_history
from src.dga_data import _dga_history_path, calculate_dga_diagnosis
from src.domain_measurements import append_measurements, load_measurements

_SOURCE_XLS = Path(
    r"D:\PDM\DGA JERANJANG\DGA\Detail report\REPORT DGA 2024"
    r"\Detail Report DGA GT#1,GT#3 DAN UAT#3...xls"
)

_SHEET_CONFIG = {
    "GT#1": {"asset_id": "AST-TRF-MAIN-1", "name": "Main Transformer Unit 1", "unit_csv": "UNIT_1"},
    "GT#2": {"asset_id": "AST-TRF-MAIN-2", "name": "Main Transformer Unit 2", "unit_csv": "UNIT_2"},
    "GT#3": {"asset_id": "AST-TRF-MAIN-3", "name": "Main Transformer Unit 3", "unit_csv": "UNIT_3"},
    "UAT": {"asset_id": "AST-TRF-UAT-3", "name": "Unit Auxiliary Transformer 3 (UAT 3)", "unit_csv": "UNIT_3"},
}

_HEADER_ROW = 8
_DATA_START_ROW = 10

_INDONESIAN_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "mei": 5, "jun": 6,
    "jul": 7, "agt": 8, "ags": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
}


def _parse_date(value) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    if pd.notna(parsed):
        return parsed
    match = re.match(r"(\d{1,2})-([A-Za-z]+)-(\d{2,4})", str(value).strip())
    if not match:
        return pd.NaT
    day, mon_text, year = match.groups()
    month = _INDONESIAN_MONTHS.get(mon_text.strip().lower()[:3])
    if not month:
        return pd.NaT
    year_full = int(year) + (2000 if len(year) == 2 else 0)
    return pd.Timestamp(year=year_full, month=month, day=int(day))


def _column_map(header_row: list) -> dict[str, int]:
    return {
        str(value).strip().upper().rstrip(): idx
        for idx, value in enumerate(header_row)
        if isinstance(value, str)
    }


def _sheet_rows(sheet_name: str) -> list[dict]:
    frame = pd.read_excel(_SOURCE_XLS, sheet_name=sheet_name, header=None)
    columns = _column_map(frame.iloc[_HEADER_ROW].tolist())

    def cell(row, name):
        idx = columns.get(name)
        return row.iloc[idx] if idx is not None else None

    rows = []
    for _, row in frame.iloc[_DATA_START_ROW:].iterrows():
        date_raw = cell(row, "DATE")
        if date_raw is None or (isinstance(date_raw, float) and pd.isna(date_raw)):
            continue
        test_date = _parse_date(date_raw)
        if pd.isna(test_date):
            continue

        def num(name):
            value = cell(row, name)
            parsed = pd.to_numeric(value, errors="coerce")
            return None if pd.isna(parsed) else float(parsed)

        gases = {
            "H2": num("H2") or 0.0, "CH4": num("CH4") or 0.0, "C2H6": num("C2H6") or 0.0,
            "C2H4": num("C2H4") or 0.0, "C2H2": num("C2H2") or 0.0,
            "CO": num("CO") or 0.0, "CO2": num("CO2") or 0.0,
        }
        if all(v == 0.0 for v in gases.values()):
            continue  # blank data row with only a date/no. carried over

        condition_text = cell(row, "CONDITION")
        condition_text = str(condition_text).strip() if isinstance(condition_text, str) and condition_text.strip() else None

        rows.append({
            "test_date": test_date.strftime("%Y-%m-%d"),
            "gases": gases,
            "water_content_ppm": num("H2O"),
            "beban_mw": num("BEBAN (MW)"),
            "condition_text": condition_text,
        })
    return rows


def main() -> None:
    if not _SOURCE_XLS.exists():
        print(f"Source workbook not found: {_SOURCE_XLS}")
        return

    legacy_path = _dga_history_path()
    legacy_existing = pd.read_csv(legacy_path) if legacy_path.exists() else pd.DataFrame()
    legacy_keys = set()
    if not legacy_existing.empty:
        legacy_keys = {
            (str(r.Equipment).strip().upper(), str(r.Date).strip())
            for r in legacy_existing.itertuples()
        }
    new_legacy_rows = []

    canonical_existing = load_measurements("DGA")
    canonical_keys = set()
    if not canonical_existing.empty:
        canonical_keys = {
            (str(r.equipment).strip().upper(), str(r.test_date.date()) if pd.notna(r.test_date) else "")
            for r in canonical_existing.itertuples()
        }
    new_canonical_rows = []

    history_existing = load_condition_history()
    history_keys = set()
    if not history_existing.empty:
        dga_hist = history_existing[history_existing["module"] == "DGA"]
        history_keys = {
            (str(r.asset_id), str(r.test_date.date()) if pd.notna(r.test_date) else "")
            for r in dga_hist.itertuples()
        }

    cond_added, cond_skipped = 0, 0

    for sheet_name, config in _SHEET_CONFIG.items():
        rows = _sheet_rows(sheet_name)
        print(f"{sheet_name} ({config['name']}): {len(rows)} readings parsed")

        for row in rows:
            eq_upper = config["name"].strip().upper()
            legacy_key = (eq_upper, row["test_date"])
            if legacy_key not in legacy_keys:
                new_legacy_rows.append({
                    "Date": row["test_date"], "Unit": config["unit_csv"], "UnitStatus": "ON",
                    "MonitoringType": "ROUTINE",
                    "MonitoringNote": f"Data historis DGA dari sheet {sheet_name}",
                    "Equipment": config["name"],
                    "H2": row["gases"]["H2"], "CH4": row["gases"]["CH4"], "C2H6": row["gases"]["C2H6"],
                    "C2H4": row["gases"]["C2H4"], "C2H2": row["gases"]["C2H2"],
                    "CO": row["gases"]["CO"], "CO2": row["gases"]["CO2"],
                    "WaterContent": row["water_content_ppm"] or 0.0, "BDV": 0.0,
                    "LoadMW": row["beban_mw"] or 0.0, "OilTemperatureC": 0.0, "WindingTemperatureC": 0.0,
                })
                legacy_keys.add(legacy_key)

            canonical_key = (eq_upper, row["test_date"])
            if canonical_key not in canonical_keys:
                identity = {
                    "equipment": config["name"], "asset_id": config["asset_id"],
                    "unit_name": config["unit_csv"].replace("_", " "), "test_date": row["test_date"],
                    "condition": row["condition_text"] or "", "source_file": sheet_name,
                }
                for gas_key, param_key, uom in (
                    ("H2", "h2", "ppm"), ("CH4", "ch4", "ppm"), ("C2H2", "c2h2", "ppm"),
                    ("C2H4", "c2h4", "ppm"), ("C2H6", "c2h6", "ppm"), ("CO", "co", "ppm"), ("CO2", "co2", "ppm"),
                ):
                    new_canonical_rows.append({**identity, "parameter": param_key,
                                                "value": row["gases"][gas_key], "raw_value": row["gases"][gas_key], "uom": uom})
                if row["water_content_ppm"] is not None:
                    new_canonical_rows.append({**identity, "parameter": "water_content_ppm",
                                                "value": row["water_content_ppm"], "raw_value": row["water_content_ppm"], "uom": "ppm"})
                if row["beban_mw"] is not None:
                    new_canonical_rows.append({**identity, "parameter": "beban_mw",
                                                "value": row["beban_mw"], "raw_value": row["beban_mw"], "uom": "MW"})
                canonical_keys.add(canonical_key)

            history_key = (config["asset_id"], row["test_date"])
            if history_key in history_keys:
                cond_skipped += 1
                continue
            diag = calculate_dga_diagnosis(row["gases"])
            condition = row["condition_text"] or diag["status"]
            summary = (
                f"Data historis DGA ({sheet_name}): TDCG={diag['tdcg']:.0f} ppm, "
                f"H2={row['gases']['H2']}, CH4={row['gases']['CH4']}, C2H4={row['gases']['C2H4']}, "
                f"C2H2={row['gases']['C2H2']}, kondisi {condition}"
            )
            try:
                add_condition_record({
                    "asset_id": config["asset_id"], "module": "DGA", "test_date": row["test_date"],
                    "condition": condition, "summary": summary, "source_file": sheet_name,
                })
                cond_added += 1
                history_keys.add(history_key)
            except ValueError as exc:
                print(f"Condition record skipped for {config['name']} ({row['test_date']}): {exc}")

    if new_legacy_rows:
        combined = pd.concat([legacy_existing, pd.DataFrame(new_legacy_rows)], ignore_index=True) if not legacy_existing.empty else pd.DataFrame(new_legacy_rows)
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(legacy_path, index=False)
    print(f"\nLegacy store (dga_history_cbmai.csv): +{len(new_legacy_rows)} rows")

    if new_canonical_rows:
        result = append_measurements("DGA", new_canonical_rows, batch_id="gt-uat-2024-report")
        print(f"Canonical store (measurements.csv): +{result['written']} rows (rejected {len(result['rejected'])})")
    else:
        print("Canonical store (measurements.csv): no new rows")

    print(f"Condition history: +{cond_added} records, {cond_skipped} duplicates")


if __name__ == "__main__":
    main()
