# Laporan Analisis Vibrasi - ID Fan Unit-1

> Dibuat: 2026-08-11T23:20:55
> Confidence merupakan skor heuristik evidence, bukan probabilitas kegagalan. Severity mengikuti alarm/site limit yang tersedia.

## 1. Data Mesin dan Pengukuran

- Mesin: **ID Fan Unit-1**
- Tipe: fan
- RPM: 1480
- Beban: 82 %
- Titik / arah: Fan DE / horizontal
- Parameter / unit: velocity / mm/s RMS
- Overall: 5.20

## 2. Kualitas Data

- Status: **GOOD**
- Score: 1.00
- FFT resolution: 75.00 CPM/line
- Minimum peak separation (perkiraan Hanning): 112.50 CPM
- Kekuatan data:
  - RPM tersedia untuk order analysis.
  - Tersedia 4 peak spectrum.
  - Resolusi FFT dapat dievaluasi (75.00 CPM/line).
  - Metode mounting diketahui: magnet.
  - Operating condition dinyatakan comparable.

## 3. Frekuensi yang Dihitung

- Running speed: 1480 CPM / 24.67 Hz
- Blade/Vane pass: 17760.00 CPM (296.00 Hz)
- Electrical-related frequencies:
  - 1X_line: 3000.00 CPM
  - 2X_line: 6000.00 CPM
  - synchronous_speed: 1500.00 CPM
  - pole_pass: 80.00 CPM

## 4. Observasi Spectrum

- Dominant peak: 1480.00 CPM (24.67 Hz), order 1.00X, amplitude 4.5.
- Integer running-speed harmonics terdeteksi: 3
- Match expected frequencies:
  - BPF/VPF: expected 17760.00 CPM, measured 17760.00 CPM, amplitude 0.18
  - 1X_line: expected 3000.00 CPM, measured 2960.00 CPM, amplitude 0.65 — AMBIGU dengan 2X running speed (2960.0 CPM) pada resolution saat ini

## 5. Diagnosis Diferensial

### 1. Rotor / mass unbalance
- Confidence: **85% (kuat)**
- Raw evidence score: 0.85
- Bukti mendukung:
  - Peak 1X running speed terdeteksi. [bobot 0.25]
  - 1X adalah peak dominan. [bobot 0.25]
  - Respons radial mendukung unbalance. [bobot 0.15]
  - Phase stabil/repeatable mendukung unbalance. [bobot 0.20]

### 2. Parallel misalignment
- Confidence: **60% (sedang)**
- Raw evidence score: 0.60
- Bukti mendukung:
  - Komponen 1X terdeteksi. [bobot 0.15]
  - Komponen 2X terdeteksi. [bobot 0.25]
  - Respons radial mendukung parallel misalignment. [bobot 0.20]
- Evidence yang masih kurang:
  - Phase radial across coupling.

### 3. Angular misalignment
- Confidence: **30% (rendah)**
- Raw evidence score: 0.30
- Bukti mendukung:
  - Komponen 1X terdeteksi. [bobot 0.15]
  - Komponen 2X terdeteksi. [bobot 0.15]
- Evidence yang masih kurang:
  - Phase axial across coupling.

### 4. Mechanical / structural looseness
- Confidence: **18% (spekulatif)**
- Raw evidence score: 0.18
- Bukti mendukung:
  - Terdeteksi 3 harmonic running speed. [bobot 0.18]
- Evidence yang masih kurang:
  - Inspeksi bolt, base, grout, bearing fit dan structural joint.

### 5. Rotor / seal rub
- Confidence: **18% (spekulatif)**
- Raw evidence score: 0.18
- Bukti mendukung:
  - Harmonic running speed multipel dapat muncul pada rub. [bobot 0.18]
- Evidence yang masih kurang:
  - Waveform dan phase untuk mencari nonlinear contact/rub.

## 6. Severity

- Level: **GOOD / ACCEPTABLE**
- Dasar: Overall masih di bawah alarm site yang diberikan.
- Overall / Alarm 1: 0.73x
- Overall / Alarm 2: 0.47x

## 7. Konfirmasi yang Disarankan

- Ukur phase radial pada kedua bearing dan bandingkan pola antar ujung rotor.
- Periksa resonance/looseness sebelum balancing jika 1X sangat tinggi.
- Ukur radial phase across coupling.
- Lakukan precision alignment + soft-foot check.
- Ukur axial phase pada kedua sisi coupling.
- Lakukan precision alignment check dan soft-foot check.

## 8. Tindakan

- Jika terkonfirmasi, lakukan balancing sesuai konfigurasi rotor.
- Ulangi spectrum, overall dan phase setelah balancing.
- Koreksi alignment jika dikonfirmasi.
- Ulangi radial/axial spectrum dan phase setelah perbaikan.
- Koreksi alignment setelah soft foot dan mechanical looseness diselesaikan.
- Verifikasi 1X/2X dan axial vibration setelah alignment.

## 9. Verifikasi Setelah Perbaikan

- Ulangi pengukuran pada titik, arah, parameter, mounting, FMAX, FFT lines, dan operating condition yang sebanding.
- Bandingkan overall, dominant peaks, harmonics/sidebands, waveform dan phase sebelum vs sesudah repair.
- Dokumentasikan before/after untuk memastikan fault signature turun dan tidak muncul masalah baru.
