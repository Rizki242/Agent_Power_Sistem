import os
import io
import json
import math
import glob
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends, Request, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

from pple.api.schemas.core import (
    EquipmentListResponse,
    HealthResponse,
    RotorBarCalculationResponse,
    SpecialistSubAgentsResponse,
    SummaryResponse,
)

def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in ['.txt', '.csv', '.json', '.md', '.log']:
            return file_bytes.decode('utf-8', errors='ignore')
        elif ext == '.pdf':
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or '' for page in reader.pages]
            return "\n".join(pages)
        elif ext in ['.docx', '.docm']:
            import docx
            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        elif ext in ['.xlsx', '.xls']:
            excel_df = pd.read_excel(io.BytesIO(file_bytes))
            return excel_df.to_string(max_rows=100)
    except Exception as e:
        return f"[File text extraction note: {e}]"
    return f"[File {filename} attached]"

from src.data_loader import (
    load_mcsa_data,
    get_latest_data,
    get_data_path,
    save_mcsa_data,
    audit_mcsa_dataframe,
    fix_mcsa_dataframe
)
from src.vibration_data import (
    load_vibration_assets,
    get_vibration_asset,
    search_vibration_assets,
    get_vibration_summary,
    get_equipment_class_list,
    get_bearing_info,
    load_vibration_monthly_tests,
)
from src.chatbot import MCSAChatbot
from src.rotorbar import evaluate_rotorbar
from src.docx_parser import parse_docx_report
from src.report_batches import create_batch, preview_batch, commit_batch, list_recent_batches
from src.ppt_generator import create_ppt
from src.knowledge_retriever import search_knowledge_base, load_knowledge_base
from src.standards import generate_initial_analysis, calculate_condition
from src.llm_assistant import MCSALLMAssistant, resolve_provider_key
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.safety_guard import SafetyGuardrailAgent
from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs
from src.fleet_reliability import build_fleet_reliability

fusion_agent = ReliabilityFusionAgent()
safety_guard = SafetyGuardrailAgent()
asset_graph = AssetKnowledgeGraph()

from pple.api.routers.work_orders import (
    _load_work_orders,
    _save_work_orders,
    _get_work_orders_store_path,
)

from pple.api.security import (
    api_key_middleware,
    cors_allow_credentials,
    resolve_cors_origins,
    startup_warning,
)
from pple.api.observability import setup_observability_and_errors

app = FastAPI(
    title="MCSA Assistant API",
    description="REST API & AI Agent backend for Motor Current Signature Analysis",
    version="2.0.0"
)

setup_observability_and_errors(app)

# Keamanan HTTP (pple/api/security.py): origin CORS dari PPLE_CORS_ORIGINS
# dengan default hanya localhost, plus API key opsional lewat PPLE_API_KEY.
# Tanpa PPLE_API_KEY perilaku lama dipertahankan supaya pemakaian lokal
# dan Streamlit tidak ikut berubah.
_cors_origins = resolve_cors_origins()

app.middleware("http")(api_key_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=cors_allow_credentials(_cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

_startup_warning = startup_warning()
if _startup_warning:
    print(_startup_warning)

# PPLE V2 (docs/final.md Phase 24): additive /api/v2/* routes exposing the
# pple.engineering module registry. Does not affect any /api/* route above.
from pple.api.router import router as pple_api_v2_router
app.include_router(pple_api_v2_router)

# PPLE V2: additive /api/v2/domain/* routes over the shared 5-domain
# measurement store (Vibrasi/DGA/Tribology/Thermal/PD) - the same
# upload/preview/report src.domain_ingest/src.domain_report already give
# the Streamlit workspace, now reachable from the React frontend/pple CLI too.
from pple.api.domain_router import router as pple_api_v2_domain_router
app.include_router(pple_api_v2_domain_router)

# Legacy-compatible specialist endpoints are isolated from this composition
# root so adding a domain no longer grows api_server.py.
from pple.api.specialist_router import router as specialist_router
app.include_router(specialist_router)

from pple.api.routers import (
    agents_router,
    equipment_router,
    knowledge_router,
    vibration_router,
    work_orders_router,
)
app.include_router(agents_router)
app.include_router(equipment_router)
app.include_router(knowledge_router)
app.include_router(vibration_router)
app.include_router(work_orders_router)

# Global Data Cache
_cached_raw_df: Optional[pd.DataFrame] = None
_cached_latest_df: Optional[pd.DataFrame] = None

def get_data_frames():
    global _cached_raw_df, _cached_latest_df
    if _cached_raw_df is None or _cached_latest_df is None:
        data_file = get_data_path('mcsa_updated.csv')
        if not os.path.exists(data_file):
            data_file = get_data_path('Report MCSA.xls')
        _cached_raw_df = load_mcsa_data(data_file)
        _cached_latest_df = get_latest_data(_cached_raw_df)
    return _cached_raw_df, _cached_latest_df

def refresh_data_cache():
    global _cached_raw_df, _cached_latest_df
    _cached_raw_df = None
    _cached_latest_df = None
    return get_data_frames()

from pple.api.routers.equipment import set_data_frames_provider as set_equipment_data_frames_provider
set_equipment_data_frames_provider(get_data_frames)

from pple.api.routers.agents import (
    set_data_frames_provider as set_agents_data_frames_provider,
    plant_skill_learner,
    env_rigger,
    subagent_coordinator,
    self_improver,
)
set_agents_data_frames_provider(get_data_frames)

class ChatRequest(BaseModel):
    message: str
    provider: Optional[str] = "gemini"
    model: Optional[str] = "gemini-2.5-flash"
    api_key: Optional[str] = None

class RotorBarCalculateRequest(BaseModel):
    upper_sb: float
    lower_sb: float
    health_index: Optional[float] = None
    se_fund: Optional[float] = None
    se_harm: Optional[float] = None


class MateriSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    return {"status": "ok", "app": "MCSA Assistant API v2.0"}

@app.get("/api/summary", response_model=SummaryResponse)
def get_summary():
    _, df_latest = get_data_frames()
    if df_latest.empty:
        return {
            "total_equipment": 0,
            "counts": {"Normal": 0, "Alarm": 0, "High": 0, "Standby": 0},
            "units": [],
            "voltages": [],
            "dates": []
        }
    
    cond_rows = df_latest[df_latest["Parameter"] == "Kondisi"] if "Parameter" in df_latest.columns else pd.DataFrame()
    counts = {"Normal": 0, "Alarm": 0, "High": 0, "Standby": 0}
    if not cond_rows.empty:
        v_counts = cond_rows["Raw_Value"].astype(str).str.strip().str.capitalize().value_counts().to_dict()
        for k, v in v_counts.items():
            if k in counts:
                counts[k] = int(v)
            else:
                counts["Normal"] += int(v)
    
    units = sorted([str(u) for u in df_latest["Unit_Name"].dropna().unique() if str(u).strip()]) if "Unit_Name" in df_latest.columns else []
    voltages = sorted([str(v) for v in df_latest["Voltage_Level"].dropna().unique() if str(v).strip()]) if "Voltage_Level" in df_latest.columns else []
    
    dates = []
    if "Date" in df_latest.columns:
        dates = sorted([str(d)[:10] for d in df_latest["Date"].dropna().unique() if str(d).strip()], reverse=True)

    total_eq = len(df_latest["Equipment"].dropna().unique()) if "Equipment" in df_latest.columns else 0

    return {
        "total_equipment": total_eq,
        "counts": counts,
        "units": units,
        "voltages": voltages,
        "dates": dates
    }

@app.post("/api/rotorbar/calculate", response_model=RotorBarCalculationResponse)
def calculate_rotorbar(req: RotorBarCalculateRequest):
    res = evaluate_rotorbar({
        "Upper Sideband": req.upper_sb,
        "Lower Sideband": req.lower_sb,
        "Rotorbar Health": req.health_index,
        "Se Fund": req.se_fund,
        "Se Harm": req.se_harm
    })
    return {
        "upper_sb": req.upper_sb,
        "lower_sb": req.lower_sb,
        "severity_level": res.get("Level", 1),
        "status": res.get("Status", "Normal"),
        "assessment": res.get("Assessment", "Normal"),
        "max_sideband": res.get("Max Sideband"),
        "diagnostic_validity": res.get("Diagnostic Validity")
    }

import tempfile
import subprocess
@app.post("/api/upload/dga")
async def upload_dga(file: UploadFile = File(...)):
    try:
        # Simpan file Excel sementara
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_excel_path = tmp.name
        
        # Siapkan tempat untuk file JSON hasil output
        tmp_json_path = tmp_excel_path + ".json"
        
        # Panggil CLI dga_analyzer.py
        script_path = os.path.join(os.path.dirname(__file__), ".agents", "skills", "dga-excel-analyzer", "scripts", "dga_analyzer.py")
        
        result = subprocess.run(
            ["python", script_path, "analyze-file", "--file", tmp_excel_path, "--output", tmp_json_path],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Error analyzing DGA: {result.stderr}")
            
        # Baca hasilnya
        with open(tmp_json_path, "r") as f:
            diagnosis_data = json.load(f)
            
        # Bersihkan file temporary
        os.remove(tmp_excel_path)
        os.remove(tmp_json_path)
        
        return {"status": "success", "data": diagnosis_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/vibration")
async def upload_vibration(file: UploadFile = File(...)):
    # Placeholder: Nantinya ini akan memanggil vision AI (Gemini) atau parser Vibration
    return {"status": "success", "message": f"Gambar spektrum '{file.filename}' berhasil diunggah dan sedang diantrekan untuk analisis PPLE Agent."}

@app.post("/api/reports/ppt")
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
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# --- AI O&M RELIABILITY COMMAND CENTER ENDPOINTS ---

@app.get("/api/reliability/fleet")
def get_fleet_reliability_summary():
    df_raw, df_latest = get_data_frames()
    return build_fleet_reliability(df_latest, fusion_agent, asset_graph)

@app.get("/api/reliability/fusion/{equipment_name}")
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

@app.post("/api/reliability/diagnose")
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
        thermal_data=req.thermal
    )
    return res

@app.get("/api/reports/assessment/{equipment}")
def get_equipment_assessment_report(equipment: str):
    """
    Generate a comprehensive Multi-Modal CBM Condition Assessment Report
    aggregating all 8 Specialist Sub-Agents, RUL, Risk Matrix, and Work Orders.
    """
    try:
        collab = subagent_coordinator.run_collaborative_diagnosis(
            equipment=equipment,
            query=f"Laporan komprehensif assessment kondisi {equipment}"
        )
        
        from datetime import datetime
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
                "fused_evidence": collab.get("fused_evidence", [])
            },
            "subagent_traces": collab.get("subagent_traces", []),
            "work_order_action": collab.get("maintenance_decision", {}),
            "safety_clearance": collab.get("safety_clearance", True),
            "signoff": {
                "prepared_by": "AI O&M Reliability Orchestrator (8 Sub-Agents)",
                "verified_by": "Predictive Maintenance Engineer (CBM Specialist)",
                "approved_by": "Chief Operation Engineer / Shift Supervisor CCR",
                "approval_status": "Awaiting Field Verification"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
