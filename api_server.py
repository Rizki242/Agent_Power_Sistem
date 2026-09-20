import os
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd




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
print(f"[PPLE] CORS origins diizinkan: {', '.join(_cors_origins)}")
print(
    "[PPLE] Jika frontend gagal terhubung (CORS error di console browser), "
    "pastikan origin di atas cocok dengan alamat frontend, atau set PPLE_CORS_ORIGINS."
)

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
    automated_reports_router,
    automations_router,
    core_router,
    equipment_router,
    knowledge_router,
    rag_router,
    reports_router,
    settings_router,
    vibration_router,
    work_orders_router,
)
app.include_router(agents_router)
app.include_router(automated_reports_router)
app.include_router(automations_router)
app.include_router(core_router)
app.include_router(equipment_router)
app.include_router(knowledge_router)
app.include_router(rag_router)
app.include_router(reports_router)
app.include_router(settings_router)
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

from pple.api.routers.core import set_data_frames_provider as set_core_data_frames_provider
set_core_data_frames_provider(get_data_frames)

from pple.api.routers.equipment import set_data_frames_provider as set_equipment_data_frames_provider
set_equipment_data_frames_provider(get_data_frames)

from pple.api.routers.reports import set_data_frames_provider as set_reports_data_frames_provider
set_reports_data_frames_provider(get_data_frames)

from pple.api.routers.agents import (
    set_data_frames_provider as set_agents_data_frames_provider,
)
set_agents_data_frames_provider(get_data_frames)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

