## Status Saat Ini
- Fungsi utama sudah jalan: filter ikut dashboard, ada slide Dashboard Ringkas, dan tabel detail sudah mengisi Satuan/Limit untuk parameter kunci (Load/Dev/THD/Voltage/Current/Power/Sideband).
- Tidak ada error yang terlihat dari pembacaan kode; `df_latest_augmented` aman dipakai lintas halaman.

## Yang Masih Perlu (Opsional, tapi disarankan)
1. **Lengkapi Satuan/Limit untuk parameter non-numerik**
   - Contoh: `power factor` → satuan `pf` (atau kosong tapi konsisten), `Rotorbar Severity`/`Rotorbar Health` → limit/arti level (mis. Level 1–5).
2. **Samakan aturan limit dengan standar yang dipakai di analisa**
   - Saat ini limit Dev/THD/Load memakai rule default; bisa diikat ke threshold yang sama dengan engine analisa (NEMA/IEEE) agar konsisten 100%.
3. **Tambahkan opsi “Standby otomatis” ke halaman Laporan PPT**
   - Saat ini Standby hanya dihitung saat berada di halaman Dashboard. Jika user ingin PPT merefleksikan “fleet universe” + missing update, tambahkan toggle yang sama pada halaman PPT.
4. **Tingkatkan kesesuaian tabel (keterbacaan)**
   - Auto-wrap/ukuran font, set lebar kolom, dan stabilkan jumlah baris per slide agar tidak kepotong.

## Implementasi Teknis (Perubahan Minimal)
- Buat satu mapping metadata parameter (unit/limit/format) yang dipakai bersama oleh:
  - renderer tabel dashboard (Streamlit)
  - renderer tabel detail PPT
- Tambahkan metadata untuk parameter yang belum tertutup (PF, rotorbar severity/health, kondisi/bearing).
- Jika opsi Standby diaktifkan pada halaman PPT, reuse blok perhitungan Standby yang sudah ada (tanpa duplikasi banyak kode).

## Verifikasi
- Generate PPT dari beberapa kombinasi filter (UNIT/Voltage/periode).
- Cek tabel detail: semua baris punya Satuan/Limit yang masuk akal dan tidak ada nilai “pecah baris”.
- Cek slide Dashboard Ringkas: total & pie chart sesuai filter dan (jika diaktifkan) sesuai universe + standby.

Jika Anda setuju, saya lanjutkan implement 4 poin opsional di atas (prioritas: 1→2→3→4).