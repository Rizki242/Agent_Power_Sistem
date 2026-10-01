# Feature Parity Streamlit dan React

Status: diperbarui 2026-10-01 terhadap kode aktual dan keputusan ownership workflow final (lihat "Riwayat" di bawah)
Tujuan: mencegah dua UI mengembangkan business rule yang berbeda.

## Riwayat penting

Versi matrix sebelumnya (baseline fase 0) mengasumsikan React memiliki workspace per-domain
CBM (`MCSA Workspace`, `Vibration Workspace`, `DGA Workspace`, dst.), `Reliability Command Center`,
`Asset Health`, `Work Order Center`, `AI Chat Panel`, dan `Digital Twin Workspace`. Komponen-komponen
itu sempat ada, tapi dihapus di commit `22be836` ("complete standalone Streamlit architecture and
remove legacy React frontend"). Frontend React yang di-track ulang di `d7d1484` ("track React
frontend, finish launcher wiring") adalah aplikasi berbeda: bukan dashboard rekayasa per-domain,
melainkan konsol operasi untuk platform PPLE V2 itu sendiri (`Overview`, `Data`, `Dokumen`, `Memori`,
`Otomasi`, `Agent Lab`, `Settings` — lihat `frontend/src/App.jsx`). Matrix di bawah mencerminkan
kondisi kode saat ini, bukan rencana lama.

Jika keputusan produk ke depan adalah membangun ulang dashboard per-domain di React (memakai
`pple/api/domain_router.py` yang sudah menyediakan data yang sama dengan `src.components.domain_workspace`
di Streamlit), perbarui matrix ini bersamaan dengan PR yang mengimplementasikannya — jangan biarkan
dokumen mendahului atau tertinggal dari kode lagi.

## Arti status

- **Canonical**: UI utama untuk workflow tersebut.
- **Supported**: UI pendamping; behavior bisnis harus memakai contract/use case yang sama.
- **Not planned**: tidak perlu diparitas-kan kecuali ada keputusan produk baru.
- **Tidak ada**: workflow ini tidak diimplementasikan di UI tersebut saat ini (beda dengan "not
  planned" — di sini tidak ada keputusan eksplisit untuk mengecualikannya, hanya belum dibangun).

## Keputusan final ownership workflow (2026-10-01)

Keputusan ini dibakukan di `docs/adr/ADR-0001-feature-parity-boundaries.md`. Intinya, parity
di repo ini ditentukan **per workflow**, bukan per halaman.

### Canonical per surface

- **Streamlit canonical** untuk workflow engineering mendalam: ingest/QC data, Word sync, manual
  report authoring/export, dan workspace engineering yang mengubah data operasional.
- **React canonical** untuk workflow operator/control center: fleet monitoring, chat/voice,
  work-order handling, automation, memory/Agent Lab, dan pengalaman login/auth.
- **FastAPI + `pple/application` canonical** untuk contract workflow yang dipakai lebih dari satu
  surface. Bila sebuah workflow berstatus `Supported`, logic kondisi/severity/evidence/audit/safety
  harus datang dari contract bersama ini.
- **CLI canonical** untuk workflow headless/offline-safe dan operasi lokal yang butuh audit trail.

### Workflow yang memang wajib dikejar paritasnya

Hanya workflow berikut yang menjadi komitmen parity lintas-surface:

1. fleet / reliability snapshot,
2. domain diagnosis read/analyze flows,
3. chat assistant + citation/RAG behavior,
4. work-order lifecycle,
5. knowledge search/upload,
6. backend-backed settings categories.

### Workflow yang **bukan** parity target saat ini

Kecuali ada ADR baru, item berikut **bukan** gap parity:

- bulk ingest/QC domain di React,
- Word sync di React,
- manual report generation di React,
- Memory / Automation / Agent Lab di Streamlit,
- knowledge delete di React,
- kategori Settings placeholder yang belum punya backend.

## Backlog parity per workflow

Backlog rinci ada di `tasks/todo.md`. Tabel ini adalah indeks keputusan dan prioritasnya.

| Workflow | Ownership final | Target parity | Gap yang masih perlu ditutup | Backlog |
| --- | --- | --- | --- | --- |
| Fleet / reliability snapshot | Streamlit + React `Supported`, contract canonical di `FleetReliabilityUseCase` / `GET /api/reliability/fleet` | Status, severity, watchlist, stale-data, dan `UNKNOWN` konsisten | Kontrak payload `coverage` + `parity_contract` sudah menjadi sumber label. Sisa kerja: regression lintas-surface di `WF-08` | `WF-01` selesai, `WF-08` |
| Domain diagnosis (MCSA/DGA/Vibration/Tribology/Thermal/PD) | Streamlit canonical untuk ingest/QC/report; React supported untuk read/analyze/dispatch | Paritas hanya untuk baca/analisa/dispatch | Perlu batas tegas agar React tidak dikejar ke Word sync/QC/manual report | `WF-02`, `WF-07`, `WF-08` |
| Chat / voice / citations | React canonical untuk UX voice+citation; Streamlit supported untuk assistant rule-based | Safety, source of truth, evidence, dan fallback sama | Perlu pemisahan tegas antara logic chat bersama vs UX voice React-only | `WF-03`, `WF-08` |
| Work orders | Streamlit + React `Supported`, API/workflow canonical di backend | Lifecycle WO dan safety checklist sama | Perlu regression coverage untuk create/approve/progress/complete/reject | `WF-04`, `WF-08` |
| Knowledge base | Search/upload supported; delete tetap Streamlit-canonical | Search/read/upload sama, delete tidak dipaksakan parity | Perlu labeling eksplisit agar React tidak menyiratkan delete support | `WF-06`, `WF-07` |
| Settings | Hanya kategori yang punya backend yang masuk parity | General, AI & LLM, engineering/system settings yang nyata | Perlu rapikan placeholder vs real settings agar tidak membingungkan user | `WF-05`, `WF-07`, `WF-08` |
| Data management + ingest/QC | Streamlit canonical | Tidak dikejar parity | Perlu label/documentation yang jelas agar tidak dianggap gap React | `WF-07` |
| Reports (manual PPT/Word/CSV) | Streamlit canonical; automated reports React canonical | Tidak ada parity target untuk manual authoring | Perlu pemisahan eksplisit manual vs automated report scope | `WF-07` |
| Automation / Agent Lab / Memory | React canonical | Tidak dikejar parity ke Streamlit | Perlu tetap diikat ke contract backend dan audit trail | `WF-07` |
| Login / auth UX | React canonical | Tidak dikejar parity ke Streamlit | Perlu tetap dibedakan dari middleware `PPLE_API_KEY` untuk klien non-browser | `WF-07` |

## Matrix — rekayasa CBM (domain engineering)

Seluruh baris berikut murni ditangani Streamlit hari ini. React tidak memiliki dashboard per-domain
sejak `22be836`; `pple/api/domain_router.py` dan `pple/application/` menyiapkan data/contract yang sama
seandainya React ingin membangunnya kembali, tapi belum ada konsumen React untuk itu.

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Fleet command center / reliability fusion | Agent Dashboard (`src/pages/agent_dashboard_page.py`, pakai `DiagnoseEquipmentUseCase`/`FleetReliabilityUseCase`) | **Supported** — `FleetWorkspace.jsx` (`/fleet`) menampilkan KPI rata-rata kesehatan armada pembangkit 3×25 MW, rincian Unit 1/2/3/Common, Critical Watchlist, estimasi RUL, dan Matriks Armada terintegrasi ke `/api/reliability/fleet` | `src.fleet_reliability`, `pple/application/fleet.py`, fusion engine | Supported pada keduanya; parity hanya untuk snapshot/health semantics, bukan seluruh drill-down engineering |
| MCSA / Vibration / DGA / Tribology / Thermal / Partial Discharge analysis | Halaman per-domain + `src.components.domain_workspace` (ingest, tren, diagnosa, laporan) | **Supported** — `MCSAWorkspace.jsx` (`/mcsa`) menampilkan data MCSA 93 motor lengkap (KPI Normal/Alarm/High, filter Unit/Voltage/Kondisi, telemetri kelistrikan, kualitas daya IEEE 519, sideband rotor bar EPRI dB, spesifikasi nameplate, ringkasan kinerja, tren riwayat, kalkulator rotor bar, dispatch WO CBM) terhubung ke `/api/equipment` & `/api/summary`. Ditambah **Dashboard CBM** (`/cbm`, `CBMDashboard.jsx`) dengan tab Segitiga Duval (DGA), tab MCSA & Motor, Parameter Vibrasi, dan Tren Kesehatan. | `src` rule-based + specialist agents, `pple/api/routers/equipment.py`, `pple/api/routers/core.py`, `pple/api/domain_router.py` | Supported pada keduanya; parity dibatasi ke read/analyze/dispatch. Ingest, QC, Word sync, dan authoring laporan tetap Streamlit-canonical |
| Chat assistant (tanya status/threshold per domain) | Chatbot (`src.chatbot.MCSAChatbot`, rule-based + LLM opsional) | **Supported** — `ChatWorkspace.jsx` + `FloatingVoiceWidget.jsx`, endpoint `/api/agent/chat`, orchestrated by `PPLEMasterAgent` (multi-domain asset resolution, safety guardrail, LLM narrative enrichment) | `src.chatbot`, `src.llm_assistant`, `src.agents.master_agent` | Supported pada keduanya; React canonical untuk agent multi-domain; Streamlit canonical untuk MCSA spesifik |
| Jawaban chat bersitasi (RAG) | Tidak ada tampilan sitasi terpisah; `rag_engine`/`knowledge_retriever` hanya dipakai untuk enrichment jawaban | **Supported** — `ChatWorkspace.jsx` menampilkan accordion "Rujukan Dokumen & Standar CBM" per pesan (`msg.citations`) dari `/api/agent/chat`; endpoint inspeksi terpisah `/api/rag/status`, `/api/rag/search`, `/api/rag/chunks`, `/api/rag/rebuild` | `src.rag_engine`, `pple/api/routers/rag.py` | React canonical untuk tampilan sitasi; fallback ke pencarian kata kunci di kedua UI bila dependensi opsional (FAISS/LangChain) tidak terpasang |

| Data management (upload/QC MCSA & 5 domain lain) | Manajemen Data, `domain_workspace` tab "Data & Upload" | Not planned | `src.data_loader`, `src.domain_ingest` | Streamlit canonical; React not planned dan bukan backlog parity |
| Word batch sync dan QC | Sync + Quality Check | Not planned | `src.report_batches` | Streamlit canonical; React not planned dan bukan backlog parity |
| Report PPT/Word/CSV (generate manual dari filter) | Laporan PPT/Word, `domain_workspace` tab "Laporan" | Tidak ada endpoint report manual di `frontend/src/api.js` | `src.ppt_generator`/`docx_generator`, `src.domain_report` | Streamlit canonical; React tidak ada. Yang dikejar parity hanya automated reports yang memang React-canonical |
| Automated Reports (readiness 6 modul CBM + PPTX terjadwal) | Tidak ada | **React canonical** — tab "Reports" di `AutomationWorkspace.jsx`: matriks kesiapan 6 modul CBM per bulan, unduh PPTX mingguan/bulanan per modul, konsolidasi bulanan, dan slide deck meeting | `src.domain_report`, `pple/api/routers/automated_reports.py` (`/api/reports/automated/*`) | React canonical; tidak ada rencana duplikasi ke Streamlit |
| Work order (draft CBM, approval, EAM) | `src/pages/work_orders_page.py` + draft otomatis dari Asset 360/Agent Dashboard (`src.work_orders`) — implementasi nyata | **Supported** — `WorkOrdersWorkspace.jsx` (`/work-orders`) + tombol aksi cepat "Terbitkan WO CBM" di `ChatWorkspace.jsx`, verifikasi checklist keselamatan LOTO, form TE IMS `FORM.JRG.F.05.006`, terhubung penuh ke `/api/workorders/*` | `src.work_orders`, `pple/api/routers/work_orders.py` | Supported pada keduanya |

## Matrix — platform PPLE V2 (operasi agent, bukan domain CBM)

React sekarang fokus di sini; Streamlit tidak punya UI setara untuk baris-baris ini (tidak ada
halaman yang memanggil `self_improvement`/`automations`/`env_harness` langsung), jadi belum ada
risiko drift business-rule — tapi harus tetap dijaga begitu ada penambahan.

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Knowledge search/read | Materi Training | `Dokumen` workspace (`getMaterials`/`searchMaterials`) | `src.knowledge_retriever`/`rag_engine`, `/api/materi*` | Supported pada keduanya |
| Knowledge upload | Materi Training edit mode | `Dokumen` workspace (`uploadMaterial`) | `src.knowledge_processor`, `/api/materi/upload` | Supported pada keduanya |
| Knowledge delete | Materi Training edit mode | Tidak ada (`frontend/src/api.js` tidak punya fungsi delete) | `src.knowledge_processor` | Streamlit canonical; belum menjadi parity target sampai ada flow audit/konfirmasi yang setara |
| Automation workflows (jadwal + approval) | Tidak ada | `Otomasi` workspace (CRUD, enable/disable, run, approve, retry) | `src.automations`, `/api/automations/*` | React canonical |
| Self-improvement / EnvHarness / benchmark | Tidak ada | `Agent Lab` (`runImprovementCycle`, `runHarnessEvaluation`, `learnFromHistory`) | `src.self_improvement`, `src.env_harness`, `/api/agent/*`, `/api/learning/*`, `/api/skills/*` | React canonical |
| Memory browsing (experiences/instructions/knowledge/parametric) | Tidak ada | `Memori` workspace | `src.agent_memory`, `/api/skills/learned-patterns`, `/api/learning/harness-status` | React canonical |
| Settings AI provider + system control | Settings (Streamlit page) | **6-tab Control Center** (`SettingsWorkspace.jsx`, route `/settings`) — AI & Model, Voice Assistant, Safety & Engineering, Data & Knowledge, System & Integration, User & Preferences. Baca/tulis file konfigurasi yang sama via `getSettingsOverview`/`saveAISettings`. | `src/ai_settings.py`, `pple/api/routers/settings.py` | Supported pada keduanya hanya untuk kategori yang sudah punya backend nyata; placeholder Streamlit bukan parity commitment |
| Login / autentikasi pengguna | Tidak ada (Streamlit terbuka di jaringan lokal) | **React canonical** — `LoginPage.jsx` + `context/AuthContext.jsx` gateway; token via `apiFetch()` | `src.auth` (PBKDF2-HMAC-SHA256, `data/users.json` runtime), `pple/api/routers/auth.py` (`/api/auth/{login,me,logout,change-password,avatar}`) | React canonical; Streamlit tidak ada. Foto profil (`avatar`, data URL kecil di `data/users.json`) tampil di sidebar utama, sidebar riwayat chat, dan gelembung chat "Anda". `PPLE_API_KEY` (middleware `pple/api/security.py`) tetap lapisan terpisah untuk klien non-browser |
| Digital twin | Tidak ada | Tidak ada (dihapus bersama frontend lama) | — | Not planned sampai ada keputusan produk baru |
| CLI engineering/status | N/A | N/A | `pple` application/domain | CLI canonical untuk automation lokal |

## Aturan perubahan parity

1. PR yang menambah fitur UI WAJIB memperbarui matrix ini bila ownership berubah.
2. UI `supported` tidak boleh membuat threshold atau status sendiri; gunakan API/use case canonical.
3. Perbedaan presentasi diperbolehkan, perbedaan hasil diagnosis tidak.
4. Workflow `not planned` tidak menjadi blocker parity release.
5. Baris "Tidak ada" harus diberi label jelas jika suatu saat dibangun sebagai placeholder — jangan
   memberi kesan workflow sudah operasional sebelum benar-benar terhubung ke data nyata.
6. Data illustrative/synthetic harus menampilkan disclaimer pada kedua UI.
7. Menghapus atau mengganti total sebuah UI surface (seperti `22be836`/`d7d1484`) WAJIB memperbarui
   matrix ini di PR yang sama — itulah yang gagal terjadi sebelumnya dan membuat dokumen ini basi.

## Contract minimum untuk fitur supported

- input asset, unit, tanggal, dan unit pengukuran sama;
- status enum dan severity mapping sama;
- evidence, confidence, provenance, dan timestamp tersedia;
- empty, unknown, stale, dan provider failure tidak diubah menjadi status normal;
- safety decision dan work-order approval tetap memerlukan jalur otorisasi yang sama.
