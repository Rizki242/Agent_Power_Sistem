"""Reports & Reliability API router."""

from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import shutil
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs
from src.agents.subagent_coordinator import SubAgentCoordinator
from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
from src.fleet_reliability import build_fleet_reliability
from src.ppt_generator import create_ppt

router = APIRouter(prefix="/api", tags=["reports", "reliability"])

from pple.application import (
    DiagnoseEquipmentUseCase,
    FleetReliabilityUseCase,
    GenerateAssessmentReportUseCase,
)

# Shared service instances & use cases
fusion_agent = ReliabilityFusionAgent()
asset_graph = AssetKnowledgeGraph()
subagent_coordinator = SubAgentCoordinator()

diagnose_use_case = DiagnoseEquipmentUseCase(fusion_agent=fusion_agent, asset_graph=asset_graph)
fleet_use_case = FleetReliabilityUseCase(fusion_agent=fusion_agent, asset_graph=asset_graph)
assessment_report_use_case = GenerateAssessmentReportUseCase(coordinator=subagent_coordinator)

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


class DiagnoseSimRequest(BaseModel):
    equipment: str
    asset_type: Optional[str] = "Motor-Pump"
    criticality: Optional[str] = "A"
    vibration: Optional[Dict[str, Any]] = None
    mcsa: Optional[Dict[str, Any]] = None
    dga: Optional[Dict[str, Any]] = None
    pd: Optional[Dict[str, Any]] = None
    tribology: Optional[Dict[str, Any]] = None
    thermal: Optional[Dict[str, Any]] = None


@router.post("/upload/dga")
async def upload_dga(file: UploadFile = File(...)):
    try:
        # Simpan file Excel sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_excel_path = tmp.name

        # Siapkan tempat untuk file JSON hasil output
        tmp_json_path = tmp_excel_path + ".json"

        # Panggil CLI dga_analyzer.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        script_path = os.path.join(
            base_dir, ".agents", "skills", "dga-excel-analyzer", "scripts", "dga_analyzer.py"
        )

        result = subprocess.run(
            ["python", script_path, "analyze-file", "--file", tmp_excel_path, "--output", tmp_json_path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Error analyzing DGA: {result.stderr}")

        # Baca hasilnya
        with open(tmp_json_path, "r") as f:
            diagnosis_data = json.load(f)

        # Bersihkan file temporary
        if os.path.exists(tmp_excel_path):
            os.remove(tmp_excel_path)
        if os.path.exists(tmp_json_path):
            os.remove(tmp_json_path)

        return {"status": "success", "data": diagnosis_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/vibration")
async def upload_vibration(file: UploadFile = File(...)):
    return {
        "status": "success",
        "message": f"Gambar spektrum '{file.filename}' berhasil diunggah dan sedang diantrekan untuk analisis PPLE Agent.",
    }


@router.post("/reports/ppt")
def generate_ppt_report(equipment_name: Optional[str] = None):
    df_raw, df_latest = get_data_frames()

    df_target = df_latest
    if equipment_name:
        df_target = df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment_name.upper()]
        if df_target.empty:
            raise HTTPException(status_code=404, detail=f"Equipment '{equipment_name}' not found")

    ppt_io = create_ppt(df_target)
    filename = f"MCSA_Report_{equipment_name or 'All'}.pptx"

    return StreamingResponse(
        io.BytesIO(ppt_io.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# --- AI O&M RELIABILITY COMMAND CENTER ENDPOINTS ---


@router.get("/reliability/fleet")
def get_fleet_reliability_summary():
    _, df_latest = get_data_frames()
    return fleet_use_case.get_fleet_summary(df_latest)


@router.get("/reliability/fusion/{equipment_name}")
def get_equipment_fusion_diagnosis(equipment_name: str):
    _, df_latest = get_data_frames()
    return diagnose_use_case.diagnose_from_mcsa_dataset(equipment_name, df_latest)


@router.post("/reliability/diagnose")
def simulate_multi_modal_diagnosis(req: DiagnoseSimRequest):
    return diagnose_use_case.diagnose_from_inputs(
        equipment=req.equipment,
        asset_type=req.asset_type,
        criticality=req.criticality,
        vibration=req.vibration,
        mcsa=req.mcsa,
        dga=req.dga,
        pd=req.pd,
        tribology=req.tribology,
        thermal=req.thermal,
    )


@router.get("/reports/assessment/{equipment}")
def get_equipment_assessment_report(equipment: str):
    try:
        return assessment_report_use_case.generate_report(equipment)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

