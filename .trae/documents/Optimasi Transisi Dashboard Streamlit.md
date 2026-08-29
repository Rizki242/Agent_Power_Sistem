## Target
- Dashboard pindah fitur cepat (minim loading).
- Tampilkan rekomendasi tindakan yang **mengacu ESA/MCSA International** (rule-based, konsisten, dan bisa dikonfigurasi).

## Perbaikan Performa Dashboard
### 1) Cache komputasi berbasis file+filter
- Cache `df_period` + `df_latest` (key: data_key + date_start/date_end).
- Cache `filtered_df` (key: data_key + date_start/date_end + sel_unit/sel_volt).
- Cache perhitungan standby/compliance (key: data_key + date_end + standby_scope + required_month_params + sel_unit/sel_volt).

### 2) Optimasi daftar equipment
- Hilangkan loop O(N^2) saat membuat label equipment.
- Gunakan `drop_duplicates('Equipment')` untuk membangun `display_map` sekali saja.

### 3) Lazy-load bagian berat
- Tambahkan mode tampilan Dashboard:
  - **Ringkasan (Cepat)** default
  - **Detail**
  - **Trend/Perbandingan/Spektrum** hanya dihitung saat dipilih
- Kurangi styling berat (hindari `Styler.applymap`) dan normalisasi kolom object sebelum `st.dataframe`.

## Rekomendasi Sesuai ESA/MCSA International
### 4) Buat “Rekomendasi Cepat (ESA/MCSA)” berbasis latest measurement
- Tambahkan panel di Detail equipment:
  - Status ringkas (Overall/Alarm/High/Monitoring/Invalid-load)
  - 3–10 rekomendasi tindakan
- Sumber data: hanya **nilai terakhir** parameter penting (tanpa scan history) agar cepat.
- Aturan engan terminologi ESA/MCSA:
  - **Load validity** (mis. <20%: Invalid diagnosis; 20–40%: Monitoring only; ≥40%: Valid diagnosis)
  - **Voltage/Current unbalance**, **THD**, **Rotor bar** (upper/lower sideband, RB index/level%), **Bearing condition** bila ada.
  - Output rekomendasi disusun per kategori (Power Quality, Unbalance, Rotor Bar, Bearing, Validity/Repeat test).

### 5) Jadikan standar configurable (agar match guideline ESA/MCSA internal perusahaan)
- Pakai mekanisme konfigurasi yang sudah ada (`config/thresholds_default.json` + override) untuk ambang batas Normal/Monitoring/Alarm/High.
- Tambahkan satu file konfigurasi guidance (mis. `config/esa_mcsa_guidance.json`) untuk teks rekomendasi per kategori/status.
- Default yang disediakan mengikuti praktik umum di kode sekarang, tetapi angka/teks bisa disesuaikan agar benar-benar identik dengan dokumen ESA/MCSA yang kamu gunakan.

### 6) Analisa Mendalam (opsional)
- Tombol “Analisa Mendalam (pakai history)” tetap tersedia.
- Saat ditekan baru menjalankan `generate_initial_analysis()` dan hasilnya di-cache per equipment.

## Validasi
- Uji performa: pindah menu dan buka Dashboard harus responsif.
- Uji hasil rekomendasi untuk 3 kondisi (Normal/Alarm/High) + kasus load rendah.
- Pastikan tidak ada error baru di terminal.

Kalau kamu setuju, saya lanjut implementasi di `app.py` dan menambah helper rekomendasi ESA/MCSA + konfigurasi thresholds/guidance di `src/standards.py`.