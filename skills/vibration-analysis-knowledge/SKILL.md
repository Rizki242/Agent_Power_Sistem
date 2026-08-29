---
name: vibration-analysis-knowledge
description: Use structured vibration-analysis training knowledge for rotating-equipment condition monitoring, FFT/spectrum interpretation, waveform review, fault-frequency calculation, trend evaluation, data-quality checks, and conservative diagnostic recommendations. Trigger when Codex is asked to analyze vibration data, explain vibration signatures, reason about unbalance, misalignment, looseness, bearing faults, gear faults, belt issues, resonance, sensor setup, predictive-maintenance workflow, or build/update vibration-analysis diagnostic software.
---

# Vibration Analysis Knowledge

## Core Rule

Use this skill as engineering decision support for vibration analysis. Calculate and verify from numeric evidence before diagnosing. Never use an LLM impression or spectrum image as the primary diagnostic source.

When project work also involves `TARGET.md`, treat `TARGET.md` as the product and architecture source of truth and use this skill as domain knowledge that supports those requirements.

## References

- Read `references/Knowledge1.md` when the task needs vibration-analysis theory, diagnostic workflow, fault signatures, sensor/setup guidance, case-history reasoning, data-quality checks, or recommended output formats.
- Read `references/Knowledge2.md` only if it contains content relevant to the request. It is currently included as a placeholder reference from the source knowledge set.

For large or targeted questions, search inside `references/Knowledge1.md` for terms such as `Protocol Operasional`, `Anti-Hallucination`, `Confidence Score`, `Input Skill`, `Output Skill`, `unbalance`, `misalignment`, `looseness`, `bearing`, `BPFO`, `BPFI`, `FTF`, `BSF`, `gear`, `GMF`, `sideband`, `phase`, `waveform`, `FMAX`, `resolution`, `mounting`, `trend`, or `verification`.

## Required Reasoning Flow

Follow this sequence for diagnostic tasks:

1. Validate input: RPM, units, sampling rate, FMAX, FFT lines, measurement point, direction, parameter, sensor/mounting, operating condition, and available history.
2. Calculate theoretical frequencies: running speed/order, harmonics, bearing frequencies, gear mesh, blade/vane pass, belt, and electrical frequencies when the required geometry is available.
3. Identify observed peaks, harmonics, sidebands, waveform features, phase evidence, and trend behavior.
4. Check data quality and acquisition limitations before assigning confidence.
5. Build 1-3 differential fault hypotheses rather than forcing a single diagnosis.
6. Separate severity from diagnostic confidence.
7. Recommend confirmation tests and engineering actions.
8. Require after-repair verification measurements.

## Diagnostic Guardrails

Do not invent missing machine data such as bearing geometry, tooth count, rotor bars, blade/vane count, belt dimensions, or RPM. If required data is missing, state what cannot be calculated and list the needed fields.

Do not diagnose from overall vibration alone, from one peak alone, or from a screenshot alone. Do not call a machine normal when FMAX, resolution, or measurement coverage is insufficient to see the relevant fault frequencies.

Treat confidence conservatively:

- `0.90-1.00`: multiple independent evidence streams agree.
- `0.75-0.89`: primary signature plus supporting evidence.
- `0.55-0.74`: plausible pattern but confirmation data is limited.
- `0.30-0.54`: weak indication only.
- `<0.30`: speculative; do not present as a final diagnosis.

## Output Pattern

For analysis results, prefer a structured answer with:

- data quality and limitations,
- calculated frequencies,
- observed peaks/harmonics/sidebands,
- differential diagnosis with evidence for and against,
- severity basis,
- required confirmation,
- recommended action,
- after-repair verification plan.

Always include the decision-support framing: results must be verified by qualified vibration analysts or maintenance engineers before maintenance decisions are made.