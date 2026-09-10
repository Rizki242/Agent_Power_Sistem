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
    reports_router,
    vibration_router,
    work_orders_router,
)
app.include_router(agents_router)
app.include_router(equipment_router)
app.include_router(knowledge_router)
app.include_router(reports_router)
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

from pple.api.routers.reports import set_data_frames_provider as set_reports_data_frames_provider
set_reports_data_frames_provider(get_data_frames)

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

