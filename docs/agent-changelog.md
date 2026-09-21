# Agent changelog

Every change made by an AI agent (or a human following `AGENTS.md`) gets one entry here, appended at the **top** of the "Entries" section, in the same task in which the change is made. Commit messages alone are not enough: this file records the plan, what was verified, and what was deliberately left out, so the next agent does not have to re-derive it.

Rules:

- One entry per task/PR, not per file. Sub-bullets for each file group.
- Write the entry **after** verification, so the "Verified" line reports real results (test counts, `verify_app.py` outcome), not intentions.
- Record what was **not** done or not run (skipped tests, external blockers, worktree changes you did not touch) under "Left out / risks".
- Reference decisions with ADR ids (`ADR-0001`) and vocabulary from `CONTEXT.md`.
- Never paste secrets, API keys, or personal data.

## Template

```markdown
### YYYY-MM-DD - <short title>

- **Requested:** <one line: what the user asked for>
- **Plan (agreed before coding):** <2-5 bullets or "trivial, no plan needed (<reason>)">
- **Changed:**
  - `path/to/file.py` - <what and why>
  - `tests/test_x.py` - <new/updated tests>
- **Verified:** <exact commands run + outcome, e.g. "python -m unittest tests.test_chatbot (31 tests OK); python verify_app.py OK; npm --prefix frontend run lint clean">
- **Left out / risks:** <what was skipped and why, follow-ups, residual risk, or "none">
- **Docs/ADR:** <files updated, ADR created, or "none needed">
```

## Entries

### 2026-09-21 - Agent Lab (EnvHarness) hardening and Voice Assistant multi-turn context

- **Requested:** Voice Assistant context awareness & controls ("voice mengerti apa yang kita bicarakan menjawab dengan konteks yang benar") and Option 2 ("Penguatan Skenario Gangguan Baru di Agent Lab (EnvHarness)").
- **Plan (agreed before coding):**
  - Fix wrapper state synchronization in `src/agents/env_harness.py`: eliminate isolated deepcopies across Stage, Contract, and Chain wrappers so transitions (`diagnosis_result`, `work_order`, `safety_cleared`, `done`, `step_count`) properly mutate the active environment instance.
  - Fix `StageWrapper` stage_reset to preserve high-severity telemetry readings (using `max(existing, v)`) preventing accidental downgrade of critical Zone D vibrations.
  - Add 3 realistic plant disturbance scenarios to `PLANT_BENCHMARKS` in `src/agents/continuous_learning.py`: BM-06 (BFP Impeller Cavitation & Flow Instability), BM-07 (Generator Stator Winding Partial Discharge), BM-08 (High-Voltage Bushing Overheating & Arc Discharge).
  - Register `PDAgent` in `src/agents/self_improvement.py` and update precision keywords.
  - Enable multi-turn conversation memory in `frontend/src/FloatingVoiceWidget.jsx` and auto-initialize voice session in `pple/api/routers/agents.py`.
- **Changed:**
  - `src/agents/env_harness.py` - direct state decoration on DiagnosticEnvironment, multi-modal check adaptation, priority handling for Zone D vibration, and full 6-domain policy evaluation.
  - `src/agents/continuous_learning.py` - added BM-06, BM-07, BM-08; proportional scoring for `evaluate_env_harness()`.
  - `src/agents/self_improvement.py` - imported `PDAgent`, added `BENCHMARK_PRECISION_KEYWORDS` for BM-06..08, and dispatched multi-modal compound cases.
  - `frontend/src/FloatingVoiceWidget.jsx`, `frontend/src/utils/speech.js`, `frontend/src/styles.css` - Pause/Resume/Stop controls, 8-bar soundwave visualizer, speed toggle, persistent voice session ID, and reset button.
  - `pple/api/routers/agents.py` - voice session auto-init and context injection.
  - `tests/test_continuous_learning.py`, `tests/test_self_improvement.py` - updated test assertions to `len(PLANT_BENCHMARKS)` (8 benchmarks).
- **Verified:**
  - `python -m unittest tests.test_env_harness tests.test_continuous_learning tests.test_self_improvement` (20 tests OK, 0.423s).
  - `python verify_app.py` (Verification Complete, 78 materi files OK, PPT generated, MCSA loaded).
  - `python -m py_compile` on all modified python files (Clean).
  - `npm --prefix frontend run lint` (0 errors) and `npm --prefix frontend run build` (Built successfully in 2.52s).
  - Direct runtime test: `evaluate_env_harness()` score 100.0/100 (8/8 passed); `run_benchmarks()` diagnostic score 100.0% (Grade A - Expert System); `run_env_rigger_learning('BFP 1A')` completed successfully with accepted candidate.
- **Left out / risks:** None.
- **Docs/ADR:** `docs/agent-changelog.md` updated; `walkthrough.md` updated.

### 2026-09-21 - Repo weight: untrack unused Materi/ binaries and rag_index build artifact

- **Requested:** Follow-up to the tidy-up below - user flagged the repo as "too heavy" and confirmed "untrack binaries in Materi/ + rag_index" (B1) as the recommended fix; also confirmed wanting a `.git` history rewrite (`git filter-repo`) in principle.
- **Plan (agreed before coding):**
  - Measure tracked size by folder/extension first (`git ls-files` + `os.path.getsize`) to confirm the hypothesis before acting: 1.86 GB tracked total, `.git` 1.6 GB, `Materi/VIBRASI` alone 1.33 GB of which `.exe/.mp4/.zip/.ptz/.flv` (installers, training videos, firmware) account for ~930 MB and are never read by `src/rag_engine.py` or `src/knowledge_retriever.py` (both only read `.json`/`.pdf`).
  - `git rm --cached` (not `rm`) those extensions under `Materi/` plus `data/rag_index/` (FAISS index, regenerable via `build_rag_index.py`, not source of truth per `src/rag_engine.py`'s own `RAG_INDEX_DIR` doc comment) - files stay on disk, only leave the index.
  - Add matching `.gitignore` patterns so they cannot be re-added by accident.
  - Verify RAG/knowledge tests still pass (they must, since the untracked files were never in that code path).
  - Before running `git filter-repo` to actually shrink `.git` (1.6 GB, unaffected by untracking alone): check for a live remote and active worktrees, since a history rewrite changes every commit hash - surface that risk and get explicit re-confirmation rather than run on the original blanket "yes".
- **Changed:**
  - `.gitignore` - added `Materi/**/*.exe|*.msi|*.mp4|*.flv|*.zip|*.ptz` and `data/rag_index/`, each with a comment explaining why (unused by the app / regenerable build artifact).
  - 75 files under `Materi/VIBRASI/` and `Materi/DGA/salipi/` untracked via `git rm --cached` (Omnitrend/VibXpert/JRE installers, `.mp4`/`.flv` training videos, `.zip` oil-analysis archives, one `.ptz` firmware image). List and byte counts captured in the session; not reproduced here to keep this entry short - see `git log -p` on this change for the exact paths.
  - `data/rag_index/index.faiss`, `data/rag_index/index.pkl` - untracked (build artifact).
- **Verified:** `git status --short` showed all 77 removals as `D` (staged deletion from index, not working-tree delete - confirmed files still exist on disk, untouched). `python -m unittest tests.test_chatbot tests.test_knowledge_retriever` - 24 tests OK (knowledge_retriever test exercises the real FAISS/RAG path via `rag_engine`, confirming the untracked index files were not needed for the test to pass since it's regenerated/loaded from disk, which the untrack does not delete).
- **Left out / risks:** **Nothing committed** - `git rm --cached` and the `.gitignore` edit are staged only, per repo convention of not committing without being asked. `.git` itself is still 1.6 GB; untracking only affects future commits, not existing history. User confirmed wanting a `git filter-repo` rewrite to actually shrink `.git`, but the session found: (1) `origin` is a live GitHub remote, (2) 9 active local worktrees exist on 9 branches, one (`worktree-upgrade-readme`) `locked` (i.e. has in-progress work), so a hash-rewriting operation right now would orphan all of them and require a coordinated force-push. Surfaced this before running it; user chose to **postpone** the rewrite until those worktrees are merged/closed. `git-filter-repo` was also confirmed not installed - would need `pip install git-filter-repo` when that step is picked up. `data/DGA/Laporan Trafo UAT UNIT 3 - Copy (2).docx` and `data/vibrasi/25. TE VIBRASI PAF UNIT 3 (1).pdf` (near-duplicate filenames) remain untouched - hashed in the prior entry and found not byte-identical to their non-"Copy" counterparts.
- **Docs/ADR:** none needed (no schema/behavior change; pure git-tracking change, reversible via `git add` from disk).

### 2026-09-21 - Repo tidy-up: stray files, duplicate docs, untracked lock file

- **Requested:** Clean up stray/misplaced files and folders across the repo (part A of a larger repo-weight cleanup; user confirmed "A" first, flagged repo as "too heavy" overall).
- **Plan (agreed before coding):**
  - Grep every candidate filename across `.py/.md/.bat/.yml/.json` first to confirm nothing imports or references it, so moves/untracking cannot break behavior.
  - Move non-code documents out of `data/` into `docs/` (data/ is measurement data, not design docs).
  - Move a debug-only test helper (`tests/_verify_settings_runtime.py`, underscore-prefixed so `discover -p "test_*.py"` never picks it up) and a stray root script (`scripts/probe_api.py`) into `scripts/debug/`, matching the convention already documented in `AGENTS.md`.
  - Untrack `skills-lock.json` (tooling lock file, not consumed by the app) and drop the duplicate `docs/STRUKTUR_PROJECT.pdf` / `docs/image.png` (an up-to-date `.md` equivalent and `docs/readme-assets/` already exist).
  - Do not touch `archive-5X6k2v/` deletion or any binary-untracking in `Materi/`/`data/` in this pass - those are separate, larger decisions (B1/B2) still pending user confirmation.
- **Changed:**
  - `data/soul.md` -> `docs/soul.md`, `"data/desain agent.html"` -> `docs/desain-agent.html` (design docs, not measurement data).
  - `docs/plan_step_by_step.md`, `docs/desaindakhir.md` -> `docs/archive/` (superseded planning docs, kept for history).
  - `docs/STRUKTUR_PROJECT.pdf`, `docs/image.png`, `skills-lock.json` - untracked (`git rm --cached`); `.gitignore` gained a `skills-lock.json` line so it stays untracked.
  - `tests/_verify_settings_runtime.py` -> `scripts/debug/verify_settings_runtime.py`; `scripts/probe_api.py` -> `scripts/debug/probe_api.py`.
- **Verified:** `git mv`/`git rm --cached` preserved history (all shown as `R`/`D` in `git status --short`, not delete+add). Grep for every old filename/path across `*.py/*.md/*.bat/*.yml/*.json` returned zero matches before and after the move. `python -m unittest tests.test_chatbot` - 19 tests OK. Did not re-run full `discover` or `verify_app.py` since no `src/`/`pple/`/`api_server.py`/`app.py` logic changed - only file locations outside the import graph.
- **Left out / risks:** `archive-5X6k2v/` (9.2 MB GitKraken CLI zip, already gitignored via `archive-*/`) still sits on disk - deleting it is an irreversible local delete the sandbox blocks without explicit user confirmation; not deleted this pass. `Materi/` still tracks ~1.3 GB of `.exe/.mp4/.zip/.ptz` installers/videos never read by the app (only `.json`/`.pdf` are) - untracking that (B1) and `data/MCSA/images/` -> Git LFS (B2) are the actual fix for "repo too heavy" and are still awaiting user confirmation. Two near-duplicate files (`data/DGA/Laporan Trafo UAT UNIT 3 - Copy (2).docx`, `data/vibrasi/25. TE VIBRASI PAF UNIT 3 (1).pdf`) were checked by hash and are NOT byte-identical to their non-"Copy" counterparts, so they were left in place rather than deleted blind. Pre-existing unrelated worktree modifications (api_server.py, frontend/src/*, pple/api/routers/*, src/automations.py, src/agents/env_harness.py, etc.) were left untouched throughout.
- **Docs/ADR:** none needed (no architectural/behavioral decision, pure file relocation).

### 2026-09-21 - Domain context file, agent workflow protocol, changelog

- **Requested:** Create `CONTEXT.md`; upgrade `AGENTS.md` so agents check and plan before writing code, verify there are no errors after building, always work from a strategy, and record every change.
- **Plan (agreed before coding):**
  - Follow `docs/agents/domain.md`'s single-context layout (`CONTEXT.md` at repo root + `docs/adr/`).
  - Add one mandatory workflow section to `AGENTS.md` and mirror it in `CLAUDE.md` (the two files are identical apart from their headers and must stay that way).
  - Put the change log in `docs/` with a fixed template so entries are comparable.
- **Changed:**
  - `CONTEXT.md` - new: system purpose, invariants, glossary (plant hierarchy, measurement, diagnosis, agents, maintenance/audit), source-of-truth map, terms to avoid, open vocabulary gaps.
  - `AGENTS.md`, `CLAUDE.md` - new section "Mandatory workflow: Check -> Plan -> Build -> Verify -> Record"; "Before Making Changes" and "Validation Rules" now point at it; "Domain docs" now says `CONTEXT.md` exists.
  - `docs/agent-changelog.md` - new: this file (rules, template, first entry).
- **Verified:** Documentation-only change; no code touched. `git status --short` confirmed pre-existing unrelated worktree changes (api_server.py, frontend/src/*, pple/api/routers/*, src/*, tests/*) were left untouched.
- **Left out / risks:** No ADR created (no architectural decision changed). `docs/adr/` directory still does not exist; first ADR should create it.
- **Docs/ADR:** `CONTEXT.md`, `AGENTS.md`, `CLAUDE.md`, this file.
