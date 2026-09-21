# Step-by-Step Implementation Plan: Multi-Agent & Specialist Sub-Agent System

Rencana eksekusi terstruktur untuk mengintegrasikan arsitektur **Multi-Agent & Specialist Sub-Agents** ke dalam ekosistem PPLE Agent (PLTU Jeranjang 3 × 25 MW).

---

## Arsitektur Sub-Agent Multi-Disiplin

```
                          USER / ENGINEER (VOICE / CHAT / UI)
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │            O&M ORCHESTRATOR AGENT             │
                  │   Query Classifier & Sub-Agent Coordinator    │
                  └───────────────────────┬───────────────────────┘
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
   ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
   │ VIBRATION AGENT │           │   MCSA AGENT    │           │    DGA AGENT    │
   │  ISO 10816/FFT  │           │ Sideband / THD  │           │ Duval & Rogers  │
   └────────┬────────┘           └────────┬────────┘           └────────┬────────┘
            │                             │                             │
            ├─────────────────────────────┼─────────────────────────────┤
            ▼                             ▼                             ▼
   ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
   │    PD AGENT     │           │ TRIBOLOGY AGENT │           │  THERMAL AGENT  │
   │  PRPD & Pulses  │           │  ASTM & ISO4406 │           │ Hotspot/Delta-T │
   └────────┬────────┘           └────────┬────────┘           └────────┬────────┘
            │                             │                             │
            └─────────────────────────────┼─────────────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │             FUSION SUB-AGENT                  │
                  │   Cross-Domain Evidence ➔ Health 0-100 ➔ RUL  │
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │             SAFETY GUARD SUB-AGENT            │
                  │   Operational Verification (Human-in-the-Loop)│
                  └───────────────────────┬───────────────────────┘
                                          │
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │           SYNTHESIZED RESPONSE & WO           │
                  │  Evidence Trace │ Consensus Diagnosis │ WO    │
                  └───────────────────────────────────────────────┘
```

---

## Langkah Kerja Terperinci:

### Langkah 1: Modul SubAgentCoordinator (`src/agents/subagent_coordinator.py`)
- [x] Mendefinisikan metadata dan kapabilitas 8 sub-agent:
  1. `subagent-vib-01`: Vibration Specialist (ISO 10816-3, FFT).
  2. `subagent-mcsa-01`: Electrical MCSA Specialist (IEEE 519, EPRI Sideband).
  3. `subagent-dga-01`: DGA Transformer Specialist (IEEE C57.104, Duval Triangle 1).
  4. `subagent-pd-01`: Partial Discharge Specialist (IEC 60270, PRPD).
  5. `subagent-tribo-01`: Tribology & Oil Specialist (ASTM D445, ISO 4406).
  6. `subagent-therm-01`: Thermal & IR Specialist (ISO 18434-1, Delta-T).
  7. `subagent-fusion-01`: Reliability Fusion & RUL Agent (Consolidated Health Index 0–100).
  8. `subagent-safety-01`: Safety Guardrail & Human-in-the-Loop Agent.
- [x] Mengimplementasikan logika delegasi dinamis (`identify_relevant_agents`) dan eksekusi kolaboratif (`run_collaborative_diagnosis`).

---

### Langkah 2: Integrasi Backend Endpoints (`api_server.py`)
- [x] Menambahkan endpoint `GET /api/agents/specialists` untuk mengekspos profil sub-agent ke frontend.
- [x] Menambahkan endpoint `POST /api/agents/collaborate` untuk diagnosa multi-agent interaktif.
- [x] Memperkaya endpoint `POST /api/agent/chat` agar menyertakan tag sub-agent aktif (`active_subagents`) dan jejak penalaran sub-agent (`subagent_traces`).

---

### Langkah 3: Pengayaan Persona LLM Assistant (`src/llm_assistant.py`)
- [x] Menginjeksi prompt persona sub-agent spesialis ke dalam orchestrator prompt.
- [x] Menambahkan sintaks sitasi sub-agent (`[Sub-Agent: Vibration]`, `[Sub-Agent: MCSA]`, dll.).

---

### Langkah 4: Antarmuka Frontend Multi-Agent (`AIChatPanel.jsx` & `ReliabilityCommandCenter.jsx`)
- [x] Menampilkan badge/pill animasi sub-agent aktif pada chat AI.
- [x] Menambahkan accordion interaktif **"🤖 Jejak Kolaborasi Sub-Agent"** untuk melihat bukti tiap agen domain.
- [x] Menambahkan **Sub-Agent Collaboration Hub** di Command Center.

---

### Langkah 5: Pengujian, Verifikasi & Upload GitHub
- [x] Membuat automated unit test suite `test_subagent_coordinator.py`.
- [x] Menjalankan seluruh 89 automated unit test (100% lulus).
- [x] Menjalankan production build Vite React (`npm run build` sukses).
- [x] Menjalankan verifikasi fungsional sistem (`python verify_app.py` sukses).
