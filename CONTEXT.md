# CONTEXT.md - PPLE Agent domain context

Single bounded context for the PPLE Agent repository (see `docs/agents/domain.md` for how agents consume this file). Read this before exploring the codebase; use the glossary's vocabulary in issue titles, plans, test names, and changelog entries. Architectural decisions live in `docs/adr/` (none recorded yet - create one when `docs/coding-protocol.md` section 13 says so).

## 1. What this system is

PPLE Agent is a Predictive Maintenance / Condition-Based Maintenance (PdM/CBM) platform for **PLTU Jeranjang** (coal-fired steam power plant, 3 units x 25 MW). It turns periodic condition-monitoring measurements into a diagnosed equipment condition, a recommendation, and - when warranted - a CBM Work Order. It never actuates the plant.

Three delivery surfaces share one Python core (`src/` + `pple/`): Streamlit dashboard (`app.py`), React/Vite frontend over FastAPI (`frontend/`, `api_server.py`), and the `pple` CLI. `docs/feature-parity.md` says which surface owns which feature.

## 2. Invariants (never violate)

1. **Rule-based logic is the source of truth.** Thresholds, condition/severity, fusion, RUL and risk are computed in local code (`src/standards.py`, `src/agents/*`, `pple/reliability`). An LLM only narrates and must always fall back to the rule answer.
2. **Missing data is `UNKNOWN` / a data gap, never "normal".** A domain without measurements is skipped and noted, never given a fabricated score.
3. **High-risk actions are blocked, not executed.** Trip/shutdown/breaker/isolation requests go through `SafetyGuardrailAgent` and require human authorization on every surface (UI, API, CLI).
4. **UI/API/CLI never duplicate business logic.** They validate, call the core, and render.
5. **Data writes are atomic, backed up, and auditable** (backups under `data/backup/`, upload batches with `manifest.json`, config mutations through `pple/core/audit.py`).
6. **Secrets never live in source or data files.** API keys come from env / `.env` / `secrets.toml` only.

## 3. Glossary

Use these terms exactly. Indonesian UI labels are given where they differ.

### Plant hierarchy

- **Plant** - PLTU Jeranjang as a whole.
- **Unit** - one of the three 25 MW generating units (Unit 1/2/3). Data folders and reports are grouped by unit.
- **System** - a functional grouping inside a unit (boiler, turbine, BOP...). Present in `src/agents/asset_graph.py`, lightly used elsewhere.
- **Equipment** (Indonesian: *peralatan*, *aset*) - the diagnosable asset: a motor, pump, fan, transformer, generator. Identified by a human name (e.g. `BFP 1A`) and, where imported from the vibration asset workbook, a **KKS code**. Do not use "asset" and "equipment" interchangeably in code names: `asset` is used for registry records (`src/asset_registry.py`, `pple/assets`), `equipment` for the diagnosed thing.
- **Sub-component** - bearing, rotor, stator, winding, air-gap: the failure location inside a piece of equipment.
- **Sensor stream** - a time series of one parameter for one piece of equipment.

### Measurement and data

- **Domain** (also *modul*, *disiplin*) - one of the six condition-monitoring disciplines: **Vibration** (*Vibrasi*), **MCSA** (Motor Current Signature Analysis; *ESA* is its older name in some files), **DGA** (Dissolved Gas Analysis), **PD** (Partial Discharge), **Tribology** (oil analysis), **Thermal** (thermography). Each has one specialist agent, one manifest, one Streamlit page, and one data source.
- **Measurement** - one value of one **parameter** for one equipment on one date. Canonical long-format row in `data/domain/<DOMAIN>/measurements.csv` (five non-MCSA domains) or `data/MCSA/mcsa_updated.csv` (MCSA).
- **Parameter** - a named quantity with an explicit unit (e.g. `overall_rms_mm_s`, `upper_sb_db`, `h2_ppm`). Parameter keys must match what the domain's specialist agent reads.
- **Seed of record** - each domain's original Excel/SQLite/CSV source, still authoritative until data is ingested into the canonical store.
- **Batch** - one upload of files (Word MCSA reports, or CSV/XLSX domain data) archived under `.../uploads/YYYY/MM/DD/batch-HHMMSS-xxxxxx/` with a `manifest.json`.
- **Preview / Quarantine / Commit** - the three ingest states. Quarantined rows fail validation and never reach the store. A re-uploaded equipment+date makes the newest batch active without deleting older archives.
- **Period** (*periode*) - the date window a page, trend chart, or report is scoped to.
- **Ringkasan Kinerja** - the Indonesian free-text performance-summary fields in MCSA reports (`- Kesimpulan`, `- Bearing`, `- Rotor`, `- Stator`, ...), used for qualitative insight.
- **Materi** - the knowledge base: JSON documents under `Materi/` (schema v1 pages or v2 articles), searched by keyword (`knowledge_retriever`) or optionally by embeddings (`rag_engine`).

### Diagnosis

- **Specialist agent** - a rule-based evaluator for one domain (`src/agents/specialist_agents.py`, wrapped unchanged by `pple/engineering/legacy_adapter.py`). Input: equipment + measurement dict. Output: a diagnosis dict.
- **Condition** (*kondisi*, *status*) - the qualitative state of equipment from one domain: `NORMAL`, `WARNING`, `ALERT`, `CRITICAL`, or `UNKNOWN` (insufficient data). Some MCSA thresholds use the wording good / alert / critical - map them to these five.
- **Severity** - integer 0-4 behind the condition (0 = unknown, 1 = normal, 2 = watch/warning, 3 = alarm/alert, 4 = critical). `pple/engineering/schemas.py` exposes it as the `Severity` enum (`NORMAL`, `WATCH`, `ALARM`, `CRITICAL`).
- **Health score / health index** - 0-100 numeric condition; `None` when unknown. Fusion produces a confidence-weighted health index, capped by the worst severity (ISO 13374 / MIMOSA style).
- **Confidence** - 0.0-1.0 trust in a diagnosis given data quality and coverage.
- **Evidence** - the measured values and threshold comparisons that justify a condition. Every diagnosis carries evidence, confidence, provenance, and `next_data_needed` when evidence is thin.
- **Failure mode / fault code / mechanism tag** - what is failing and how (e.g. broken rotor bar, bearing wear, thermal fault T2). Fault codes are the `FaultCode` enum.
- **DiagnosticResult** - the standard output shape targeted by the V2 migration (`pple/engineering/schemas.py`).
- **Fusion** - combining several domains' diagnoses for one equipment into one health index, RUL, and risk (`src/agents/fusion_engine.py` `ReliabilityFusionAgent`, `pple/reliability` `ReliabilityFusionEngine`). A disabled module or a domain with no data is excluded, never faked.
- **RUL** - Remaining Useful Life estimate (Indonesian speech: *sisa umur operasi*).
- **Risk** - failure probability x consequence, from `RiskEngine`.
- **Value type** - provenance label on every derived number: `measured`, `calculated`, `rule_based`, `ML_prediction`, `LLM_interpretation`.
- **Recommendation** (*rekomendasi*) - actionable maintenance advice attached to a diagnosis. Never a plant actuation command.
- **Fleet reliability** - the cross-equipment matrix built by `src/fleet_reliability.py`.

### Agents and orchestration

- **Master agent / chatbot** - `src/agents/master_agent.py` and `src/chatbot.MCSAChatbot`: answer natural-language questions from rule-based data first; the LLM (`src/llm_assistant.py`) only enriches.
- **SubAgentCoordinator** - runs the specialist agents plus Fusion and Safety and aggregates their evidence.
- **Safety guard** - `SafetyGuardrailAgent`: classifies a request as safe or **HIGH-RISK** (trip, shutdown, breaker, isolation...). HIGH-RISK is blocked outright and needs human-in-the-loop authorization.
- **Risk tier** (CLI) - `READ` (always allowed), `WRITE` (mutates PPLE config; needs y/N confirmation in `pple ask`/`pple shell`), `HIGH-RISK` (never executed).
- **Module** (V2) - a declarative engineering module (`pple/engineering/manifests/*.yaml`) with id, applicable equipment, capabilities, standards. Load status: `ACTIVE`, `DISABLED`, `ERROR`. Per-equipment enable/disable overrides live in `EquipmentModuleStore`.
- **Offline mode** - `pple --offline`: no cloud LLM call is possible; local `ollama` still allowed.
- **Automation** - a scheduled run of one whitelisted local action (`learning_cycle`, `knowledge_health_check`), optionally requiring human approval. Never a plant-affecting action.
- **Learning cycle / self-improvement** - background accuracy tuning with a never-regress guardrail (`src/agents/self_improvement.py`, `src/agent_cron.py`).
- **Voice assistant** - browser Web Speech API STT/TTS (`frontend/src/utils/speech.js`, `FloatingVoiceWidget.jsx`) over the same chat endpoint; the backend only supplies `summary_for_speech` text. No server-side TTS or voice cloning exists today.

### Maintenance and audit

- **Work Order (WO)** - a CBM maintenance request generated from a diagnosis (`src/work_orders.py`); duplicates for the same equipment/failure mode are returned, not recreated.
- **Audit log** - JSONL trail of configuration changes (WHO/WHAT/WHEN/OLD/NEW/SOURCE) in `data/audit/audit_log.jsonl`; fail-open.
- **Event** - one of the ten fixed names in `pple/core/events.py` (`equipment.created`, `measurement.uploaded`, `analysis.completed`, `workorder.requested`, ...). Publishing an unknown name raises.
- **Source** - which surface caused an action: `CLI`, `API`, `STREAMLIT`, `VOICE`.
- **Actor** - who did it: `X-Actor` header, `PPLE_ACTOR` env, or OS user.

## 4. Source-of-truth map

| Concern | Authoritative location | Do not put it in |
|---|---|---|
| MCSA/ESA thresholds | `src/standards.py`, `data/MCSA/config/` | UI pages, API routers, prompts |
| Domain diagnosis rules | `src/agents/specialist_agents.py` | `pple/engineering/modules/*` (metadata only) |
| Fusion / RUL / risk formulas | `src/agents/fusion_engine.py` (reused by `pple/reliability`) | anywhere new |
| High-risk action list | `src/agents/safety_guard.py` | `pple/cli/safety.py` (delegates), prompts |
| Editable asset records | `src/asset_registry.py` (JSON) | `pple/assets` (read-through view only) |
| Active MCSA data | `data/MCSA/mcsa_updated.csv` | `Report MCSA.xls` (fallback seed only) |
| Non-MCSA measurements | `data/domain/<DOMAIN>/measurements.csv` | each domain's seed Excel/SQLite once ingested |
| LLM provider/model preference | `data/MCSA/config/ai_settings.json` | API keys never go here |
| Feature ownership per surface | `docs/feature-parity.md` | - |
| Coding standards / DoD | `docs/coding-protocol.md` | - |
| Target architecture / roadmap | `docs/architecture-evolution.md`, `docs/final.md` | - |
| Change history by agents | `docs/agent-changelog.md` | commit messages alone |

## 5. Terms to avoid

- "asset" for a diagnosed piece of equipment in new code (use *equipment*; *asset* is the registry record).
- "healthy" / "OK" as a condition value (use `NORMAL`).
- "no data = normal" in any wording; say *data gap* / `UNKNOWN`.
- "execute", "trip", "shutdown" as something the agent does; it *recommends* and *blocks*.
- "database" for the current stores: there is no DB yet (deliberately deferred); say *store*, *CSV*, *JSON*, *SQLite file*.
- "ESA" in new names (use MCSA; keep ESA only where existing files already use it).

## 6. Open vocabulary gaps

Note here (or in an ADR) when a term is needed but undefined, so `/domain-modeling` can resolve it:

- `severity.changed` / `recommendation.created` events are declared but unpublished; the "previous value" concept they need has no name or owner yet.
- The relationship between `System` in `asset_graph.py` and the unit/equipment folders in `data/` is not formalized.
