"""Standby augmentation for the MCSA latest-data snapshot.

Moved verbatim out of app.py's standby block so the Streamlit entrypoint
only orchestrates session-state caching. Equipment in the reference scope
without any measurement in the reference month is marked Standby instead
of silently disappearing from the dashboard. Behavior is unchanged.
"""

import json
import os
from typing import Tuple

import pandas as pd

from src.data_loader import get_data_path
from src.equipment_canon import canon_unit_name, canon_voltage_level, norm_equipment


def compute_standby(
    df: pd.DataFrame,
    df_latest: pd.DataFrame,
    df_latest_all: pd.DataFrame,
    eq_master_df: pd.DataFrame,
    master_norm_to_unit: dict,
    master_norm_to_volt: dict,
    date_end,
    standby_scope,
    sel_unit: str,
    sel_volt: str,
    required_month_params: list,
) -> Tuple[pd.DataFrame, dict, pd.DataFrame, pd.DataFrame]:
    """Return (df_latest_augmented, standby_report, df_month, meta_df)."""
    df_latest_augmented = df_latest.copy()

    ref_dt = pd.Timestamp(date_end)
    month_start = ref_dt.replace(day=1)
    month_end = month_start + pd.offsets.MonthEnd(0)

    df_month = df.copy()
    df_month["Date"] = pd.to_datetime(df_month.get("Date", pd.NaT), errors="coerce")
    df_month = df_month[(df_month["Date"] >= month_start) & (df_month["Date"] <= month_end)]

    if "Unit_Name" in df_month.columns:
        df_month["_unit_canon"] = df_month["Unit_Name"].astype(str).map(canon_unit_name)
    if "Voltage_Level" in df_month.columns:
        df_month["_volt_canon"] = df_month["Voltage_Level"].astype(str).map(canon_voltage_level)
    df_month["_norm"] = df_month.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
    df_month["_unit_master"] = df_month["_norm"].map(master_norm_to_unit)
    df_month["_volt_master"] = df_month["_norm"].map(master_norm_to_volt)
    df_month["_unit_scope"] = df_month["_unit_master"]
    if "_unit_canon" in df_month.columns:
        df_month["_unit_scope"] = df_month["_unit_scope"].fillna(df_month["_unit_canon"])
    df_month["_volt_scope"] = df_month["_volt_master"]
    if "_volt_canon" in df_month.columns:
        df_month["_volt_scope"] = df_month["_volt_scope"].fillna(df_month["_volt_canon"])

    base_meta_df = eq_master_df if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty else df_latest_all
    meta_df = base_meta_df.copy()
    if "Unit_Name" in meta_df.columns:
        meta_df["_unit_canon"] = meta_df["Unit_Name"].astype(str).map(canon_unit_name)
    if "Voltage_Level" in meta_df.columns:
        meta_df["_volt_canon"] = meta_df["Voltage_Level"].astype(str).map(canon_voltage_level)
    if standby_scope and standby_scope.startswith("Per Unit"):
        if sel_unit != "All":
            if "_unit_canon" in meta_df.columns:
                meta_df = meta_df[meta_df["_unit_canon"] == sel_unit]
            df_month = df_month[df_month["_unit_scope"] == sel_unit]
        if sel_volt != "All":
            if "_volt_canon" in meta_df.columns:
                meta_df = meta_df[meta_df["_volt_canon"] == sel_volt]
            df_month = df_month[df_month["_volt_scope"] == sel_volt]
    else:
        if sel_volt != "All":
            if "_volt_canon" in meta_df.columns:
                meta_df = meta_df[meta_df["_volt_canon"] == sel_volt]
            df_month = df_month[df_month["_volt_scope"] == sel_volt]

    meta_eq = meta_df.get("Equipment", pd.Series(dtype=str)).astype(str)
    meta_norm = meta_eq.map(norm_equipment)
    meta_df = meta_df.assign(_norm=meta_norm)
    norm_to_eq = meta_df.drop_duplicates(subset=["_norm"]).set_index("_norm")["Equipment"].to_dict() if not meta_df.empty else {}
    eq_universe_norm = set(norm_to_eq.keys())

    df_month_req = df_month.copy()
    raw_ok = pd.Series([False] * len(df_month_req), index=df_month_req.index)
    val_ok = pd.Series([False] * len(df_month_req), index=df_month_req.index)
    if "Raw_Value" in df_month_req.columns:
        rv = df_month_req["Raw_Value"]
        raw_ok = rv.notna() & rv.astype(str).str.strip().ne("")
    if "Value" in df_month_req.columns:
        vv = df_month_req["Value"]
        val_ok = vv.notna()
    df_month_req = df_month_req[raw_ok | val_ok]
    eq_present_raw = df_month_req.get("Equipment", pd.Series(dtype=str)).astype(str)
    eq_present_norm = set(eq_present_raw.map(norm_equipment))
    missing_norm = sorted([n for n in (eq_universe_norm - eq_present_norm) if n and n.lower() not in {"nan", "none"}])
    standby_eq = [norm_to_eq.get(n, n) for n in missing_norm]
    eq_present = sorted([norm_to_eq.get(n, n) for n in (eq_universe_norm & eq_present_norm) if n and n.lower() not in {"nan", "none"}])
    eq_universe = sorted([norm_to_eq.get(n, n) for n in eq_universe_norm if n and n.lower() not in {"nan", "none"}])

    reasons_path = get_data_path("config", "standby_reasons.json")
    reasons_data = {}
    try:
        if os.path.exists(reasons_path):
            with open(reasons_path, "r", encoding="utf-8") as fp:
                reasons_data = json.load(fp)
    except Exception:
        reasons_data = {}

    month_key = month_start.strftime("%Y-%m")
    reasons_for_month = reasons_data.get(month_key, {})

    standby_report = {
        "month_start": month_start,
        "month_end": month_end,
        "required_params": required_month_params,
        "scope": standby_scope,
        "sel_unit": sel_unit,
        "sel_volt": sel_volt,
        "eq_universe": eq_universe,
        "eq_present": eq_present,
        "eq_missing": standby_eq,
        "standby_reasons": reasons_for_month,
    }

    if standby_eq:
        meta_map = meta_df.drop_duplicates(subset=["Equipment"]).set_index("Equipment") if "Equipment" in meta_df.columns else pd.DataFrame()
        month_name = month_start.strftime("%b").upper()
        year_val = int(month_start.year)
        standby_rows = []
        for eq in standby_eq:
            unit_name = "Unknown"
            volt_name = "Unknown"
            full_name = eq
            if not meta_map.empty and eq in meta_map.index:
                r = meta_map.loc[eq]
                if isinstance(r, pd.DataFrame):
                    r = r.iloc[0]
                unit_name = r.get("Unit_Name", unit_name)
                volt_name = r.get("Voltage_Level", volt_name)
                full_name = r.get("Full_Name", full_name)
            standby_rows.append({
                "Equipment": eq,
                "Parameter": "Kondisi",
                "Month": month_name,
                "Year": year_val,
                "Month_Name": month_name,
                "Date": str(month_end.date()),
                "Raw_Value": "Standby",
                "Value": None,
                "Unit": "",
                "Limit": "",
                "Status": "Standby",
                "Status_Category": "Standby",
                "Status_Level": 0,
                "Unit_Name": unit_name,
                "Voltage_Level": volt_name,
                "Full_Name": full_name
            })
        df_latest_augmented = pd.concat([df_latest_augmented, pd.DataFrame(standby_rows)], ignore_index=True)

    return df_latest_augmented, standby_report, df_month, meta_df
