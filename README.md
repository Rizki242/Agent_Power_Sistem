<p align="center">
  <img src="docs/readme-assets/banner.svg" alt="AGENT LEARNING POWER — PPLE Agent" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-3776AB?logo=python&logoColor=white" alt="Python 3.11">
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit">
  <img src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=000" alt="React 19">
  <img src="https://img.shields.io/badge/decision%20core-rule--based-0284c7" alt="Rule-based decision core">
  <img src="https://img.shields.io/badge/tests-360%20passing-10b981" alt="360 unit tests passing">
  <img src="https://img.shields.io/badge/platform-Windows--first-64748b" alt="Windows-first">
</p>

# AGENT LEARNING POWER

## Platform Condition-Based Maintenance untuk Pembangkit Listrik

**AGENT LEARNING POWER** (kode proyek: **PPLE Agent**) adalah platform Condition-Based Maintenance (CBM) dan Predictive Maintenance (PdM) untuk membantu tim operasi dan pemeliharaan membaca kondisi aset, menggabungkan bukti lintas domain, serta menyusun tindak lanjut yang dapat ditinjau engineer. Implementasi saat ini berfokus pada data PLTU Jeranjang (3 × 25 MW) dan menggunakan **logika rule-based sebagai sumber keputusan utama**; integrasi LLM hanya bersifat opsional dan selalu punya fallback lokal.

Antarmuka utama menggunakan Streamlit dengan desain navigasi berbasis domain. Dataset, filter MCSA, dan renderer halaman dimuat secara lazy hanya saat dibutuhkan. React/Vite dan FastAPI tersedia sebagai antarmuka serta API pendamping untuk kebutuhan integrasi modern, dan CLI `pple` (Typer) menyediakan akses baris perintah — termasuk perintah bahasa natural — ke inti yang sama.

> Hasil diagnosis adalah dukungan keputusan teknis, bukan instruksi operasi otomatis. Keputusan trip, shutdown, perubahan proteksi, atau pekerjaan lapangan tetap wajib mengikuti SOP dan otorisasi engineer.

## Daftar isi

- [Desain aplikasi saat ini](#desain-aplikasi-saat-ini)
- [Kapabilitas utama](#kapabilitas-utama)
- [Alur diagnosis multi-agent](#alur-diagnosis-multi-agent)
- [Arsitektur](#arsitektur)
- [CLI `pple`](#cli-pple)
- [Prasyarat](#prasyarat)
- [Instalasi dan verifikasi](#instalasi-dan-verifikasi)
- [Menjalankan aplikasi](#menjalankan-aplikasi)
- [Alur penggunaan](#alur-penggunaan)
- [Data, materi, dan audit](#data-materi-dan-audit)
- [Konfigurasi environment](#konfigurasi-environment)
- [Struktur repository](#struktur-repository)
- [Catatan operasional](#catatan-operasional)

Dokumen pengembangan:

- [Evolusi arsitektur](docs/architecture-evolution.md) - hasil audit, arsitektur target, dan roadmap refactor aman.
- [Protokol coding](docs/coding-protocol.md) - dependency rules, standar UI/API/domain, quality gate, dan definition of done.
- [Feature parity](docs/feature-parity.md) - ownership workflow antara Streamlit, React, FastAPI, dan CLI.

## Desain aplikasi saat ini

Halaman awal adalah **Agent Dashboard**, sebuah command center yang menampilkan kondisi armada dari snapshot data terbaru. Pengguna dapat melihat jumlah aset, Fleet Health, watchlist, status specialist agent, Fleet Health Matrix, lalu memilih equipment untuk diagnosis multi-agent secara rinci.

Navigasi Streamlit dikelompokkan sebagai berikut:

| Kelompok | Halaman | Kegunaan |
| --- | --- | --- |
| Command Center | Agent Dashboard, Chatbot, Materi Training | Monitoring armada, tanya jawab teknis, dan basis pengetahuan. |
| Asset Management | Register Aset, Asset 360° View, Laporan Kondisi, Manajemen Data, Sync Laporan Word, Quality Check Laporan | Pengelolaan aset, data, dan batch laporan. Asset 360° View menggabungkan MCSA/vibrasi/thermal/tribology jadi satu pandangan health index per equipment. |
| Engineering | MCSA, Vibrasi, DGA, Tribology, Thermal, Partial Discharge, Control Condition | Analisis per disiplin condition monitoring. |
| Reliability | Reliability | Titik masuk reliabilitas; fusion engine saat ini tersedia di Agent Dashboard. |
| Reports | Laporan PPT, Laporan Word | Pembuatan laporan dari filter data aktif. |
| Work Orders | Work Orders | Endpoint API dan halaman Streamlit lengkap: KPI, filter/pencarian, approve/progress/complete/reject, form pembuatan WO baru. |
| Utilitas | Settings, Help & Support | Help & Support sudah lengkap. Settings punya beberapa kategori ("Appearance", "API Keys terpusat", "Database config", dll.) yang masih menampilkan "akan hadir di rilis mendatang" — bagian inti (General, AI & LLM, Engineering Modules) sudah berfungsi. |

Diagram rancangan target (visi jangka panjang, termasuk database dan admin config yang belum diimplementasi) tersedia di [docs/desain.png](docs/desain.png). Diagram tersebut adalah arah arsitektur, bukan gambaran kondisi saat ini — bagian [Arsitektur](#arsitektur) di bawah menjelaskan apa yang benar-benar berjalan hari ini.

## Kapabilitas utama

- **Diagnosis multi-agent rule-based** untuk MCSA, vibrasi, DGA, partial discharge, tribology, dan thermal.
- **Reliability fusion**: Health Index, status kesehatan, failure mode, confidence, estimasi RUL, probabilitas gagal 30 hari, risiko, dan draft work order ketika data pengukuran tersedia.
- **Safety guardrail**: diagnosis tidak menjalankan tindakan fisik; tindakan berisiko (trip/shutdown/breaker) selalu diblokir dan memerlukan human-in-the-loop — baik dari UI maupun dari CLI `pple ask`.
- **MCSA dashboard**: evaluasi sideband rotor bar, deviasi arus/tegangan, THD, status bearing, tren, dan ringkasan kinerja.
- **Manajemen laporan**: preview, quality check, sinkronisasi laporan Word, arsip batch, manifest audit, serta backup CSV otomatis.
- **Knowledge base**: pencarian kata kunci selalu tersedia; pencarian semantik FAISS bersifat opsional dan memiliki fallback.
- **Laporan**: generator PowerPoint dan Word dari data/filter aktif.
- **API FastAPI**: akses data aset, ringkasan domain, diagnostik fusion, chatbot, knowledge base, laporan, dan work order — plus `/api/v2/*` (modules, assets, reliability, agents) dari migrasi `pple`.
- **CLI `pple`**: status/doctor sistem, jalankan analisis satu modul, telusuri hierarki aset, cek reliability fusion, perintah bahasa natural (`pple ask "cek CWP-1A"`) dengan klasifikasi risiko READ/WRITE/HIGH-RISK, `pple config llm` untuk melihat/mengganti provider-model LLM dari terminal, `pple chat` (chatbot rule-based, opsional diperkaya LLM), flag `--offline` yang memblokir semua provider cloud, dan `pple serve api/frontend/all` sebagai alternatif native untuk skrip `.bat`.

## Alur diagnosis multi-agent

<p align="center">
  <img src="docs/readme-assets/diagnosis-pipeline.svg" alt="Alur diagnosis multi-agent menuju keputusan yang dapat ditinjau engineer" width="100%">
</p>

Setiap specialist agent hanya menilai domainnya sendiri dengan evidence dan confidence eksplisit; Reliability Fusion Engine mengorelasikan bukti lintas domain (mis. BPFO vibrasi + sideband MCSA + Fe pada oli + kenaikan suhu → indikasi cacat bearing) menjadi satu Health Index. Safety Guardrail berdiri sebagai gerbang wajib sebelum rekomendasi apa pun yang menyentuh tindakan berisiko tinggi — bukan fitur tambahan, tapi bagian dari alur.

## Arsitektur

<p align="center">
  <img src="docs/readme-assets/architecture-current.svg" alt="Arsitektur PPLE Agent saat ini: Streamlit, React, FastAPI, CLI di atas satu core Python" width="100%">
</p>

Dua (tiga, dengan CLI) antarmuka berbagi satu core Python:

```text
Streamlit UI (app.py) ─┐
                       ├─ src/: data, domain logic, agents, knowledge, reports
React/Vite frontend ───┼─ FastAPI (api_server.py)
                       │      └─ data/MCSA/, Materi/, data domain lainnya
pple CLI (Typer) ──────┘      └─ /api/v2/* (pple.api.router)
```

Logika rule-based di `src/` adalah sumber kebenaran untuk perhitungan kondisi, threshold, dan rekomendasi. Bila AI provider tidak dikonfigurasi atau gagal, aplikasi tetap menggunakan jawaban dan evaluasi lokal. Paket `pple/` (migrasi V2, lihat `docs/final.md`) dibangun **secara aditif** di atas `src/` — `LegacyAgentAdapterModule` memanggil ulang agent yang sama, bukan menduplikasi logikanya.

## CLI `pple`

```powershell
pip install -e .          # sekali saja, mendaftarkan console script `pple`

pple status                              # snapshot sistem: modul aktif, jumlah equipment, safety guard
pple doctor                              # health check startup
pple assets tree                         # hierarki Plant -> Unit -> Equipment
pple reliability health CWP-1A           # fusion Health Index/RUL/Risk untuk satu equipment
pple analyze vibration "CWP 1A" --data '{"overall_rms": 5.2}'

pple ask "cek CWP-1A"                    # bahasa natural -> READ, langsung jalan
pple ask "aktifkan modul vibration untuk CWP-1A"   # WRITE -> minta konfirmasi y/N
pple ask "trip generator sekarang"       # HIGH-RISK -> diblokir Safety Guardrail, tidak pernah dieksekusi
pple shell                               # REPL interaktif untuk perintah di atas

pple config llm                          # provider/model LLM aktif saat ini + status API key
pple config set llm.provider groq        # gemini | groq | opencode | ollama
pple config set llm.model qwen/3.6-27b   # model untuk provider yang sedang aktif
pple config test                         # tes koneksi ke provider aktif (helper yang sama dengan tombol "Tes Koneksi" di Settings)

pple chat "status CWP 1A"                # chatbot rule-based (src.chatbot), boleh diperkaya LLM bila dikonfigurasi
pple --offline chat "status CWP 1A"      # sama persis, tapi provider cloud (gemini/groq/opencode) dipastikan tidak dipanggil
pple --offline config test               # ditolak untuk provider cloud; provider ollama (lokal) tetap boleh

pple serve api                           # setara run_api.bat, plus --host/--port kustom
pple serve frontend                      # setara run_frontend.bat
pple serve all                           # setara run_all.bat (API sebagai subprocess + frontend di depan)
```

`pple analyze` wajib menerima setidaknya satu field pengukuran yang dikenali
oleh modul. Payload kosong atau field yang tidak relevan ditolak agar data yang
hilang tidak pernah ditampilkan sebagai kondisi sehat. Hasil diagnosis V2
menyertakan status kualitas data, konteks yang masih kurang, hash input, dan
versi rule untuk traceability. Nilai RUL serta probabilitas gagal saat ini
berstatus `heuristic_unvalidated`: keduanya adalah proyeksi rule-based dari
Health Index, bukan prediksi ML yang telah dikalibrasi terhadap histori kegagalan.
Aturan yang sama berlaku pada diagnosis kolaboratif: modality yang tidak dikirim
tidak diisi dengan baseline sintetis. Tanpa telemetry yang dapat dinilai, hasilnya
adalah `UNKNOWN`, RUL/risk tidak tersedia, dan tindak lanjutnya `COLLECT_DATA`.

Klasifikasi risiko (`pple/cli/safety.py`) memisahkan command menjadi **READ** (selalu boleh), **WRITE** (minta konfirmasi eksplisit), dan **HIGH-RISK** (diblokir total oleh `SafetyGuardrailAgent` yang sama dengan yang dipakai UI — tidak ada jalur pintas). `pple config` membaca/menulis `data/MCSA/config/ai_settings.json` yang sama dengan halaman Settings Streamlit — CLI dan UI berbagi satu preferensi, dan API key tidak pernah ikut tersimpan di file itu.

Flag global `--offline` (docs/final.md Phase 22) memastikan PPLE tetap bisa dipakai tanpa internet: jawaban `pple chat` selalu dari `src.chatbot.MCSAChatbot` (rule-based) lebih dulu, LLM (cloud maupun Ollama lokal) hanya memperkaya narasinya dan tidak pernah menjadi sumber kebenaran untuk threshold/status engineering.

`pple serve` (docs/final.md Phase 23) tidak menggantikan `run_api.bat`/`run_frontend.bat`/`run_all.bat` — ketiganya tetap berfungsi seperti biasa — hanya menyediakan jalur yang sama lewat CLI, memanggil launcher Python yang sama persis (`scripts/run_server.py`). Lihat `docs/final.md` untuk roadmap migrasi `pple` V2 selengkapnya.

## Prasyarat

- Windows dan Python 3.11
- Node.js dan npm untuk frontend React
- Data MCSA: `data/MCSA/mcsa_updated.csv` atau `Report MCSA.xls`

## Instalasi dan verifikasi

Cara paling cepat adalah menjalankan build terpadu dari root repository:

```powershell
.\build.bat
```

Skrip tersebut membuat atau menggunakan `.venv`, memasang dependensi Python, membangun frontend, menjalankan unit test, dan menjalankan verifikasi aplikasi.

Untuk setup manual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend install
npm --prefix frontend run build
```

Jalankan validasi berikut dari root repository:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"
.\.venv\Scripts\python.exe verify_app.py
```

## Menjalankan aplikasi

| Layanan | Perintah | Alamat |
| --- | --- | --- |
| Semua layanan | `.\run_all.bat` | API `http://localhost:8000`, React `http://localhost:5173` |
| Dashboard Streamlit | `.\run.bat` | `http://localhost:8501` |
| FastAPI | `.\run_api.bat` | `http://localhost:8000/docs` |
| React/Vite | `.\run_frontend.bat` | `http://localhost:5173` |

Jika virtual environment tercampur versi Python dan Streamlit menampilkan layar perbaikan dependensi, hapus `.venv`, buat ulang menggunakan Python 3.11, lalu pasang kembali `requirements.txt`.

## Alur penggunaan

1. Buka **Agent Dashboard** untuk melihat kondisi armada dan critical watchlist.
2. Pilih equipment pada bagian diagnosis multi-agent untuk meninjau evidence, failure mode, RUL, risiko, dan rekomendasi.
3. Buka modul Engineering yang sesuai untuk analisis domain MCSA, vibrasi, DGA, tribology, thermal, atau PD.
4. Gunakan **Mode Edit** hanya saat mengelola data, menyinkronkan laporan Word, atau memperbarui materi training.
5. Jalankan **Quality Check Laporan** sebelum mengonfirmasi batch laporan.
6. Buat laporan PPT atau Word berdasarkan periode, unit, voltage, dan equipment yang dipilih.

## Data, materi, dan audit

| Lokasi | Isi |
| --- | --- |
| `data/MCSA/mcsa_updated.csv` | Data gabungan aktif dari sinkronisasi laporan dan edit manual. |
| `Report MCSA.xls` | Sumber fallback bila CSV aktif belum tersedia. |
| `data/MCSA/config/` | Metadata equipment dan konfigurasi standar MCSA/ESA. |
| `data/Laporan/uploads/YYYY/MM/DD/...` | Arsip upload batch beserta `manifest.json` audit. |
| `Materi/` | Knowledge base JSON format v1 (`pages`) atau v2 (`sections`). |

Setiap penyimpanan CSV membuat backup bertimestamp. Atur jumlah backup melalui `MCSA_MAX_BACKUPS` (default `5`, minimum `1`). Untuk deployment, gunakan storage persisten dan arahkan `MCSA_DATA_DIR` ke lokasi data tersebut.

Contoh knowledge base v2:

```json
{
  "id": "mcsa-bearing-fault",
  "title": "Analisis MCSA untuk Bearing Fault",
  "tags": ["MCSA", "Motor", "Bearing"],
  "language": "id",
  "sections": [
    {"id": "intro", "heading": "Pendahuluan", "content": "..."}
  ]
}
```

Setelah menambah atau menghapus materi melalui kode, panggil `load_knowledge_base(force_reload=True)` agar indeks dimuat ulang.

## Konfigurasi environment

Gunakan [.env.example](.env.example) sebagai referensi. Jangan menyimpan API key di source code atau commit file rahasia.

| Variabel | Kegunaan |
| --- | --- |
| `MCSA_DATA_DIR` | Direktori data persisten; default `data/`. |
| `MCSA_MAX_BACKUPS` | Retensi backup CSV; default `5`. |
| `WORK_ORDERS_FILE` | Lokasi JSON penyimpanan work order; opsional. |
| `VITE_API_BASE_URL` | Base URL FastAPI untuk frontend React; default `http://localhost:8000`. |
| `GEMINI_API_KEY` | Opsional untuk enhancement AI (model dapat dipilih/diketik bebas di halaman Settings). |

File `.env` tidak dimuat otomatis oleh seluruh aplikasi. Untuk Streamlit, gunakan environment variable atau `.streamlit/secrets.toml`; modul asisten LLM juga dapat membaca `.env` sebagai fallback.

## Struktur repository

```text
app.py                 Dashboard Streamlit dan routing halaman
api_server.py          FastAPI, tipis di atas modul src/
src/                   Domain logic, specialist agents, komponen, dan halaman
pple/                  Migrasi V2 (aditif): engineering, assets, reliability, agents, cli, api
frontend/              Frontend React/Vite
data/                  Data operasional dan konfigurasi
Materi/                Knowledge base
tests/                 Unit test unittest
docs/desain.png        Rancangan arsitektur dan navigasi target
docs/final.md          Roadmap migrasi pple V2 (30 fase)
docs/readme-assets/    Diagram SVG yang dipakai README ini
```

## Catatan operasional

- Partial Discharge dapat menggunakan data contoh/default bila data sumber belum tersedia; interpretasikan hasilnya sesuai penanda di aplikasi.
- Data modalitas yang tidak tersedia tidak boleh dianggap sebagai bukti diagnosis; fusion hanya menggunakan pengukuran yang ada.
- Korelasi bearing menggunakan `fault_code` dan `mechanism_tags` yang stabil, bukan pencocokan teks diagnosis. Hasil fusion menambahkan `ranked_hypotheses` berisi bukti pendukung, bukti yang bertentangan, bukti yang belum tersedia, mekanisme fisik, alasan confidence, dan konfirmasi yang diwajibkan.
- Rule rotor bar, shaft misalignment, DGA, dan partial discharge juga menggunakan taxonomy terstruktur. Kontrak `failure_mode_diagnosis` dan setiap item hipotesis divalidasi oleh schema API, dengan confidence dibatasi pada rentang `0..1` dan severity `0..4`.
- Fusion V2 mengevaluasi kandidat secara independen, mengurutkan beberapa hipotesis dengan `ranking_score`, serta memberi penalti eksplisit untuk bukti yang bertentangan dan domain konfirmasi yang belum tersedia. Status diagnosis dibatasi secara konservatif menjadi `PROBABLE`, `POSSIBLE`, `INCONCLUSIVE`, atau `INSUFFICIENT_DATA`; `CONFIRMED` memerlukan outcome lapangan terverifikasi.
- Sebelum rilis, jalankan unit test dan `verify_app.py`, lalu lakukan satu batch uji untuk memastikan backup serta `manifest.json` terbentuk.
