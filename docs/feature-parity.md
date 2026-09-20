# Feature Parity Streamlit dan React

Status: diperbarui 2026-09-18 terhadap kode aktual (lihat "Riwayat" di bawah)
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

## Matrix — rekayasa CBM (domain engineering)

Seluruh baris berikut murni ditangani Streamlit hari ini. React tidak memiliki dashboard per-domain
sejak `22be836`; `pple/api/domain_router.py` dan `pple/application/` menyiapkan data/contract yang sama
seandainya React ingin membangunnya kembali, tapi belum ada konsumen React untuk itu.

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Fleet command center / reliability fusion | Agent Dashboard (`src/pages/agent_dashboard_page.py`, pakai `DiagnoseEquipmentUseCase`/`FleetReliabilityUseCase`) | Tidak ada dashboard fleet; `Overview` hanya menampilkan status agent (`/api/v2/agents`) dan module-load-report, bukan health/watchlist | `src.fleet_reliability`, `pple/application/fleet.py`, fusion engine | Streamlit canonical; React tidak ada |
| MCSA / Vibration / DGA / Tribology / Thermal / Partial Discharge analysis | Halaman per-domain + `src.components.domain_workspace` (ingest, tren, diagnosa, laporan) | **Dashboard CBM** (`/cbm`, `CBMDashboard.jsx`) — Segitiga Duval interaktif (DGA), Parameter Vibrasi, Tren Kesehatan multi-domain. Data dari `/api/dga/*` + `/api/v2/domain/*`; rule-based thresholds per IEC 60599/ISO 10816. Upload/ingest/laporan masih Streamlit canonical. | `src` rule-based + specialist agents, `pple/api/domain_router.py`, `pple/api/specialist_router.py` | Streamlit canonical untuk ingest/laporan/diagnosa penuh; React supported untuk visualisasi grafik CBM |
| Chat assistant (tanya status/threshold per domain) | Chatbot (`src.chatbot.MCSAChatbot`, rule-based + LLM opsional) | **Supported** — `ChatWorkspace.jsx` + `FloatingVoiceWidget.jsx`, endpoint `/api/agent/chat`, orchestrated by `PPLEMasterAgent` (multi-domain asset resolution, safety guardrail, LLM narrative enrichment) | `src.chatbot`, `src.llm_assistant`, `src.agents.master_agent` | Supported pada keduanya; React canonical untuk agent multi-domain; Streamlit canonical untuk MCSA spesifik |

| Data management (upload/QC MCSA & 5 domain lain) | Manajemen Data, `domain_workspace` tab "Data & Upload" | Not planned | `src.data_loader`, `src.domain_ingest` | Streamlit canonical; React not planned |
| Word batch sync dan QC | Sync + Quality Check | Not planned | `src.report_batches` | Streamlit canonical; React not planned |
| Report PPT/Word/CSV | Laporan PPT/Word, `domain_workspace` tab "Laporan" | Tidak ada endpoint report di `frontend/src/api.js` | `src.ppt_generator`/`docx_generator`, `src.domain_report` | Streamlit canonical; React tidak ada |
| Work order (draft CBM, approval, EAM) | `src/pages/work_orders_page.py` + draft otomatis dari Asset 360/Agent Dashboard (`src.work_orders`) — implementasi nyata | **Supported** — `WorkOrdersWorkspace.jsx` (`/work-orders`) + tombol aksi cepat "Terbitkan WO CBM" di `ChatWorkspace.jsx`, verifikasi checklist keselamatan LOTO, form TE IMS `FORM.JRG.F.05.006`, terhubung penuh ke `/api/workorders/*` | `src.work_orders`, `pple/api/routers/work_orders.py` | Supported pada keduanya |
| Chat assistant (tanya status/threshold per domain) | Chatbot (`src.chatbot.MCSAChatbot`, rule-based + LLM opsional) | Tidak ada panel chat | `src.chatbot`, `src.llm_assistant` | Streamlit canonical; React tidak ada |

## Matrix — platform PPLE V2 (operasi agent, bukan domain CBM)

React sekarang fokus di sini; Streamlit tidak punya UI setara untuk baris-baris ini (tidak ada
halaman yang memanggil `self_improvement`/`automations`/`env_harness` langsung), jadi belum ada
risiko drift business-rule — tapi harus tetap dijaga begitu ada penambahan.

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Knowledge search/read | Materi Training | `Dokumen` workspace (`getMaterials`/`searchMaterials`) | `src.knowledge_retriever`/`rag_engine`, `/api/materi*` | Supported pada keduanya |
| Knowledge upload | Materi Training edit mode | `Dokumen` workspace (`uploadMaterial`) | `src.knowledge_processor`, `/api/materi/upload` | Supported pada keduanya |
| Knowledge delete | Materi Training edit mode | Tidak ada (`frontend/src/api.js` tidak punya fungsi delete) | `src.knowledge_processor` | Streamlit canonical |
| Automation workflows (jadwal + approval) | Tidak ada | `Otomasi` workspace (CRUD, enable/disable, run, approve, retry) | `src.automations`, `/api/automations/*` | React canonical |
| Self-improvement / EnvHarness / benchmark | Tidak ada | `Agent Lab` (`runImprovementCycle`, `runHarnessEvaluation`, `learnFromHistory`) | `src.self_improvement`, `src.env_harness`, `/api/agent/*`, `/api/learning/*`, `/api/skills/*` | React canonical |
| Memory browsing (experiences/instructions/knowledge/parametric) | Tidak ada | `Memori` workspace | `src.agent_memory`, `/api/skills/learned-patterns`, `/api/learning/harness-status` | React canonical |
| Settings AI provider + system control | Settings (Streamlit page) | **6-tab Control Center** (`SettingsWorkspace.jsx`, route `/settings`) — AI & Model, Voice Assistant, Safety & Engineering, Data & Knowledge, System & Integration, User & Preferences. Baca/tulis file konfigurasi yang sama via `getSettingsOverview`/`saveAISettings`. | `src/ai_settings.py`, `pple/api/routers/settings.py` | Supported pada keduanya; keduanya baca/tulis file konfigurasi yang sama |
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
