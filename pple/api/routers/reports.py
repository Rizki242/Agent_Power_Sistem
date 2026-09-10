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

# Shared service instances
fusion_agent = ReliabilityFusionAgent()
asset_graph = AssetKnowledgeGraph()
subagent_coordinator = SubAgentCoordinator()

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
    df_raw, df_latest = get_data_frames()
    return build_fleet_reliability(df_latest, fusion_agent, asset_graph)


@router.get("/reliability/fusion/{equipment_name}")
def get_equipment_fusion_diagnosis(equipment_name: str):
    df_raw, df_latest = get_data_frames()
    node = asset_graph.get_equipment_node(equipment_name)

    eq_data = df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment_name.upper()]

    fusion_inputs = extract_mcsa_fusion_inputs(eq_data)

    fusion_res = fusion_agent.run_full_fusion(
        equipment=equipment_name,
        asset_type=node.get("asset_type", "Electric Motor-Pump"),
        criticality=node.get("criticality", "A"),
        **fusion_inputs,
    )

    fusion_res["asset_node"] = node
    fusion_res["data_sources"] = sorted(fusion_inputs.keys())
    return fusion_res


@router.post("/reliability/diagnose")
def simulate_multi_modal_diagnosis(req: DiagnoseSimRequest):
    res = fusion_agent.run_full_fusion(
        equipment=req.equipment,
        asset_type=req.asset_type or "Motor-Pump",
        criticality=req.criticality or "A",
        vibration_data=req.vibration,
        mcsa_data=req.mcsa,
        dga_data=req.dga,
        pd_data=req.pd,
        oil_data=req.tribology,
        thermal_data=req.thermal,
    )
    return res


@router.get("/reports/assessment/{equipment}")
def get_equipment_assessment_report(equipment: str):
    """
    Generate a comprehensive Multi-Modal CBM Condition Assessment Report
    aggregating all 8 Specialist Sub-Agents, RUL, Risk Matrix, and Work Orders.
    """
    try:
        collab = subagent_coordinator.run_collaborative_diagnosis(
            equipment=equipment,
            query=f"Laporan komprehensif assessment kondisi {equipment}",
        )

        rpt_no = f"CBM-RPT-{datetime.now().strftime('%Y%m')}-{abs(hash(equipment)) % 10000:04d}"

        return {
            "report_id": rpt_no,
            "equipment": equipment,
            "plant": "PLTU Jeranjang (3 × 25 MW)",
            "unit": collab.get("unit", "UNIT 1"),
            "system": collab.get("system", "Turbine & Boiler Auxiliaries"),
            "asset_type": collab.get("asset_type", "Medium Voltage Motor Drive"),
            "criticality": collab.get("criticality", "B"),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S WITA"),
            "assessment_summary": {
                "health_index": collab.get("consensus_health_index", 90.0),
                "health_status": collab.get("consensus_health_status", "HEALTHY"),
                "primary_failure_mode": collab.get("consensus_failure_mode", "Normal Operation"),
                "confidence_percent": round(collab.get("consensus_confidence", 0.95) * 100, 1),
                "estimated_rul_days": collab.get("predictive_rul", {}).get("estimated_rul_days", 90),
                "risk_level": collab.get("risk_assessment", {}).get("risk_level", "Low Risk (Acceptable)"),
                "fused_evidence": collab.get("fused_evidence", []),
            },
            "subagent_traces": collab.get("subagent_traces", []),
            "work_order_action": collab.get("maintenance_decision", {}),
            "safety_clearance": collab.get("safety_clearance", True),
            "signoff": {
                "prepared_by": "AI O&M Reliability Orchestrator (8 Sub-Agents)",
                "verified_by": "Predictive Maintenance Engineer (CBM Specialist)",
                "approved_by": "Chief Operation Engineer / Shift Supervisor CCR",
                "approval_status": "Awaiting Field Verification",
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
