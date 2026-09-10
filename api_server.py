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
    equipment_router,
    knowledge_router,
    vibration_router,
    work_orders_router,
)
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

from src.agents.subagent_coordinator import SubAgentCoordinator

subagent_coordinator = SubAgentCoordinator()


@app.get("/api/agents/specialists", response_model=SpecialistSubAgentsResponse)
def get_specialist_subagents():
    """List all registered specialist sub-agents with capability metadata and standards."""
    return {
        "specialists": subagent_coordinator.list_specialists(),
        "total_count": len(subagent_coordinator.list_specialists()),
        "status": "ALL_ONLINE"
    }


class MultiAgentCollaborateRequest(BaseModel):
    equipment: str
    query: Optional[str] = ""
    custom_telemetry: Optional[Dict[str, Any]] = None


@app.post("/api/agents/collaborate")
def collaborate_subagents(req: MultiAgentCollaborateRequest):
    """
    Execute multi-agent collaborative diagnosis across specialist sub-agents
    (Vibration, MCSA, DGA, PD, Tribology, Thermal, Fusion, Safety).
    """
    return subagent_coordinator.run_collaborative_diagnosis(
        equipment=req.equipment,
        query=req.query or f"Kolaborasi diagnosa kondisi {req.equipment}",
        custom_telemetry=req.custom_telemetry
    )


from src.agents.continuous_learning import PowerPlantSkillLearner

plant_skill_learner = PowerPlantSkillLearner()


class TeachSkillRequest(BaseModel):
    equipment: str
    title: Optional[str] = ""
    system: Optional[str] = ""
    category: Optional[str] = "VIBRASI"
    symptoms: List[str] = []
    verified_root_cause: str
    corrective_action_taken: str
    lesson_learned: str
    author: Optional[str] = "CBM Engineer PLTU Jeranjang"


@app.get("/api/skills/learned-patterns")
def get_learned_skill_patterns():
    """Retrieve all dynamically learned technical disturbance patterns and lessons."""
    skills = plant_skill_learner.load_learned_skills()
    return {
        "skills": skills,
        "total_count": len(skills),
        "status": "LEARNING_ACTIVE"
    }


@app.post("/api/skills/teach")
def teach_agent_skill(req: TeachSkillRequest):
    """Teach the agent a new verified failure signature, lesson learned, or disturbance finding."""
    return plant_skill_learner.teach_agent(
        equipment=req.equipment,
        title=req.title,
        system=req.system,
        category=req.category,
        symptoms=req.symptoms,
        verified_root_cause=req.verified_root_cause,
        corrective_action_taken=req.corrective_action_taken,
        lesson_learned=req.lesson_learned,
        author=req.author or "CBM Engineer PLTU Jeranjang"
    )


@app.get("/api/skills/benchmarks")
def get_diagnostic_benchmarks():
    """Run diagnostic benchmark suite across plant disturbance scenarios and compute accuracy score."""
    return plant_skill_learner.run_benchmarks()


from src.agents.self_improvement import RecursiveSelfImprover

self_improver = RecursiveSelfImprover()


class SelfImproveRequest(BaseModel):
    max_iterations: Optional[int] = 6


class RecordPredictionRequest(BaseModel):
    equipment: str
    predicted_mode: str
    predicted_severity: int = 1
    confidence: float = 0.8
    actual_mode: Optional[str] = ""
    actual_severity: Optional[int] = None


@app.post("/api/agent/self-improve")
def run_self_improvement_cycle(req: SelfImproveRequest):
    """
    Run one recursive self-improvement cycle:
    measure accuracy -> propose weight tuning -> validate -> retain only if improved.
    """
    return self_improver.run_improvement_cycle(max_iterations=req.max_iterations)


@app.get("/api/agent/improvement-status")
def get_self_improvement_status():
    """Report current generation, best score, weights, and prediction statistics of the learning engine."""
    return self_improver.get_status()


@app.post("/api/agent/predictions")
def record_agent_prediction(req: RecordPredictionRequest):
    """Record a diagnostic prediction (and optionally its verified outcome) for accuracy learning."""
    entry = self_improver.record_prediction(
        equipment=req.equipment,
        predicted_mode=req.predicted_mode,
        severity=req.predicted_severity,
        confidence=req.confidence,
    )
    outcome = None
    if req.actual_mode or req.actual_severity is not None:
        outcome = self_improver.record_outcome(
            prediction_id=entry["id"],
            actual_mode=req.actual_mode or "",
            actual_severity=req.actual_severity or 1,
        )
    return {"status": "success", "prediction": entry, "outcome": outcome}


@app.post("/api/agent/learn-from-history")
def learn_from_historical_data():
    """Mine historical MCSA measurement data for degradation precursor patterns (data-driven lessons)."""
    try:
        df = load_mcsa_data(get_data_path("mcsa_updated.csv"))
        if df is None or df.empty:
            df = load_mcsa_data(get_data_path("Report MCSA.xls"))
    except Exception as exc:
        return {"status": "error", "message": f"Gagal memuat data historis: {exc}", "lessons_created": 0}
    return self_improver.learn_from_history(df)


from src.agents.env_harness import EnvRigger

env_rigger = EnvRigger()


class RiggerCycleRequest(BaseModel):
    equipment: Optional[str] = "BFP 1A"


@app.get("/api/learning/harness-status")
def get_harness_status():
    """Report active EnvHarness wrappers (Stage, Contract, Chain) and EnvRigger history."""
    return env_rigger.get_status()


@app.post("/api/learning/rigger-cycle")
def execute_rigger_cycle(req: RiggerCycleRequest):
    """
    Run an automated EnvRigger Observe -> Diagnose -> Write -> Validate cycle,
    customizing the environment to target agent weaknesses and recording new skills.
    """
    return plant_skill_learner.run_env_rigger_learning(equipment=req.equipment or "BFP 1A")


@app.post("/api/learning/evaluate-harness")
def evaluate_agent_on_harness():
    """Evaluate diagnostic agent performance against wrapped composite EnvHarness environments."""
    return plant_skill_learner.evaluate_env_harness()



@app.post("/api/agent/chat")
async def agent_chat(
    request: Request,
    message: Optional[str] = Form(None),
    provider: Optional[str] = Form("gemini"),
    model: Optional[str] = Form("gemini-2.5-flash"),
    api_key: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    df_raw, df_latest = get_data_frames()
    bot = MCSAChatbot(df_latest, df_all=df_raw)
    
    content_type = request.headers.get("content-type", "")
    file_name = None
    extra_file_context = ""
    
    if "application/json" in content_type:
        body = await request.json()
        msg_text = body.get("message", "")
        prov = body.get("provider", "gemini")
        mdl = body.get("model", "gemini-2.5-flash")
        k = body.get("api_key")
    else:
        msg_text = message or ""
        prov = provider or "gemini"
        mdl = model or "gemini-2.5-flash"
        k = api_key
        if file and file.filename:
            file_name = file.filename
            file_bytes = await file.read()
            extracted_text = extract_text_from_upload(file_bytes, file.filename)
            extra_file_context = f"\n\n--- KONTEN DOKUMEN/FILE TERLAMPIR ({file.filename}) ---\n{extracted_text[:12000]}\n--- AKHIR DOKUMEN TERLAMPIR ---"

    bot_reply = bot.process_query(msg_text) if msg_text else ""
    if not bot_reply and file_name:
        bot_reply = f"File `{file_name}` berhasil diterima. Silakan ajukan pertanyaan terkait dokumen ini."
        
    matched_eq = bot.last_matched_equipment

    # Identify active specialist sub-agents
    active_agent_keys = subagent_coordinator.identify_relevant_agents(msg_text, matched_eq)
    all_specs = {s["domain"].lower(): s for s in subagent_coordinator.list_specialists()}
    active_subagents = []
    for k_agent in active_agent_keys:
        for s_desc in subagent_coordinator.list_specialists():
            if k_agent in s_desc["agent_id"] or k_agent == s_desc["domain"].lower():
                active_subagents.append(s_desc)
                break

    # Safety Guardrail Check
    safety_check = safety_guard.check_safety(msg_text)
    if not safety_check["safe"]:
        return {
            "reply": safety_check["message"],
            "matched_equipment": matched_eq,
            "ai_enhanced": False,
            "file_name": file_name,
            "provider": prov,
            "safety_blocked": True,
            "active_subagents": active_subagents,
            "subagent_traces": []
        }

    # Execute Multi-Agent Diagnostic Collaboration if equipment is recognized
    subagent_traces = []
    subagents_context = ""
    if matched_eq:
        try:
            collab_result = subagent_coordinator.run_collaborative_diagnosis(matched_eq, msg_text)
            subagent_traces = collab_result.get("subagent_traces", [])
            subagents_context = (
                f"Consolidated Health: {collab_result.get('consensus_health_index')}/100 ({collab_result.get('consensus_health_status')})\n"
                f"Primary Failure Mode: {collab_result.get('consensus_failure_mode')} (Confidence: {collab_result.get('consensus_confidence', 0.9)*100:.0f}%)\n"
                f"Estimated RUL: {collab_result.get('predictive_rul', {}).get('estimated_rul_days')} hari\n"
            )
            for t in subagent_traces:
                subagents_context += f"• [{t['subagent']['name']}] ({t['status']}): {t['key_finding']}\n"
        except Exception as e:
            print(f"Sub-agent collaboration note: {e}")

    resolved_key = resolve_provider_key(prov, k)
    ai_enhanced = False
    final_reply = bot_reply
    
    if resolved_key:
        try:
            assistant = MCSALLMAssistant(
                enabled=True,
                provider=prov or "gemini",
                model=mdl or "gemini-2.5-flash",
                api_key=resolved_key
            )
            if assistant.available:
                ai_resp = assistant.enhance_answer(
                    question=msg_text or f"Analisis isi dokumen {file_name}",
                    rule_answer=bot_reply,
                    df_context=df_latest,
                    df_history=df_raw,
                    include_knowledge=True,
                    extra_file_context=extra_file_context,
                    subagents_context=subagents_context
                )
                if ai_resp and len(ai_resp.strip()) > 10:
                    final_reply = ai_resp
                    ai_enhanced = True
        except Exception as e:
            print(f"LLM AI processing note: {e}")

    return {
        "reply": final_reply,
        "matched_equipment": matched_eq,
        "ai_enhanced": ai_enhanced,
        "file_name": file_name,
        "provider": prov,
        "active_subagents": active_subagents,
        "subagent_traces": subagent_traces
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
