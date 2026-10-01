# Feature parity workflow backlog

> Temporary task list target for this session. The repo convention is GitHub Issues,
> but `gh` is unavailable in the current environment, so these tasks are recorded
> locally until they can be published upstream.

## Task WF-01: Align fleet and reliability parity contract

**Description:** Finalize the shared contract for fleet monitoring so React and
Streamlit present the same health, severity, stale-data, and watchlist semantics
even if their layouts differ.

**Acceptance criteria:**
- [x] React and Streamlit document the same ownership split for fleet monitoring and engineering drill-down.
- [x] The workflow explicitly defines how `UNKNOWN`, stale data, and missing domains are rendered.
- [x] The task identifies the shared use case / endpoint contract that both surfaces must trust.

**Verification:**
- [x] Review `docs/feature-parity.md` for the workflow boundary.
- [x] Confirm the referenced shared contract lives in FastAPI / `pple/application`, not UI code.
- [x] Manual check: no backlog item asks React to duplicate Streamlit-only engineering drill-downs.

**Dependencies:** None

**Files likely touched:**
- `docs/feature-parity.md`
- `pple/application/fleet.py`
- `frontend/src/FleetWorkspace.jsx`
- `src/pages/agent_dashboard_page.py`

**Estimated scope:** Medium

## Task WF-02: Narrow domain diagnosis parity to read/analyze flows

**Description:** Keep parity commitments for domain engineering focused on
read/analyze/dispatch workflows, while leaving ingest, QC, and manual authoring in
Streamlit unless a later ADR expands scope.

**Acceptance criteria:**
- [ ] The parity doc states that React does not own bulk ingest, QC, Word sync, or manual report authoring.
- [ ] Domain diagnosis parity covers status, evidence, confidence, provenance, and next action only.
- [ ] The backlog identifies any missing capability labels or unsupported-state messaging in React.

**Verification:**
- [ ] Review `docs/feature-parity.md` rows for the six engineering domains.
- [ ] Confirm the workflow boundary matches `docs/adr/ADR-0001-feature-parity-boundaries.md`.
- [ ] Manual check: no task asks for page-by-page cloning of Streamlit workspaces.

**Dependencies:** WF-01

**Files likely touched:**
- `docs/feature-parity.md`
- `frontend/src/CBMDashboard.jsx`
- `frontend/src/MCSAWorkspace.jsx`
- `pple/api/domain_router.py`

**Estimated scope:** Medium

## Task WF-03: Align chat, voice, and citation behavior

**Description:** Make the parity goal explicit for chat workflows: both surfaces
must respect the same safety, evidence, and fallback rules, while React remains the
canonical UX for voice and citation display.

**Acceptance criteria:**
- [ ] Chat parity expectations name the same safety boundary and rule-based source of truth.
- [ ] Citation support is described as a contract capability, not a prompt-only behavior.
- [ ] Voice-specific work is clearly marked React-canonical, not a Streamlit parity gap.

**Verification:**
- [ ] Review `docs/feature-parity.md` chat and RAG rows.
- [ ] Confirm the workflow references `src.chatbot`, `src.agents.master_agent`, and `/api/agent/chat`.
- [ ] Manual check: the backlog separates shared chat logic from React-only voice UX work.

**Dependencies:** WF-02

**Files likely touched:**
- `docs/feature-parity.md`
- `frontend/src/ChatWorkspace.jsx`
- `frontend/src/FloatingVoiceWidget.jsx`
- `pple/api/routers/agents.py`

**Estimated scope:** Medium

## Task WF-04: Close work-order parity gaps with shared lifecycle tests

**Description:** Keep work orders supported on both surfaces, but drive remaining
gaps through a shared lifecycle contract for create, approve, progress, complete,
reject, and safety checklist handling.

**Acceptance criteria:**
- [ ] The workflow backlog names state transitions that must stay identical across surfaces.
- [ ] The task identifies the API contract and test surface that will prove parity.
- [ ] UI-only differences are limited to layout and navigation.

**Verification:**
- [ ] Review the work-order row in `docs/feature-parity.md`.
- [ ] Confirm the lifecycle references `src.work_orders` and `/api/workorders/*`.
- [ ] Manual check: approval and safety checklist behavior are treated as shared rules, not per-UI logic.

**Dependencies:** WF-01

**Files likely touched:**
- `docs/feature-parity.md`
- `frontend/src/WorkOrdersWorkspace.jsx`
- `src/pages/work_orders_page.py`
- `tests/test_work_orders_api.py`

**Estimated scope:** Medium

## Task WF-05: Resolve settings parity scope and placeholders

**Description:** Remove ambiguity from Settings by distinguishing backend-backed
categories from placeholders, then decide which placeholder categories will be
implemented versus downgraded to not planned.

**Acceptance criteria:**
- [ ] The parity doc treats only backend-backed settings categories as supported parity.
- [ ] Placeholder settings categories are called out as non-parity scope until a backend exists.
- [ ] The backlog names the next concrete settings slice to implement or hide.

**Verification:**
- [ ] Review the settings row in `docs/feature-parity.md`.
- [ ] Confirm the scope matches `src/pages/settings_page.py` and `frontend/src/SettingsWorkspace.jsx`.
- [ ] Manual check: no placeholder is described as if it were operational today.

**Dependencies:** None

**Files likely touched:**
- `docs/feature-parity.md`
- `src/pages/settings_page.py`
- `frontend/src/SettingsWorkspace.jsx`

**Estimated scope:** Medium

## Task WF-06: Keep knowledge parity focused on search and upload

**Description:** Treat knowledge search and upload as supported parity, while
leaving delete/edit-governance workflows outside parity until audit-safe behavior is
defined.

**Acceptance criteria:**
- [ ] Search/read and upload remain supported parity workflows.
- [ ] Delete is explicitly documented as Streamlit-canonical or deferred pending audit design.
- [ ] The backlog identifies any UI messaging needed so React does not imply delete support.

**Verification:**
- [ ] Review knowledge rows in `docs/feature-parity.md`.
- [ ] Confirm the workflow references `/api/materi*` and `src.knowledge_processor`.
- [ ] Manual check: delete is not left ambiguous.

**Dependencies:** WF-05

**Files likely touched:**
- `docs/feature-parity.md`
- `frontend/src/DocumentWorkspace.jsx`
- `src/pages/materi_page.py`

**Estimated scope:** Small

## Task WF-07: Label canonical-only workflows across surfaces

**Description:** Add consistent labeling in docs and UI backlog so users can tell
which workflows are intentionally Streamlit-only, React-only, or CLI-only rather
than assuming a parity bug.

**Acceptance criteria:**
- [ ] Canonical-only workflows are grouped clearly in the parity document.
- [ ] The backlog identifies where unsupported workflows need explicit labeling or navigation hints.
- [ ] The task distinguishes "not planned" from "not implemented yet".

**Verification:**
- [ ] Review `docs/feature-parity.md` canonical-only sections.
- [ ] Confirm the labels match ADR-0001 terminology.
- [ ] Manual check: no row conflates absence with a future parity commitment.

**Dependencies:** WF-02

**Files likely touched:**
- `docs/feature-parity.md`
- `frontend/src/App.jsx`
- `app.py`

**Estimated scope:** Small

## Task WF-08: Add shared contract regression coverage for supported workflows

**Description:** Turn the parity decision into enforceable tests by adding
regression coverage at the FastAPI / `pple/application` boundary for each supported
workflow.

**Acceptance criteria:**
- [ ] Each supported workflow names the API or use-case test that should guard parity.
- [ ] Test work is sequenced after ownership decisions, not before them.
- [ ] The backlog avoids UI snapshot parity as the primary proof of correctness.

**Verification:**
- [ ] Review supported workflow rows and ensure each maps to a contract test target.
- [ ] Confirm the plan references existing API/use-case tests where available.
- [ ] Manual check: verification relies on shared business contracts first, UI checks second.

**Dependencies:** WF-01, WF-02, WF-03, WF-04, WF-05, WF-06

**Files likely touched:**
- `tests/test_api_server.py`
- `tests/test_application_use_cases.py`
- `docs/feature-parity.md`

**Estimated scope:** Medium

## Checkpoint CP-01: Ownership locked

- [ ] ADR-0001 and `docs/feature-parity.md` agree on canonical boundaries.
- [ ] Every workflow is categorized as canonical, supported, or not planned.

## Checkpoint CP-02: Backlog ready

- [ ] Every workflow task has acceptance criteria and verification steps.
- [ ] Shared-contract testing work is sequenced after ownership decisions.
- [ ] The backlog can be published to GitHub Issues once `gh` is available.
