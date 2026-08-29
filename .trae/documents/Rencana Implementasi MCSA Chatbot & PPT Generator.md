# Rencana Pengembangan Sistem MCSA (Chatbot + Dashboard + PPT)

Saya akan membangun aplikasi berbasis **Python (Streamlit)** yang berfungsi sebagai Dashboard, Chatbot, dan Generator PPT otomatis berdasarkan data Excel dan Laporan Word yang tersedia.

## 1. Persiapan & Instalasi
- Menginstal library yang dibutuhkan: `pandas`, `xlrd` (untuk baca .xls), `python-pptx` (untuk PPT), `streamlit` (untuk Web App/Chatbot), `plotly` (untuk grafik).

## 2. Modul Data Processing (`src/data_loader.py`)
- **Fungsi `load_mcsa_data()`**: Membaca file `data/Report MCSA.xls`.
- **Pembersihan Data**: Mengonversi kolom parameter menjadi tipe numerik, menangani *missing values*.
- **Mapping Status**: Jika file Excel belum memiliki kolom "Status" final, kita buat logika sederhana berdasarkan threshold standar (misal: dB level > -40dB = Warning).
- **Link Dokumen**: Mengaitkan nama equipment (misal `C3WP1A`) dengan file `.docx` yang ada di folder `data/Laporan` agar bisa diakses mudah.

## 3. Modul Chatbot Logic (`src/chatbot.py`)
- **Query Processing**: Menerima input teks (misal: "Kondisi C3WP1A" atau "List motor alarm").
- **Lookup Engine**: Mencari data relevan di DataFrame.
- **Response Generation**: Format jawaban teks ringkas untuk WhatsApp/Web.
  - *Contoh Output*: "⚠️ **C3WP1A**: Warning. Sideband level -38dB. Rekomendasi: Cek ulang 3 bulan."

## 4. Modul Generator PPT (`src/ppt_generator.py`)
- **Template**: Membuat master slide sederhana secara programatis (atau load existing jika ada).
- **Looping Asset**: Untuk setiap motor yang dipilih:
  - Buat slide baru.
  - Tulis Header (Nama Asset).
  - Buat Tabel Parameter (Rotor Bar, Eccentricity, dll).
  - Tampilkan Indikator Visual (Kotak Hijau/Kuning/Merah).
- **Ringkasan**: Slide awal berisi statistik total (Pie chart: Normal vs Alarm).

## 5. Web Dashboard & Interface (`app.py`)
- **Menu Navigasi**:
  1.  **Dashboard**: Overview kondisi fleet (Grafik Bar/Pie), Tabel data yang bisa di-filter.
  2.  **Chatbot**: Simulasi chat interface (bisa dites seperti WhatsApp).
  3.  **Generate Report**: Tombol untuk download file PPT hasil generate.

## Langkah Implementasi (Coding)
1.  Setup project & install dependencies.
2.  Eksplorasi & parsing file Excel (memastikan nama kolom benar).
3.  Implementasi `ppt_generator.py`.
4.  Implementasi `app.py` (Streamlit Dashboard + Chatbot UI).
5.  Verifikasi dengan data sampel.
