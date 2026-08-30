"""Shared equipment-code canonicalization and MCSA overall-status rules.

Moved verbatim out of app.py and src/pages/dashboard_page.py, which carried
duplicate copies of these helpers, plus the equipment-master loading block
from app.py. Keeping them here lets the Streamlit entrypoint stay a thin
dispatcher while the vocabulary stays identical everywhere.
"""

import json
import os
import re
from typing import Optional, Tuple

import pandas as pd

from src.components.status_colors import canon_condition_status
from src.standards import calculate_condition


def norm_equipment(x) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(x or "")).upper()


def canon_unit_name(x) -> str:
    s = str(x or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    s0 = s.replace(" ", "")
    if s0 == "UNIT1":
        return "UNIT 1"
    if s0 == "UNIT2":
        return "UNIT 2"
    if s0 == "UNIT3":
        return "UNIT 3"
    if s0 == "UNITCOMMON":
        return "UNIT COMMON"
    return s if s else "Unknown"


def canon_voltage_level(x) -> str:
    s = str(x or "").strip().upper()
    if not s:
        return "Unknown"
    s0 = re.sub(r"\s+", "", s)
    if "6.3" in s0 and "KV" in s0:
        return "6.3 KV"
    if any(k in s0 for k in ["380/400", "380-400", "380400", "400V", "400/380"]):
        return "380/400 V"
    if s0 == "UNKNOWN":
        return "Unknown"
    return s


def safe_float(v) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, float) and pd.isna(v):
            return None
        s = str(v).strip()
        if s == "" or s.lower() in {"nan", "none"}:
            return None
        return float(s)
    except Exception:
        return None


def compute_overall_status_from_rows(rows: Optional[pd.DataFrame]) -> str:
    if rows is None or rows.empty:
        return "Unknown"

    def _get_param(name: str):
        g = rows[rows["Parameter"] == name]
        if g.empty:
            return None
        r = g.iloc[0]
        v = r.get("Value", None)
        v2 = safe_float(v)
        if v2 is not None:
            return v2
        return r.get("Raw_Value", None)

    params = {
        "Dev Voltage": _get_param("Dev Voltage"),
        "Dev Current": _get_param("Dev Current"),
        "THD Voltage %": _get_param("THD Voltage %"),
        "THD Current %": _get_param("THD Current %"),
        "Upper Sideband": _get_param("Upper Sideband"),
        "Lower Sideband": _get_param("Lower Sideband"),
        "Rotorbar Health": _get_param("Rotorbar Health"),
        "Se Fund": _get_param("Se Fund"),
        "Se Harm": _get_param("Se Harm"),
        "Rotorbar Level %": _get_param("Rotorbar Level %"),
        "Bearing": _get_param("Bearing"),
    }

    try:
        result = calculate_condition(params)
        return str(result.get("Overall", "Normal"))
    except Exception:
        k_rows = rows[rows["Parameter"] == "Kondisi"]
        if not k_rows.empty:
            val = k_rows["Raw_Value"].astype(str).iloc[0]
            return canon_condition_status(val)
        return "Unknown"


def load_equipment_master(master_path: str) -> pd.DataFrame:
    eq_master_df = pd.DataFrame()
    try:
        if os.path.exists(master_path):
            with open(master_path, "r", encoding="utf-8") as fp:
                eq_master = json.load(fp) or []
            eq_master_df = pd.DataFrame(eq_master)
    except Exception:
        eq_master_df = pd.DataFrame()
    if not eq_master_df.empty:
        for col in ["Equipment", "Unit_Name", "Voltage_Level"]:
            if col not in eq_master_df.columns:
                eq_master_df[col] = ""
        if "Full_Name" not in eq_master_df.columns:
            eq_master_df["Full_Name"] = eq_master_df.get("Equipment", "")
        eq_master_df["Equipment"] = eq_master_df["Equipment"].astype(str)
        eq_master_df["Unit_Name"] = eq_master_df["Unit_Name"].astype(str)
        eq_master_df["Voltage_Level"] = eq_master_df["Voltage_Level"].astype(str)
        eq_master_df["Full_Name"] = eq_master_df["Full_Name"].astype(str)
    return eq_master_df


def build_master_norm_maps(eq_master_df: pd.DataFrame) -> Tuple[dict, dict]:
    master_norm_to_unit: dict = {}
    master_norm_to_volt: dict = {}
    if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty:
        tmp = eq_master_df.copy()
        tmp["_norm"] = tmp["Equipment"].astype(str).map(norm_equipment)
        tmp["_unit"] = tmp["Unit_Name"].astype(str).map(canon_unit_name)
        tmp["_volt"] = tmp["Voltage_Level"].astype(str).map(canon_voltage_level)
        tmp = tmp.drop_duplicates(subset=["_norm"], keep="first")
        master_norm_to_unit = tmp.set_index("_norm")["_unit"].to_dict()
        master_norm_to_volt = tmp.set_index("_norm")["_volt"].to_dict()
    return master_norm_to_unit, master_norm_to_volt
