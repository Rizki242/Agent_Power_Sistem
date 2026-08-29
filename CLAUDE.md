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

Tests use `unittest`, not pytest. `tests/test_api_server.py` uses FastAPI `TestClient` — no live server needed. Knowledge-retriever tests assert against actual `Materi/*.json` content, so renaming/removing those files can break them.

## Architecture

This is PPLE Agent — an integrated Predictive Maintenance (PdM) / Condition-Based Maintenance (CBM) platform for a power plant (PLTU Jeranjang, 3 × 25 MW), combining 6 specialist AI agents (Vibration, MCSA, DGA, Partial Discharge, Tribology, Thermal), a Reliability Fusion Engine, predictive RUL/failure-probability/risk scoring, a safety guardrail, Work Order/EAM integration, and a voice assistant.

Two UIs share one Python core:

- **Streamlit dashboard**: `app.py` + `src/pages/`. `app.py` imports every page module up front — one broken import kills the whole app with the venv-repair screen, so guard new page imports carefully.
- **React/Vite frontend** (`frontend/`) calling **FastAPI** `api_server.py` (thin HTTP layer over the same `src/` modules; do not duplicate business logic there).

`src/` layers:
- `src/pages/` + `src/components/` — Streamlit UI.
- `src/agents/` — specialist agents (`specialist_agents.py` for vibration/MCSA/DGA/PD/tribology/thermal), `fusion_engine.py` (multi-modal condition fusion / failure-mode correlation), `safety_guard.py` (blocks high-risk commands like trip/shutdown, requires human-in-the-loop authorization), `subagent_coordinator.py` (orchestrates the specialist agents + fusion/safety agents and aggregates their evidence), `asset_graph.py` (plant hierarchy: Plant → Unit → System → Equipment → Sub-components → Sensor Streams), `continuous_learning.py`, `self_improvement.py` (recursive accuracy tuning with a never-regress guardrail), `env_harness.py`.
- Domain modules at `src/` root: `data_loader.py`, `standards.py`, `knowledge_processor.py`/`knowledge_retriever.py`, `rag_engine.py`, `llm_assistant.py`, `docx_parser.py`/`docx_generator.py`, `ppt_generator.py`/`ppt_theme.py`/`ppt_assets.py`, `vibration_data.py`, `tribology_data.py`, `thermal_data.py`, `dga_data.py`, `rotorbar.py`, `report_batches.py`, `time_filters.py`, `analytics.py`, `metadata.py`, `chatbot.py`, `utils.py`.
- `src/agent_memory.py` — SQLite-backed conversation history (`data/agent_memory.db`). `src/agent_cron.py` — background daemon that periodically runs the `self_improvement` cycle and mines new measurement data for precursor patterns; every cycle is error-safe so a failing run never kills the daemon.

Rule-based logic is the source of truth. The LLM (`src/llm_assistant.py`) is an optional enhancement that always falls back to the rule answer on failure — never let it become a required dependency.

## Knowledge Base (Materi/)

- Documents are JSON in `Materi/`: schema v1 (list of `pages`, or object with a `pages` key) or v2 (single article object or array, with `id`/`title`/`tags`/`sections`); see README for examples.
- `src/knowledge_processor.py` converts uploads (PDF/MD/DOCX/JSON/TXT) into v2 JSON. After writing/deleting knowledge files you must call `load_knowledge_base(force_reload=True)` — the index is a cached module global.
- `src/knowledge_retriever.py` provides keyword search (always available, no extra deps). `src/rag_engine.py` adds optional LangChain + FAISS semantic search over `Materi/VIBRASI/` and `Materi/TRIBOLOGY/`; it needs optional packages (`langchain`, `langchain-community`, `faiss-cpu`, `sentence-transformers`) and every call path must fall back to keyword search when they are missing.
- For very large Materi files, search happens within the selected file only, to keep it fast; prefer splitting large files by topic.
- Gotcha: `knowledge_retriever.py` indexes guidance/thresholds from `data/config/`, but the real config lives in `data/MCSA/config/` — that indexing is currently a silent no-op.

## Data & Environment

- Data root resolves via `MCSA_DATA_DIR` (default `data/`); `get_data_path()` in `src/data_loader.py` transparently falls back to the `data/MCSA/` subfolder.
- Key files: `data/MCSA/Report MCSA.xls` (fallback Excel source), `data/MCSA/mcsa_updated.csv` (active merged data — result of Word sync + manual edits + merge), `data/MCSA/Laporan/` (recommended structure: `UNIT 1/380-400/...docx`, `UNIT 2/6.3/...docx`), `data/MCSA/config/` (equipment metadata and MCSA/ESA evaluation standards), `data/MCSA/backup/` (automatic CSV backups on save/sync).
- Saving `mcsa_updated.csv` writes a timestamped backup to `data/backup/` first (atomic replace); retention via `MCSA_MAX_BACKUPS` (default 5, minimum 1). Do not store `data/` on ephemeral filesystems in deployment — mount a persistent volume and point `MCSA_DATA_DIR` at it.
- Word-report sync: each upload batch is archived under `data/Laporan/uploads/YYYY/MM/DD/batch-HHMMSS-xxxxxx/` with a `manifest.json` (checksums, preview/quarantine status, `audit_events`) for audit. If the same equipment+date is re-uploaded, the newest batch becomes active data without deleting prior archives.
- `.env` is NOT auto-loaded by the app — except `src/llm_assistant.py`, which parses `.env` for AI API keys. API-key resolution order: argument → Streamlit session state → `st.secrets` → environment variables → `.env` file.
- Never hardcode API keys; read them from environment variables or `.streamlit/secrets.toml` (both gitignored). See `.env.example` for the variable list (`MCSA_DATA_DIR`, `MCSA_MAX_BACKUPS`, `WORK_ORDERS_FILE`, `VITE_API_BASE_URL`, `GEMINI_API_KEY`).

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
