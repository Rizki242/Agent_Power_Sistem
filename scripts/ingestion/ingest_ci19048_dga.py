"""
Script to ingest 18 Transformer Assets and all DGA test history from
Laporan CI19048 into the system:
1. Central Asset Registry (data/MCSA/config/asset_registry.json)
2. Condition History (data/MCSA/asset_management/condition_history.csv)
3. DGA History (data/DGA/dga_history_cbmai.csv)
"""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd

from src.asset_registry import upsert_asset, add_condition_record, list_assets
from src.dga_data import calculate_dga_diagnosis, _dga_history_path

# Load the extracted data from CI19048
# Intermediate extraction output lives in scripts/scratch/ (gitignored), see CLAUDE.md.
_EXTRACT_JSON = Path(__file__).resolve().parents[1] / "scratch" / "extracted_trafo_ci19048.json"
with open(_EXTRACT_JSON, "r", encoding="utf-8") as f:
    trafo_list = json.load(f)

print(f"Loaded {len(trafo_list)} transformers from extracted_trafo_ci19048.json")

# Mapping configuration for the 18 transformers
TRAFO_CONFIG = {
    "MAIN TRAFO UNIT 1": {
        "asset_id": "AST-TRF-MAIN-1",
        "name": "Main Transformer Unit 1",
        "unit": "UNIT 1",
        "unit_csv": "UNIT_1",
        "equipment_type": "Power Transformer (Step-Up)",
        "voltage_level": "165 kV / 6.3 kV",
        "aliases": ["MAIN TRAFO UNIT 1", "MAIN TRANSFORMER 1", "GT 1", "GENERATOR TRANSFORMER 1", "TRAFO UTAMA 1"],
    },
    "TRAFO 1 ESP UNIT 1": {
        "asset_id": "AST-TRF-ESP1-1",
        "name": "Transformer ESP 1 Unit 1",
        "unit": "UNIT 1",
        "unit_csv": "UNIT_1",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 1 ESP UNIT 1", "TRAFO ESP 1 UNIT 1", "ESP 1 UNIT 1", "TR-ESP-1-1"],
    },
    "TRAFO 2 ESP UNIT 1": {
        "asset_id": "AST-TRF-ESP2-1",
        "name": "Transformer ESP 2 Unit 1",
        "unit": "UNIT 1",
        "unit_csv": "UNIT_1",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 2 ESP UNIT 1", "TRAFO ESP 2 UNIT 1", "ESP 2 UNIT 1", "TR-ESP-2-1"],
    },
    "TRAFO 3 ESP UNIT 1": {
        "asset_id": "AST-TRF-ESP3-1",
        "name": "Transformer ESP 3 Unit 1",
        "unit": "UNIT 1",
        "unit_csv": "UNIT_1",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 3 ESP UNIT 1", "TRAFO ESP 3 UNIT 1", "ESP 3 UNIT 1", "TR-ESP-3-1"],
    },
    "TRAFO 4 ESP UNIT 1": {
        "asset_id": "AST-TRF-ESP4-1",
        "name": "Transformer ESP 4 Unit 1",
        "unit": "UNIT 1",
        "unit_csv": "UNIT_1",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 4 ESP UNIT 1", "TRAFO ESP 4 UNIT 1", "ESP 4 UNIT 1", "TR-ESP-4-1"],
    },
    "MAIN TRAFO UNIT 3": {
        "asset_id": "AST-TRF-MAIN-3",
        "name": "Main Transformer Unit 3",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "Power Transformer (Step-Up)",
        "voltage_level": "150 kV / 6.3 kV",
        "aliases": ["MAIN TRAFO UNIT 3", "MAIN TRANSFORMER 3", "GT 3", "GENERATOR TRANSFORMER 3", "TRAFO UTAMA 3"],
    },
    "UAT 3": {
        "asset_id": "AST-TRF-UAT-3",
        "name": "Unit Auxiliary Transformer 3 (UAT 3)",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "Unit Auxiliary Transformer (UAT)",
        "voltage_level": "6.3 kV / 6.3 kV",
        "aliases": ["UAT 3", "UAT #3", "UNIT AUXILIARY TRANSFORMER 3", "UAT-3", "TRAFO UAT 3", "TRF-UAT-3"],
    },
    "TRAFO 1 ESP UNIT 3": {
        "asset_id": "AST-TRF-ESP1-3",
        "name": "Transformer ESP 1 Unit 3",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 415 V",
        "aliases": ["TRAFO 1 ESP UNIT 3", "TRAFO ESP 1 UNIT 3", "ESP 1 UNIT 3", "TR-ESP-1-3"],
    },
    "TRAFO 2 ESP UNIT 3": {
        "asset_id": "AST-TRF-ESP2-3",
        "name": "Transformer ESP 2 Unit 3",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 415 V",
        "aliases": ["TRAFO 2 ESP UNIT 3", "TRAFO ESP 2 UNIT 3", "ESP 2 UNIT 3", "TR-ESP-2-3"],
    },
    "TRAFO 3 ESP UNIT 3": {
        "asset_id": "AST-TRF-ESP3-3",
        "name": "Transformer ESP 3 Unit 3",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 415 V",
        "aliases": ["TRAFO 3 ESP UNIT 3", "TRAFO ESP 3 UNIT 3", "ESP 3 UNIT 3", "TR-ESP-3-3"],
    },
    "TRAFO 4 UNIT 3": {
        "asset_id": "AST-TRF-ESP4-3",
        "name": "Transformer ESP 4 Unit 3",
        "unit": "UNIT 3",
        "unit_csv": "UNIT_3",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 415 V",
        "aliases": ["TRAFO 4 UNIT 3", "TRAFO 4 ESP UNIT 3", "TRAFO ESP 4 UNIT 3", "ESP 4 UNIT 3", "TR-ESP-4-3"],
    },
    "ASH HANDLING-1": {
        "asset_id": "AST-TRF-ASH-1",
        "name": "Ash Handling Transformer 1",
        "unit": "COMMON",
        "unit_csv": "COMMON",
        "equipment_type": "Auxiliary Transformer",
        "voltage_level": "6.3 kV / 400 V",
        "aliases": ["ASH HANDLING-1", "ASH HANDLING 1", "TRAFO ASH HANDLING 1", "TR-ASH-1"],
    },
    "ASH HANDLING-2": {
        "asset_id": "AST-TRF-ASH-2",
        "name": "Ash Handling Transformer 2",
        "unit": "COMMON",
        "unit_csv": "COMMON",
        "equipment_type": "Auxiliary Transformer",
        "voltage_level": "6.3 kV / 400 V",
        "aliases": ["ASH HANDLING-2", "ASH HANDLING 2", "TRAFO ASH HANDLING 2", "TR-ASH-2"],
    },
    "TRAFO 1 ESP UNIT 2": {
        "asset_id": "AST-TRF-ESP1-2",
        "name": "Transformer ESP 1 Unit 2",
        "unit": "UNIT 2",
        "unit_csv": "UNIT_2",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 1 ESP UNIT 2", "TRAFO ESP 1 UNIT 2", "ESP 1 UNIT 2", "TR-ESP-1-2"],
    },
    "TRAFO 2 ESP UNIT 2": {
        "asset_id": "AST-TRF-ESP2-2",
        "name": "Transformer ESP 2 Unit 2",
        "unit": "UNIT 2",
        "unit_csv": "UNIT_2",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 2 ESP UNIT 2", "TRAFO ESP 2 UNIT 2", "ESP 2 UNIT 2", "TR-ESP-2-2"],
    },
    "TRAFO 3 ESP UNIT 2": {
        "asset_id": "AST-TRF-ESP3-2",
        "name": "Transformer ESP 3 Unit 2",
        "unit": "UNIT 2",
        "unit_csv": "UNIT_2",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 3 ESP UNIT 2", "TRAFO ESP 3 UNIT 2", "ESP 3 UNIT 2", "TR-ESP-3-2"],
    },
    "TRAFO 4 ESP UNIT 2": {
        "asset_id": "AST-TRF-ESP4-2",
        "name": "Transformer ESP 4 Unit 2",
        "unit": "UNIT 2",
        "unit_csv": "UNIT_2",
        "equipment_type": "ESP Transformer Rectifier",
        "voltage_level": "72 kV / 380 V",
        "aliases": ["TRAFO 4 ESP UNIT 2", "TRAFO ESP 4 UNIT 2", "ESP 4 UNIT 2", "TR-ESP-4-2"],
    },
    "MAIN TRAFO UNIT 2": {
        "asset_id": "AST-TRF-MAIN-2",
        "name": "Main Transformer Unit 2",
        "unit": "UNIT 2",
        "unit_csv": "UNIT_2",
        "equipment_type": "Power Transformer (Step-Up)",
        "voltage_level": "170 kV / 6.3 kV",
        "aliases": ["MAIN TRAFO UNIT 2", "MAIN TRANSFORMER 2", "GT 2", "GENERATOR TRANSFORMER 2", "TRAFO UTAMA 2"],
    },
}

# 1. Register Transformer Assets into Central Asset Registry
print("\n--- 1. Upserting Assets into Central Asset Registry ---")
for t in trafo_list:
    raw_name = t["unit_name"]
    cfg = TRAFO_CONFIG.get(raw_name)
    if not cfg:
        print(f"Warning: No config for {raw_name}")
        continue
    
    kva_str = t.get("kva", "-")
    if "PRI" in kva_str:
        kva_str = "-"
    
    specs = {
        "manufacturer": t.get("mfg", "-"),
        "date_mfg": t.get("date_mfg", "-"),
        "serial_number": t.get("sn", "-"),
        "rated_capacity_kva": kva_str,
        "primary_voltage": t.get("pri", "-"),
        "secondary_voltage": t.get("sec", "-"),
        "oil_litres": t.get("litres", "-"),
        "oil_type": "Mineral Oil",
        "transformer_class": t.get("class", "-"),
        "impedance": t.get("impedence", "-"),
        "weight_kg": t.get("weight_kg", "-"),
        "phase": t.get("phase", "-"),
        "source_report": "CI19048 (PT IP UJP PLTU Jeranjang - Desember 2019)",
    }
    
    # Determine latest condition
    latest_status = "Normal"
    dga_rows = t.get("dga_rows", [])
    if dga_rows:
        latest_dga = dga_rows[-1]
        gases = {
            "H2": latest_dga.get("H2", 0),
            "CH4": latest_dga.get("CH4", 0),
            "C2H6": latest_dga.get("C2H6", 0),
            "C2H4": latest_dga.get("C2H4", 0),
            "C2H2": latest_dga.get("C2H2", 0),
            "CO": latest_dga.get("CO", 0),
            "CO2": latest_dga.get("CO2", 0),
        }
        diag = calculate_dga_diagnosis(gases)
        if diag["status"] in ("WARNING", "HIGH"):
            latest_status = "Warning" if diag["status"] == "WARNING" else "Critical"
        elif diag["status"] == "PREWARNING":
            latest_status = "Prewarning"
        else:
            latest_status = "Normal"

    asset_payload = {
        "asset_id": cfg["asset_id"],
        "name": cfg["name"],
        "unit": cfg["unit"],
        "equipment_type": cfg["equipment_type"],
        "voltage_level": cfg["voltage_level"],
        "lifecycle_status": "Aktif",
        "monitoring_modules": ["DGA", "PD", "THERMAL"],
        "kks": f"TRF-{cfg['asset_id'].split('-')[-1]}",
        "aliases": cfg["aliases"],
        "specs": specs,
        "status": latest_status,
        "notes": f"Aset Transformer diimpor dari Laporan Oil Analisis CI19048 CENNIX/TxM Services (S/N: {t.get('sn', '-')})",
    }
    
    upserted = upsert_asset(asset_payload)
    print(f"Upserted: {upserted['asset_id']} - {upserted['name']} (S/N: {specs['serial_number']}, Status: {latest_status})")

# 2. Append DGA History Rows to data/DGA/dga_history_cbmai.csv
print("\n--- 2. Ingesting DGA Test History ---")
csv_path = _dga_history_path()
existing_df = pd.DataFrame()
if csv_path.exists():
    try:
        existing_df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error reading existing CSV: {e}")

# Build new rows
new_records = []
for t in trafo_list:
    raw_name = t["unit_name"]
    cfg = TRAFO_CONFIG.get(raw_name)
    if not cfg:
        continue

    dga_rows = t.get("dga_rows", [])
    for r in dga_rows:
        # Convert date to YYYY-MM-DD
        dt_str = r["date"]
        try:
            dt = datetime.strptime(dt_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        except:
            dt = dt_str

        # Match water content if available
        w_ppm = 0.0
        w_temp = 0.0
        for w in t.get("water_rows", []):
            if w.get("date") == dt_str:
                try:
                    w_ppm = float(w.get("ppm", 0))
                    w_temp = float(w.get("temp", 0))
                except:
                    pass
                break
        
        # Match dielectric (BDV) if available
        bdv = 0.0
        for s in t.get("screen_rows", []):
            if s.get("date") == dt_str:
                try:
                    bdv = float(s.get("dielectric", 0))
                except:
                    pass
                break

        # Check if already present in existing_df to avoid duplicate entries
        if not existing_df.empty:
            # Check by Equipment and Date
            match = existing_df[
                (existing_df["Equipment"].astype(str).str.upper() == cfg["name"].upper()) &
                (pd.to_datetime(existing_df["Date"], errors="coerce") == pd.to_datetime(dt))
            ]
            if not match.empty:
                continue

        rec = {
            "Date": dt,
            "Unit": cfg["unit_csv"],
            "UnitStatus": "ONLINE",
            "MonitoringType": "ROUTINE",
            "MonitoringNote": f"Uji Lab CI19048 CENNIX (S/N: {t.get('sn', '-')})",
            "Equipment": cfg["name"],
            "H2": r.get("H2", 0.0),
            "CH4": r.get("CH4", 0.0),
            "C2H6": r.get("C2H6", 0.0),
            "C2H4": r.get("C2H4", 0.0),
            "C2H2": r.get("C2H2", 0.0),
            "CO": r.get("CO", 0.0),
            "CO2": r.get("CO2", 0.0),
            "WaterContent": w_ppm,
            "BDV": bdv,
            "LoadMW": 0.0,
            "OilTemperatureC": w_temp,
            "WindingTemperatureC": 0.0,
        }
        new_records.append(rec)

print(f"New DGA history rows to insert: {len(new_records)}")
if new_records:
    new_df = pd.DataFrame(new_records)
    combined_df = pd.concat([existing_df, new_df], ignore_index=True) if not existing_df.empty else new_df
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(csv_path, index=False)
    print(f"Saved {len(combined_df)} total DGA rows to {csv_path}")

# 3. Add Condition History records for the latest test date
print("\n--- 3. Adding Latest Condition Records into Central History ---")
for t in trafo_list:
    raw_name = t["unit_name"]
    cfg = TRAFO_CONFIG.get(raw_name)
    if not cfg:
        continue
    
    dga_rows = t.get("dga_rows", [])
    if not dga_rows:
        continue
    latest_dga = dga_rows[-1]
    dt_str = latest_dga["date"]
    try:
        dt = datetime.strptime(dt_str, "%d/%m/%Y").strftime("%Y-%m-%d")
    except:
        dt = dt_str

    gases = {
        "H2": latest_dga.get("H2", 0),
        "CH4": latest_dga.get("CH4", 0),
        "C2H6": latest_dga.get("C2H6", 0),
        "C2H4": latest_dga.get("C2H4", 0),
        "C2H2": latest_dga.get("C2H2", 0),
        "CO": latest_dga.get("CO", 0),
        "CO2": latest_dga.get("CO2", 0),
    }
    diag = calculate_dga_diagnosis(gases)
    
    # Water content
    w_ppm = 0.0
    for w in t.get("water_rows", []):
        if w.get("date") == dt_str:
            try:
                w_ppm = float(w.get("ppm", 0))
            except:
                pass
            break
            
    summary_text = (
        f"DGA Hasil Uji Lab CI19048: TDCG={diag['tdcg']} ppm ({diag['ieee_condition']}), "
        f"Duval={diag['duval_diagnosis']}, Status={diag['status']}, "
        f"H2={gases['H2']}, CH4={gases['CH4']}, C2H4={gases['C2H4']}, C2H2={gases['C2H2']}"
    )
    if w_ppm > 0:
        summary_text += f", Water={w_ppm} ppm"

    cond_rec = {
        "asset_id": cfg["asset_id"],
        "module": "DGA",
        "test_date": dt,
        "condition": diag["status"],
        "summary": summary_text,
        "source_file": "Laporan - CI19048 PT IP UJP PLTU Jeranjang - Desember 2019.pdf",
    }
    try:
        res = add_condition_record(cond_rec)
        print(f"Condition recorded for {cfg['name']}: {res['record_id']} ({res['condition']})")
    except Exception as e:
        print(f"Error adding condition for {cfg['name']}: {e}")

print("\nIngestion complete!")

