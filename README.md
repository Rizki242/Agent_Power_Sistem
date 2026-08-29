# PPLE Agent - AI O&M Reliability Command Center

Platform terintegrasi Predictive Maintenance (PdM) dan Condition-Based Maintenance (CBM) berbasis multi-modal AI untuk pembangkit listrik (PLTU Jeranjang 3 × 25 MW). Sistem menggabungkan 6 Specialist AI Agents (Vibration, MCSA, DGA, PD, Tribology, Thermal), Reliability Fusion Engine, Predictive RUL, Risk Matrix, Safety Guardrail, Work Order EAM, dan Live Voice Assistant.

## Fitur Utama
1. **AI O&M Reliability Command Center (`/fusion`)**: Matriks reliabilitas armada multi-sensor (Health Index 0–100), estimasi Remaining Useful Life (RUL), Failure Probability 30-hari, dan Risk Engine.
2. **Multi-Modal Condition Fusion & Failure Mode Engine**: Korelasi bukti multi-teknologi (mis. Vibrasi BPFO + MCSA Sideband + Tribologi Fe + Thermal Suhu ➔ Cacat Bearing dengan Confidence 94%).
3. **6 Specialist AI Agents**:
   - **Vibration Agent**: ISO 10816-3 RMS, 1X/2X harmonics, BPFO/BPFI bearing defect analysis.
   - **MCSA Agent**: Pole-pass sideband dB (EPRI/IEEE Severity Level 1–4), deviasi arus/tegangan, THD %.
   - **DGA Agent**: Dissolved Gas Analysis ($H_2, CH_4, C_2H_2, C_2H_4, C_2H_6, CO, CO_2$), TDCG (IEEE C57.104), Duval Triangle 1, Rogers/IEC Ratios.
   - **Partial Discharge (PD) Agent**: PRPD pattern recognition, magnitudo pulsa (pC), corona/surface/slot/internal discharge.
   - **Tribology Agent**: Viskositas oli (ASTM D445), TAN, air ppm (ASTM D6304), partikel keausan Fe/Cu/Al, ISO 4406 Cleanliness.
   - **Thermal Agent**: Suhu IR & RTD, hotspot detection, dan gradien Delta-T.
4. **Live Voice Assistant (🎙️ & 🔊)**: Perekaman suara langsung (STT Bahasa Indonesia), pembacaan verbal jawaban AI (TTS), dan lampiran dokumen multi-format (PDF, Word, Excel, CSV, TXT, Gambar).
5. **Safety Guardrail Agent**: Memblokir perintah berisiko tinggi (*Trip/Shutdown*) dan mewajibkan otorisasi manual engineer (*Human-in-the-Loop*).
6. **Work Orders & EAM Center (`/workorders`)**: Pembuatan draft Work Order otomatis (P1–P4) terintegrasi sistem CMMS/SAP dengan alur otorisasi Chief Engineer.
7. **Basis Data Spesifikasi & Nameplate**: Data spesifikasi teknis lengkap motor pembangkit (kW, FLA, RPM, Kutub, Manufaktur, Tipe Bearing DE/NDE, VFD).
8. **Dashboard Streamlit & Generator Laporan**: Generator PowerPoint (PPTX) dan Word (DOCX) otomatis dari hasil filter.

## Alur Build & Instalasi

### Cara Cepat (Otomatis dengan Skrip Build)
Cukup jalankan satu skrip build terpadu:
```powershell
.\build.bat
```
Skrip ini secara otomatis:
1. Memeriksa/membuat virtual environment Python (`.venv`).
2. Menginstal & memperbarui semua dependensi Python (`requirements.txt`).
3. Menginstal dependensi dan mem-build frontend modern (`frontend/`).
4. Menjalankan seluruh rangkaian automated unit test dan verifikasi sistem.

---

### Cara Manual (Step-by-Step)

#### Langkah 1: Persiapan Python Environment
Pastikan Python 3.11+ terinstal, lalu jalankan:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

#### Langkah 2: Build Frontend (Vite / React)
Jika Anda menggunakan antarmuka web modern React:
```powershell
npm --prefix frontend install
npm --prefix frontend run build
```

#### Langkah 3: Verifikasi & Testing
Jalankan pengujian unit dan verifikasi fungsionalitas MCSA:
```powershell
# Menjalankan seluruh unit test
.\.venv\Scripts\python.exe -m unittest discover -s . -p "test_*.py"

# Menjalankan verifikasi sistem (Data loading, Chatbot, PPT generator, Materi)
.\.venv\Scripts\python.exe verify_app.py
```

---

## Cara Menjalankan Aplikasi

### 1. Menjalankan Penuh Sekaligus (FastAPI Backend + React Frontend)
Cukup klik dua kali `run_all.bat` atau jalankan:
```powershell
.\run_all.bat
```
Skrip ini akan membuka:
- **Backend API (FastAPI)** di `http://localhost:8000` (Swagger: `http://localhost:8000/docs`)
- **Frontend Modern (React)** di `http://localhost:5173`

---

### 2. Menjalankan Layanan Secara Terpisah

#### A. Dashboard Streamlit
Klik dua kali `run.bat` atau jalankan:
```powershell
.\.venv\Scripts\streamlit.exe run app.py
```
Akses dashboard di `http://localhost:8501`.

#### B. Backend API Server Saja (FastAPI)
Klik dua kali `run_api.bat` atau jalankan:
```powershell
.\.venv\Scripts\python.exe -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
```

#### C. Frontend React Saja
Klik dua kali `run_frontend.bat` atau jalankan:
```powershell
npm --prefix frontend run dev
```
Akses di `http://localhost:5173`.

## Alur penggunaan singkat

1. Atur periode, Unit, Voltage, dan Equipment pada sidebar.
2. Gunakan **Dashboard** untuk meninjau kondisi dan tren terbaru.
3. Aktifkan **Mode Edit** bila perlu memperbarui data, mengunggah laporan Word, atau menambah materi training.
4. Jalankan **Quality Check Laporan** sebelum mengonfirmasi batch laporan Word.
5. Buat **Laporan PPT** atau **Laporan Word** dari hasil filter yang aktif.

## Data & Folder
- `data/MCSA/Report MCSA.xls`: Sumber data Excel (fallback jika `mcsa_updated.csv` belum ada).
- `data/MCSA/mcsa_updated.csv`: Data gabungan aktif (hasil sync Word + edit manual + merge).
- `data/MCSA/Laporan/`: Struktur laporan Word yang direkomendasikan:
  - `data/MCSA/Laporan/UNIT 1/380-400/...docx`
  - `data/MCSA/Laporan/UNIT 2/6.3/...docx`
- `data/MCSA/config/`: Konfigurasi metadata equipment dan standar evaluasi MCSA/ESA.
- `data/MCSA/backup/`: Backup otomatis CSV saat penyimpanan/sync laporan.

## Materi Training
- Simpan file materi di folder `Materi/` (se-level dengan `app.py`).
- Aplikasi mendukung 2 format JSON:

### Format v1 (Halaman)
Berupa list halaman atau object dengan `pages`.

```json
[
  {"page": 1, "content": "..."},
  {"page": 2, "content": "..."}
]
```

atau

```json
{
  "pages": [
    {"page": 1, "content": "..."}
  ]
}
```

### Format v2 (Artikel + Sections)
Berupa satu object artikel atau array artikel.

```json
{
  "id": "mcsa-bearing-fault",
  "title": "Analisis MCSA untuk Bearing Fault",
  "tags": ["MCSA", "Motor", "Bearing", "Fault"],
  "level": "intermediate",
  "source": "Internal Training",
  "language": "id",
  "sections": [
    {"id": "intro", "heading": "Pendahuluan", "content": "..."},
    {"id": "spectrum", "heading": "Karakteristik Spektrum", "content": "..."}
  ]
}
```

### Catatan Performa
- Untuk folder materi yang besar (mis. ratusan MB), pencarian dilakukan di dalam file yang dipilih agar tetap ringan.
- Jika file materi sangat besar, disarankan memecah per topik agar waktu buka lebih cepat.

## Sync Laporan Word
1. Jalankan aplikasi dan aktifkan **Mode Edit**.
2. Buka halaman **Sync Laporan Word**, pilih satu atau beberapa `.docx`/`.docm`, lalu klik **Siapkan preview**.
3. Periksa equipment, tanggal laporan, metadata, jumlah parameter, dan status setiap file.
4. Klik **Konfirmasi dan perbarui dashboard**. File valid masuk ke `data/mcsa_updated.csv`; file bermasalah tetap diarsipkan sebagai karantina.
5. Setiap upload disimpan sebagai batch terpisah di `data/Laporan/uploads/YYYY/MM/DD/batch-HHMMSS-xxxxxx/` dengan `manifest.json` untuk audit.
6. Jika equipment dan tanggal yang sama direvisi, batch terbaru menjadi data aktif tanpa menghapus file arsip sebelumnya.

Setelah commit, Dashboard otomatis diarahkan ke tanggal dan equipment dari batch baru. Filter global tersedia berurutan berdasarkan Tahun, Bulan, rentang Tanggal, Unit, Voltage, dan Equipment.

## Rotor Bar & Status
- Parameter rotor bar yang digunakan/ditambahkan:
  - `Upper Sideband`, `Lower Sideband`, `Rotorbar Health` (RB Hlt Index)
  - `Se Fund`, `Se Harm`, `Rotorbar Level %` (jika tersedia di report)
  - `Rotorbar Severity Level` (1–4)
  - `Rotorbar` (status 3 warna: Normal/Alarm/High)
- Saat load data, aplikasi melakukan **recalculation hanya untuk data latest per equipment** agar tetap ringan.

## Performance Summary (Bahasa Indonesia)
- Parameter yang disimpan berupa teks dan diawali prefix:
  - `Ringkasan Kinerja - Kesimpulan`
  - `Ringkasan Kinerja - Faktor Daya`
  - `Ringkasan Kinerja - Arus`
  - `Ringkasan Kinerja - Tegangan`
  - `Ringkasan Kinerja - Beban`
  - `Ringkasan Kinerja - Koneksi Fasa`
  - `Ringkasan Kinerja - Rotor`
  - `Ringkasan Kinerja - Stator`
  - `Ringkasan Kinerja - Air-gap Rotor/Stator`
  - `Ringkasan Kinerja - Distorsi Harmonik`
  - `Ringkasan Kinerja - Misalignment/Unbalance`
  - `Ringkasan Kinerja - Bearing`

## Verifikasi
Jalankan verifikasi cepat:
```bash
python verify_app.py
```

## Operasional dan Deployment Streamlit

### Backup dan audit

- Setiap penyimpanan `mcsa_updated.csv` membuat backup bertimestamp di `data/backup/` sebelum file utama diganti secara atomic.
- Jumlah backup diatur melalui `MCSA_MAX_BACKUPS` (default `5`, minimum `1`).
- Setiap batch menyimpan `manifest.json` di `data/Laporan/uploads/.../` beserta checksum file, status preview/karantina, dan `audit_events` untuk pembuatan, preview, dan commit.
- Jangan menyimpan `data/` pada filesystem sementara saat deployment. Pasang volume persisten dan arahkan `MCSA_DATA_DIR` ke lokasi tersebut.

### Konfigurasi environment

Gunakan [.env.example](.env.example) sebagai daftar variabel. File `.env` tidak dimuat otomatis; tetapkan variabel melalui platform deployment atau shell.

| Variabel | Kegunaan |
| --- | --- |
| `MCSA_DATA_DIR` | Direktori data persisten. Default: folder `data/` di repository. |
| `MCSA_MAX_BACKUPS` | Jumlah backup CSV yang dipertahankan. Default: `5`. |
| `WORK_ORDERS_FILE` | Opsional, file JSON untuk menyimpan status Work Order runtime. Default memakai folder runtime lokal di data. |
| `VITE_API_BASE_URL` | Base URL backend FastAPI untuk frontend React. Default: `http://localhost:8000`. |
| `GEMINI_API_KEY` | Opsional, untuk fitur AI. Gunakan environment variable atau `.streamlit/secrets.toml`; jangan commit key. |

### Menjalankan di server

1. Instal Python 3.11, lalu buat environment dan dependensi:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

2. Tetapkan lokasi data persisten dan retensi backup, misalnya:

   ```powershell
   $env:MCSA_DATA_DIR = "D:\MCSA-data"
   $env:MCSA_MAX_BACKUPS = "10"
   ```

3. Jalankan Streamlit pada host/port yang sesuai jaringan internal:

   ```powershell
   .\.venv\Scripts\streamlit.exe run app.py --server.address 0.0.0.0 --server.port 8501
   ```

Sebelum rilis, jalankan `python -m unittest`, buka halaman **Quality Check Laporan**, lakukan satu batch uji, dan pastikan backup serta `manifest.json` baru terbentuk.

## Rekomendasi & Analisa Kondisi (MCSA/ESA, ATPOLL II)
- **Tujuan**: Menetapkan langkah tindak lanjut yang konsisten saat kondisi berubah (Normal/Alarm/High) berdasarkan praktik internasional MCSA/ESA.
- **Pengambilan Data (ATPOLL II)**:
  - Gunakan clamp arus dan tegangan sesuai spesifikasi alat, pastikan koneksi aman dan polaritas benar.
  - Ambil data pada beban yang cukup (≥40–60% nameplate) untuk analisa rotor bar yang lebih reliabel.
  - Rekam durasi yang memadai (≥30–60 detik) untuk stabilitas spektrum, hindari transien start/stop.
  - Catat metadata: Unit, Voltage, beban (perkiraan atau FLA/Load%), tanggal/jam, kondisi operasi (standby/normal).
- **Interpretasi Utama**:
  - Rotor Bar: evaluasi sideband sekitar fundamental (Upper/Lower SB). Ambang dasar: bagus jika < -54 dB; waspada -54 s/d -45 dB; kritis jika ≥ -45 dB. Perkuat keputusan dengan RB Hlt Index dan rasio Se harm vs Se fund bila tersedia.
  - Unbalance Tegangan/Arus: gunakan deviasi % fase; tegangan >1% waspada, >2% tinggi; arus >5% waspada, >10% tinggi.
  - THD Tegangan: rujukan IEEE 519; >5% waspada, >8% tinggi.
  - Bearing/Stator/Air-gap: gunakan Performance Summary untuk insight kualitatif dan tindak lanjut awal.
- **Langkah Tindak Lanjut**:
  - Normal: lanjutkan operasi; lakukan trending berkala (mingguan/bulanan) dan simpan rekaman.
  - Alarm: lakukan inspeksi terarah (cek koneksi fase, terminal, ground reference; survei vibrasi untuk misalignment/unbalance; review beban terhadap nameplate), tingkatkan frekuensi trending.
  - High: rencanakan tindakan segera (survei vibrasi menyeluruh, inspeksi koneksi dan terminal, evaluasi beban dan supply), siapkan rencana maintenance/penurunan beban untuk mitigasi risiko.
- **Best Practice**:
  - Bandingkan hasil saat beban rendah vs tinggi; hasil rotor bar pada beban rendah bisa tidak konklusif.
  - Konsistenkan titik ukur dan durasi rekaman untuk komparabilitas antar sesi.
  - Gunakan panel Ringkasan Performance untuk komunikasi cepat lintas tim (operasi/maintenance).

## Struktur File
- `data/`: Folder data (Report MCSA.xls, Laporan Word).
- `src/`: Source code (loader, generator, chatbot).
- `tests/`: Unit test (`test_*.py`), dijalankan dengan `unittest discover` dari root.
- `app.py`: Aplikasi utama (Streamlit).
