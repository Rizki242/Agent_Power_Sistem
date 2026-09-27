"""Sync the DGA GT Unit 1-3 Juli 2026 batch into the legacy CBMAI seed file.

This session's Juli 2026 ingest wrote 12 new (equipment, date) readings into
the canonical store (data/domain/DGA/measurements.csv) via the standard
domain_ingest pipeline (preview -> commit). That pipeline does not touch
data/DGA/dga_history_cbmai.csv - a separate, older seed of record that
src.dga_data.search_dga_transformers()/get_dga_transformer_detail() read
directly, and which both the React CBM Dashboard's DGA/Duval tab
(getDgaTransformers() -> /api/dga/transformers) and the chat assistant
(master_agent.py, chatbot.py) use for DGA answers. Vibrasi and Tribology
have no such second seed in the front-end path (confirmed: their frontend
surfaces call /api/v2/domain/*/measurements, which reads the canonical
store directly) - DGA is the one domain where "front juga update" requires
this second write, mirroring the precedent already set by
scripts/ingestion/ingest_dga_gt_uat_report.py.

Idempotent on (Equipment, Date); safe to re-run.
"""

import pandas as pd

from src.dga_data import _dga_history_path
from src.domain_measurements import load_measurements

_UNIT_CSV = {"UNIT 1": "UNIT_1", "UNIT 2": "UNIT_2", "UNIT 3": "UNIT_3"}
_SOURCE_FILE = "DGA GT Unit 1-3 2025-2026.csv"


def main() -> None:
    canonical = load_measurements("DGA")
    batch = canonical[canonical["source_file"] == _SOURCE_FILE]
    if batch.empty:
        print(f"No rows found with source_file={_SOURCE_FILE!r}; nothing to sync.")
        return

    pivot = (
        batch.pivot_table(
            index=["equipment", "unit_name", "test_date", "notes"],
            columns="parameter", values="value", aggfunc="first",
        )
        .reset_index()
    )

    legacy_path = _dga_history_path()
    legacy = pd.read_csv(legacy_path) if legacy_path.exists() else pd.DataFrame()
    existing_keys = set()
    if not legacy.empty:
        existing_keys = {
            (str(r.Equipment).strip().upper(), str(r.Date).strip())
            for r in legacy.itertuples()
        }

    new_rows = []
    for row in pivot.itertuples():
        test_date = pd.Timestamp(row.test_date).strftime("%Y-%m-%d")
        key = (str(row.equipment).strip().upper(), test_date)
        if key in existing_keys:
            continue

        def val(name, default=0.0):
            v = getattr(row, name, None)
            return default if v is None or pd.isna(v) else float(v)

        new_rows.append({
            "Date": test_date, "Unit": None, "UnitStatus": None,
            "MonitoringType": None, "MonitoringNote": None,
            "Equipment": row.equipment,
            "H2": val("h2"), "CH4": val("ch4"), "C2H6": val("c2h6"),
            "C2H4": val("c2h4"), "C2H2": val("c2h2"),
            "CO": val("co"), "CO2": val("co2"),
            "WaterContent": val("h2o"), "BDV": val("bdv_kv"),
            "LoadMW": val("beban_mw"), "OilTemperatureC": val("temp_oil"),
            "WindingTemperatureC": val("temp_winding"), "TDCG": val("tdcg"),
            # Left blank rather than guessed: this column is metadata only
            # (search_dga_transformers() computes status live from the gas
            # values via calculate_dga_diagnosis(), never reads Condition),
            # and the source sheet gives no plant-assigned condition label
            # for these specific rows - matching (not guessing) beats a
            # fabricated "Normal" on a row DGAAgent independently flags as
            # T3/ALERT (Main Transformer Unit 2, 2026-06-29).
            "Condition": None,
        })
        existing_keys.add(key)

    if not new_rows:
        print("All rows already present in dga_history_cbmai.csv; nothing to do.")
        return

    merged = pd.concat([legacy, pd.DataFrame(new_rows)], ignore_index=True)
    merged.to_csv(legacy_path, index=False)
    print(f"Appended {len(new_rows)} rows to {legacy_path} (was {len(legacy)}, now {len(merged)}).")
    for row in new_rows:
        print(f"  {row['Equipment']} {row['Date']}")


if __name__ == "__main__":
    main()
