# Feature Parity Streamlit dan React

Status: diperbarui 2026-10-03 terhadap kode aktual dan keputusan ownership workflow final (lihat "Riwayat" di bawah)
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
| Domain diagnosis (MCSA/DGA/Vibration/Tribology/Thermal/PD) | Streamlit canonical untuk ingest/QC/report; React supported untuk read/analyze/dispatch | Paritas hanya untuk baca/analisa/dispatch | Batas dan inventaris gap selesai di WF-02; label dan regresi contract masih terbuka | `WF-02` selesai, `WF-07`, `WF-08` |
| Chat / voice / citations | React canonical untuk UX voice+citation; Streamlit supported untuk assistant rule-based | Safety, source of truth, evidence, dan fallback sama | Guard prompt/lampiran Streamlit sudah diuji; contract API teks/VOICE, fallback citation, dan respons masih follow-up | `WF-03` selesai, `WF-08` |
| Work orders | Streamlit + React `Supported`, API/workflow canonical di backend | Lifecycle WO dan safety checklist sama | Perlu regression coverage untuk create/approve/progress/complete/reject | `WF-04`, `WF-08` |
| Knowledge base | Search/upload supported; delete tetap Streamlit-canonical | Search/read/upload sama, delete tidak dipaksakan parity | Perlu labeling eksplisit agar React tidak menyiratkan delete support | `WF-06`, `WF-07` |
| Settings | Hanya kategori yang punya backend yang masuk parity | General, AI & LLM, engineering/system settings yang nyata | Perlu rapikan placeholder vs real settings agar tidak membingungkan user | `WF-05`, `WF-07`, `WF-08` |
| Data management + ingest/QC | Streamlit canonical | Tidak dikejar parity | Perlu label/documentation yang jelas agar tidak dianggap gap React | `WF-07` |
| Reports (manual PPT/Word/CSV) | Streamlit canonical; automated reports React canonical | Tidak ada parity target untuk manual authoring | Perlu pemisahan eksplisit manual vs automated report scope | `WF-07` |
| Automation / Agent Lab / Memory | React canonical | Tidak dikejar parity ke Streamlit | Perlu tetap diikat ke contract backend dan audit trail | `WF-07` |
| Login / auth UX | React canonical | Tidak dikejar parity ke Streamlit | Perlu tetap dibedakan dari middleware `PPLE_API_KEY` untuk klien non-browser | `WF-07` |

## WF-02: Batas diagnosis read/analyze/dispatch (2026-10-03)

WF-02 menetapkan batas workflow, bukan menyatakan seluruh tampilan diagnosis sudah setara.
React membaca data, menampilkan hasil analisa backend, dan mengirim permintaan draft WO.
Bulk ingest, preview/quarantine/commit, QC, Word sync, dan authoring laporan manual tetap
Streamlit-canonical. Ketersediaan endpoint upload/report tidak mengubah ownership UI.

Contract yang perlu dijaga untuk keenam domain:

- Identitas equipment, domain, periode/timestamp, nilai, unit, dan sumber pengukuran harus jelas.
- Condition, severity, dan health score berasal dari core; skor `None` dan `UNKNOWN` tidak
  boleh diberi fallback Normal atau angka sehat oleh UI.
- Evidence, confidence, provenance, recommendation/next action, dan kebutuhan data tambahan
  berasal dari hasil diagnosis yang sama. Confidence bukan probabilitas terkalibrasi.
- Domain tanpa data yang cukup dicatat sebagai data gap; tidak masuk pembobotan fusion.
- Dispatch membuat permintaan WO melalui backend; approval dan safety tetap workflow bersama.

Boundary kode: `src.agents.specialist_agents` untuk evaluasi domain,
`pple/application/diagnostics.py` untuk fusion, `/api/equipment/*` untuk MCSA,
`/api/dga/*` untuk DGA, dan `/api/v2/domain/{domain}/measurements|summary` untuk store kanonik.
Summary saat ini hanya membawa condition/health/failure mode/readings; evidence, confidence,
provenance, dan next-data belum lengkap. Itu gap contract untuk WF-08, bukan parity yang sudah lulus.

Gap yang sudah diperiksa dan dialokasikan:

| Area | Kondisi aktual | Tindak lanjut |
| --- | --- | --- |
| MCSA (`MCSAWorkspace.jsx`) | `StatusBadge`/`RotorBarBadge` memakai fallback Normal saat status kosong | WF-07: label UNKNOWN eksplisit; WF-08: regression unknown/empty |
| Vibrasi (`CBMDashboard.jsx`) | Empty-state menyarankan upload via halaman Data, tetapi `DataWorkspace.jsx` adalah registry/config modul | WF-07: arahkan ingest/QC ke Streamlit |
| DGA (`CBMDashboard.jsx`) | Visual Duval/Rogers juga memiliki kalkulasi lokal dan simulator | WF-08: bandingkan hasil backend; bedakan simulasi dari diagnosis operasional |
| Tribology/Thermal/PD | Belum ada workspace diagnosis tersendiri pada route React aktual; data tampil lewat tren/chat | WF-07: label dukungan baca terbatas, jangan menyiratkan analyze lengkap |
| Tren lintas-domain | Nilai health yang tidak tersedia dipetakan ke 0 lalu disaring; skor sah 0 ikut hilang | WF-08: uji skor 0 vs UNKNOWN dan provenance seri |
| Adapter V2 | Data quality dibentuk ulang dan severity 0 dipetakan ke NORMAL; kebutuhan data agen belum diteruskan | WF-08: kontrak abstention/UNKNOWN dan metadata parsial |
| Tribology legacy (`src/tribology_data.py`) | `evaluate_tribology_sample` masih memiliki fallback angka dan ambang berbeda dari specialist agent | WF-08: audit kontrak legacy secara terpisah; perbaikan agen pada tugas ini tidak mengklaim parity semua jalur |

## WF-03: Contract chat, voice, dan citation (2026-10-03)

WF-03 selesai untuk batas workflow dan inventaris gap. Ini bukan klaim bahwa kedua
jalur chat sudah memakai satu implementasi atau seluruh perilakunya sudah setara.
ADR-0001 tetap menetapkan React sebagai canonical UX voice/citation dan Streamlit
sebagai supported assistant rule-based. Voice tidak menjadi backlog parity Streamlit.

### Perilaku bersama yang wajib dijaga

- Jawaban kondisi/status/threshold/evidence berasal dari core Python dan pengukuran nyata.
  LLM hanya memperkaya narasi; provider gagal/tidak tersedia mengembalikan rule answer.
  Data gap/UNKNOWN tidak boleh berubah menjadi Normal atau angka pengukuran buatan.
- Input teks dan transkrip voice tunduk pada `SafetyGuardrailAgent` yang sama. Permintaan
  trip/shutdown/breaker/isolation diblokir sebelum enrichment; chat tidak mengeksekusi
  tindakan plant. Peringatan keselamatan harus tetap ada pada jawaban dan ringkasan suara.
- Equipment dan konteks percakapan harus tetap scoped pada aset yang benar; follow-up
  bukan izin memakai sample aset lain. Dokumen terlampir adalah sumber konteks, bukan
  otorisasi untuk melewati guard atau mengganti hasil engineering.
- Citation adalah hasil retrieval terstruktur, bukan sumber/nomor halaman yang dibuat LLM.
  Contract minimal mencakup `source`, `title`, `heading`, dan `preview` bila tersedia.
  Locator halaman/chunk/skor hanya boleh ditampilkan bila benar-benar tersedia dari sumber.
  Tanpa sumber yang relevan, gunakan daftar kosong, jangan membuat rujukan.
- Jawaban tanpa LLM tetap harus bisa menggunakan keyword retrieval saat semantic RAG
  tidak tersedia. Citation yang tampil harus tetap konsisten setelah sesi dimuat kembali.

### Jalur aktual dan target tes

| Jalur | Implementasi aktual | Target verifikasi |
| --- | --- | --- |
| Streamlit | `src/pages/chatbot_page.py` -> `src.chatbot.MCSAChatbot` -> `MCSALLMAssistant.enhance_answer`; citation tampil di expander, riwayat session_state, dan export Markdown | Rule answer/fallback + citation persistence saat LLM on/off; test guard pada prompt teks/file |
| React chat/voice | `ChatWorkspace.jsx` dan `FloatingVoiceWidget.jsx` -> `sendChatMessage` -> `/api/agent/chat` di `pple/api/routers/agents.py` | Guard dan response contract untuk teks/VOICE; citation payload dan sesi |
| Orkestrasi domain | API memakai `get_master_agent().resolve_asset`/`execute_collaborative_diagnosis`; `PPLEMasterAgent.process_query` juga memiliki jalur tersendiri | `tests.test_master_agent`, `tests.test_chat_context`; jangan mengasumsikan API mendelegasikan seluruh chat ke `process_query` |
| Knowledge/citation | API mengambil `assistant.last_citations` atau `build_knowledge_context`; keyword fallback berada di knowledge retriever | `tests.test_rag_citations_chat`, `tests.test_rag_api`, serta regression fallback tanpa semantic deps di WF-08 |
| Ringkasan suara | API menyediakan `summary_for_speech`; browser Web Speech API menyediakan STT/TTS | `tests.test_speech_summary`; UX microphone/hands-free/browser fallback tetap React-only |

Contract target respons chat menyatakan `reply`, `matched_equipment`, `ai_enhanced`,
`safety_blocked`, `citations`, `summary_for_speech`, dan identitas sesi bila digunakan.
Perbedaan layout/format teks boleh ada; keputusan safety dan hasil engineering harus sama.

Gap aktual untuk WF-08:

1. Guard Streamlit diterapkan pada `render_chatbot_page`: prompt dan konteks lampiran
   aktif diperiksa oleh `SafetyGuardrailAgent` sebelum rule processing/LLM. Penolakan
   tersimpan di history tetapi tidak masuk konteks giliran berikutnya. Regresi:
   `tests.test_streamlit_chat_safety` (AI on/off, multi-file, lampiran persisten,
   dan follow-up aman). Kebijakan substring guard tetap berlaku; API teks/VOICE
   masih memerlukan coverage contract lintas-surface WF-08.
2. `enhance_answer` langsung kembali ke rule answer saat provider unavailable sebelum
   retrieval; Streamlit menyimpan citation hanya bila `ai_active`. API memiliki retrieval
   langsung bila assistant tidak berjalan. Citation offline belum setara di kedua surface.
3. API normal reply belum menyertakan `safety_blocked=False`, sementara blocked reply
   tidak menyertakan `citations=[]`; normalisasi field dan regression dibutuhkan.
4. Tes citation API membuktikan schema/persistence, belum mengikat setiap klaim dalam
   jawaban ke sumber atau membuktikan seluruh fallback tanpa optional dependency.
5. Dua generator ringkasan suara (API/master) perlu regression untuk menjaga UNKNOWN,
   angka/unit, dan penolakan safety; widget voice ringkas tidak wajib menduplikasi accordion
   citation milik ChatWorkspace.

WF-08 berikutnya memprioritaskan contract safety API teks/VOICE, lalu fallback citation,
respons sesi, dan konsistensi ringkasan suara. Perubahan runtime dibuat sebagai tugas kecil
terpisah dengan failing test; scope dokumentasi WF-03 tidak mengubah safety policy.

## Matrix — rekayasa CBM (domain engineering)

Streamlit memiliki workspace engineering lengkap. React saat ini memiliki MCSA Workspace
dan Dashboard CBM yang memakai API MCSA/DGA serta measurements lintas-domain; dukungan ini
tidak berarti semua domain sudah memiliki analyze view lengkap (lihat gap WF-02 di atas).

| Capability | Streamlit | React | Sumber logic/contract | Keputusan |
| --- | --- | --- | --- | --- |
| Fleet command center / reliability fusion | Agent Dashboard (`src/pages/agent_dashboard_page.py`, pakai `DiagnoseEquipmentUseCase`/`FleetReliabilityUseCase`) | **Supported** — `FleetWorkspace.jsx` (`/fleet`) menampilkan KPI rata-rata kesehatan armada pembangkit 3×25 MW, rincian Unit 1/2/3/Common, Critical Watchlist, estimasi RUL, dan Matriks Armada terintegrasi ke `/api/reliability/fleet` | `src.fleet_reliability`, `pple/application/fleet.py`, fusion engine | Supported pada keduanya; parity hanya untuk snapshot/health semantics, bukan seluruh drill-down engineering |
| MCSA / Vibration / DGA / Tribology / Thermal / Partial Discharge analysis | Halaman per-domain + `src.components.domain_workspace` (ingest, tren, diagnosa, laporan) | **Supported** — `MCSAWorkspace.jsx` (`/mcsa`) menampilkan data MCSA 93 motor lengkap (KPI Normal/Alarm/High, filter Unit/Voltage/Kondisi, telemetri kelistrikan, kualitas daya IEEE 519, sideband rotor bar EPRI dB, spesifikasi nameplate, ringkasan kinerja, tren riwayat, kalkulator rotor bar, dispatch WO CBM) terhubung ke `/api/equipment` & `/api/summary`. Ditambah **Dashboard CBM** (`/cbm`, `CBMDashboard.jsx`) dengan tab Segitiga Duval (DGA), tab MCSA & Motor, Parameter Vibrasi, dan Tren Kesehatan. | `src` rule-based + specialist agents, `pple/api/routers/equipment.py`, `pple/api/routers/core.py`, `pple/api/domain_router.py` | Supported pada keduanya; parity dibatasi ke read/analyze/dispatch. Ingest, QC, Word sync, dan authoring laporan tetap Streamlit-canonical |
| Chat assistant (tanya status/threshold per domain) | Chatbot (`src.chatbot.MCSAChatbot`, rule-based + LLM opsional); page memeriksa prompt/lampiran dengan shared guard | **Supported** — `ChatWorkspace.jsx` + `FloatingVoiceWidget.jsx`, endpoint `/api/agent/chat`; API memakai master untuk resolve/diagnosis dan memiliki orkestrasi chat sendiri | `src.chatbot`, `src.llm_assistant`, `src.agents.master_agent`, `pple/api/routers/agents.py` | React canonical UX chat/voice; Streamlit supported. Guard Streamlit diuji melalui `tests.test_streamlit_chat_safety`; contract API teks/VOICE masih follow-up WF-08 |
| Jawaban chat bersitasi (RAG) | Expander referensi (`title`, `heading`, `source`, `preview`), riwayat session_state, dan export Markdown; persistence citation hanya saat AI aktif | **Supported** — `ChatWorkspace.jsx` menampilkan accordion "Rujukan Dokumen & Standar CBM" per pesan (`msg.citations`) dari `/api/agent/chat`; citation disimpan pada sesi backend | `src.knowledge_retriever`, `src.rag_engine`, `src.llm_assistant`, `pple/api/routers/agents.py` | React canonical UX citation; Streamlit supported. Contract retrieval/persistence dan fallback offline diuji di WF-08 |

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
