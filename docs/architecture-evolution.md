# Evolusi Arsitektur PPLE Agent

Status: usulan arsitektur target dan backlog refactor bertahap  
Ruang lingkup: Streamlit, React/Vite, FastAPI, CLI, domain CBM, data, knowledge base, dan report

## 1. Ringkasan audit

Fondasi proyek sudah tepat: rule-based diagnosis adalah sumber kebenaran, LLM hanya pelengkap, dan semua antarmuka diarahkan ke core Python yang sama. Risiko terbesar saat ini bukan kekurangan fitur, tetapi pertumbuhan coupling di entry point dan kemungkinan dua UI berkembang dengan perilaku berbeda.

Temuan utama dari source saat audit:

| Area | Bukti saat ini | Risiko | Prioritas |
| --- | --- | --- | --- |
| Entry point API | `api_server.py` sekitar 1.374 baris dan menampung endpoint lintas domain | Konflik perubahan, sulit direview dan diuji terpisah | P0 |
| Dashboard Streamlit | `src/pages/dashboard_page.py` sekitar 1.027 baris | UI, orkestrasi, AI, dan analitik mudah tercampur | P0 |
| Bootstrap Streamlit | `app.py` sekitar 522 baris; memuat data/filter MCSA sebelum halaman aktif dijalankan | Halaman non-MCSA ikut menanggung state dan biaya MCSA | P0 |
| Dua UI | Streamlit dan React menyediakan kapabilitas yang tumpang tindih | Feature drift dan hasil diagnosis tidak konsisten | P0 |
| Kontrak frontend | React memakai JavaScript dan memanggil sekitar 51 `apiFetch`, tanpa test frontend yang terdeteksi | Bentuk response dapat berubah tanpa alarm awal | P1 |
| Design system | Token ada di `.streamlit/config.toml`, `src/components/theme.py`, dan `frontend/src/index.css`; masih ada raw color di komponen | Status/kontras dapat berbeda antarhalaman | P1 |
| Streamlit styling | Masih ada 9 penggunaan `unsafe_allow_html`; CSS mengandalkan selector internal Streamlit | Upgrade Streamlit dapat merusak tampilan | P1 |
| Loading halaman | Sejumlah `tabs`/`expander` berisi pekerjaan domain; konten tersembunyi berpotensi tetap dihitung | Rerun lambat dan UI terasa stale | P1 |
| Migrasi V2 | `pple/` dan `src/` hidup bersamaan melalui legacy adapter | Batas kepemilikan logic perlu dibuat eksplisit | P1 |

## 2. Keputusan arsitektur

Gunakan arsitektur modular monolith dengan dependency satu arah. Jangan memecah menjadi microservice sebelum ada kebutuhan deployment, ownership, atau scaling yang terukur.

```text
Streamlit UI       React UI       CLI
     |                 |           |
     |             FastAPI         |
     +-----------------+-----------+
                       |
              application/use cases
                       |
        domain: engineering + reliability
                       |
          ports: repository/provider interfaces
                       |
     infrastructure: CSV/Excel/JSON/FAISS/LLM/report
```

Aturan dependency:

| Layer | Boleh bergantung pada | Dilarang bergantung pada |
| --- | --- | --- |
| UI Streamlit/React | application contract, view model | dataframe mentah lintas domain, threshold lokal, implementasi storage |
| API/CLI | application use case, schema publik | komponen UI, kalkulasi diagnosis duplikat |
| Application | domain, port/interface | Streamlit, React, FastAPI request object |
| Domain | schema/value object domain | framework UI/API, file system, environment, provider LLM |
| Infrastructure | port/interface dan library eksternal | keputusan UI |

## 3. Kepemilikan package selama migrasi

Tidak perlu memindahkan semua file sekaligus. Gunakan pola strangler yang sudah dimulai oleh `LegacyAgentAdapterModule`.

```text
pple/
  core/             exception, audit, tipe lintas domain
  assets/           identitas dan hierarki aset
  engineering/      kontrak modul dan hasil diagnosis
  reliability/      fusion, health index, risk, RUL
  application/      use case lintas domain (ditambahkan bertahap)
  infrastructure/   adapter data/provider (ditambahkan saat diekstrak)
  api/              router, schema transport, dependency FastAPI

src/
  agents/           implementasi rule-based legacy yang masih kanonik
  *_data.py         adapter data legacy
  pages/            UI Streamlit saja
  components/       komponen UI Streamlit saja
```

Ketentuan transisi:

1. Logic yang sudah ada tidak dipindah hanya demi struktur folder.
2. Behavior baru lintas UI masuk melalui use case di `pple/application/`.
3. Rule legacy dipanggil melalui adapter; jangan disalin ke `pple/`.
4. Sebuah modul legacy baru boleh dihapus setelah semua caller pindah dan characterization test lulus.
5. Endpoint lama dipertahankan sampai ada deprecation window dan consumer migration yang tercatat.

## 4. Target per delivery layer

### 4.1 Streamlit

Target `app.py` hanya melakukan page config, bootstrap state global minimal, navigation, dan menjalankan halaman aktif.

Perbaikan bertahap:

- Pindahkan halaman ke pola file `app_pages/` yang dijalankan langsung oleh `st.Page`.
- Hanya halaman MCSA/report yang memuat filter dan dataframe MCSA.
- Pusatkan key session state di helper kecil; gunakan prefix per fitur seperti `mcsa_`, `dga_`, `chat_`.
- Cache sumber data mahal, lalu lakukan filter murah di luar cache.
- Gunakan `st.form` untuk input berkelompok dan `st.fragment` untuk bagian independen.
- Guard pekerjaan mahal di tab/expander atau ganti dengan segmented control dan conditional render.
- Pertahankan native Streamlit sebagai default; `unsafe_allow_html` hanya untuk kebutuhan yang tidak tersedia secara native dan harus punya regression check.

Target ukuran bukan aturan absolut, tetapi sinyal review:

- entry point: kurang dari 200 baris;
- page module: idealnya kurang dari 400 baris;
- fungsi render: idealnya kurang dari 80 baris;
- business rule: nol di file page.

### 4.2 FastAPI

Pecah `api_server.py` tanpa mengubah URL publik:

```text
pple/api/
  app.py
  dependencies.py
  errors.py
  schemas/
  routers/
    health.py
    equipment.py
    agents.py
    knowledge.py
    reports.py
    work_orders.py
    domains.py
```

Endpoint hanya bertugas: validasi request, memanggil use case, memetakan hasil ke response schema, dan menerjemahkan exception domain ke HTTP. File endpoint tidak boleh menghitung threshold atau membaca CSV secara langsung.

### 4.3 React

Pertahankan React sebagai thin client terhadap FastAPI dan susun per fitur:

```text
frontend/src/
  app/               router dan provider
  layouts/           application shell
  features/
    dashboard/
    assets/
    reliability/
    work-orders/
    knowledge/
    engineering/
  shared/
    api/
    ui/
    hooks/
    lib/
    styles/
```

Setiap feature memiliki `api`, `components`, `hooks`, dan page bila memang dibutuhkan. Hindari barrel import besar pada jalur render; gunakan import langsung untuk komponen berat. Lazy-load route workspace domain dan jalankan request independen secara paralel.

Minimal contract safety sebelum migrasi ke TypeScript penuh:

- satu wrapper API yang memeriksa `response.ok` dan bentuk error;
- JSDoc typedef untuk request/response penting;
- contract test terhadap OpenAPI untuk endpoint yang dipakai UI;
- loading, empty, stale, dan error state wajib eksplisit.

### 4.4 Dua UI

Selama Streamlit dan React sama-sama aktif, buat feature parity matrix dengan tiga status: `canonical`, `supported`, atau `not planned`. Satu workflow tidak boleh diam-diam memiliki dua implementasi bisnis.

Rekomendasi peran:

- Streamlit: engineering analysis mendalam, ingest/QC data, konfigurasi, dan workflow internal yang cepat berubah.
- React: command center, navigasi aset, reliability, work order, dan pengalaman operator yang stabil.
- FastAPI/application layer: satu-satunya kontrak untuk workflow yang harus identik di kedua UI.

Ini adalah batas produk, bukan alasan menghapus salah satu UI sekarang.

## 5. Sistem UI/UX yang disarankan

Hasil pencarian `ui-ux-pro-max` paling cocok dengan operations dashboard yang minimal, dense, low-motion, dan mempunyai status telemetry yang jelas. Pertahankan arah visual yang sudah ada: neutral slate, cyan sebagai aksi/selection, serta green/amber/orange/red sebagai status.

Aturan utama:

- Status selalu memakai teks atau ikon selain warna.
- Normal text memiliki contrast minimal 4.5:1 dan focus ring terlihat.
- Target interaksi minimal 44 x 44 px pada kontrol utama.
- Badge “online/live” wajib berasal dari health check nyata serta menampilkan waktu update/stale state.
- Body text minimal 14 px untuk dashboard padat; 16 px untuk teks panjang. Hindari `text-[9px]`/`text-[10px]` untuk informasi penting.
- Gunakan SVG/Material Symbols, bukan emoji sebagai ikon fungsional.
- Motion 150-250 ms dan hormati `prefers-reduced-motion`.
- Chart tidak mengandalkan warna saja; berikan label, tooltip, unit, source, dan timestamp.
- Mobile tidak harus memuat semua kepadatan desktop; prioritaskan health, alert, dan next action.

Design token perlu memiliki nama semantik yang sama pada kedua UI: `surface`, `surface-muted`, `text`, `text-muted`, `border`, `action`, `healthy`, `watch`, `warning`, `alert`, `critical`, dan `focus`. Implementasi boleh berbeda antara Streamlit dan CSS, tetapi nilai serta maknanya harus tercatat dalam satu tabel kontrak.

## 6. Roadmap aman

### Fase 0 - Baseline dan governance (1-2 hari)

- Terapkan `docs/coding-protocol.md` sebagai aturan review.
- Gunakan `docs/feature-parity.md` untuk ownership dan feature parity Streamlit/React.
- Tambah baseline endpoint/UI smoke test sebelum memindahkan file.
- Ukur waktu startup Streamlit, waktu render dashboard, dan ukuran bundle React.

### Fase 1 - Kurangi coupling entry point (3-5 hari)

- Ekstrak router FastAPI satu domain per PR tanpa mengubah path/response.
- Ekstrak bootstrap/filter MCSA dari `app.py` dan lazy-load hanya pada halaman terkait.
- Pecah dashboard Streamlit menjadi section presenter tanpa memindahkan rule domain.

Progress implementasi:

- endpoint DGA, tribology, thermal, dan PD sudah dipindahkan ke `pple/api/specialist_router.py`;
- bootstrap, cache, filter, equipment mapping, dan standby MCSA sudah dipindahkan ke `src/components/mcsa_page_context.py`;
- halaman non-MCSA tidak lagi memanggil loader dataset MCSA dari application shell.
- renderer dan dependensi khusus halaman Streamlit baru di-import ketika halaman aktif; kegagalan import satu halaman tidak lagi menggagalkan bootstrap seluruh navigasi.
- sampling compliance dan ringkasan distribusi kondisi MCSA sudah diekstrak dari `dashboard_page.py` ke presenter `src/components/mcsa_dashboard_sections.py` dengan characterization test.
- view Trend dan Perbandingan MCSA sudah diekstrak ke presenter `src/components/mcsa_dashboard_trends.py`; key widget, grafik, serta metrik perbandingan bulanan dan YoY dijaga oleh characterization test.
- view Ringkasan, Rekomendasi ESA/MCSA, Analisa Mendalam, dan Spektrum sudah dipindahkan ke `src/components/mcsa_dashboard_detail_views.py`; dashboard MCSA kini berperan sebagai orkestrator data dan pemilih presenter, sementara integrasi LLM tetap lazy dan opsional.
- filter snapshot detail, fallback metadata master, pembentukan tabel parameter/THD, health score, dan deteksi anomali sudah dipindahkan ke view-model murni `src/components/mcsa_dashboard_view_model.py`; transformasi tersebut kini dapat diuji tanpa runtime Streamlit.
- section equipment detail MCSA (selector, badge, metric summary, table styler, dan delegasi sub-view) telah diekstrak ke presenter `src/components/mcsa_dashboard_detail_section.py`; `src/pages/dashboard_page.py` kini murni hanya mengorkestrasi section header, compliance, condition summary, dan detail presenter (~60 baris) dan diverifikasi oleh `tests/test_mcsa_dashboard_detail_section.py`.
- endpoint materi / knowledge base (`/api/materi`, `/api/materi/search`) dan work orders (`/api/workorders`, `/api/workorders/approve`) telah diekstrak ke modular router `pple/api/routers/knowledge.py` dan `pple/api/routers/work_orders.py` tanpa merubah URL publik.
- endpoint equipment MCSA (`/api/equipment`, `/api/equipment/{equipment_name}`) telah diekstrak ke modular router `pple/api/routers/equipment.py` dengan data provider injection terstandar dan regression test ownership.
- endpoint multi-agent collaboration, technical disturbance skills learning, self-improvement, EnvHarness, dan multi-turn AI chatbot (`/api/agents/*`, `/api/skills/*`, `/api/agent/*`, `/api/learning/*`) telah diekstrak ke modular router `pple/api/routers/agents.py`.
- endpoint reports, uploads, fleet reliability, fusion diagnosis multi-modal, dan comprehensive assessment report (`/api/upload/dga`, `/api/upload/vibration`, `/api/reports/ppt`, `/api/reliability/fleet`, `/api/reliability/fusion/{equipment_name}`, `/api/reliability/diagnose`, `/api/reports/assessment/{equipment}`) telah diekstrak ke modular router `pple/api/routers/reports.py` dengan dependency injection data frames provider terstandar.
- endpoint core MCSA (`/api/health`, `/api/summary`, `/api/rotorbar/calculate`) telah diekstrak ke modular router `pple/api/routers/core.py`; `api_server.py` kini murni berperan sebagai composition root (FastAPI app, middleware, CORS, security, dan router mounting).

### Fase 2 - Contract dan design system (3-5 hari)

- Tambah response schema untuk endpoint yang masih mengembalikan dict bebas.
- Tambah error envelope konsisten dan request correlation ID.
- Konsolidasikan semantic tokens serta state loading/empty/error.
- Tambah unit/interaction test frontend untuk navigation dan API state.

Progress implementasi:

- schema Pydantic typed response models untuk 11 endpoint domain spesialis (DGA, Tribology, Thermal, PD) telah dibuat di `pple/api/schemas/specialist.py` dan diterapkan pada `pple/api/specialist_router.py` tanpa merusak kompatibilitas kontrak React;
- schema Pydantic typed response models untuk endpoint core MCSA & agents (`/api/health`, `/api/summary`, `/api/equipment`, `/api/rotorbar/calculate`, `/api/agents/specialists`) telah dibuat di `pple/api/schemas/core.py` dan diterapkan pada `api_server.py`;
- middleware correlation ID (`X-Request-ID`, `X-Correlation-ID`) dan standardized error envelope terstandar (`error`: {`code`, `message`, `correlation_id`}) diimplementasikan di `pple/api/observability.py` dan dipasang ke FastAPI app, tetap menjaga field `detail` agar kompatibel dengan legacy consumer;
- helper `parseApiError` dan komponen `ErrorState` (dengan request correlation ID & retry button) diimplementasikan dan diintegrasikan ke seluruh workspace domain React (`DGAWorkspace`, `TribologyWorkspace`, `ThermalWorkspace`, `PDWorkspace`, `MCSAWorkspace`);
- characterization & regression test ditambahkan di `tests/test_api_server.py` (`test_equipment_detail`, `test_equipment_router_modular_ownership`, `test_agents_router_modular_ownership`, `test_core_router_modular_ownership`, `test_reports_router_modular_ownership`, `test_fleet_reliability_endpoint`, `test_fusion_diagnosis_endpoint`, `test_simulate_multi_modal_diagnosis_endpoint`, `test_upload_vibration_placeholder_endpoint`, `test_error_envelope_and_correlation_id`), dengan seluruh 62 tests lulus (OK), 570 full test suite lulus, dan functional verification `verify_app.py` lulus 100%.


### Fase 3 - Application use cases (bertahap per fitur)

- Pindahkan orkestrasi lintas domain ke `pple/application/`.
- Arahkan API, CLI, dan Streamlit ke use case yang sama.
- Pertahankan adapter legacy sampai characterization test membuktikan output setara.

### Fase 4 - Performance dan observability

- Profile React sebelum memoization.
- Tambahkan bounded cache/TTL dan fragments pada Streamlit berdasarkan pengukuran.
- Tambahkan structured log untuk ingest, diagnosis, report, work order, dan provider fallback.

## 7. Indikator selesai

Arsitektur dianggap membaik bila:

- rule yang sama tidak ditemukan di lebih dari satu delivery layer;
- perubahan threshold hanya membutuhkan satu implementation change;
- endpoint dapat diuji per router tanpa memuat seluruh data yang tidak terkait;
- membuka halaman non-MCSA tidak memuat pipeline MCSA;
- schema API dan consumer React gagal cepat saat kontrak berubah;
- setiap status memiliki provenance, timestamp, dan state stale/unknown;
- full gate repo tetap lulus dan output diagnosis characterization test tidak berubah.
