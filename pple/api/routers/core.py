"""Core MCSA API router (Health, Summary, RotorBar)."""

from __future__ import annotations

import os
from typing import Callable, Optional, Tuple

import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from pple.api.schemas.core import (
    HealthResponse,
    RotorBarCalculationResponse,
    SummaryResponse,
)
from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
from src.rotorbar import evaluate_rotorbar

router = APIRouter(prefix="/api", tags=["core"])

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


class RotorBarCalculateRequest(BaseModel):
    upper_sb: float
    lower_sb: float
    health_index: Optional[float] = None
    se_fund: Optional[float] = None
    se_harm: Optional[float] = None


import time

_server_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
def health_check():
    uptime = round(time.time() - _server_start_time, 2)
    cache_loaded = _cached_raw_df is not None and _cached_latest_df is not None
    return {
        "status": "ok",
        "app": "MCSA Assistant API v2.0",
        "uptime_seconds": uptime,
        "version": "2.0.0",
        "active_domains": ["VIBRASI", "MCSA", "DGA", "TRIBOLOGY", "THERMAL", "PD"],
        "cache_loaded": cache_loaded,
    }



@router.get("/summary", response_model=SummaryResponse)
def get_summary():
    _, df_latest = get_data_frames()
    if df_latest.empty:
        return {
            "total_equipment": 0,
            "counts": {"Normal": 0, "Alarm": 0, "High": 0, "Standby": 0},
            "units": [],
            "voltages": [],
            "dates": [],
        }

    cond_rows = (
        df_latest[df_latest["Parameter"] == "Kondisi"]
        if "Parameter" in df_latest.columns
        else pd.DataFrame()
    )
    counts = {"Normal": 0, "Alarm": 0, "High": 0, "Standby": 0}
    if not cond_rows.empty:
        v_counts = (
            cond_rows["Raw_Value"]
            .astype(str)
            .str.strip()
            .str.capitalize()
            .value_counts()
            .to_dict()
        )
        for k, v in v_counts.items():
            if k in counts:
                counts[k] = int(v)
            else:
                counts["Normal"] += int(v)

    units = (
        sorted([str(u) for u in df_latest["Unit_Name"].dropna().unique() if str(u).strip()])
        if "Unit_Name" in df_latest.columns
        else []
    )
    voltages = (
        sorted([str(v) for v in df_latest["Voltage_Level"].dropna().unique() if str(v).strip()])
        if "Voltage_Level" in df_latest.columns
        else []
    )

    dates = []
    if "Date" in df_latest.columns:
        dates = sorted(
            [str(d)[:10] for d in df_latest["Date"].dropna().unique() if str(d).strip()],
            reverse=True,
        )

    total_eq = (
        len(df_latest["Equipment"].dropna().unique())
        if "Equipment" in df_latest.columns
        else 0
    )

    return {
        "total_equipment": total_eq,
        "counts": counts,
        "units": units,
        "voltages": voltages,
        "dates": dates,
    }


@router.post("/rotorbar/calculate", response_model=RotorBarCalculationResponse)
def calculate_rotorbar(req: RotorBarCalculateRequest):
    res = evaluate_rotorbar(
        {
            "Upper Sideband": req.upper_sb,
            "Lower Sideband": req.lower_sb,
            "Rotorbar Health": req.health_index,
            "Se Fund": req.se_fund,
            "Se Harm": req.se_harm,
        }
    )
    return {
        "upper_sb": req.upper_sb,
        "lower_sb": req.lower_sb,
        "severity_level": res.get("Level", 1),
        "status": res.get("Status", "Normal"),
        "assessment": res.get("Assessment", "Normal"),
        "max_sideband": res.get("Max Sideband"),
        "diagnostic_validity": res.get("Diagnostic Validity"),
    }
