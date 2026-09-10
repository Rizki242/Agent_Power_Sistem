"""Equipment API router."""

from __future__ import annotations

import math
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from pple.api.schemas.core import EquipmentListResponse
from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
from src.standards import generate_initial_analysis

router = APIRouter(prefix="/api", tags=["equipment"])

# Module-level cached dataframes provider fallback
_cached_raw_df: Optional[pd.DataFrame] = None
_cached_latest_df: Optional[pd.DataFrame] = None
_data_frames_provider: Optional[Callable[[], Tuple[pd.DataFrame, pd.DataFrame]]] = None


def set_data_frames_provider(provider: Callable[[], Tuple[pd.DataFrame, pd.DataFrame]]) -> None:
    """Inject shared data frames provider (e.g. from api_server)."""
    global _data_frames_provider
    _data_frames_provider = provider


def get_data_frames() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Retrieve raw and latest MCSA dataframes."""
    global _cached_raw_df, _cached_latest_df, _data_frames_provider
    if _data_frames_provider is not None:
        return _data_frames_provider()

    if _cached_raw_df is None or _cached_latest_df is None:
        data_file = get_data_path("mcsa_updated.csv")
        if not os.path.exists(data_file):
            data_file = get_data_path("Report MCSA.xls")
        _cached_raw_df = load_mcsa_data(data_file)
        _cached_latest_df = get_latest_data(_cached_raw_df)
    return _cached_raw_df, _cached_latest_df


@router.get("/equipment", response_model=EquipmentListResponse)
def get_equipment_list(
    unit: Optional[str] = Query(None),
    voltage: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    df_raw, df_latest = get_data_frames()
    if df_latest.empty or "Equipment" not in df_latest.columns:
        return {"equipment": [], "count": 0}

    cond_rows = (
        df_latest[df_latest["Parameter"] == "Kondisi"].copy()
        if "Parameter" in df_latest.columns
        else pd.DataFrame()
    )
    if cond_rows.empty:
        cond_rows = df_latest.drop_duplicates(subset=["Equipment"]).copy()

    # Filter by unit, voltage, search, status
    if unit and unit.upper() != "ALL" and "Unit_Name" in cond_rows.columns:
        cond_rows = cond_rows[cond_rows["Unit_Name"].astype(str).str.upper() == unit.upper()]
    if voltage and voltage.upper() != "ALL" and "Voltage_Level" in cond_rows.columns:
        cond_rows = cond_rows[cond_rows["Voltage_Level"].astype(str).str.upper() == voltage.upper()]
    if status and status.upper() != "ALL" and "Raw_Value" in cond_rows.columns:
        cond_rows = cond_rows[
            cond_rows["Raw_Value"].astype(str).str.strip().str.capitalize() == status.capitalize()
        ]
    if search:
        s_term = search.lower().strip()
        cond_rows = cond_rows[cond_rows["Equipment"].astype(str).str.lower().str.contains(s_term)]

    eq_names = cond_rows["Equipment"].dropna().unique()

    result = []
    for eq in eq_names:
        eq_data = df_latest[df_latest["Equipment"] == eq]
        cond_val = "Normal"
        c_row = eq_data[eq_data["Parameter"] == "Kondisi"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not c_row.empty:
            cond_val = str(c_row["Raw_Value"].iloc[0]).strip().capitalize()

        last_date = ""
        if "Date" in eq_data.columns and not eq_data["Date"].dropna().empty:
            last_date = str(eq_data["Date"].dropna().iloc[0])[:10]

        unit_val = str(eq_data["Unit_Name"].iloc[0]) if "Unit_Name" in eq_data.columns and not eq_data.empty else ""
        volt_val = str(eq_data["Voltage_Level"].iloc[0]) if "Voltage_Level" in eq_data.columns and not eq_data.empty else ""

        rb_status = "Normal"
        rb_row = eq_data[eq_data["Parameter"] == "Rotorbar"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not rb_row.empty:
            rb_status = str(rb_row["Raw_Value"].iloc[0]).strip().capitalize()

        brg_status = "Normal"
        brg_row = eq_data[eq_data["Parameter"] == "Bearing"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not brg_row.empty:
            brg_status = str(brg_row["Raw_Value"].iloc[0]).strip().capitalize()

        result.append({
            "equipment": str(eq),
            "unit": unit_val,
            "voltage": volt_val,
            "status": cond_val,
            "condition": cond_val,
            "rotorbar_status": rb_status,
            "bearing_status": brg_status,
            "last_date": last_date,
            "date": last_date,
        })

    return {"equipment": result, "count": len(result)}


@router.get("/equipment/{equipment_name}")
def get_equipment_detail(equipment_name: str):
    df_raw, df_latest = get_data_frames()

    eq_latest = df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment_name.upper()]
    eq_history = df_raw[df_raw["Equipment"].astype(str).str.upper() == equipment_name.upper()]

    if eq_history.empty and eq_latest.empty:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Target dataframe for parameters
    target_df = eq_latest if not eq_latest.empty else eq_history.tail(20)

    # Structured parameters dictionary
    structured_params = {}
    perf_summary = {}
    latest_params = {}

    cond_val = "Normal"
    latest_date_str = ""

    for _, row in target_df.iterrows():
        p_name = str(row.get("Parameter", "")).strip()
        p_raw = str(row.get("Raw_Value", "")).strip()
        p_unit = str(row.get("Unit", "")) if pd.notna(row.get("Unit")) else ""
        if p_unit == "nan":
            p_unit = ""

        if not p_name:
            continue

        latest_params[p_name] = p_raw

        if p_name.startswith("Ringkasan Kinerja - ") or p_name.startswith("Performance Summary"):
            short_k = p_name.replace("Ringkasan Kinerja - ", "").replace("Performance Summary - ", "")
            perf_summary[short_k] = p_raw
        else:
            structured_params[p_name] = {
                "value": p_raw,
                "unit": p_unit,
            }

        if p_name == "Kondisi":
            cond_val = p_raw.capitalize()

        if "Date" in row and pd.notna(row["Date"]) and not latest_date_str:
            latest_date_str = str(row["Date"])[:10]

    # History trend data
    history_records = []
    if "Date" in eq_history.columns:
        dates = eq_history["Date"].dropna().unique()
        for d in sorted(dates)[-12:]:
            sub = eq_history[eq_history["Date"] == d]
            rec = {"date": str(d)[:10]}
            for _, r in sub.iterrows():
                param_key = str(r["Parameter"])
                raw_v = r.get("Raw_Value")
                try:
                    f_val = float(raw_v)
                    if math.isnan(f_val) or math.isinf(f_val):
                        rec[param_key] = str(raw_v) if (raw_v is not None and str(raw_v) != "nan") else ""
                    else:
                        rec[param_key] = f_val
                except (ValueError, TypeError):
                    rec[param_key] = str(raw_v) if (raw_v is not None and str(raw_v) != "nan") else ""
            history_records.append(rec)

    analysis = generate_initial_analysis(target_df) if not target_df.empty else {"recommendations": [], "references": []}

    unit_val = str(target_df["Unit_Name"].iloc[0]) if "Unit_Name" in target_df.columns and not target_df.empty else ""
    volt_val = str(target_df["Voltage_Level"].iloc[0]) if "Voltage_Level" in target_df.columns and not target_df.empty else ""

    # Nameplate specifications
    spec_dict = {}
    try:
        from src.data_loader import load_nameplate_csv

        df_np = load_nameplate_csv()
        if not df_np.empty:
            eq_np = df_np[df_np["Equipment"].astype(str).str.upper() == equipment_name.upper()]
            if not eq_np.empty:
                raw_dict = eq_np.iloc[0].to_dict()
                spec_dict = {
                    k: (str(v) if pd.notna(v) and str(v) != "nan" else "")
                    for k, v in raw_dict.items()
                }
    except Exception:
        pass

    # Build categorized telemetry groups
    electrical_params = {}
    pq_params = {}
    rotor_params = {}
    bearing_params = {}
    other_params = {}

    for k, v in structured_params.items():
        k_lower = k.lower()
        val_str = str(v.get("value", "")).strip()
        if not val_str or val_str in ("nan", "None"):
            val_str = "-"
        v_clean = {"value": val_str, "unit": v.get("unit", "")}

        if any(w in k_lower for w in ["current", "voltage", "arus", "tegangan", "dev current", "dev voltage"]):
            if "thd" in k_lower:
                pq_params[k] = v_clean
            else:
                electrical_params[k] = v_clean
        elif any(w in k_lower for w in ["thd", "power factor", "real power", "load", "beban", "pf"]):
            pq_params[k] = v_clean
        elif any(w in k_lower for w in ["rotor", "sideband", "rb", "se fund", "se harm"]):
            rotor_params[k] = v_clean
        elif any(w in k_lower for w in ["bearing", "kondisi", "status"]):
            bearing_params[k] = v_clean
        else:
            other_params[k] = v_clean

    telemetry_groups = {
        "electrical": electrical_params,
        "power_quality": pq_params,
        "rotor_bar": rotor_params,
        "mechanical": bearing_params,
        "other": other_params,
    }

    return {
        "equipment": equipment_name,
        "unit": unit_val,
        "voltage": volt_val,
        "condition": cond_val,
        "latest_date": latest_date_str,
        "parameters": structured_params,
        "latest_parameters": latest_params,
        "telemetry_groups": telemetry_groups,
        "specification": spec_dict,
        "performance_summary": perf_summary,
        "recommendations": analysis.get("recommendations", []),
        "references": analysis.get("references", []),
        "history": history_records,
        "analysis": analysis,
    }
