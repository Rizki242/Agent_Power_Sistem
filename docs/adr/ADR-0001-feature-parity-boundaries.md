# ADR-0001: Workflow-based feature parity boundaries

- **Status:** Accepted
- **Date:** 2026-10-01

## Context

PPLE Agent currently ships multiple delivery surfaces over one rule-based Python core:
Streamlit, React/Vite over FastAPI, and the `pple` CLI. `docs/feature-parity.md`
already records current capabilities, but it mixes "implemented today", "supported
on two surfaces", and "future parity expectations" without a final ownership rule.

That ambiguity creates two recurring risks:

1. a React or Streamlit change quietly widens scope until it starts duplicating a
   workflow that should stay canonical elsewhere; and
2. backlog items are written as generic "achieve parity" tasks instead of targeted
   work on the few workflows that actually need cross-surface consistency.

The repository rules require architectural decisions that change the Streamlit /
React / API / CLI boundary to be recorded as an ADR.

## Decision

Adopt workflow-based parity boundaries instead of page-by-page parity expectations.

1. **Streamlit is canonical** for deep engineering workflows:
   - domain data ingestion and QC,
   - Word batch sync,
   - manual report authoring/export,
   - detailed engineering workspaces that mutate plant-maintenance data,
   - asset registry/admin workflows that do not yet have an audited React flow.

2. **React is canonical** for operator and control-center workflows:
   - fleet monitoring and watchlists,
   - chat/voice assistant experience,
   - work-order handling UX,
   - automation control,
   - memory / Agent Lab / operator-facing settings,
   - user authentication experience.

3. **FastAPI + `pple/application` are canonical** for business contracts shared
   across multiple surfaces. When a workflow is marked as supported on more than one
   surface, all condition, severity, evidence, audit, and safety behavior must come
   from shared use cases or existing rule-based core modules.

4. **CLI is canonical** for headless and local-operator workflows:
   - scripted diagnosis,
   - local automation inspection,
   - offline-safe operator commands,
   - audit-friendly configuration changes.

5. Cross-surface parity commitments are intentionally limited to these workflows:
   - fleet / reliability snapshot,
   - domain diagnosis read/analyze flows,
   - chat assistant and RAG-backed citations,
   - work-order lifecycle,
   - knowledge search/upload,
   - backend-backed settings categories.

6. The following are **not parity commitments** unless a later ADR changes scope:
   - bulk ingest and QC in React,
   - Word sync in React,
   - manual report generation in React,
   - memory / automation / Agent Lab in Streamlit,
   - React delete flows for knowledge documents,
   - placeholder settings categories with no backend implementation.

## Consequences

- `docs/feature-parity.md` must distinguish:
  - canonical workflows,
  - supported workflows that require parity backlog,
  - canonical-only workflows that are intentionally not planned elsewhere.
- New backlog items should be written per workflow, not per page.
- PRs that change ownership of a workflow must update both
  `docs/feature-parity.md` and this ADR.
- Placeholder UI sections do not count as supported parity until a real backend
  contract exists.

## Alternatives considered

### 1. Full page-by-page parity across Streamlit and React

Rejected. It would force React to chase Streamlit-only engineering workflows such as
batch sync and manual report authoring, creating unnecessary duplication.

### 2. Streamlit-only strategy

Rejected. The repository already has an active React surface with distinct operator
and control-center workflows, plus auth flows that are not present in Streamlit.

### 3. React-only strategy

Rejected. Streamlit remains the fastest path for deep engineering analysis, ingest,
QC, and report authoring over the existing Python-first ecosystem.

## Migration / rollout

1. Update `docs/feature-parity.md` with final workflow ownership rules and a backlog
   section keyed by workflow.
2. Record the implementation backlog in the project task list target.
3. Future work should close parity only for the supported workflows listed above.
4. Workflow-specific tests should move toward shared contract coverage through
   FastAPI and `pple/application`.

## Rollback

If product direction changes, revert this ADR and the paired updates in
`docs/feature-parity.md`, then replace them with a new ADR that defines the new
surface boundaries.
