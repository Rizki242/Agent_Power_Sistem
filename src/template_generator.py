"""CBM Standard Template Generator.

Provides pre-formatted CSV templates and sample data for all 5 monitoring domains:
- MCSA (Electrical Signature)
- Vibrasi (Vibration & FFT)
- Thermal (Thermography & RTD)
- Tribology (Lubricant & Wear Metals)
- DGA (Dissolved Gas Analysis)
"""

from __future__ import annotations

from typing import Dict, List
import pandas as pd


TEMPLATES: Dict[str, Dict[str, Any]] = {
    "MCSA": {
        "columns": [
            "Equipment", "Date", "Rotorbar", "Dev Current",
            "Dev Voltage", "THD Voltage %", "THD Current %", "Bearing",
        ],
        "sample": [
            {
                "Equipment": "BC 10.1",
                "Date": "2026-08-01",
                "Rotorbar": "Normal",
                "Dev Current": 1.2,
                "Dev Voltage": 0.5,
                "THD Voltage %": 2.1,
                "THD Current %": 3.4,
                "Bearing": "Normal",
            },
            {
                "Equipment": "PA FAN 1A",
                "Date": "2026-08-01",
                "Rotorbar": "Alarm",
                "Dev Current": 5.8,
                "Dev Voltage": 1.1,
                "THD Voltage %": 4.2,
                "THD Current %": 6.0,
                "Bearing": "Normal",
            },
        ],
        "required": ["Equipment", "Date"],
    },
    "VIBRASI": {
        "columns": [
            "Equipment", "Date", "Velocity_RMS", "1X", "2X", "Bearing_Status",
        ],
        "sample": [
            {
                "Equipment": "BC 10.1",
                "Date": "2026-08-01",
                "Velocity_RMS": 2.4,
                "1X": 1.1,
                "2X": 0.4,
                "Bearing_Status": "Normal",
            },
            {
                "Equipment": "PA FAN 1A",
                "Date": "2026-08-01",
                "Velocity_RMS": 5.6,
                "1X": 4.2,
                "2X": 1.8,
                "Bearing_Status": "Warning",
            },
        ],
        "required": ["Equipment", "Date", "Velocity_RMS"],
    },
    "THERMAL": {
        "columns": [
            "Equipment", "Date", "Bearing_Temp", "Winding_Temp", "Delta_T",
        ],
        "sample": [
            {
                "Equipment": "BC 10.1",
                "Date": "2026-08-01",
                "Bearing_Temp": 62.5,
                "Winding_Temp": 68.0,
                "Delta_T": 2.5,
            },
            {
                "Equipment": "PA FAN 1A",
                "Date": "2026-08-01",
                "Bearing_Temp": 86.0,
                "Winding_Temp": 92.5,
                "Delta_T": 8.5,
            },
        ],
        "required": ["Equipment", "Date", "Bearing_Temp"],
    },
    "TRIBOLOGY": {
        "columns": [
            "Equipment", "Date", "Water_ppm", "TAN", "Fe_ppm", "Viscosity_cSt",
        ],
        "sample": [
            {
                "Equipment": "BC 10.1",
                "Date": "2026-08-01",
                "Water_ppm": 45,
                "TAN": 0.12,
                "Fe_ppm": 10,
                "Viscosity_cSt": 46.0,
            },
            {
                "Equipment": "BFP 1A",
                "Date": "2026-08-01",
                "Water_ppm": 320,
                "TAN": 0.45,
                "Fe_ppm": 48,
                "Viscosity_cSt": 65.2,
            },
        ],
        "required": ["Equipment", "Date", "Water_ppm"],
    },
    "DGA": {
        "columns": [
            "Equipment", "Date", "H2", "CH4", "C2H2", "C2H4", "C2H6", "CO", "CO2",
        ],
        "sample": [
            {
                "Equipment": "GT 1",
                "Date": "2026-08-01",
                "H2": 25,
                "CH4": 15,
                "C2H2": 1,
                "C2H4": 20,
                "C2H6": 12,
                "CO": 210,
                "CO2": 1850,
            },
            {
                "Equipment": "UAT 1",
                "Date": "2026-08-01",
                "H2": 150,
                "CH4": 95,
                "C2H2": 14,
                "C2H4": 110,
                "C2H6": 45,
                "CO": 420,
                "CO2": 3200,
            },
        ],
        "required": ["Equipment", "Date"],
    },
}


def get_template_csv(domain: str) -> str:
    """Returns the CSV template string with sample records."""
    d = domain.upper()
    info = TEMPLATES.get(d)
    if not info:
        return "Equipment,Date,Parameter,Value\n"
    df = pd.DataFrame(info["sample"], columns=info["columns"])
    return df.to_csv(index=False)


def validate_batch_dataframe(domain: str, df: pd.DataFrame) -> Dict[str, Any]:
    """Validates an uploaded dataframe against the domain's required columns."""
    d = domain.upper()
    info = TEMPLATES.get(d)
    if not info:
        return {
            "valid": True,
            "missing_columns": [],
            "row_count": len(df),
            "warnings": [],
        }

    required = info["required"]
    missing = [col for col in required if col not in df.columns]

    warnings = []
    optional_missing = [col for col in info["columns"] if col not in df.columns and col not in missing]
    if optional_missing:
        warnings.append(f"Kolom opsional tidak ditemukan: {', '.join(optional_missing)}")

    if df.empty:
        missing.append("File tidak memiliki baris data")

    return {
        "valid": len(missing) == 0,
        "missing_columns": missing,
        "row_count": len(df),
        "warnings": warnings,
    }
