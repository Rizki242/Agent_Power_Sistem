"""Safe system settings API; secrets and engineering thresholds are never exposed."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src import ai_settings
from src.automations import list_workflows
from src.knowledge_retriever import materi_dir
from src.llm_assistant import (
    AVAILABLE_GEMINI_MODELS,
    AVAILABLE_GROQ_MODELS,
    AVAILABLE_OLLAMA_MODELS,
    AVAILABLE_OPENCODE_MODELS,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENCODE_BASE_URL,
    DEFAULT_OPENCODE_MODEL,
    resolve_provider_key,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])
ProviderName = Literal["gemini", "groq", "opencode", "ollama"]


class ProviderStatus(BaseModel):
    configured: bool
    active: bool
    model: str
    models: List[str]


class SafetyPermission(BaseModel):
    name: str
    allowed: bool
    category: Literal["analysis", "actuation"]


class SafetyStatus(BaseModel):
    guardrail_active: bool = True
    core_locked: bool = True
    policy: str = "ISO 13374 / CBM Advisory"
    permissions: List[SafetyPermission]


class CBMDomainStatus(BaseModel):
    id: str
    name: str
    status: Literal["ACTIVE", "STANDBY", "EMPTY"]
    description: str


class DatabaseStatus(BaseModel):
    engine: str = "SQLite"
    status: Literal["HEALTHY", "WARNING", "ERROR"] = "HEALTHY"
    documents_count: int = Field(ge=0)
    max_backups: int = Field(ge=1)
    backup_frequency: str = "Daily"


class SystemStatus(BaseModel):
    api: Literal["ONLINE"] = "ONLINE"
    data_store: Literal["DEFAULT", "CUSTOM"]
    knowledge_documents: int = Field(ge=0)
    automation_workflows: int = Field(ge=0)
    scheduler: Literal["CONFIGURED"] = "CONFIGURED"
    api_auth_enabled: bool
    api_protection_label: str = "Protected — Localhost"
    custom_cors_enabled: bool
    max_backups: int = Field(ge=1)


class SettingsOverview(BaseModel):
    ai_enabled: bool
    active_provider: ProviderName
    providers: Dict[str, ProviderStatus]
    system: SystemStatus
    safety: SafetyStatus
    data_sources: List[CBMDomainStatus]
    database: DatabaseStatus
    version: str
    generated_at: datetime


class AISettingsUpdate(BaseModel):
    ai_enabled: bool
    ai_provider: ProviderName
    model: str = Field(min_length=1, max_length=160)
    ollama_host: Optional[str] = Field(default=None, max_length=500)
    opencode_base_url: Optional[str] = Field(default=None, max_length=500)


class AISettingsEnvelope(BaseModel):
    ai_enabled: bool
    active_provider: ProviderName
    model: str
    message: str


def _provider_model(preferences: dict, provider: str) -> str:
    defaults = {
        "gemini": DEFAULT_GEMINI_MODEL,
        "groq": DEFAULT_GROQ_MODEL,
        "opencode": DEFAULT_OPENCODE_MODEL,
        "ollama": DEFAULT_OLLAMA_MODEL,
    }
    return str(preferences.get(f"{provider}_model") or defaults[provider])


@router.get("/overview", response_model=SettingsOverview)
def get_settings_overview():
    preferences = ai_settings.load()
    active_provider = preferences.get("ai_provider", "gemini")
    if active_provider not in {"gemini", "groq", "opencode", "ollama"}:
        active_provider = "gemini"
    model_options = {
        "gemini": AVAILABLE_GEMINI_MODELS,
        "groq": AVAILABLE_GROQ_MODELS,
        "opencode": AVAILABLE_OPENCODE_MODELS,
        "ollama": AVAILABLE_OLLAMA_MODELS,
    }
    providers = {}
    for provider, models in model_options.items():
        configured = bool(preferences.get("ollama_host", DEFAULT_OLLAMA_HOST)) if provider == "ollama" else bool(resolve_provider_key(provider))
        providers[provider] = {
            "configured": configured,
            "active": provider == active_provider,
            "model": _provider_model(preferences, provider),
            "models": models,
        }

    knowledge_path = materi_dir()
    knowledge_count = 0
    if os.path.isdir(knowledge_path):
        knowledge_count = sum(name.lower().endswith(".json") for name in os.listdir(knowledge_path))
    try:
        max_backups = max(1, int(os.environ.get("MCSA_MAX_BACKUPS", "5")))
    except ValueError:
        max_backups = 5

    api_auth = bool(os.environ.get("PPLE_API_KEY"))
    protection_label = "Protected — API Key Required" if api_auth else "Protected — Localhost"

    safety = {
        "guardrail_active": True,
        "core_locked": True,
        "policy": "ISO 13374 / CBM Advisory Boundary",
        "permissions": [
            {"name": "Read equipment data & telemetry", "allowed": True, "category": "analysis"},
            {"name": "Analyze CBM multi-modal data", "allowed": True, "category": "analysis"},
            {"name": "Generate RUL & risk recommendations", "allowed": True, "category": "analysis"},
            {"name": "Create maintenance assessment report", "allowed": True, "category": "analysis"},
            {"name": "Control physical equipment", "allowed": False, "category": "actuation"},
            {"name": "Trip generator / motor breaker", "allowed": False, "category": "actuation"},
            {"name": "Shutdown plant boiler / turbine unit", "allowed": False, "category": "actuation"},
            {"name": "Modify protection relay thresholds", "allowed": False, "category": "actuation"},
        ],
    }

    data_sources = [
        {"id": "dga", "name": "DGA (Dissolved Gas Analysis)", "status": "ACTIVE", "description": "Analisa gas terlarut trafo (Duval Triangle & TDCG)"},
        {"id": "mcsa", "name": "MCSA & ESA", "status": "ACTIVE", "description": "Motor Current Signature & Electrical Signature Analysis"},
        {"id": "vibration", "name": "Vibration Mechanical", "status": "ACTIVE", "description": "Spektrum FFT, 1X/2X, dan kondisi bearing ISO 10816"},
        {"id": "thermal", "name": "Thermal / Infrared", "status": "ACTIVE", "description": "Termografi inframerah titik panas (hotspot) busbar & motor"},
        {"id": "tribology", "name": "Tribology & Oil", "status": "ACTIVE", "description": "Viskositas, TAN, kontaminasi partikel dan keausan Fe/Cu"},
        {"id": "pd", "name": "Partial Discharge", "status": "ACTIVE", "description": "Deteksi lucutan parsial isolasi stator tegangan tinggi"},
    ]

    database = {
        "engine": "SQLite",
        "status": "HEALTHY",
        "documents_count": knowledge_count,
        "max_backups": max_backups,
        "backup_frequency": "Daily",
    }

    return {
        "ai_enabled": bool(preferences.get("ai_enabled", False)),
        "active_provider": active_provider,
        "providers": providers,
        "system": {
            "data_store": "CUSTOM" if os.environ.get("MCSA_DATA_DIR") else "DEFAULT",
            "knowledge_documents": knowledge_count,
            "automation_workflows": len(list_workflows()),
            "api_auth_enabled": api_auth,
            "api_protection_label": protection_label,
            "custom_cors_enabled": bool(os.environ.get("PPLE_CORS_ORIGINS")),
            "max_backups": max_backups,
        },
        "safety": safety,
        "data_sources": data_sources,
        "database": database,
        "version": "2.0.0",
        "generated_at": datetime.now(timezone.utc),
    }


@router.post("/test-ai")
def test_ai_connection():
    from src import ai_settings
    from src.llm_assistant import (
        DEFAULT_GEMINI_MODEL,
        DEFAULT_GROQ_MODEL,
        DEFAULT_OLLAMA_HOST,
        DEFAULT_OPENCODE_BASE_URL,
        DEFAULT_OPENCODE_MODEL,
        resolve_provider_key,
        test_gemini_connection,
        test_groq_connection,
        test_ollama_connection,
        test_opencode_connection,
    )
    prefs = ai_settings.load()
    provider = prefs.get("ai_provider", "gemini")

    if provider == "gemini":
        key = resolve_provider_key("gemini")
        model = prefs.get("gemini_model", DEFAULT_GEMINI_MODEL)
        ok, msg = test_gemini_connection(key, model=model)
        return {"success": ok, "provider": provider, "model": model, "message": msg}

    elif provider == "groq":
        key = resolve_provider_key("groq")
        model = prefs.get("groq_model", DEFAULT_GROQ_MODEL)
        ok, msg = test_groq_connection(key, model=model)
        return {"success": ok, "provider": provider, "model": model, "message": msg}

    elif provider in {"opencode", "openai"}:
        key = resolve_provider_key(provider)
        base_url = prefs.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL)
        model = prefs.get(f"{provider}_model", DEFAULT_OPENCODE_MODEL)
        ok, msg = test_opencode_connection(base_url=base_url, api_key=key, model=model)
        return {"success": ok, "provider": provider, "model": model, "message": msg}

    elif provider == "ollama":
        host = prefs.get("ollama_host", DEFAULT_OLLAMA_HOST)
        ok, msg, _ = test_ollama_connection(host=host)
        return {"success": ok, "provider": provider, "message": msg}

    return {"success": False, "provider": provider, "message": f"Provider {provider} tidak dikenal."}


@router.put("/ai", response_model=AISettingsEnvelope)
def update_ai_settings(body: AISettingsUpdate):
    fields = {
        "ai_enabled": body.ai_enabled,
        "ai_provider": body.ai_provider,
        f"{body.ai_provider}_model": body.model.strip(),
    }
    if body.ai_provider == "ollama" and body.ollama_host:
        fields["ollama_host"] = body.ollama_host.strip()
    if body.ai_provider == "opencode" and body.opencode_base_url:
        fields["opencode_base_url"] = body.opencode_base_url.strip()
    saved = ai_settings.save(fields)
    return {
        "ai_enabled": bool(saved.get("ai_enabled", body.ai_enabled)),
        "active_provider": saved.get("ai_provider", body.ai_provider),
        "model": saved.get(f"{body.ai_provider}_model", body.model),
        "message": "Preferensi AI tersimpan. API key tetap dibaca dari environment.",
    }
