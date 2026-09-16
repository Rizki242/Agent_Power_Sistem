# PPLE V2 — Baseline Report (Phase 0)

Dibuat sesuai instruksi Phase 0 di `docs/final.md`: mempelajari kondisi existing sebelum refactor apa pun dimulai. **Tidak ada refactor dilakukan pada tahap ini.**

Branch kerja: `feature/pple-v2` (dibuat dari `master` @ commit `3175e93`).

---

# 1. STATUS BASELINE (VERIFIED)

Dijalankan langsung, bukan asumsi:

```text
Unit test (unittest discover)   98 tests — OK (0 failures, 0 errors)
                                 2 DeprecationWarning non-fatal (numpy/pandas
                                 timedelta unit di data_loader.py:835,
                                 starlette/httpx testclient warning)

verify_app.py                   PASS — semua 5 langkah:
                                 1. Load data: 7885 rows
                                 2. Latest data: 1941 rows
                                 3. Chatbot: query "List Alarm" & "Status <eq>" OK
                                 4. PPT generation: 1,331,825 bytes
                                 5. Materi loading: 20/20 file OK

Frontend build (vite build)     PASS — 80 modules, bundle 459.5 KB (115.6 KB gzip)
                                 0 error

Frontend lint (oxlint)          21 warning, 0 error (kosmetik: unused vars,
                                 missing hook deps — lihat riwayat commit
                                 5982450 dan sebelumnya untuk detail)
```

**Kesimpulan:** kondisi awal HIJAU. Aman untuk mulai Phase 1 (skeleton package `pple/`) kapan pun disetujui.

Catatan lingkungan: tes di atas dijalankan dengan Python 3.14 (system interpreter WSL) + dependency inti (`pandas<3`, `streamlit`, `fastapi`, dll.) diinstal `--user --break-system-packages` di luar `.venv` project — bukan Python 3.11 resmi yang dipakai `build.bat`. Dependency RAG opsional (`langchain`, `faiss-cpu`, `sentence-transformers`) sengaja TIDAK diinstal di sesi ini karena berat (~GB, termasuk torch) dan project sendiri mewajibkan semua RAG call path fallback ke keyword search saat tidak tersedia — jadi tidak menghalangi baseline test.

---

# 2. ARSITEKTUR EXISTING

```text
                         ┌─────────────────────────┐
                         │      src/  (Python)      │
                         │  domain modules + agents  │
                         └────────────┬─────────────┘
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
        ┌───────────────────────┐             ┌───────────────────────┐
        │   Streamlit Dashboard  │             │   FastAPI Backend      │
        │   app.py + src/pages/  │             │   api_server.py        │
        │   :8501                │             │   :8000 (Swagger /docs)│
        └───────────────────────┘             └────────────┬──────────┘
                                                             │ REST/JSON
                                                             ▼
                                               ┌───────────────────────┐
                                               │  React/Vite Frontend   │
                                               │  frontend/  :5173      │
                                               └───────────────────────┘
```

Detail lengkap sudah didokumentasikan di `docs/STRUKTUR_PROJECT.md` (dibuat sebelum baseline ini) — laporan ini fokus pada hal yang relevan untuk migrasi ke arsitektur `final.md`, tidak mengulang semuanya.

```text
Total baris kode src/ (termasuk src/agents/):   11,198 baris (.py)
Jumlah endpoint REST (api_server.py):           42
Jumlah unit test file:                          16 (98 test case)
```

---

# 3. DEPENDENCIES (requirements.txt)

```text
WAJIB (core, dipakai langsung tanpa fallback):
  pandas<3        xlrd            python-pptx     streamlit
  plotly          openpyxl        python-docx     lxml
  pillow          pyarrow         google-genai    pypdf
  fastapi         uvicorn         httpx

OPSIONAL (setiap call path WAJIB fallback bila absen):
  langchain>=0.2.0            \
  langchain-community>=0.2.0   |  rag_engine.py — semantic search
  langchain-core>=0.2.0        |  Materi/VIBRASI + Materi/TRIBOLOGY
  faiss-cpu>=1.7.4              |  fallback: keyword search (knowledge_retriever.py)
  sentence-transformers>=2.2.0 /
```

Tidak ditemukan dependency yang sudah usang secara mencolok atau berkonflik versi saat instalasi (kecuali catatan pandas di atas — `requirements.txt` benar memakai `pandas<3`, resolusi tanpa pin sempat menarik pandas 3.0.5 yang lebih baru dari yang didukung).

---

# 4. API ROUTES (42 endpoint, api_server.py)

```text
Core / Equipment
  GET  /api/health
  GET  /api/summary
  GET  /api/equipment
  GET  /api/equipment/{equipment_name}
  POST /api/rotorbar/calculate

Multi-Agent
  GET  /api/agents/specialists
  POST /api/agents/collaborate
  POST /api/agent/chat

Reliability / Fusion
  GET  /api/reliability/fleet
  GET  /api/reliability/fusion/{equipment_name}
  POST /api/reliability/diagnose

Work Order
  GET  /api/workorders
  POST /api/workorders/approve

Domain modalitas (masing-masing: summary, list, detail/{id}, +tests untuk vibration)
  /api/vibration/*     /api/dga/*     /api/tribology/*     /api/thermal/*

Knowledge & Reporting
  GET  /api/materi
  POST /api/materi/search
  POST /api/reports/ppt

Upload
  POST /api/upload/dga
  POST /api/upload/vibration

Continuous Learning
  POST /api/agent/self-improve
  GET  /api/agent/improvement-status
  POST /api/agent/predictions
  POST /api/agent/learn-from-history
  GET  /api/learning/harness-status
  POST /api/learning/rigger-cycle
  POST /api/learning/evaluate-harness

Skills
  GET  /api/skills/learned-patterns
  POST /api/skills/teach
  GET  /api/skills/benchmarks
```

Semua route berpola `/api/*` (legacy, per terminologi `final.md` Phase 24). Tidak ada `/api/v2/*` saat ini.

---

# 5. DATA SOURCES

```text
data/MCSA/mcsa_updated.csv      DATA AKTIF — sumber tunggal kebenaran untuk
                                 status equipment MCSA/ESA, dipakai Streamlit
                                 DAN FastAPI (bukan database).

data/MCSA/Report MCSA.xls       Fallback Excel.

data/MCSA/config/               equipment_master.json, esa_mcsa_guidance.json,
                                 thresholds_default.json,
                                 thresholds_{motor,site}_override.json
                                 — SUDAH dalam bentuk JSON config, BUKAN
                                 hard-coded Python, tapi juga BUKAN
                                 database-driven (final.md Phase 2-4).

data/DGA/ , data/vibrasi/       Data modalitas lain, format serupa
                                 (file-based, bukan DB).

src/equipment_mapping.json      16 kategori equipment (PAF, SAF, BFP, CWP,
                                 IDF, IDFF, C3WP, CCWP, CEP, VCP, ...) —
                                 mapping nama alias ke equipment class.
```

**Kesimpulan kunci:** seluruh data operasional saat ini FILE-BASED (CSV/Excel/JSON), tidak ada database (SQLite/PostgreSQL). Ini adalah gap terbesar terhadap `final.md` Phase 2 (Database Configuration) — migrasi ke skema `plants/units/systems/equipment/...` akan memerlukan ETL dari CSV+JSON existing, bukan sekadar tambahan skema kosong.

---

# 6. SPECIALIST AGENTS — KESESUAIAN DENGAN final.md

Temuan penting: struktur existing **sudah lebih dekat** ke target `final.md` daripada dugaan awal.

```text
src/agents/specialist_agents.py

  class BaseSpecialistAgent:
      def evaluate(self, equipment, data) -> Dict[str, Any]:
          raise NotImplementedError

  class VibrationAgent(BaseSpecialistAgent)
  class MCSAAgent(BaseSpecialistAgent)
  class DGAAgent(BaseSpecialistAgent)
  class PDAgent(BaseSpecialistAgent)
  class TribologyAgent(BaseSpecialistAgent)
  class ThermalAgent(BaseSpecialistAgent)
```

Ini SUDAH merupakan pola common-interface (mirip semangat `EngineeringModule` abstract class di `final.md` Phase 5) — bukan `if module == "vibration": ... elif ...` seperti yang ingin dihindari `final.md` Bagian 2. Tidak ditemukan pola if/elif dispatch semacam itu di `src/agents/*.py`.

Perbandingan skema output vs target `DiagnosticResult` (`final.md` Phase 9):

```text
Field final.md DiagnosticResult    Ada di evaluate() existing?
──────────────────────────────────────────────────────────────
equipment_id                       ADA (sbg "equipment")
module / module_id                 BEDA NAMA (sbg "domain")
timestamp                          TIDAK ADA
health_score                       ADA
severity                           ADA
confidence                         ADA
findings (list)                    TIDAK ADA (mirip evidence, tp beda bentuk)
faults / fault hypotheses          SEBAGIAN (sbg "failure_mode", bukan list)
evidence (list)                    ADA
recommendations (list)             ADA (singular "recommendation")
standards (list referensi)         TIDAK ADA sbg field terpisah
metadata                           ADA (sbg "metrics", scope beda)
```

`subagent_coordinator.py` sudah mendefinisikan 8 sub-agent dengan `agent_id` eksplisit (`subagent-vib-01`, `subagent-mcsa-01`, dst. — termasuk `subagent-fusion-01` dan `subagent-safety-01`), sudah punya `identify_relevant_agents()` dan `run_collaborative_diagnosis()`. Ini fondasi yang relevan untuk `ModuleRegistry` (`final.md` Phase 7) tapi saat ini registrasi masih manual/hard-coded di constructor, bukan hasil scan manifest.

---

# 7. HARD-CODED REFERENCES (Unit / Equipment / Domain)

Sesuai instruksi Phase 0, diperiksa langsung ke source:

```text
Referensi literal 'UNIT 1' / 'UNIT 2' / 'UNIT 3' / 'COMMON':
  30 kemunculan di 5 file:
    src/data_loader.py
    src/dga_data.py
    src/thermal_data.py
    src/tribology_data.py
    src/vibration_data.py

Pola dispatch if/elif per-domain (if module == "vibration": ...):
  TIDAK DITEMUKAN di src/agents/ — specialist agent sudah polymorphic
  (lihat §6). Hard-coding yang ada bersifat data-path/label, bukan
  dispatch logic.

Equipment/module list di frontend (React):
  frontend/src/App.jsx — 11 route (/mcsa, /vibration, /dga, dst.)
  di-hard-code sebagai <Route> tetap, BUKAN hasil GET /api/v2/modules
  seperti target final.md Phase 25.
```

**Kesimpulan:** hard-coding utama ada di dua tempat — (1) label Unit/Voltage di modul data-loading Python (bentuknya konstanta path/label, relatif mudah dipetakan ke tabel `units`), dan (2) daftar menu/route di React (`App.jsx`) yang statis. Tidak ada dispatch logic besar yang perlu dibongkar di layer agent — ini kabar baik, mengurangi risiko Phase 10 (migrasi specialist agent).

---

# 8. TECHNICAL DEBT / GAP TERHADAP final.md

```text
Gap                                          Dampak       Fase final.md terkait
────────────────────────────────────────────────────────────────────────────────
Tidak ada database (file-based CSV/JSON)     BESAR        Phase 2, 3, 4
Asset hierarchy implisit (folder/label,      SEDANG       Phase 3
  bukan tabel Plant/Unit/System eksplisit)
Equipment spec tidak schema-driven           SEDANG       Phase 4
  (equipment_mapping.json statis)
DiagnosticResult belum standar/Pydantic      KECIL-SEDANG Phase 9
  (dict bebas per agent, field tidak seragam)
Module registry belum ada (agent             SEDANG       Phase 6, 7, 8
  diregistrasi manual di constructor)
Tidak ada CLI (semua akses via UI/API)       BESAR        Phase 12-19
Frontend route/menu statis di App.jsx        KECIL        Phase 25
API masih satu versi (/api/*, belum          KECIL        Phase 24
  /api/v2/* terpisah)
Tidak ada event bus internal                 KECIL        Phase 28
Tidak ada audit log terstruktur              SEDANG       Phase 29
  (baru ada di level upload-batch manifest.json,
  bukan generik per-perubahan data)
```

Update pasca-baseline (2026-09-16): baris "Frontend route/menu statis di App.jsx" (Phase 25)
sudah tidak berlaku - frontend React ditulis ulang (lihat docs/feature-parity.md "Riwayat") dan
frontend baru membaca daftar modul dari GET /api/v2/module-load-report secara generik, tanpa
hardcoded module list. Lihat catatan status di docs/final.md Phase 25. Baris gap lain di tabel
di atas belum diverifikasi ulang terhadap kode saat ini - jangan anggap statusnya masih akurat
tanpa mengecek langsung.

```text

SUDAH SESUAI ARAH final.md (tidak perlu dirombak):
  - BaseSpecialistAgent polymorphic per domain (§6)
  - Rule-based logic tetap source of truth, LLM fallback opsional
    (sudah persis prinsip final.md "LLM is assistance layer only")
  - Safety Guardrail sudah memblokir Trip/Shutdown + wajib HITL
    (final.md Phase 20 sudah terpenuhi secara prinsip)
  - Config JSON terpisah dari kode (data/MCSA/config/)
```

---

# 9. REKOMENDASI URUTAN KERJA

Mengikuti `final.md` Bagian "RECOMMENDED FIRST MVP" — jangan kerjakan 30 fase sekaligus. Baseline ini menunjukkan titik mulai paling murah risiko:

```text
1. PPLE CORE (package pple/, tanpa pindah logic dulu)
       │
       ├── pple/core        (config, events, exceptions — skeleton)
       │
       └── pple/engineering
               │
               ├── base.py       EngineeringModule ABC — mirip
               │                 BaseSpecialistAgent existing,
               │                 diperluas ke schema DiagnosticResult §6
               │
               └── registry.py   Wrapper TIPIS di atas
                                 subagent_coordinator.py existing
                                 (BUKAN ganti coordinator sekaligus)
```

MVP pertama yang realistis: satu module (`vibration`) berjalan lewat `EngineeringModule` interface baru sambil `src/agents/specialist_agents.py` existing tetap jadi implementasi di baliknya (adapter, bukan rewrite) — persis strategi "compatibility layer" yang diminta `final.md` Phase 1.

**Tidak direkomendasikan mengerjakan Phase 2-4 (database) lebih dulu** — risiko migrasi data CSV/JSON ke skema relasional jauh lebih besar daripada membangun interface module, dan tidak ada di jalur kritis MVP pertama.

---

*Baseline ini adalah snapshot 2026-08-29 di branch `feature/pple-v2`. Tidak ada file kode yang diubah untuk menghasilkan laporan ini — hanya dependency Python tambahan (di luar `.venv` project) untuk menjalankan test suite secara nyata.*
