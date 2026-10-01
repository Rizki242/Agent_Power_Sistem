# Implementation Plan: Feature parity decision and workflow backlog

## Overview

This task finalizes which workflows are canonical to Streamlit, React, FastAPI, and
CLI, then records the backlog needed only for workflows that genuinely require
cross-surface parity. The goal is to stop treating "feature parity" as a blanket
requirement and replace it with explicit workflow ownership plus a sequenced backlog.

## Architecture Decisions

- Workflow ownership follows `docs/adr/ADR-0001-feature-parity-boundaries.md`.
- `docs/feature-parity.md` remains the canonical matrix of current state plus parity
  commitments.
- The repository normally tracks backlog in GitHub Issues, but the `gh` CLI is not
  available in this environment, so the actionable backlog is recorded locally in
  `tasks/todo.md` for now.

## Task List

Tasks are tracked in `tasks/todo.md`.

### Phase 1: Finalize ownership rules
- [ ] Record workflow ownership boundaries in an ADR
- [ ] Update the feature parity document with final decisions

### Checkpoint: Ownership baseline
- [ ] Canonical vs supported vs not-planned workflows are explicit
- [ ] No backlog item asks for blanket page-by-page parity

### Phase 2: Publish actionable backlog
- [ ] Write workflow-specific backlog entries with acceptance criteria
- [ ] Distinguish shared-contract work from surface-specific work

### Checkpoint: Backlog quality
- [ ] Every workflow task has verification steps
- [ ] Every supported workflow references the shared contract boundary

### Phase 3: Record and hand off
- [ ] Update `docs/agent-changelog.md`
- [ ] Re-read the diff for scope drift

### Checkpoint: Complete
- [ ] Documentation matches current product direction
- [ ] Backlog is ready for future implementation sessions

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ambiguous ownership remains in the matrix | High | Encode ownership rules in an ADR and reference them from the parity document |
| Backlog grows into a full product roadmap instead of parity work | Medium | Keep tasks scoped to workflow contracts and parity gaps only |
| Tracker state diverges because GitHub Issues were not created here | Medium | Note the environment limitation in the plan and changelog; keep backlog in `tasks/todo.md` until issue creation is available |

## Open Questions

- Should knowledge delete eventually move to React with explicit audit/confirmation, or stay Streamlit-only permanently?
- Which placeholder Settings categories should be implemented next versus downgraded to not planned?
