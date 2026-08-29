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
from src.dga_data import (
    get_dga_summary,
    search_dga_transformers,
    get_dga_transformer_detail,
    calculate_dga_diagnosis,
)
from src.tribology_data import (
    get_tribology_summary,
    search_tribology_samples,
    get_tribology_sample_detail,
    evaluate_tribology_sample,
)
from src.thermal_data import (
    load_thermal_irt_tests,
    get_thermal_summary,
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

fusion_agent = ReliabilityFusionAgent()
safety_guard = SafetyGuardrailAgent()
asset_graph = AssetKnowledgeGraph()

# In-memory mirror for callers that inspect module state, backed by JSON storage.
_work_orders_db = []


def _status_from_equipment_rows(eq_data: pd.DataFrame) -> str:
    if eq_data is None or eq_data.empty or "Parameter" not in eq_data.columns:
        return "Normal"
    c_row = eq_data[eq_data["Parameter"].astype(str) == "Kondisi"]
    if c_row.empty:
        return "Normal"
    raw_value = str(c_row.iloc[0].get("Raw_Value", "Normal")).strip().capitalize()
    return raw_value if raw_value else "Normal"


def _numeric_param(eq_data: pd.DataFrame, *param_names: str) -> Optional[float]:
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


def _extract_mcsa_fusion_inputs(eq_data: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Build fusion inputs only from measured rows present in the dataframe."""
    cond_val = _status_from_equipment_rows(eq_data)

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
        val = _numeric_param(eq_data, *names)
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
        if (val := _numeric_param(eq_data, *names)) is not None
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
        if (val := _numeric_param(eq_data, *names)) is not None
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
        if (val := _numeric_param(eq_data, *names)) is not None
    }
    if oil_data:
        inputs["oil_data"] = oil_data

    return inputs


def _seed_work_orders() -> List[Dict[str, Any]]:
    return [
        {
            "wo_number": "WO-202608-0101",
            "equipment": "BC 10.1",
            "title": "Investigasi Bearing & Re-greasing DE/NDE",
            "priority": "P2 - High",
            "reason": "AI Multi-Modal Fusion: Indikasi keausan bearing & suhu naik",
            "required_tools": ["Vibration Analyzer", "Thermal Camera", "Grease Gun"],
            "required_parts": ["Grease Shell Gadus S2", "Bearing 6314 C3"],
            "required_manpower": "2 Technicians",
            "target_completion_date": "2026-08-30",
            "status": "Draft - Awaiting Approval",
        },
        {
            "wo_number": "WO-202608-0102",
            "equipment": "BFP 1A",
            "title": "Laser Alignment Verification & Soft Foot Check",
            "priority": "P3 - Medium",
            "reason": "AI Diagnostics: Modulasi spektrum 2X & getaran aksial",
            "required_tools": ["Laser Alignment Kit", "Dial Indicator"],
            "required_parts": ["Stainless Steel Shim Pack 0.05-1.0mm"],
            "required_manpower": "1 Alignment Specialist + 1 Mechanic",
            "target_completion_date": "2026-09-05",
            "status": "Approved - Ready for Execution",
        },
    ]


def _get_work_orders_store_path() -> str:
    configured = os.environ.get("WORK_ORDERS_FILE")
    if configured and configured.strip():
        return os.path.abspath(configured.strip())
    return get_data_path("runtime", "work_orders.json")


def _load_work_orders() -> List[Dict[str, Any]]:
    global _work_orders_db
    path = _get_work_orders_store_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, list):
                _work_orders_db = data
                return data
        except Exception:
            pass

    _work_orders_db = _seed_work_orders()
    return list(_work_orders_db)


def _save_work_orders(work_orders: List[Dict[str, Any]]) -> str:
    global _work_orders_db
    path = _get_work_orders_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fp:
        json.dump(work_orders, fp, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    _work_orders_db = list(work_orders)
    return path

app = FastAPI(
    title="MCSA Assistant API",
    description="REST API & AI Agent backend for Motor Current Signature Analysis",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": "MCSA Assistant API v2.0"}

@app.get("/api/summary")
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

@app.get("/api/equipment")
def get_equipment_list(
    unit: Optional[str] = None,
    voltage: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    df_raw, df_latest = get_data_frames()
    if df_latest.empty or "Equipment" not in df_latest.columns:
        return {"equipment": [], "count": 0}

    cond_rows = df_latest[df_latest["Parameter"] == "Kondisi"].copy() if "Parameter" in df_latest.columns else pd.DataFrame()
    if cond_rows.empty:
        cond_rows = df_latest.drop_duplicates(subset=["Equipment"]).copy()
    
    # Filter by unit, voltage, search, status
    if unit and unit.upper() != "ALL" and "Unit_Name" in cond_rows.columns:
        cond_rows = cond_rows[cond_rows["Unit_Name"].astype(str).str.upper() == unit.upper()]
    if voltage and voltage.upper() != "ALL" and "Voltage_Level" in cond_rows.columns:
        cond_rows = cond_rows[cond_rows["Voltage_Level"].astype(str).str.upper() == voltage.upper()]
    if status and status.upper() != "ALL" and "Raw_Value" in cond_rows.columns:
        cond_rows = cond_rows[cond_rows["Raw_Value"].astype(str).str.strip().str.capitalize() == status.capitalize()]
    if search:
        s_term = search.lower().strip()
        cond_rows = cond_rows[cond_rows["Equipment"].astype(str).str.lower().str.contains(s_term)]

    eq_names = cond_rows["Equipment"].dropna().unique()
    
    result = []
    for eq in eq_names:
        eq_data = df_latest[df_latest["Equipment"] == eq]
        cond_val = "Normal"
        c_row = eq_data[eq_data["Parameter"] == "Kondisi"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not c_row.empty:
            cond_val = str(c_row["Raw_Value"].iloc[0]).strip().capitalize()
        
        last_date = ""
        if "Date" in eq_data.columns and not eq_data["Date"].dropna().empty:
            last_date = str(eq_data["Date"].dropna().iloc[0])[:10]
            
        unit_val = str(eq_data["Unit_Name"].iloc[0]) if "Unit_Name" in eq_data.columns and not eq_data.empty else ""
        volt_val = str(eq_data["Voltage_Level"].iloc[0]) if "Voltage_Level" in eq_data.columns and not eq_data.empty else ""
        
        rb_status = "Normal"
        rb_row = eq_data[eq_data["Parameter"] == "Rotorbar"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not rb_row.empty:
            rb_status = str(rb_row["Raw_Value"].iloc[0]).strip().capitalize()
            
        brg_status = "Normal"
        brg_row = eq_data[eq_data["Parameter"] == "Bearing"] if "Parameter" in eq_data.columns else pd.DataFrame()
        if not brg_row.empty:
            brg_status = str(brg_row["Raw_Value"].iloc[0]).strip().capitalize()

        result.append({
            "equipment": str(eq),
            "unit": unit_val,
            "voltage": volt_val,
            "status": cond_val,
            "condition": cond_val,
            "rotorbar_status": rb_status,
            "bearing_status": brg_status,
            "last_date": last_date,
            "date": last_date
        })

    return {"equipment": result, "count": len(result)}

@app.get("/api/equipment/{equipment_name}")
def get_equipment_detail(equipment_name: str):
    df_raw, df_latest = get_data_frames()
    
    eq_latest = df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment_name.upper()]
    eq_history = df_raw[df_raw["Equipment"].astype(str).str.upper() == equipment_name.upper()]
    
    if eq_history.empty and eq_latest.empty:
        raise HTTPException(status_code=404, detail="Equipment not found")

    # Target dataframe for parameters
    target_df = eq_latest if not eq_latest.empty else eq_history.tail(20)

    # Structured parameters dictionary
    structured_params = {}
    perf_summary = {}
    latest_params = {}
    
    cond_val = "Normal"
    latest_date_str = ""

    for _, row in target_df.iterrows():
        p_name = str(row.get("Parameter", "")).strip()
        p_raw = str(row.get("Raw_Value", "")).strip()
        p_unit = str(row.get("Unit", "")) if pd.notna(row.get("Unit")) else ""
        if p_unit == "nan":
            p_unit = ""
            
        if not p_name:
            continue
            
        latest_params[p_name] = p_raw
        
        if p_name.startswith("Ringkasan Kinerja - ") or p_name.startswith("Performance Summary"):
            short_k = p_name.replace("Ringkasan Kinerja - ", "").replace("Performance Summary - ", "")
            perf_summary[short_k] = p_raw
        else:
            structured_params[p_name] = {
                "value": p_raw,
                "unit": p_unit
            }
            
        if p_name == "Kondisi":
            cond_val = p_raw.capitalize()
            
        if "Date" in row and pd.notna(row["Date"]) and not latest_date_str:
            latest_date_str = str(row["Date"])[:10]

    # History trend data
    history_records = []
    if "Date" in eq_history.columns:
        dates = eq_history["Date"].dropna().unique()
        for d in sorted(dates)[-12:]:
            sub = eq_history[eq_history["Date"] == d]
            rec = {"date": str(d)[:10]}
            for _, r in sub.iterrows():
                param_key = str(r["Parameter"])
                raw_v = r.get("Raw_Value")
                try:
                    f_val = float(raw_v)
                    if math.isnan(f_val) or math.isinf(f_val):
                        rec[param_key] = str(raw_v) if (raw_v is not None and str(raw_v) != "nan") else ""
                    else:
                        rec[param_key] = f_val
                except (ValueError, TypeError):
                    rec[param_key] = str(raw_v) if (raw_v is not None and str(raw_v) != "nan") else ""
            history_records.append(rec)

    analysis = generate_initial_analysis(target_df) if not target_df.empty else {"recommendations": [], "references": []}
    
    unit_val = str(target_df["Unit_Name"].iloc[0]) if "Unit_Name" in target_df.columns and not target_df.empty else ""
    volt_val = str(target_df["Voltage_Level"].iloc[0]) if "Voltage_Level" in target_df.columns and not target_df.empty else ""

    # Nameplate specifications
    spec_dict = {}
    try:
        from src.data_loader import load_nameplate_csv
        df_np = load_nameplate_csv()
        if not df_np.empty:
            eq_np = df_np[df_np["Equipment"].astype(str).str.upper() == equipment_name.upper()]
            if not eq_np.empty:
                raw_dict = eq_np.iloc[0].to_dict()
                spec_dict = {
                    k: (str(v) if pd.notna(v) and str(v) != "nan" else "")
                    for k, v in raw_dict.items()
                }
    except Exception:
        pass

    # Build categorized telemetry groups
    electrical_params = {}
    pq_params = {}
    rotor_params = {}
    bearing_params = {}
    other_params = {}

    for k, v in structured_params.items():
        k_lower = k.lower()
        val_str = str(v.get("value", "")).strip()
        if not val_str or val_str in ("nan", "None"):
            val_str = "-"
        v_clean = {"value": val_str, "unit": v.get("unit", "")}
        
        if any(w in k_lower for w in ["current", "voltage", "arus", "tegangan", "dev current", "dev voltage"]):
            if "thd" in k_lower:
                pq_params[k] = v_clean
            else:
                electrical_params[k] = v_clean
        elif any(w in k_lower for w in ["thd", "power factor", "real power", "load", "beban", "pf"]):
            pq_params[k] = v_clean
        elif any(w in k_lower for w in ["rotor", "sideband", "rb", "se fund", "se harm"]):
            rotor_params[k] = v_clean
        elif any(w in k_lower for w in ["bearing", "kondisi", "status"]):
            bearing_params[k] = v_clean
        else:
            other_params[k] = v_clean

    telemetry_groups = {
        "electrical": electrical_params,
        "power_quality": pq_params,
        "rotor_bar": rotor_params,
        "mechanical": bearing_params,
        "other": other_params
    }

    return {
        "equipment": equipment_name,
        "unit": unit_val,
        "voltage": volt_val,
        "condition": cond_val,
        "latest_date": latest_date_str,
        "parameters": structured_params,
        "latest_parameters": latest_params,
        "telemetry_groups": telemetry_groups,
        "specification": spec_dict,
        "performance_summary": perf_summary,
        "recommendations": analysis.get("recommendations", []),
        "references": analysis.get("references", []),
        "history": history_records,
        "analysis": analysis
    }

@app.post("/api/rotorbar/calculate")
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


@app.get("/api/agents/specialists")
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

@app.get("/api/materi")
def get_materi_list():
    base_dir = os.path.dirname(__file__)
    materi_dir = os.path.join(base_dir, 'Materi')
    files = []
    if os.path.exists(materi_dir):
        files = sorted([f for f in os.listdir(materi_dir) if f.lower().endswith('.json')])
    materi = [
        {
            "id": os.path.splitext(f)[0],
            "filename": f,
            "title": os.path.splitext(f)[0].replace("-", " ").replace("_", " ").title(),
            "level": "General",
            "tags": [],
        }
        for f in files
    ]
    return {"materials": files, "materi": materi}

@app.post("/api/materi/search")
async def search_materi(
    payload: Optional[MateriSearchRequest] = Body(None),
    query: Optional[str] = Query(None, min_length=1),
):
    query_text = (payload.query if payload is not None else query) or ""
    query_text = query_text.strip()
    if not query_text:
        raise HTTPException(status_code=422, detail="query is required")
    results = search_knowledge_base(query_text, top_k=5)
    return {"results": results, "query": query_text}

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
    if df_latest.empty:
        return {"total_assets": 0, "health_summary": {}, "fleet_health_average": 90.0, "asset_matrix": []}

    eq_names = [str(e) for e in df_latest["Equipment"].dropna().unique()]
    
    asset_matrix = []
    health_counts = {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0}
    health_sum = 0.0

    for eq in eq_names[:60]: # Top 60 fleet assets
        eq_data = df_latest[df_latest["Equipment"] == eq]
        node = asset_graph.get_equipment_node(eq)
        
        fusion_inputs = _extract_mcsa_fusion_inputs(eq_data)

        fusion_res = fusion_agent.run_full_fusion(
            equipment=eq,
            asset_type=node.get("asset_type", "Electric Motor-Pump"),
            criticality=node.get("criticality", "A"),
            **fusion_inputs,
        )

        h_stat = fusion_res["health_status"]
        if h_stat in health_counts:
            health_counts[h_stat] += 1
        health_sum += fusion_res["health_index"]

        asset_matrix.append({
            "equipment": eq,
            "unit": node.get("unit", "UNIT COMMON"),
            "system": node.get("system", "Auxiliary"),
            "criticality": node.get("criticality", "A"),
            "health_index": fusion_res["health_index"],
            "health_status": h_stat,
            "health_color": fusion_res["health_color"],
            "primary_failure_mode": fusion_res["failure_mode_diagnosis"]["primary_failure_mode"],
            "severity": fusion_res["failure_mode_diagnosis"]["severity"],
            "confidence": fusion_res["failure_mode_diagnosis"]["confidence"],
            "rul_days": fusion_res["predictive_rul"]["estimated_rul_days"],
            "risk_level": fusion_res["risk_assessment"]["risk_level"]
        })

    avg_health = round(health_sum / len(asset_matrix), 1) if asset_matrix else 90.0
    
    # Sort asset matrix by severity descending and health index ascending
    asset_matrix.sort(key=lambda x: (x["health_index"], -x["severity"]))

    return {
        "total_assets": len(asset_matrix),
        "fleet_health_average": avg_health,
        "health_summary": health_counts,
        "critical_watchlist": [a for a in asset_matrix if a["health_status"] in ["CRITICAL", "ALERT", "WARNING"]][:10],
        "asset_matrix": asset_matrix
    }

@app.get("/api/reliability/fusion/{equipment_name}")
def get_equipment_fusion_diagnosis(equipment_name: str):
    df_raw, df_latest = get_data_frames()
    node = asset_graph.get_equipment_node(equipment_name)
    
    eq_data = df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment_name.upper()]
    
    fusion_inputs = _extract_mcsa_fusion_inputs(eq_data)

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

@app.get("/api/workorders")
def get_work_orders():
    work_orders = _load_work_orders()
    return {"work_orders": work_orders, "count": len(work_orders)}

class ApproveWORequest(BaseModel):
    wo_number: str
    approved_by: str
    action: Optional[str] = "Approve" # "Approve" | "Reject" | "Complete"

@app.post("/api/workorders/approve")
def approve_work_order(req: ApproveWORequest):
    work_orders = _load_work_orders()
    for wo in work_orders:
        if wo["wo_number"] == req.wo_number:
            if req.action == "Approve":
                wo["status"] = f"Approved by {req.approved_by} - In Progress"
            elif req.action == "Complete":
                wo["status"] = f"Completed & Closed by {req.approved_by}"
            elif req.action == "Reject":
                wo["status"] = f"Rejected by {req.approved_by}"
            _save_work_orders(work_orders)
            return {"status": "success", "work_order": wo}
            
    raise HTTPException(status_code=404, detail="Work Order not found")

# ---------------------------------------------------------------------------
# Vibration Asset Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/vibration/summary")
def get_vib_summary():
    """Quick counts by unit, status, and category."""
    try:
        return get_vibration_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vibration/equipment")
def get_vib_equipment_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """List vibration assets with optional filters."""
    kwargs = {}
    if unit and unit.upper() != "ALL":
        kwargs["unit_group"] = unit
    if status and status.upper() != "ALL":
        kwargs["status"] = status
    if category and category.upper() != "ALL":
        kwargs["equipment_class"] = category
    if search and search.strip():
        kwargs["keyword"] = search.strip()

    assets = search_vibration_assets(**kwargs)

    equipment = []
    for a in assets:
        equipment.append({
            "asset_id": a.get("asset_id", ""),
            "equipment": a.get("equipment", ""),
            "kks": a.get("kks", ""),
            "unit": a.get("unit_group", ""),
            "category": a.get("asset_category_derived", ""),
            "equipment_class": a.get("equipment_class_normalized", ""),
            "status": a.get("status_vibrasi", "NORMAL"),
            "pm_week": a.get("pm_week", ""),
            "measurement_date": a.get("measurement_date", ""),
            "component_1": a.get("component_1", ""),
            "component_2": a.get("component_2", ""),
            "c1_speed": a.get("c1_speed", ""),
            "c1_power": a.get("c1_power", ""),
            "c1_foundation": a.get("c1_foundation", ""),
        })

    return {"equipment": equipment, "count": len(equipment)}


@app.get("/api/vibration/equipment/{asset_id}")
def get_vib_equipment_detail(asset_id: str):
    """Full detail for a single vibration asset."""
    asset = get_vibration_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Vibration asset {asset_id} not found")

    bearing = get_bearing_info(asset_id) or {}

    # Build structured specs for motor (component 1)
    motor_specs = {}
    for key, label in [
        ("c1_type_mfg", "Type / Mfg"),
        ("c1_speed", "Speed"),
        ("c1_power", "Power"),
        ("c1_bearing_type", "Bearing Type"),
        ("c1_inboard_bearing", "Inboard Bearing"),
        ("c1_outboard_bearing", "Outboard Bearing"),
        ("c1_rotor_bar", "Rotor Bar"),
        ("c1_foundation", "Foundation"),
        ("c1_house_power", "House Power"),
        ("c1_rated_speed", "Rated Speed"),
        ("c1_rated_active_power", "Rated Active Power"),
        ("c1_rated_stator_voltage", "Rated Stator Voltage"),
        ("c1_rated_stator_current", "Rated Stator Current"),
    ]:
        val = asset.get(key)
        if val is not None and str(val).strip() and str(val).strip() not in ("None", "nan", "-"):
            motor_specs[label] = str(val)

    # Build structured specs for driven equipment (component 2)
    driven_specs = {}
    for key, label in [
        ("c2_type_mfg", "Type / Mfg"),
        ("c2_manufacturer", "Manufacturer"),
        ("c2_speed", "Speed"),
        ("c2_power", "Power"),
        ("c2_capacity", "Capacity"),
        ("c2_pressure", "Pressure"),
        ("c2_flow_rate", "Flow Rate"),
        ("c2_bearing_type", "Bearing Type"),
        ("c2_inboard_bearing", "Inboard Bearing"),
        ("c2_onboard_bearing", "Outboard Bearing"),
        ("c2_total_blade", "Total Blade"),
        ("c2_stages", "Stages"),
    ]:
        val = asset.get(key)
        if val is not None and str(val).strip() and str(val).strip() not in ("None", "nan", "-"):
            driven_specs[label] = str(val)

    # ISO evaluation recommendation based on status
    status = str(asset.get("status_vibrasi", "NORMAL")).upper()
    recommendation = "Kondisi getaran normal; lanjutkan monitoring berkala sesuai jadwal PM."
    if status == "WARNING":
        recommendation = "Getaran dalam zona waspada. Lakukan survei vibrasi terarah dan periksa alignment/pondasi dalam 1 minggu."
    elif status == "ALARM":
        recommendation = "Getaran melewati batas alarm. Periksa spektrum FFT untuk identifikasi sumber kerusakan, jadwalkan tindakan korektif."
    elif status == "PREWARNING":
        recommendation = "Tren vibrasi naik mendekati batas. Monitor lebih intensif dan periksa pelumasan bearing."

    # Look up matching test points and velocity max
    eq_name = str(asset.get("equipment", "")).strip()
    test_points = {}
    velocity_max = 0.0
    test_date = asset.get("measurement_date", "")
    try:
        all_tests = load_vibration_monthly_tests()
        for t in all_tests:
            t_eq = str(t.get("equipment", "")).strip()
            if t_eq.lower() in eq_name.lower() or eq_name.lower() in t_eq.lower():
                test_points = t.get("points", {})
                velocity_max = t.get("velocity_max", 0.0)
                test_date = t.get("test_date", test_date)
                break
    except Exception:
        pass

    return {
        "asset_id": asset.get("asset_id", ""),
        "equipment": asset.get("equipment", ""),
        "kks": asset.get("kks", ""),
        "unit": asset.get("unit_group", ""),
        "category": asset.get("asset_category_derived", ""),
        "equipment_class": asset.get("equipment_class_normalized", ""),
        "status": status,
        "pm_week": asset.get("pm_week", ""),
        "measurement_date": test_date or asset.get("measurement_date", ""),
        "velocity_max": velocity_max,
        "points": test_points,
        "component_1": asset.get("component_1", ""),
        "component_2": asset.get("component_2", ""),
        "motor_specs": motor_specs,
        "driven_specs": driven_specs,
        "bearing": bearing,
        "recommendation": recommendation,
    }


@app.get("/api/vibration/classes")
def get_vib_classes():
    """Distinct ISO equipment classes."""
    return {"classes": get_equipment_class_list()}


@app.get("/api/vibration/tests")
def get_vib_monthly_tests(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns monthly periodic vibration test records with individual measurement points (1V, 1H, 1A, etc.)."""
    try:
        tests = load_vibration_monthly_tests()
        if unit and unit.upper() != "ALL":
            tests = [t for t in tests if t["unit"].upper() == unit.upper()]
        if status and status.upper() != "ALL":
            tests = [t for t in tests if t["status"].upper() == status.upper()]
        if search and search.strip():
            st = search.lower().strip()
            tests = [t for t in tests if st in t["equipment"].lower()]
        return {"tests": tests, "count": len(tests)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# DGA (Transformer Oil) Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/dga/summary")
def get_dga_summary_endpoint():
    """Returns summary counts for transformers by status and unit."""
    try:
        return get_dga_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dga/transformers")
def get_dga_transformers_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns list of transformers with DGA analysis."""
    try:
        transformers = search_dga_transformers(unit=unit, status=status, search=search)
        return {"transformers": transformers, "count": len(transformers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dga/transformers/{transformer_id}")
def get_dga_transformer_detail_endpoint(transformer_id: str):
    """Returns full DGA details and historical trends for a transformer."""
    target = get_dga_transformer_detail(transformer_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Transformer {transformer_id} not found")
    return target


# ---------------------------------------------------------------------------
# Tribology (Lubricant & Wear) Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/tribology/summary")
def get_tribology_summary_endpoint():
    """Returns summary counts for lubrication samples."""
    try:
        return get_tribology_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tribology/samples")
def get_tribology_samples_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    oil_type: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns list of oil samples with evaluation."""
    try:
        samples = search_tribology_samples(unit=unit, status=status, oil_type=oil_type, search=search)
        return {"samples": samples, "count": len(samples)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tribology/samples/{sample_id}")
def get_tribology_sample_detail_endpoint(sample_id: str):
    """Returns detailed oil analysis and historical trend."""
    target = get_tribology_sample_detail(sample_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
    return target


# ---------------------------------------------------------------------------
# Thermal (Infrared Thermography / IRT) Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/thermal/summary")
def get_thermal_summary_endpoint():
    """Returns summary counts for IRT inspections."""
    try:
        return get_thermal_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/thermal/inspections")
def get_thermal_inspections_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns list of thermal IRT inspection points."""
    try:
        records = load_thermal_irt_tests()
        if unit and unit.upper() != "ALL":
            records = [r for r in records if r["unit"].upper() == unit.upper()]
        if status and status.upper() != "ALL":
            records = [r for r in records if r["status"].upper() == status.upper()]
        if search and search.strip():
            st = search.lower().strip()
            records = [r for r in records if st in r["equipment"].lower() or st in r["kks"].lower()]
        return {"inspections": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

