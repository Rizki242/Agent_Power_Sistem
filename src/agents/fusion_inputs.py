"""Telemetry extraction from MCSA dataframe rows into fusion-engine inputs.

Moved verbatim out of api_server.py so the FastAPI layer and the Streamlit
Agent Dashboard build fusion inputs from the exact same rules: only
parameters actually measured in the dataframe are passed on, missing
modalities are never invented.
"""

import math
from typing import Any, Dict, Optional

import pandas as pd


def status_from_equipment_rows(eq_data: pd.DataFrame) -> str:
    if eq_data is None or eq_data.empty or "Parameter" not in eq_data.columns:
        return "Normal"
    c_row = eq_data[eq_data["Parameter"].astype(str) == "Kondisi"]
    if c_row.empty:
        return "Normal"
    raw_value = str(c_row.iloc[0].get("Raw_Value", "Normal")).strip().capitalize()
    return raw_value if raw_value else "Normal"


def numeric_param(eq_data: pd.DataFrame, *param_names: str) -> Optional[float]:
    if eq_data is None or eq_data.empty or "Parameter" not in eq_data.columns:
        return None
    wanted = {p.lower() for p in param_names}
    rows = eq_data[eq_data["Parameter"].astype(str).str.strip().str.lower().isin(wanted)]
    if rows.empty:
        return None
    for _, row in rows.iterrows():
        for field in ("Value", "Raw_Value"):
            try:
                val = row.get(field)
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    continue
                parsed = float(str(val).strip())
                if math.isnan(parsed) or math.isinf(parsed):
                    continue
                return parsed
            except (TypeError, ValueError):
                continue
    return None


def extract_mcsa_fusion_inputs(eq_data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Build fusion inputs only from measured rows present in the dataframe."""
    cond_val = status_from_equipment_rows(eq_data)

    mcsa_data = {
        "bearing_status": cond_val,
    }
    mcsa_param_map = {
        "upper_sb": ("Upper Sideband",),
        "lower_sb": ("Lower Sideband",),
        "dev_current": ("Dev Current",),
        "dev_voltage": ("Dev Voltage",),
        "thd_current": ("THD Current %",),
    }
    for out_key, names in mcsa_param_map.items():
        val = numeric_param(eq_data, *names)
        if val is not None:
            mcsa_data[out_key] = val

    inputs: Dict[str, Dict[str, Any]] = {"mcsa_data": mcsa_data}

    vibration_map = {
        "overall_rms": ("Overall Vibration RMS", "Vibration RMS", "Velocity RMS", "RMS Velocity"),
        "bpfo_amp": ("BPFO", "BPFO Amp", "BPFO Amplitude"),
        "bpfi_amp": ("BPFI", "BPFI Amp", "BPFI Amplitude"),
        "amp_1x": ("1X", "Amp 1X", "1X Amplitude"),
        "amp_2x": ("2X", "Amp 2X", "2X Amplitude"),
        "axial_1x": ("Axial 1X",),
    }
    vibration_data = {
        out_key: val
        for out_key, names in vibration_map.items()
        if (val := numeric_param(eq_data, *names)) is not None
    }
    if vibration_data:
        inputs["vibration_data"] = vibration_data

    thermal_map = {
        "bearing_temp": ("Bearing Temperature", "Bearing Temp", "Thermal Bearing Temp"),
        "winding_temp": ("Winding Temperature", "Winding Temp"),
        "ambient_temp": ("Ambient Temperature", "Ambient Temp"),
        "delta_t_phase": ("Delta T Phase", "Delta-T Phase", "Phase Delta T"),
        "hotspot_temp": ("Hotspot Temperature", "Hotspot Temp"),
    }
    thermal_data = {
        out_key: val
        for out_key, names in thermal_map.items()
        if (val := numeric_param(eq_data, *names)) is not None
    }
    if thermal_data:
        inputs["thermal_data"] = thermal_data

    oil_map = {
        "viscosity_40c": ("Viscosity 40C", "Viscosity 40°C", "Visk 40C"),
        "water_ppm": ("Water ppm", "Water", "Moisture ppm"),
        "fe_ppm": ("Fe ppm", "Iron ppm", "Fe"),
        "cu_ppm": ("Cu ppm", "Copper ppm", "Cu"),
        "tan": ("TAN", "Total Acid Number"),
    }
    oil_data = {
        out_key: val
        for out_key, names in oil_map.items()
        if (val := numeric_param(eq_data, *names)) is not None
    }
    if oil_data:
        inputs["oil_data"] = oil_data

    return inputs
