# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Windows-first repo; `.bat` scripts create/use `.venv` with Python 3.11 (`py -3.11`, with fallbacks). A `.venv` mixed across Python versions (cp311 vs cp313) triggers the dependency-repair screen in `app.py` — recreate the venv if that appears.

- Full build + test: `.\build.bat` (venv → pip install → frontend build → unit tests → `verify_app.py`)
- Unit tests (must run from repo root; tests import `from src...` and `from api_server import app`):
  `python -m unittest discover -s . -p "test_*.py"`
- Single test: `python -m unittest tests.test_chatbot` or `python -m unittest tests.test_chatbot.ChatbotTests.test_fuzzy_match_equipment`
- Functional verification (data loading, chatbot, PPT generation, Materi schema): `python verify_app.py` (requires `Report MCSA.xls` or `mcsa_updated.csv` to be present)
- RAG index (optional deps): `python build_rag_index.py [--force] [--test "<query>"]`
- Frontend lint uses **oxlint** (not eslint): `npm --prefix frontend run lint`; build: `npm --prefix frontend run build`
- Run: `run.bat` (Streamlit :8501), `run_api.bat` (FastAPI :8000, Swagger at `/docs`), `run_frontend.bat` (Vite :5173), `run_all.bat` (backend + frontend)
- `pple` CLI (additive, see `pple/` below): `pip install -e .` once (registers the console script via `pyproject.toml`, no other deps declared there), then `pple status`, `pple doctor`, `pple module list` / `pple module show <id>`, `pple analyze <module_id> <equipment> --data '<json>'`, `pple equipment modules <equipment>` / `module-add` / `module-remove`, `pple assets tree|list|show`, `pple reliability health <equipment_id>`, `pple agents list`.

Tests use `unittest`, not pytest. `tests/test_api_server.py` uses FastAPI `TestClient` — no live server needed. Knowledge-retriever tests assert against actual `Materi/*.json` content, so renaming/removing those files can break them. For Streamlit UI changes, verify with `streamlit.testing.v1.AppTest` (see `tests/test_streamlit_app.py`) — `AppTest.from_file("app.py")` for a full app load, `AppTest.from_function(...)` to exercise one `render_*` page function directly without needing a real nav route.

## Architecture

This is PPLE Agent — an integrated Predictive Maintenance (PdM) / Condition-Based Maintenance (CBM) platform for a power plant (PLTU Jeranjang, 3 × 25 MW), combining 6 specialist AI agents (Vibration, MCSA, DGA, Partial Discharge, Tribology, Thermal), a Reliability Fusion Engine, predictive RUL/failure-probability/risk scoring, a safety guardrail, Work Order/EAM integration, and a voice assistant.

Two UIs share one Python core:

- **Streamlit dashboard**: `app.py` + `src/pages/`. `app.py` imports every page module up front — one broken import kills the whole app with the venv-repair screen, so guard new page imports carefully. Routing uses `st.navigation`/`st.Page`, grouped to match `docs/desain.png`'s target IA (Command Center/Asset Management/Engineering/Reliability/AI Agent/Knowledge/Reports/Work Orders/Settings/Help & Support); each nav entry is a no-arg closure built in `app.py` that closes over variables the script computes earlier, so individual `render_*` page functions still just take `st` (+ explicit data) as before.
- **React/Vite frontend** (`frontend/`) calling **FastAPI** `api_server.py` (thin HTTP layer over the same `src/` modules; do not duplicate business logic there).

`src/` layers:
- `src/pages/` + `src/components/` — Streamlit UI.
- `src/agents/` — specialist agents (`specialist_agents.py` for vibration/MCSA/DGA/PD/tribology/thermal), `fusion_engine.py` (multi-modal condition fusion / failure-mode correlation), `safety_guard.py` (blocks high-risk commands like trip/shutdown, requires human-in-the-loop authorization), `subagent_coordinator.py` (orchestrates the specialist agents + fusion/safety agents and aggregates their evidence), `asset_graph.py` (plant hierarchy: Plant → Unit → System → Equipment → Sub-components → Sensor Streams), `continuous_learning.py`, `self_improvement.py` (recursive accuracy tuning with a never-regress guardrail), `env_harness.py`.
- Domain modules at `src/` root: `data_loader.py`, `standards.py`, `knowledge_processor.py`/`knowledge_retriever.py`, `rag_engine.py`, `llm_assistant.py`, `docx_parser.py`/`docx_generator.py`, `ppt_generator.py`/`ppt_theme.py`/`ppt_assets.py`, `vibration_data.py`, `tribology_data.py`, `thermal_data.py`, `dga_data.py`, `rotorbar.py`, `report_batches.py`, `time_filters.py`, `analytics.py`, `metadata.py`, `chatbot.py`, `utils.py`.
- `src/agent_memory.py` — SQLite-backed conversation history (`data/agent_memory.db`). `src/agent_cron.py` — background daemon that periodically runs the `self_improvement` cycle and mines new measurement data for precursor patterns; every cycle is error-safe so a failing run never kills the daemon.

Rule-based logic is the source of truth. The LLM (`src/llm_assistant.py`) is an optional enhancement that always falls back to the rule answer on failure — never let it become a required dependency.

## PPLE V2 migration (`pple/` package)

An incremental migration toward a dynamic, plugin-based module architecture is underway alongside (not replacing) `src/`, following the 30-phase plan in `docs/final.md` (baseline + gap analysis in `docs/pple_v2_baseline.md`). `pple/core` must never import Streamlit/React; FastAPI, Streamlit, and the CLI are meant to converge on the same service layer over time.

- `pple/engineering/`: `base.py` (`EngineeringModule` ABC — validate/analyze/diagnose/recommend), `schemas.py` (`DiagnosticResult`, the target standard output shape), `legacy_adapter.py` (`LegacyAgentAdapterModule` wraps the existing `src.agents.specialist_agents.*Agent.evaluate()` calls unchanged — the 6 domain modules under `modules/` are thin metadata declarations on this base, not reimplementations), `manifests/*.yaml` + `loader.load_modules_from_manifests()` (declarative id/applicable_equipment/capabilities/standards per module; a broken manifest reports `ERROR` in the load result but never crashes the scan), `registry.py` (`ModuleRegistry`: register/get/list/get_for_equipment), `equipment_modules.py` (`EquipmentModuleStore`: JSON-backed per-equipment-instance module enable/disable override, default opt-out).
- `src/agents/fusion_engine.py`'s `ReliabilityFusionAgent` and `src/agents/subagent_coordinator.py`'s `SubAgentCoordinator` each build their own `ModuleRegistry` + `EquipmentModuleStore` and consult them live — a disabled module is excluded exactly like a domain with no data, never given a fabricated score.
- `pple/assets/`: `AssetRegistry` (Phase 3) — a **read-through** Plant → Unit → Equipment view built fresh from `src.dga_data`/`src.vibration_data` on every call, not a persisted store. Deliberately separate from `src/asset_registry.py` (the CRUD-capable, JSON-backed register behind the Streamlit "Register Aset" page) — that one is the editable source of truth for cross-domain asset records + condition history; `pple/assets` is a derived, read-only aggregation for the CLI/API v2 surface. Don't merge them without a deliberate migration; they serve different callers today.
- `pple/reliability/`: `ReliabilityFusionEngine` (Phase 11/17) — fuses a `DiagnosticResult[]` (confidence-weighted health index, ISO 13374/MIMOSA severity capping) and reuses `src.agents.fusion_engine`'s calibrated `RULPredictor`/`RiskEngine` for RUL/risk rather than inventing new formulas. `FusionResult` labels every derived field's `ValueType` (`measured`/`calculated`/`rule_based`/`ML_prediction`/`LLM_interpretation`). `fuse_equipment()` sources real DGA gas readings and vibration monthly-test records via `pple/assets` + `pple/engineering`; a domain with no matching real measurement is skipped and recorded in `FusionResult.notes`, never faked.
- `pple/agents/`: `AgentRegistry` (Phase 18) — reuses `SubAgentCoordinator.list_specialists()`'s existing 8-agent descriptor metadata rather than re-declaring it, but overrides the 6 specialists' status with the real manifest load result (ACTIVE/DISABLED/ERROR) instead of the coordinator's hardcoded "ONLINE"; Fusion/Safety (not manifest-driven) stay "ONLINE".
- `pple/api/router.py`: additive `/api/v2/*` FastAPI routes (modules, module-load-report, equipment/{id}/modules, assets/tree, assets, assets/{id}, reliability/{id}, agents, agents/{id}), mounted in `api_server.py` alongside legacy `/api/*` — never replaces or duplicates a legacy endpoint.
- `pple/cli/main.py`: Typer + Rich CLI (see the `pple` command above; also `pple assets tree|list|show`, `pple reliability health <equipment_id>`, `pple agents list`).
- No database yet — deliberately deferred (`docs/final.md` Phase 2-4) as the highest-risk, non-critical-path piece; equipment-module overrides and manifests stay file-based (JSON/YAML) in the meantime. `pple/database/` stays an empty stub until that phase is picked up.

## Knowledge Base (Materi/)

- Documents are JSON in `Materi/`: schema v1 (list of `pages`, or object with a `pages` key) or v2 (single article object or array, with `id`/`title`/`tags`/`sections`); see README for examples.
- `src/knowledge_processor.py` converts uploads (PDF/MD/DOCX/JSON/TXT) into v2 JSON. After writing/deleting knowledge files you must call `load_knowledge_base(force_reload=True)` — the index is a cached module global.
- `src/knowledge_retriever.py` provides keyword search (always available, no extra deps). `src/rag_engine.py` adds optional LangChain + FAISS semantic search over `Materi/VIBRASI/` and `Materi/TRIBOLOGY/`; it needs optional packages (`langchain`, `langchain-community`, `faiss-cpu`, `sentence-transformers`) and every call path must fall back to keyword search when they are missing.
- For very large Materi files, search happens within the selected file only, to keep it fast; prefer splitting large files by topic.
- `knowledge_retriever.py` indexes guidance/thresholds from `data/config/`, falling back to `data/MCSA/config/` (where the real files actually live) when the former doesn't exist — fixed in commit `f9ce79b`.

## Data & Environment

- Data root resolves via `MCSA_DATA_DIR` (default `data/`); `get_data_path()` in `src/data_loader.py` transparently falls back to the `data/MCSA/` subfolder.
- Key files: `data/MCSA/Report MCSA.xls` (fallback Excel source), `data/MCSA/mcsa_updated.csv` (active merged data — result of Word sync + manual edits + merge), `data/MCSA/Laporan/` (recommended structure: `UNIT 1/380-400/...docx`, `UNIT 2/6.3/...docx`), `data/MCSA/config/` (equipment metadata and MCSA/ESA evaluation standards), `data/MCSA/backup/` (automatic CSV backups on save/sync).
- Saving `mcsa_updated.csv` writes a timestamped backup to `data/backup/` first (atomic replace); retention via `MCSA_MAX_BACKUPS` (default 5, minimum 1). Do not store `data/` on ephemeral filesystems in deployment — mount a persistent volume and point `MCSA_DATA_DIR` at it.
- Word-report sync: each upload batch is archived under `data/Laporan/uploads/YYYY/MM/DD/batch-HHMMSS-xxxxxx/` with a `manifest.json` (checksums, preview/quarantine status, `audit_events`) for audit. If the same equipment+date is re-uploaded, the newest batch becomes active data without deleting prior archives.
- `.env` is NOT auto-loaded by the app — except `src/llm_assistant.py`, which parses `.env` for AI API keys. API-key resolution order: argument → Streamlit session state → `st.secrets` → environment variables → `.env` file.
- Never hardcode API keys; read them from environment variables or `.streamlit/secrets.toml` (both gitignored). See `.env.example` for the variable list (`MCSA_DATA_DIR`, `MCSA_MAX_BACKUPS`, `WORK_ORDERS_FILE`, `VITE_API_BASE_URL`, `GEMINI_API_KEY`, `PPLE_API_KEY`, `PPLE_CORS_ORIGINS`, `VITE_API_KEY`).
- API security lives in `pple/api/security.py`, applied in `api_server.py` as one HTTP middleware (not per-route `Depends`) so every current and future route is covered: `PPLE_API_KEY` empty keeps the API open as before, set means every request except `/api/health` needs `X-API-Key` (or `Authorization: Bearer`). CORS origins come from `PPLE_CORS_ORIGINS`, defaulting to localhost only - never restore `allow_origins=["*"]` with `allow_credentials=True`, browsers reject that pairing. The React client sends the key through `apiFetch()` in `frontend/src/api.js`; use it instead of bare `fetch()` for backend calls.

## Domain notes (MCSA/ESA thresholds)

Rule-based thresholds used across the codebase (keep these consistent when touching `standards.py` / specialist agents):
- Rotor Bar sideband (Upper/Lower SB): good if < -54 dB; alert -54 to -45 dB; critical if ≥ -45 dB. Corroborate with RB Health Index and Se harmonic/fundamental ratio when available.
- Voltage/current unbalance (per-phase deviation %): voltage >1% alert, >2% high; current >5% alert, >10% high.
- Voltage THD (IEEE 519 reference): >5% alert, >8% high.
- Bearing/Stator/Air-gap: use the Indonesian-language "Ringkasan Kinerja" (Performance Summary) text fields for qualitative insight, prefixed e.g. `Ringkasan Kinerja - Kesimpulan`, `- Bearing`, `- Rotor`, `- Stator`, `- Distorsi Harmonik`, etc. (see README for the full list).

## Primary Goal

- Preserve the existing MCSA workflow and data model.
- Make small, targeted changes that fit the current codebase.
- Prefer improving the existing rule-based logic over replacing it.

## Before Making Changes

- Read `README.md` and the relevant source files first.
- Follow the local patterns already used in `app.py` and `src/`.
- Check for existing tests and extend them when behavior changes.

## Coding Rules

- Keep edits narrowly scoped.
- Use ASCII by default unless the file already uses non-ASCII text. UI text and docstrings are mostly Bahasa Indonesia — keep new user-facing strings in Indonesian.
- Do not add new frameworks or abstractions unless they clearly remove real complexity.
- Keep UI and business logic aligned with the current Streamlit app structure.

## AI / LLM Rules

- Treat the LLM as an assistant layer, not the source of truth.
- Keep MCSA calculations, thresholds, and status logic in local code.
- Never hardcode API keys in source files.
- Read keys from environment variables or `secrets.toml`.
- If an AI provider is added, make it optional and keep a non-AI fallback.

## Validation Rules

- Add or update tests for behavior changes.
- Run the relevant test commands after edits (see Commands).
- Run `python verify_app.py` before claiming completion.

## Safety Rules

- Do not overwrite user changes you did not make.
- Do not use destructive git commands unless explicitly requested.
- If a file already has an established pattern, follow that pattern instead of inventing a new one.

## Agent skills

### Issue tracker

Issues and tasks are tracked via GitHub Issues (`gh` CLI). See `docs/agents/issue-tracker.md`. Note: this working copy may not have `.git` initialized; those docs describe the upstream repo workflow.

### Triage labels

Canonical triage vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout (`CONTEXT.md` + `docs/adr/`). See `docs/agents/domain.md`. These files are created lazily by the domain-modeling skill; proceed silently if absent.
