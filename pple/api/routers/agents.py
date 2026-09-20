"""Agents & Learning API router."""

from __future__ import annotations

from datetime import datetime
import io
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel

from pple.api.schemas.core import SpecialistSubAgentsResponse
from pple.core.audit import record_change
from src.agent_memory import (
    create_chat_session,
    delete_chat_session,
    get_chat_session_messages,
    list_chat_sessions,
    save_session_message,
    update_session_title,
)
from src.agents.continuous_learning import PowerPlantSkillLearner
from src.agents.env_harness import EnvRigger
from src.agents.master_agent import get_master_agent
from src.agents.safety_guard import SafetyGuardrailAgent
from src.agents.self_improvement import RecursiveSelfImprover
from src.agents.subagent_coordinator import SubAgentCoordinator
from src.chatbot import MCSAChatbot
from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
from src.llm_assistant import DEFAULT_GEMINI_MODEL, MCSALLMAssistant, resolve_provider_key

router = APIRouter(prefix="/api", tags=["agents"])

# Singletons for master agent, coordinator, safety guard, learning, and harness
master_agent = get_master_agent()
subagent_coordinator = SubAgentCoordinator()
safety_guard = SafetyGuardrailAgent()
plant_skill_learner = PowerPlantSkillLearner()
self_improver = RecursiveSelfImprover()
env_rigger = EnvRigger()

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


def extract_text_from_upload(file_bytes: bytes, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    try:
        if ext in [".txt", ".csv", ".json", ".md", ".log"]:
            return file_bytes.decode("utf-8", errors="ignore")
        elif ext == ".pdf":
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)
        elif ext in [".docx", ".docm"]:
            import docx

            doc = docx.Document(io.BytesIO(file_bytes))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        elif ext in [".xlsx", ".xls"]:
            excel_df = pd.read_excel(io.BytesIO(file_bytes))
            return excel_df.to_string(max_rows=100)
    except Exception as e:
        return f"[File text extraction note: {e}]"
    return f"[File {filename} attached]"


MONTH_NAMES_ID = {
    "januari": 1, "februari": 2, "maret": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "agustus": 8, "september": 9, "oktober": 10, "november": 11, "desember": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "agu": 8, "agt": 8, "sep": 9, "okt": 10, "nov": 11, "des": 12,
}


def detect_document_date(text: str, filename: str = "") -> Tuple[str, str, str]:
    """
    Ekstrak tanggal referensi dari teks dokumen atau nama file.
    Aturan bisnis:
    1. Jika di dalam dokumen terdapat tanggal, maka waktu data merujuk pada tanggal tersebut.
    2. Jika TIDAK ada tanggal, waktu data merujuk pada tanggal saat di-upload (hari ini).
    Mengembalikan (date_str_YYYY_MM_DD, source ['document'|'upload_date'], label).
    """
    sample = (filename + " " + text[:5000]).lower()

    # 1. Format ISO YYYY-MM-DD
    m_iso = re.search(r"\b(20\d{2})[-/](0[1-9]|1[0-2])[-/](0[1-9]|[12]\d|3[01])\b", sample)
    if m_iso:
        d_str = f"{m_iso.group(1)}-{m_iso.group(2)}-{m_iso.group(3)}"
        return (d_str, "document", f"Terdeteksi tanggal dokumen: {d_str}")

    # 2. Format DD/MM/YYYY atau DD-MM-YYYY
    m_dmy = re.search(r"\b(0?[1-9]|[12]\d|3[01])[-/](0?[1-9]|1[0-2])[-/](20\d{2})\b", sample)
    if m_dmy:
        day = int(m_dmy.group(1))
        month = int(m_dmy.group(2))
        year = int(m_dmy.group(3))
        d_str = f"{year:04d}-{month:02d}-{day:02d}"
        return (d_str, "document", f"Terdeteksi tanggal dokumen: {d_str}")

    # 3. Format teks Indonesia: "15 September 2026" atau "10 Okt 2025"
    m_txt = re.search(r"\b(0?[1-9]|[12]\d|3[01])\s+([a-zA-Z]{3,9})\s+(20\d{2})\b", sample)
    if m_txt:
        day = int(m_txt.group(1))
        m_name = m_txt.group(2).lower()
        year = int(m_txt.group(3))
        if m_name in MONTH_NAMES_ID:
            d_str = f"{year:04d}-{MONTH_NAMES_ID[m_name]:02d}-{day:02d}"
            return (d_str, "document", f"Terdeteksi tanggal dokumen: {d_str}")

    # 4. Format Bulan-Tahun: "September 2026"
    m_my = re.search(r"\b([a-zA-Z]{3,9})\s+(20\d{2})\b", sample)
    if m_my:
        m_name = m_my.group(1).lower()
        year = int(m_my.group(2))
        if m_name in MONTH_NAMES_ID:
            d_str = f"{year:04d}-{MONTH_NAMES_ID[m_name]:02d}-01"
            return (d_str, "document", f"Terdeteksi periode dokumen: {m_my.group(1).title()} {year} ({d_str})")

    # Fallback: Tidak ada tanggal pada dokumen -> merujuk ke tanggal upload hari ini
    today_str = datetime.now().strftime("%Y-%m-%d")
    return (today_str, "upload_date", f"Tidak ada tanggal pada dokumen -> Data merujuk pada tanggal upload ({today_str})")


# Request Models
class MultiAgentCollaborateRequest(BaseModel):
    equipment: str
    query: Optional[str] = ""
    custom_telemetry: Optional[Dict[str, Any]] = None


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


class SelfImproveRequest(BaseModel):
    max_iterations: Optional[int] = 6


class RecordPredictionRequest(BaseModel):
    equipment: str
    predicted_mode: str
    predicted_severity: int = 1
    confidence: float = 0.8
    actual_mode: Optional[str] = ""
    actual_severity: Optional[int] = None


class RiggerCycleRequest(BaseModel):
    equipment: Optional[str] = "BFP 1A"


@router.get("/agents/specialists", response_model=SpecialistSubAgentsResponse)
def get_specialist_subagents():
    """List all registered specialist sub-agents with capability metadata and standards."""
    return {
        "specialists": subagent_coordinator.list_specialists(),
        "total_count": len(subagent_coordinator.list_specialists()),
        "status": "ALL_ONLINE",
    }


@router.post("/agents/collaborate")
def collaborate_subagents(req: MultiAgentCollaborateRequest):
    """
    Execute multi-agent collaborative diagnosis across specialist sub-agents
    (Vibration, MCSA, DGA, PD, Tribology, Thermal, Fusion, Safety).
    """
    return subagent_coordinator.run_collaborative_diagnosis(
        equipment=req.equipment,
        query=req.query or f"Kolaborasi diagnosa kondisi {req.equipment}",
        custom_telemetry=req.custom_telemetry,
    )


@router.get("/skills/learned-patterns")
def get_learned_skill_patterns():
    """Retrieve all dynamically learned technical disturbance patterns and lessons."""
    skills = plant_skill_learner.load_learned_skills()
    return {
        "skills": skills,
        "total_count": len(skills),
        "status": "LEARNING_ACTIVE",
    }


@router.post("/skills/teach")
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
        author=req.author or "CBM Engineer PLTU Jeranjang",
    )


@router.get("/skills/benchmarks")
def get_diagnostic_benchmarks():
    """Run diagnostic benchmark suite across plant disturbance scenarios and compute accuracy score."""
    return plant_skill_learner.run_benchmarks()


@router.post("/api/agent/self-improve")
@router.post("/agent/self-improve")
def run_self_improvement_cycle(req: SelfImproveRequest):
    """
    Run one recursive self-improvement cycle:
    measure accuracy -> propose weight tuning -> validate -> retain only if improved.
    """
    return self_improver.run_improvement_cycle(max_iterations=req.max_iterations)


@router.get("/api/agent/improvement-status")
@router.get("/agent/improvement-status")
def get_self_improvement_status():
    """Report current generation, best score, weights, and prediction statistics of the learning engine."""
    return self_improver.get_status()


@router.post("/api/agent/predictions")
@router.post("/agent/predictions")
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


@router.post("/api/agent/learn-from-history")
@router.post("/agent/learn-from-history")
def learn_from_historical_data():
    """Mine historical MCSA measurement data for degradation precursor patterns (data-driven lessons)."""
    try:
        df = load_mcsa_data(get_data_path("mcsa_updated.csv"))
        if df is None or df.empty:
            df = load_mcsa_data(get_data_path("Report MCSA.xls"))
    except Exception as exc:
        return {"status": "error", "message": f"Gagal memuat data historis: {exc}", "lessons_created": 0}
    return self_improver.learn_from_history(df)


@router.get("/learning/harness-status")
def get_harness_status():
    """Report active EnvHarness wrappers (Stage, Contract, Chain) and EnvRigger history."""
    return env_rigger.get_status()


@router.post("/learning/rigger-cycle")
def execute_rigger_cycle(req: RiggerCycleRequest):
    """
    Run an automated EnvRigger Observe -> Diagnose -> Write -> Validate cycle,
    customizing the environment to target agent weaknesses and recording new skills.
    """
    return plant_skill_learner.run_env_rigger_learning(equipment=req.equipment or "BFP 1A")


@router.post("/learning/evaluate-harness")
def evaluate_agent_on_harness():
    """Evaluate diagnostic agent performance against wrapped composite EnvHarness environments."""
    return plant_skill_learner.evaluate_env_harness()


def generate_speech_summary(text: str, matched_equipment: Optional[str] = None) -> str:
    """
    Generate concise, natural spoken Indonesian narrative free of raw codes/tables.
    Optimized for radio/headset listening during plant field walkdown inspections.
    """
    if not text:
        return ""

    # Check for structured multi-agent CBM diagnostic output
    health_m = re.search(r"(?:Consolidated\s+Health\s+Index|Health\s+Score|Skor\s+Kesehatan)[*_]*\s*:\s*[*_]*([0-9.]+)(?:/100)?[*_]*\s*(?:\(([^)]+)\))?", text, re.IGNORECASE)
    failure_m = re.search(r"(?:Primary\s+Failure\s+Mode|Mode\s+Kegagalan)[*_]*\s*:\s*[*_]*([^\n\r*]+)", text, re.IGNORECASE)
    recom_m = re.search(r"(?:Rekomendasi\s+CBM|Rekomendasi\s+Tindakan|Rekomendasi)[*_]*\s*:\s*[*_]*([^\n\r*]+)", text, re.IGNORECASE)

    if health_m and matched_equipment:
        score = health_m.group(1).strip()
        status = (health_m.group(2) or "Normal").strip()
        mode = failure_m.group(1).strip() if failure_m else "kondisi operasi normal"
        recom = recom_m.group(1).strip() if recom_m else "lanjutkan pemantauan rutin"

        spoken_diag = (
            f"Laporan CBM untuk {matched_equipment}. "
            f"Indeks kesehatan {score} persen dengan status {status}. "
            f"Indikasi utama: {mode}. "
            f"Rekomendasi tindakan: {recom}."
        )
        return spoken_diag

    # Clean LaTeX math syntax
    clean = re.sub(r"\\(?:Delta|delta)\s*T", "Delta T", text)
    clean = re.sub(r"\\pm", "plus minus", clean)
    clean = re.sub(r"\\(?:times|cdot)", "kali", clean)
    clean = re.sub(r"\\(?:le|leq)", "kurang dari sama dengan", clean)
    clean = re.sub(r"\\(?:ge|geq)", "lebih dari sama dengan", clean)
    clean = re.sub(r"\\(?:mu|micro)", "mikro", clean)
    clean = re.sub(r"\\\s*%", "persen", clean)
    clean = re.sub(r"\\[a-zA-Z]+", " ", clean)  # drop any remaining latex commands
    clean = re.sub(r"[\$\(\)\[\]]{1,2}(.*?)[\$\(\)\[\]]{1,2}", r"\1", clean)

    # Strip markdown headers, code blocks, bold, bullets, table syntax
    clean = re.sub(r"```[\s\S]*?```", "", clean)
    clean = re.sub(r"\|[^\n]+\|", "", clean)
    clean = re.sub(r"^[\s*•#-]+", "", clean, flags=re.MULTILINE)
    clean = re.sub(r"[*_#~`]", "", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    clean = re.sub(r"\s+", " ", clean).strip()

    # Expand technical abbreviations for natural Indonesian pronunciation
    replacements = [
        (r"\bmm/s\b", "milimeter per detik"),
        (r"\bdegC\b", "derajat Celcius"),
        (r"°C", "derajat Celcius"),
        (r"\bTDCG\b", "T D C G total gas terlarut"),
        (r"\bpC\b", "piko Coulomb"),
        (r"\bTHD\b", "T H D distorsi harmonik"),
        (r"\bkV\b", "kilo Volt"),
        (r"\bMW\b", "Mega Watt"),
        (r"\bkW\b", "kilo Watt"),
        (r"\bRUL\b", "sisa umur operasi"),
        (r"\bDGA\b", "D G A"),
        (r"\bMCSA\b", "M C S A"),
        (r"\bISO\b", "standar I S O"),
        (r"\bIEEE\b", "standar I triple E"),
        (r"\bBFP\b", "B F P Boiler Feed Pump"),
        (r"\bCWP\b", "C W P Circulating Water Pump"),
        (r"\bID Fan\b", "I D Fan"),
        (r"\bFD Fan\b", "F D Fan"),
        (r"\bPA Fan\b", "P A Fan"),
        (r"\bPLTU\b", "P L T U"),
        (r"\bWO\b", "Work Order"),
    ]
    for pattern, rep in replacements:
        clean = re.sub(pattern, rep, clean, flags=re.IGNORECASE)

    # Take first 2-3 coherent sentences
    raw_sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", clean)
        if s.strip() and len(s.strip()) > 5
    ]
    if raw_sentences:
        speech = " ".join(raw_sentences[:3])
        if len(speech) > 320:
            speech = " ".join(raw_sentences[:2])
    else:
        speech = clean[:250]

    return speech.strip()



@router.get("/agent/chat/sessions")
def get_chat_sessions(session_type: Optional[str] = None, limit: int = 50):
    """Retrieve chat and task sessions for the chat sidebar."""
    return {"sessions": list_chat_sessions(session_type=session_type, limit=limit)}


@router.post("/agent/chat/sessions")
async def create_new_chat_session(request: Request):
    """Create a new chat session."""
    body = {}
    try:
        if "application/json" in request.headers.get("content-type", ""):
            body = await request.json()
    except Exception:
        pass
    title = body.get("title", "Untitled")
    session_type = body.get("session_type", "chat")
    session_id = create_chat_session(title=title, session_type=session_type)
    return {"session_id": session_id, "title": title, "session_type": session_type}


@router.get("/agent/chat/sessions/{session_id}")
def get_single_chat_session(session_id: str):
    """Retrieve messages for a specific chat session."""
    messages = get_chat_session_messages(session_id)
    return {"session_id": session_id, "messages": messages}


@router.delete("/agent/chat/sessions/{session_id}")
def delete_single_chat_session(session_id: str):
    """Delete a chat session and its messages."""
    delete_chat_session(session_id)
    return {"status": "success", "session_id": session_id}


@router.post("/agent/chat")
async def agent_chat(
    request: Request,
    message: Optional[str] = Form(None),
    provider: Optional[str] = Form("gemini"),
    model: Optional[str] = Form(DEFAULT_GEMINI_MODEL),
    api_key: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    df_raw, df_latest = get_data_frames()
    bot = MCSAChatbot(df_latest, df_all=df_raw)

    content_type = request.headers.get("content-type", "")
    file_name = None
    extra_file_context = ""
    source_val = source or request.headers.get("X-Source")
    session_id_val = None

    from src import ai_settings
    saved_ai = ai_settings.load()

    if "application/json" in content_type:
        body = await request.json()
        msg_text = body.get("message", "")
        prov = body.get("provider") or saved_ai.get("ai_provider") or "gemini"
        saved_model = saved_ai.get(f"{prov}_model")
        mdl = body.get("model") or saved_model or DEFAULT_GEMINI_MODEL
        k = body.get("api_key")
        source_val = body.get("source") or source_val or "CHAT"
        session_id_val = body.get("session_id")
    else:
        msg_text = message or ""
        prov = provider or saved_ai.get("ai_provider") or "gemini"
        saved_model = saved_ai.get(f"{prov}_model")
        mdl = model or saved_model or DEFAULT_GEMINI_MODEL
        k = api_key
        source_val = source_val or "CHAT"
        session_id_val = session_id
        if file and file.filename:
            file_name = file.filename
            file_bytes = await file.read()
            extracted_text = extract_text_from_upload(file_bytes, file.filename)
            detected_date, date_source, date_label = detect_document_date(extracted_text, file.filename)
            extra_file_context = (
                f"\n\n--- KONTEN DOKUMEN/FILE TERLAMPIR ({file.filename}) ---\n"
                f"[STATUS TEMPORAL DOKUMEN]: {date_label}\n"
                f"[WAKTU ACUAN PENGUJIAN]: {detected_date} (Sumber Acuan: {date_source})\n"
                f"[PEDOMAN ANALISIS HISTORIS & CONTINUOUS LEARNING]:\n"
                f"- Jika data bertanggal masa lalu ({date_source} == 'document'), perlakukan dokumen ini sebagai data historis/baseline.\n"
                f"- Jika dokumen tidak bertanggal ({date_source} == 'upload_date'), data merujuk pada pengukuran saat di-upload ({detected_date}).\n"
                f"- Jadikan data ini sebagai riwayat pembelajaran untuk menganalisis tren perubahan parameter, pola degradasi, dan perbandingan kondisi mesin dari waktu ke waktu.\n\n"
                f"{extracted_text[:12000]}\n--- AKHIR DOKUMEN TERLAMPIR ---"
            )

    # Save user message to session history if session_id is active
    if session_id_val and msg_text:
        save_session_message(
            session_id_val,
            "user",
            msg_text,
            payload={"file": file_name, "source": source_val},
        )
        # Automatically update Untitled sessions with a short title
        try:
            sessions = list_chat_sessions(limit=50)
            current_s = next((s for s in sessions if s["session_id"] == session_id_val), None)
            if current_s and current_s.get("title") == "Untitled":
                clean_title = msg_text[:32].strip()
                if len(msg_text) > 32:
                    clean_title += "..."
                update_session_title(session_id_val, clean_title)
        except Exception:
            pass

    bot_reply = bot.process_query(msg_text) if msg_text else ""
    if not bot_reply and file_name:
        bot_reply = f"File `{file_name}` berhasil diterima. Silakan ajukan pertanyaan terkait dokumen ini."

    # Asset resolution via Master Agent across all plant domains (MCSA, DGA, Vibration, Central Register)
    resolved_info = master_agent.resolve_asset(msg_text) if msg_text else None
    matched_eq = bot.last_matched_equipment or (resolved_info.get("equipment") if resolved_info else None)

    # Identify active specialist sub-agents
    active_agent_keys = subagent_coordinator.identify_relevant_agents(msg_text, matched_eq)
    active_subagents = []
    for k_agent in active_agent_keys:
        for s_desc in subagent_coordinator.list_specialists():
            if k_agent in s_desc["agent_id"] or k_agent == s_desc["domain"].lower():
                active_subagents.append(s_desc)
                break

    # Safety Guardrail Check
    safety_check = safety_guard.check_safety(msg_text)
    if not safety_check["safe"]:
        speech_warning = f"Peringatan keselamatan! Perintah ditolak oleh Safety Guardrail: {safety_check['message']}"
        record_change(
            entity="SAFETY_GUARDRAIL",
            field="command_intercepted",
            old_value=msg_text,
            new_value="BLOCKED",
            source=source_val or "CHAT",
            details={"reason": safety_check["message"]},
        )
        if session_id_val:
            save_session_message(
                session_id_val,
                "assistant",
                safety_check["message"],
                summary_for_speech=speech_warning,
                payload={"safety_blocked": True, "active_subagents": active_subagents},
            )
        return {
            "reply": safety_check["message"],
            "summary_for_speech": speech_warning,
            "matched_equipment": matched_eq,
            "ai_enhanced": False,
            "file_name": file_name,
            "provider": prov,
            "session_id": session_id_val,
            "safety_blocked": True,
            "active_subagents": active_subagents,
            "subagent_traces": [],
        }

    # Execute Multi-Agent Diagnostic Collaboration if equipment is recognized
    subagent_traces = []
    subagents_context = ""
    if matched_eq:
        try:
            collab_result = master_agent.execute_collaborative_diagnosis(matched_eq, msg_text)
            subagent_traces = collab_result.get("subagent_traces", [])
            subagents_context = (
                f"Consolidated Health: {collab_result.get('consensus_health_index')}/100 ({collab_result.get('consensus_health_status')})\n"
                f"Primary Failure Mode: {collab_result.get('consensus_failure_mode')} (Confidence: {collab_result.get('consensus_confidence', 0.9)*100:.0f}%)\n"
                f"Estimated RUL: {collab_result.get('predictive_rul', {}).get('estimated_rul_days')} hari\n"
            )
            for t in subagent_traces:
                subagents_context += f"• [{t['subagent']['name']}] ({t['status']}): {t['key_finding']}\n"

            # If bot_reply was empty (e.g. non-MCSA transformer or vibration asset), format full diagnosis
            if not bot_reply:
                h_idx = collab_result.get("consensus_health_index", 90.0)
                h_st = collab_result.get("consensus_health_status", "HEALTHY")
                f_mode = collab_result.get("consensus_failure_mode", "Operasi Normal")
                rul_days = collab_result.get("predictive_rul", {}).get("estimated_rul_days", "N/A")
                dec = collab_result.get("maintenance_decision", {}).get("recommended_action", "Lanjutkan pemantauan berkala.")
                diag_lines = [
                    f"### 📋 Evaluasi CBM Multi-Disiplin: **{matched_eq}**",
                    f"- **Unit & Sistem**: {collab_result.get('unit', '-')} | {collab_result.get('system', '-')}",
                    f"- **Tipe Aset & Kritikalitas**: {collab_result.get('asset_type', '-')} (Kelas {collab_result.get('criticality', '-')})",
                    f"- **Consolidated Health Index**: **{h_idx}/100** ({h_st})",
                    f"- **Primary Failure Mode**: {f_mode}",
                    f"- **Prediksi Sisa Umur (RUL)**: **{rul_days} hari**",
                    f"- **Rekomendasi CBM**: {dec}",
                    "\n#### 🔬 Temuan Specialist Sub-Agents:",
                ]
                for tr in subagent_traces:
                    diag_lines.append(f"- {tr['subagent'].get('icon', '🔹')} **{tr['subagent']['name']}** [{tr.get('status')}]: {tr.get('key_finding')}")
                bot_reply = "\n".join(diag_lines)
        except Exception as e:
            print(f"Sub-agent collaboration note: {e}")

    resolved_key = resolve_provider_key(prov, k)
    ai_enhanced = False
    final_reply = bot_reply
    resilience_meta = {
        "primary_provider": prov,
        "primary_model": mdl,
        "effective_provider": prov,
        "effective_model": mdl,
        "failover_occurred": False,
        "fallback_used": None,
    }

    citations = []
    assistant = None
    if resolved_key or str(prov).lower() in ("ollama", "opencode"):
        try:
            assistant = MCSALLMAssistant(
                enabled=True,
                provider=prov or "gemini",
                model=mdl or DEFAULT_GEMINI_MODEL,
                api_key=resolved_key or "local",
            )
            if assistant.available:
                ai_resp = assistant.enhance_answer(
                    question=msg_text or f"Analisis isi dokumen {file_name}",
                    rule_answer=bot_reply,
                    df_context=df_latest,
                    df_history=df_raw,
                    include_knowledge=True,
                    extra_file_context=extra_file_context,
                    subagents_context=subagents_context,
                )
                r_info = getattr(assistant, "resilience_info", {})
                if r_info:
                    resilience_meta.update(r_info)
                    prov = r_info.get("effective_provider", prov)
                    mdl = r_info.get("effective_model", mdl)

                if getattr(assistant, "last_citations", None):
                    citations = assistant.last_citations

                if ai_resp and len(ai_resp.strip()) > 10 and ai_resp.strip() != bot_reply.strip() and not getattr(assistant, "last_error", None):
                    final_reply = ai_resp
                    ai_enhanced = True
        except Exception as e:
            print(f"LLM AI processing note: {e}")

    # Fallback to direct RAG retrieval if citations not yet populated and query exists
    if not citations and msg_text:
        try:
            from src.knowledge_retriever import build_knowledge_context
            _, retrieved_cits = build_knowledge_context(msg_text, max_items=3, use_rag=True)
            if retrieved_cits:
                citations = retrieved_cits
        except Exception as e:
            print(f"Direct RAG retrieval note: {e}")

    speech_summary = generate_speech_summary(final_reply, matched_eq)

    # Log voice commands or significant equipment queries in the audit trail
    if source_val == "VOICE":
        record_change(
            entity=matched_eq or "VOICE_COMMAND",
            field="voice_input",
            old_value=msg_text,
            new_value="PROCESSED",
            source="VOICE",
            details={"summary": speech_summary[:120]},
        )

    if session_id_val:
        save_session_message(
            session_id_val,
            "assistant",
            final_reply,
            summary_for_speech=speech_summary,
            payload={
                "matched_equipment": matched_eq,
                "ai_enhanced": ai_enhanced,
                "safety_blocked": False,
                "subagent_traces": subagent_traces,
                "active_subagents": active_subagents,
                "provider": prov,
                "model": mdl,
                "resilience": resilience_meta,
                "citations": citations,
            },
        )

    return {
        "reply": final_reply,
        "summary_for_speech": speech_summary,
        "matched_equipment": matched_eq,
        "ai_enhanced": ai_enhanced,
        "file_name": file_name,
        "provider": prov,
        "model": mdl,
        "session_id": session_id_val,
        "active_subagents": active_subagents,
        "subagent_traces": subagent_traces,
        "resilience": resilience_meta,
        "citations": citations,
    }
