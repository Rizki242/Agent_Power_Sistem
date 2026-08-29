# Basis Pengetahuan Training Analisis Vibrasi

> **Sumber:** PDF training analisis vibrasi Technical Associates yang diunggah.
>
> **Tujuan:** basis pengetahuan Markdown terstruktur untuk training, RAG, konteks AI assistant, atau referensi engineering internal.
>
> **Catatan:** PDF sumber berupa hasil scan/gambar. Dokumen ini mempertahankan konsep utama, struktur bab, logika diagnosis, serta tabel teknis yang dapat dibaca dari materi. Diagram dijelaskan dalam bentuk teks bila memungkinkan.

---

## Dokumen Sumber

1. `1.0 Introduction.pdf`
2. `1.1 Analysis 1 - seminar overview.pdf`
3. `1.2 What is vibration.pdf`
4. `1.3 Overview of the strengths.pdf`
5. `1.4 Overview of various vibration.pdf`
6. `1.5 Role of spike energy.pdf`
7. `1.6 use of vibration signature.pdf`
8. `1.7 Proven method for specifying.pdf`
9. `1.8 Common in pitfalls in everyday.pdf`
10. `1.9 Setup and implementation of effective PDM.pdf`
11. `1.10 Actual case histories.pdf`
12. `rotor asses1.pdf`

> **Mode penggunaan sebagai skill agen:** pengetahuan sumber dipakai untuk menjelaskan, menghitung, dan membangun hipotesis diagnosis. Agen tidak boleh mengubah satu pola spektrum menjadi diagnosis pasti tanpa cross-check terhadap RPM, arah pengukuran, waveform, phase, trend, konfigurasi mesin, dan kondisi operasi.

---

# 1. Gambaran Umum Seminar Analysis I

## 1.1 Tujuan Predictive Maintenance

Program **Predictive Maintenance (PMP)** yang efektif dibangun sebagai urutan logis:

1. **Deteksi (Detection)**
2. **Analisis (Analysis)**
3. **Koreksi (Correction)**
4. **Verifikasi (Verification)**

Program pertama-tama mendeteksi awal timbulnya masalah pada mesin, kemudian menentukan penyebab yang paling mungkin, mendukung tindakan korektif yang efektif dan efisien, lalu memverifikasi bahwa tindakan tersebut benar-benar menyelesaikan masalah tanpa menimbulkan masalah baru.

Analisis vibrasi digunakan untuk mengikuti kondisi komponen mesin dengan memantau perubahan level vibrasi dan **vibration signature** dari waktu ke waktu.

## 1.2 Baseline dan Pengukuran Tindak Lanjut

Predictive maintenance biasanya dimulai dengan **baseline survey** atau pengukuran awal mesin. Pengukuran berikutnya dilakukan pada interval yang ditentukan berdasarkan faktor seperti:

- jenis mesin,
- tingkat kekritisan,
- biaya operasi dan pemeliharaan,
- kecepatan operasi,
- jenis bearing,
- jenis gear,
- desain mesin,
- duty atau pola pelayanan mesin.

Analis membandingkan data saat ini dengan baseline dan data historis, mengevaluasi perubahan, lalu mendokumentasikan kesimpulan dalam laporan kondisi.

## 1.3 Kesimpulan Kondisi yang Umum

Hasil survey dapat menghasilkan kesimpulan seperti:

1. **Tidak ditemukan masalah.**
2. **Masalah kecil** — lanjutkan trending pada interval survey normal.
3. **Masalah berpotensi serius** — perpendek interval monitoring karena kerusakan dapat berkembang.
4. **Masalah berpotensi serius tetapi sumber belum terkonfirmasi** — lakukan diagnosis vibrasi tambahan.
5. **Masalah signifikan** — rencanakan tindakan korektif, umumnya pada scheduled shutdown berikutnya.
6. **Masalah sangat berat** — dapat memerlukan tindakan korektif segera atau shutdown.

## 1.4 Verifikasi Setelah Perbaikan

Tindakan korektif bukan akhir dari proses diagnosis. Setelah perbaikan:

- ulangi pengukuran vibrasi,
- ulangi analisis diagnostik,
- pastikan signature kerusakan awal hilang atau menurun,
- pastikan tidak muncul masalah baru,
- dokumentasikan tanggal dan tindakan perbaikan,
- simpan data **sebelum (before)** dan **sesudah (after)** perbaikan.

Dokumentasi before/after merupakan bagian penting dari program condition monitoring yang matang.

## 1.5 Cakupan Training

Materi seminar mencakup:

- dasar-dasar vibrasi,
- time waveform dan frequency spectrum,
- displacement, velocity, dan acceleration,
- phase,
- instrumentasi vibrasi,
- pemilihan transducer,
- Spike Energy, HFD, dan Shock Pulse,
- vibration signature analysis,
- spectral alarm bands,
- kesalahan umum dalam pengukuran,
- implementasi program predictive maintenance,
- contoh diagnosis mesin dari kondisi nyata.

---

# 2. Apa Itu Vibrasi dan Bagaimana Digunakan untuk Mengevaluasi Kondisi Mesin?

## 2.1 Definisi Dasar

Vibrasi adalah gerakan osilasi mesin atau komponen mesin di sekitar posisi referensi atau posisi netral.

Model mekanis sederhana terdiri dari:

- massa,
- pegas atau stiffness,
- gaya yang bekerja,
- tahanan terhadap gerakan.

Materi training menyatakan hubungan dasarnya secara konseptual sebagai:

**Respons amplitudo vibrasi berbanding lurus dengan gaya dinamis dan berbanding terbalik dengan tahanan dinamis.**

Artinya, vibrasi dapat meningkat karena gaya eksitasi bertambah, stiffness/damping mesin berubah, atau keduanya terjadi bersamaan.

## 2.2 Time Waveform

**Time waveform** menampilkan amplitudo vibrasi terhadap waktu.

Time waveform menunjukkan bagaimana mesin bergerak pada setiap siklus dan berguna untuk mengenali:

- impact,
- modulation,
- looseness,
- rubbing,
- bentuk gelombang non-sinusoidal,
- transient event,
- pola berulang yang mungkin tidak terlihat hanya dari overall vibration.

## 2.3 Frekuensi

Frekuensi adalah jumlah siklus vibrasi lengkap per satuan waktu.

Satuan yang umum:

- **Hz** = cycle per second,
- **CPM** = cycle per minute.

Konversi:

```text
1 Hz = 60 CPM
Frequency (Hz) = CPM / 60
Frequency (CPM) = Hz × 60
```

Pada rotating machinery, frekuensi sering dinyatakan terhadap shaft speed:

```text
1X = frekuensi putaran shaft
2X = dua kali frekuensi shaft
3X = tiga kali frekuensi shaft
...
```

## 2.4 Displacement

Displacement mengukur besarnya perpindahan fisik dari satu posisi ke posisi lain.

Satuan yang umum:

- mils peak-to-peak,
- micrometer peak-to-peak.

Displacement sangat berguna pada frekuensi rendah dan untuk pengukuran shaft-relative.

## 2.5 Velocity

Velocity adalah laju perubahan displacement terhadap waktu.

Satuan umum:

- in/s,
- mm/s.

Velocity banyak digunakan untuk penilaian severity mesin secara umum karena memberikan respons yang baik pada rentang frekuensi menengah yang luas.

## 2.6 Acceleration

Acceleration adalah laju perubahan velocity.

Satuan yang umum:

- g,
- in/s²,
- m/s².

Acceleration sangat efektif untuk vibrasi frekuensi tinggi dan fenomena yang berkaitan dengan impact.

Hubungan ketiga parameter dapat diringkas sebagai:

```text
Displacement --diferensiasi--> Velocity --diferensiasi--> Acceleration
Acceleration --integrasi-----> Velocity --integrasi-----> Displacement
```

## 2.7 Phase

Phase menggambarkan perbedaan waktu relatif antara suatu sinyal vibrasi dengan sinyal referensi.

Phase biasanya dinyatakan dalam derajat:

- 0° = gerakan terjadi bersamaan,
- 90° = satu sinyal bergeser seperempat siklus,
- 180° = gerakan berlawanan,
- 360° = satu siklus penuh.

Phase merupakan parameter diagnostik penting untuk membedakan mekanisme kerusakan yang menghasilkan peak spektrum serupa.

## 2.8 Frequency Spectrum / FFT / Vibration Signature

Frequency spectrum menampilkan amplitudo vibrasi terhadap frekuensi.

FFT memisahkan time waveform yang kompleks menjadi komponen sinusoidal individual. Dengan demikian analis tidak hanya melihat total gerakan, tetapi dapat melihat amplitudo pada frekuensi tertentu.

Materi sumber menyebut frequency spectrum sebagai **vibration signature** karena jenis kerusakan mekanis yang berbeda cenderung menghasilkan pola frekuensi yang khas.

## 2.9 Time Domain vs Frequency Domain

### Time domain berguna untuk:

- timing impact,
- bentuk waveform,
- transient event,
- modulation,
- repeated impacts,
- perilaku non-periodik.

### Frequency domain berguna untuk:

- memisahkan beberapa sumber vibrasi yang terjadi bersamaan,
- mengidentifikasi running-speed harmonics,
- bearing defect frequency,
- gear mesh frequency,
- sideband,
- komponen resonansi,
- frekuensi elektris.

Diagnosis yang kuat menggunakan **keduanya**, bukan hanya salah satu.

## 2.10 Frequency Resolution dan Setup FFT

Akurasi FFT dipengaruhi oleh pengaturan seperti:

- frequency span / maximum frequency,
- jumlah FFT lines,
- sample size,
- window function,
- averaging,
- sampling rate.

Resolusi yang buruk dapat membuat peak yang berdekatan menyatu dan sideband sulit terlihat.

Frequency span yang terlalu lebar juga dapat mengurangi detail diagnosis pada area frekuensi yang sebenarnya ingin dianalisis.

## 2.11 Windowing

Window function digunakan untuk mengurangi **spectral leakage** ketika data time record tidak berisi jumlah siklus integer yang tepat.

Pemilihan window memengaruhi:

- akurasi amplitudo,
- resolusi frekuensi,
- leakage,
- kemampuan memisahkan peak yang berdekatan.

## 2.12 Kegunaan Pengukuran Phase

Pengukuran phase sangat berguna untuk:

- diagnosis unbalance,
- membedakan force unbalance dan couple unbalance,
- misalignment,
- bent shaft,
- resonance,
- looseness,
- rotor rub,
- soft foot,
- Operating Deflection Shape (ODS).

---

# 3. Kelebihan dan Kelemahan Instrumen Vibrasi

## 3.1 Kategori Instrumen

Materi training membagi instrumen vibrasi ke dalam lima kelompok utama:

1. **Overall-level vibration meter**
2. **Swept-filter analyzer**
3. **FFT data collector**
4. **Real-time spectrum analyzer**
5. **Instrumentation-quality tape/data recorder**

## 3.2 Kriteria Evaluasi Instrumen

Saat membandingkan instrumen, pertimbangkan:

- portability,
- frequency range,
- format pengukuran data,
- jenis display,
- jenis transducer,
- kemampuan strobe/phototach,
- kemampuan multi-channel,
- Spike Energy/HFD/Shock Pulse,
- high-frequency enveloped spectrum,
- kecepatan update spectrum,
- kemudahan penggunaan,
- penyimpanan time waveform,
- penyimpanan frequency spectrum,
- kompatibilitas predictive-maintenance software,
- natural-frequency testing,
- Operating Deflection Shape,
- modal analysis,
- synchronous time averaging,
- waterfall/cascade plotting,
- biaya.

## 3.3 Overall-Level Vibration Meter

### Kelebihan

- sederhana,
- portable,
- cepat,
- relatif murah,
- berguna untuk screening dan route measurement.

### Kelemahan

Overall level hanyalah satu nilai broadband sehingga tidak menunjukkan frekuensi mana yang menghasilkan vibrasi.

Akibatnya, beberapa kerusakan berbeda dapat menghasilkan nilai overall yang hampir sama.

Kerusakan lokal berfrekuensi tinggi juga dapat berkembang tanpa menyebabkan kenaikan besar pada overall reading.

## 3.4 Swept-Filter Analyzer

Instrumen ini digunakan sebelum FFT data collector modern menjadi umum. Prinsipnya menggunakan tunable filter yang menyapu suatu rentang frekuensi.

### Kelebihan

- memberikan informasi berdasarkan frekuensi,
- berguna untuk field balancing,
- berguna untuk studi resonance,
- memberikan informasi diagnosis lebih baik daripada overall meter.

### Kelemahan

- lebih lambat daripada FFT,
- sangat bergantung pada operator,
- kurang praktis untuk route collection rutin,
- penyimpanan dan otomatisasinya terbatas dibanding sistem modern.

## 3.5 FFT Programmable Data Collector

FFT data collector merupakan alat utama dalam program predictive-maintenance modern.

### Kelebihan

- acquisition spectrum cepat,
- route tersimpan,
- histori mesin tersimpan,
- automatic measurement setup,
- penyimpanan waveform,
- banyak parameter vibrasi,
- kompatibel dengan predictive-maintenance software,
- trend analysis,
- field diagnostics.

Perangkat tertentu juga mendukung:

- spike-energy spectrum,
- amplitude-demodulated spectrum,
- acceleration-enveloped spectrum,
- high-frequency measurement.

## 3.6 Real-Time Spectrum Analyzer

Real-time analyzer memberikan update spectrum sangat cepat dan dapat menampilkan perubahan vibrasi secara terus-menerus.

### Kelebihan

- sangat baik untuk dynamic troubleshooting,
- transient capture,
- run-up/coastdown,
- natural-frequency testing,
- multi-channel phase measurement,
- pengamatan spectrum secara real-time.

### Kelemahan

- umumnya lebih mahal,
- kurang praktis untuk route besar dibanding portable collector,
- membutuhkan kemampuan pengguna yang lebih tinggi.

## 3.7 Instrumentation-Quality Recorder

Recorder menyimpan sinyal vibrasi mentah untuk dianalisis kemudian.

### Kelebihan

- mempertahankan sinyal asli,
- memungkinkan post-processing berulang,
- berguna untuk transient atau kejadian yang sulit diulang,
- berguna untuk multi-channel data collection,
- memungkinkan pengaturan analisis berbeda diterapkan setelah pengambilan data.

Digital recorder umumnya memiliki dynamic range dan frequency response lebih baik dibanding analog recorder lama.

---

# 4. Transducer Vibrasi dan Pemilihannya

## 4.1 Jenis Utama Transducer

Materi training menjelaskan empat keluarga transducer utama:

1. **Accelerometer**
2. **Velocity pickup**
3. **Non-contact eddy-current displacement probe**
4. **Shaft-contact displacement probe**

Pemilihan transducer bergantung pada:

- kecepatan mesin,
- expected fault frequency,
- konstruksi mesin,
- parameter yang ingin diukur,
- metode mounting,
- temperature,
- environmental condition,
- frequency response,
- sensitivity,
- measurement range.

## 4.2 Accelerometer

Accelerometer mengukur acceleration secara langsung dan merupakan transducer portable yang paling umum digunakan.

Konstruksi tipikal menggunakan elemen piezoelectric dan seismic mass.

Jenisnya meliputi:

- compression type,
- inverted compression type,
- shear type.

### Kelebihan

- frequency range luas,
- ukuran kecil,
- ringan,
- respons frekuensi tinggi sangat baik,
- cocok untuk diagnosis bearing dan gear,
- dapat diintegrasikan menjadi velocity atau displacement jika sesuai.

### Hal yang Harus Diperhatikan

- sensitivity (mV/g),
- resonant frequency,
- mounted resonance,
- temperature rating,
- electrical noise,
- kondisi kabel,
- mounting stiffness,
- performa frekuensi rendah.

## 4.3 ICP / Integrated Electronics Accelerometer

Banyak accelerometer modern memiliki built-in electronics dan bekerja sebagai sensor low-impedance tipe ICP.

Keuntungannya:

- sensitivitas terhadap cable noise lebih rendah,
- lebih mudah digunakan di lapangan,
- transmisi kabel panjang lebih andal,
- kompatibel dengan banyak portable analyzer.

Sensor tetap harus dipilih sesuai frequency range dan lingkungan pengukuran.

## 4.4 Pengaruh Mounting

Mounting sensor sangat memengaruhi usable frequency response.

Metode mounting yang umum:

- stud mount,
- adhesive mount,
- magnetic mount,
- hand-held probe.

Secara umum, mounting permanen yang kaku memberikan respons high-frequency dan repeatability terbaik.

Untuk trending, pengukuran harus dilakukan pada **lokasi fisik dan orientasi yang sama** setiap kali.

## 4.5 Velocity Pickup

Velocity pickup menghasilkan sinyal listrik yang secara langsung proporsional terhadap vibration velocity.

Sensor ini secara tradisional digunakan untuk pengukuran mesin umum pada frequency range menengah.

Dalam sistem modern, acceleration dari accelerometer sering diintegrasikan secara elektronik menjadi velocity, tetapi velocity pickup masih berguna pada aplikasi tertentu.

## 4.6 Non-Contact Eddy-Current Displacement Probe

Probe ini mengukur relative shaft displacement tanpa menyentuh shaft.

Aplikasi umum:

- sleeve-bearing machine,
- turbine-generator,
- compressor,
- rotating shaft berukuran besar,
- shaft orbit analysis,
- shaft centerline position,
- relative vibration measurement.

Sistem biasanya terdiri dari:

- probe,
- extension cable,
- oscillator/demodulator atau proximitor,
- calibrated target material dan gap.

## 4.7 Shaft-Contact Displacement Probe

Contact probe mengukur displacement dengan mengikuti gerakan shaft atau permukaan secara mekanis.

Sensor ini lebih jarang digunakan dalam permanent monitoring modern dibanding non-contact probe, tetapi masih dijumpai pada aplikasi khusus.

## 4.8 Logika Pemilihan Umum

Prinsip praktis dari materi:

- gunakan **displacement** untuk low-frequency atau shaft-relative motion,
- gunakan **velocity** untuk general machinery severity,
- gunakan **acceleration** untuk high-frequency fault detection,
- gunakan **high-frequency technique** untuk deteksi dini impact pada bearing/gear.

Tidak ada satu transducer yang optimal untuk semua mesin dan semua frekuensi kerusakan.

---

# 5. Spike Energy, HFD, dan Shock Pulse

## 5.1 Tujuan

Spike Energy, **High Frequency Detection (HFD)**, dan **Shock Pulse Method (SPM)** digunakan untuk mendeteksi energi frekuensi tinggi akibat repeated mechanical impact dan kerusakan permukaan.

Sangat berguna untuk deteksi dini:

- rolling-element bearing wear,
- lubrication problem,
- gear distress,
- cavitation,
- rubbing atau impact.

## 5.2 Daerah Ultrasonic / High Frequency

Materi sumber menjelaskan metode ultrasonic diagnostic yang bekerja pada daerah puluhan kilohertz.

Spike Energy dan Shock Pulse memanfaatkan resonant response dari sistem pengukuran untuk memperkuat impact berdurasi sangat pendek.

Konsep yang disebutkan dalam materi mencakup resonance sensor pada orde puluhan kHz dan analysis band yang jauh di atas frekuensi running speed normal.

## 5.3 Mengapa Kerusakan Bearing Menghasilkan Frekuensi Tinggi

Ketika permukaan rolling-element bearing mengalami kerusakan, terjadi impact antara permukaan yang rusak dengan rolling element.

Impact ini mengeksitasi natural frequency bearing, housing, dan sensor.

Mekanisme kerusakan yang mungkin:

- micro-spall,
- crack,
- fatigue damage,
- brinelling,
- false brinelling,
- overload,
- stress akibat misalignment,
- poor fit,
- surface roughening akibat lubrication tidak cukup,
- contamination damage,
- electrical-current damage.

## 5.4 Atenuasi Energi Ultrasonic

Energi impact frekuensi tinggi melemah dengan cepat ketika melewati mechanical interface.

Karena itu:

- ukur sedekat mungkin dengan bearing yang dianalisis,
- gunakan titik pengukuran yang konsisten,
- hindari terlalu banyak interface antara bearing dan sensor.

Sifat lokal ini juga menguntungkan karena bearing yang rusak biasanya memberikan high-frequency response jauh lebih kuat di dekat bearing tersebut daripada di lokasi mesin yang lebih jauh.

## 5.5 Kerusakan yang Dapat Dideteksi Metode High-Frequency Ultrasonic

Materi menyebut sensitivitas terhadap:

- bearing wear,
- poor bearing lubrication,
- cavitation,
- rotor/seal rub,
- belt squeal,
- gear meshing impact,
- sheave rubbing pada guard,
- impact pada reciprocating machine,
- steam leakage,
- high-pressure air flow.

## 5.6 Kerusakan yang Bukan Target Utama

High-frequency/ultrasonic measurement umumnya bukan indikator utama untuk:

- unbalance,
- misalignment,
- bent shaft,
- electrical problem,
- eccentric rotor,
- resonance,
- structural looseness/weakness,
- beat vibration.

Kerusakan tersebut biasanya memberikan informasi lebih kuat di daerah frekuensi rendah.

## 5.7 Spike Energy

Spike Energy mengubah high-frequency impact excitation menjadi nilai terproses yang sering dinyatakan sebagai **gSE**.

Hal penting:

- nilai sangat dipengaruhi jenis sensor dan mounting,
- lokasi pengukuran harus repeatable,
- accelerometer yang berbeda dapat menghasilkan amplitudo berbeda secara signifikan,
- steam dapat mengganggu sebagian pengukuran spike energy,
- trending paling baik dilakukan dengan sensor dan lokasi mounting yang sama.

## 5.8 Shock Pulse

Shock Pulse adalah metode impact detection yang terutama ditujukan untuk rolling-element bearing.

Keuntungan utamanya adalah deteksi dini bearing distress.

Sebagian implementasi membutuhkan informasi dimensi/jenis bearing untuk menentukan reference level.

## 5.9 High Frequency Detection (HFD)

HFD berbeda dari spike-energy dan shock-pulse berbasis resonance karena dijelaskan sebagai **pengukuran acceleration pada high-frequency band**.

Salah satu rentang yang disebutkan:

```text
5.000 Hz sampai 20.000 Hz
```

Setiap vendor dapat menggunakan lower dan upper cutoff yang berbeda.

HFD sensitif terhadap:

- bearing wear,
- gear wear,
- cavitation,
- high-frequency impact source lainnya.

HFD umumnya tidak sensitif terhadap low-frequency fault seperti:

- unbalance,
- misalignment,
- eccentricity.

## 5.10 Tabel Toleransi Umum Process Machinery

Materi training memberikan korelasi umum untuk process machinery dengan rolling-element bearing:

| Unfiltered Velocity, in/s peak | Shock Pulse / Acoustic Emission, dB | Microlog HFD, g | IRD Spike Energy, gSE | Severity / Status |
|---:|---:|---:|---:|---|
| 1.5+ | 50+ | 5.0+ | 3.0+ | Danger - Shutdown |
| 0.75-1.49 | 40-49 | 3.0-4.99 | 1.50-2.99 | Very Rough - Alert |
| 0.40-0.74 | 30-39 | 1.50-2.99 | 0.80-1.49 | Rough - Alert |
| 0.20-0.39 | 20-29 | 0.75-1.49 | 0.40-0.79 | Fair - Acceptable |
| 0.10-0.19 | 10-19 | 0.30-0.74 | 0.20-0.39 | Good - Acceptable |
| 0.01-0.09 | 1-9 | 0.01-0.29 | 0.01-0.19 | Smooth - Acceptable |

Nilai tersebut merupakan **general guideline**, bukan pengganti baseline khusus mesin dan trend analysis.

---

# 6. Penggunaan Vibration Signature Analysis untuk Diagnosis Kerusakan Mesin

## 6.1 Filosofi Diagnosis

Spectrum tidak boleh didiagnosis hanya dengan mencari satu peak.

Analis harus mempertimbangkan:

1. **Frekuensi apa yang muncul?**
2. **Bagaimana hubungannya dengan running speed?**
3. **Berapa amplitudonya?**
4. **Apakah terdapat harmonics atau sidebands?**
5. **Bagaimana phase relationship-nya?**
6. **Bagaimana pola ini dibandingkan dengan pengukuran sebelumnya?**
7. **Bagaimana desain dan operating condition mesin?**

Frekuensi yang sama dapat muncul pada beberapa jenis fault sehingga konteks dan pattern recognition sangat penting.

## 6.2 Phase sebagai Alat Diagnosis

Materi menekankan bahwa phase sangat kuat untuk membedakan beberapa fault mechanism.

Contoh perilaku phase:

- force/static unbalance → phase hampir sama pada arah radial yang sama,
- couple unbalance → hubungan phase mendekati berlawanan antara kedua ujung rotor,
- bent shaft dan misalignment → karakteristik axial/radial phase tertentu,
- resonance → perubahan phase cepat di sekitar kondisi resonance,
- rotor rub → phase tidak stabil atau berubah-ubah,
- looseness → phase dapat tidak konsisten karena gerakan non-linear.

---

# 7. Signature Diagnosis yang Diilustrasikan

## 7.1 Mass / Force Unbalance

Karakteristik umum:

- dominant **1X running speed**,
- paling kuat pada arah radial,
- spectrum relatif bersih jika unbalance merupakan masalah utama,
- phase stabil dan repeatable.

Gunakan phase untuk membedakan pure force unbalance dari fault 1X lainnya.

## 7.2 Couple Unbalance

Karakteristik:

- **1X** kuat pada kedua ujung rotor,
- radial vibration penting,
- phase relationship antar ujung rotor membantu mengidentifikasi kondisi couple.

## 7.3 Dynamic Unbalance

Dynamic unbalance merupakan kombinasi force dan couple component.

Karakteristik:

- **1X** signifikan,
- radial motion,
- hubungan phase bergantung pada kondisi balance dan lokasi pengukuran.

## 7.4 Overhung Rotor Unbalance

Karakteristik:

- **1X** kuat,
- dapat menghasilkan radial dan axial response yang signifikan,
- phase measurement antar bearing membantu konfirmasi.

## 7.5 Eccentric Rotor

Eccentric rotor dapat menghasilkan 1X kuat meskipun mass balance bukan akar masalah.

Pertimbangkan:

- mechanical eccentricity,
- pulley/sheave eccentricity,
- gear eccentricity,
- rotor-to-stator air-gap variation.

## 7.6 Bent Shaft

Indikasi umum:

- **1X** kuat,
- axial vibration dapat tinggi tergantung lokasi bend,
- phase relationship berbeda dari simple mass unbalance.

## 7.7 Angular Misalignment

Indikasi:

- axial vibration meningkat,
- **1X** kuat dan kadang disertai harmonics,
- characteristic phase difference across coupling.

## 7.8 Parallel Misalignment

Indikasi:

- radial vibration meningkat,
- **1X dan 2X** sering dominan,
- phase relationship across coupling penting.

## 7.9 Misaligned Bearing / Bearing Cocked on Shaft

Bearing yang cocked dapat menimbulkan axial vibration dan harmonics yang menyerupai coupling misalignment.

Pengukuran pada kedua sisi bearing dan perbandingan axial phase membantu membedakan sumbernya.

## 7.10 Resonance

Resonance terjadi ketika excitation frequency mendekati natural frequency.

Gejala penting:

- amplitudo meningkat besar di sekitar resonant frequency,
- sangat sensitif terhadap speed,
- terjadi perubahan phase besar ketika melewati resonance,
- amplification dapat terjadi walaupun excitation force relatif kecil.

Diagnosis resonance sebaiknya mencakup data phase dan speed response, bukan hanya satu spectrum.

---

# 8. Mechanical Looseness

Diagnostic chart membagi mechanical looseness ke beberapa bentuk.

## 8.1 Structural / Base / Frame Looseness

Kemungkinan penyebab:

- loose mounting bolt,
- weak base,
- cracked frame,
- poor grouting,
- foundation weakness.

Karakteristik vibrasi:

- 1X tinggi,
- harmonics,
- directional difference,
- perubahan phase di structural joint.

## 8.2 Bearing Housing atau Rotating-Part Looseness

Internal clearance atau loose fit dapat menghasilkan:

- banyak running-speed harmonic,
- waveform non-linear,
- impact-like signal,
- phase tidak stabil.

## 8.3 Catatan Diagnosis

Looseness sering memperkuat fault lain.

Contoh: mesin unbalance yang juga mengalami looseness dapat menunjukkan harmonic content jauh lebih banyak dibanding mesin yang rigid dengan besar unbalance force yang sama.

---

# 9. Rotor Rub

Rotor rub terjadi ketika bagian rotating bersentuhan dengan stationary part.

Gejala yang mungkin:

- running-speed component,
- harmonics,
- subharmonics,
- broadband energy,
- phase berubah/tidak stabil,
- time waveform non-sinusoidal.

Diagnosis rub harus dikorelasikan dengan:

- machine clearance,
- temperature,
- operating load,
- process condition.

---

# 10. Journal Bearing Problems

Diagnostic chart mencakup kondisi journal bearing seperti:

- oil whirl,
- oil whip,
- instability.

Masalah tersebut dapat menghasilkan **sub-synchronous vibration**, bukan hanya integer running-speed harmonics.

Untuk sleeve-bearing machine, gunakan:

- shaft-relative displacement,
- shaft orbit,
- phase,
- spectrum,
- operating speed,
- bearing design,
- kondisi oil.

---

# 11. Tahapan Kerusakan Rolling-Element Bearing

Materi sumber menjelaskan konsep multi-stage bearing failure.

## Stage 1 — Very Early Defect

- high-frequency ultrasonic/resonance energy meningkat,
- conventional low-frequency spectrum mungkin masih terlihat normal.

Teknik yang berguna:

- Spike Energy,
- HFD,
- Shock Pulse,
- envelope/demodulation.

## Stage 2 — Natural Frequency Mulai Tereksitasi

- impact mengeksitasi resonance bearing dan housing,
- aktivitas high-frequency spectrum semakin jelas.

## Stage 3 — Bearing Defect Frequency Muncul

- discrete bearing defect frequency terlihat,
- harmonic dan sideband dapat muncul,
- severity defect meningkat.

Frekuensi penting:

- **BPFO** — Ball Pass Frequency Outer Race,
- **BPFI** — Ball Pass Frequency Inner Race,
- **BSF** — Ball Spin Frequency,
- **FTF** — Fundamental Train Frequency.

## Stage 4 — Kerusakan Lanjut

- broadband noise meningkat,
- banyak harmonic dapat muncul,
- defect frequency dapat menjadi kurang jelas saat kerusakan sangat berat,
- running-speed vibration dapat meningkat akibat looseness dan mechanical degradation.

---

# 12. Hydraulic dan Aerodynamic Forces

## 12.1 Blade / Vane Pass Frequency

Pump, fan, dan compressor dapat menghasilkan peak pada:

```text
Blade Pass Frequency = jumlah blade × shaft rotational frequency
Vane Pass Frequency  = jumlah vane × shaft rotational frequency
```

Amplitudo blade/vane pass yang tinggi dapat berkaitan dengan:

- hydraulic excitation,
- aerodynamic excitation,
- flow disturbance,
- clearance problem,
- resonance,
- perubahan process condition.

## 12.2 Flow Turbulence

Flow turbulence cenderung menghasilkan broadband/random vibration, bukan hanya satu discrete frequency yang bersih.

## 12.3 Cavitation

Cavitation dapat menghasilkan high-frequency random vibration dan impact energy.

Korelasikan dugaan cavitation dengan:

- suction pressure,
- NPSH condition,
- flow rate,
- valve position,
- process noise,
- high-frequency vibration.

---

# 13. Gear Problems

Diagnostic chart mencakup:

- normal gear mesh,
- tooth wear,
- tooth load,
- gear eccentricity dan backlash,
- gear misalignment,
- cracked/broken tooth,
- hunting-tooth problem,
- gear-assembly phase problem.

## 13.1 Gear Mesh Frequency

```text
GMF = jumlah gigi gear × rotational frequency gear
```

Gearbox normal tetap memiliki komponen GMF, tetapi amplitudo dan sideband structure menentukan apakah respons tersebut abnormal.

## 13.2 Sideband

Sideband di sekitar GMF dapat menunjukkan modulation akibat:

- eccentricity,
- backlash,
- misalignment,
- tooth damage,
- shaft-speed modulation.

Sideband spacing harus dibandingkan dengan rotational frequency gear atau pinion yang terkait.

## 13.3 Cracked atau Broken Tooth

Localized tooth defect dapat menimbulkan periodic impact setiap kali gigi yang rusak masuk mesh.

Time waveform dan synchronous averaging dapat membantu mengisolasi fault ini.

---

# 14. Electric Motor Problems

Diagnostic chart mencakup AC induction motor, synchronous motor, dan DC motor.

Kemungkinan fault:

- stator eccentricity,
- rotor eccentricity,
- loose iron,
- rotor bar problem,
- broken/cracked rotor bar,
- phase imbalance,
- electrical-current effect,
- synchronous magnetic force.

## 14.1 Electrical Frequencies

Analisis vibrasi elektris harus mempertimbangkan:

- line frequency,
- twice-line-frequency,
- slip-related sidebands,
- pole-pass frequency,
- rotor-bar-related component.

Electrical fault harus dibedakan dari mechanical fault dengan membandingkan hubungan frekuensi terhadap:

- line frequency,
- running speed,
- jumlah poles,
- slip frequency,
- load.

---

# 15. Belt Drive Problems

Diagnostic chart mencakup:

- worn/loose/mismatched belt,
- belt/pulley misalignment,
- eccentric pulley,
- belt resonance.

Frekuensi diagnosis dapat mencakup:

- belt rotational frequency,
- pulley rotational frequency,
- harmonics,
- resonance-related component.

Masalah belt harus dikorelasikan dengan:

- kondisi fisik belt,
- belt tension,
- alignment,
- kondisi pulley.

---

# 16. Beat Vibration

Beat vibration terjadi ketika dua frekuensi sangat berdekatan.

Waveform menunjukkan naik-turun amplitudo secara periodik pada **beat frequency**:

```text
Beat Frequency = |F1 - F2|
```

Hal ini dapat terjadi ketika dua mesin beroperasi pada speed sedikit berbeda atau ketika dua excitation source memiliki frekuensi yang sangat dekat.

---

# 17. Soft Foot / Sprung Foot / Foundation Problem

Soft foot terjadi ketika satu atau lebih machine feet tidak menapak secara merata pada base.

Efek yang mungkin:

- frame distortion saat bolt dikencangkan,
- perubahan alignment,
- 1X meningkat,
- 2X atau harmonics meningkat,
- phase tidak stabil,
- coupling stress,
- bearing loading.

Soft foot sebaiknya diperiksa sebelum precision alignment.

---

# 18. Kualitas Pengukuran dan Kesalahan Umum

Diagnosis vibrasi yang andal memerlukan data collection yang repeatable.

Penyebab data menyesatkan antara lain:

- lokasi transducer tidak konsisten,
- orientasi transducer tidak konsisten,
- poor mounting,
- salah frequency range,
- salah measurement parameter,
- FFT resolution tidak cukup,
- maximum frequency tidak sesuai,
- windowing tidak sesuai,
- sampling setup tidak tepat,
- pengukuran dilakukan pada operating condition yang berbeda,
- sensor magnet longgar,
- kabel rusak,
- frequency response sensor tidak mencukupi.

## 18.1 Aturan Repeatability

Untuk trending:

- gunakan titik yang sama,
- gunakan arah yang sama,
- gunakan jenis sensor yang sama,
- gunakan mounting method yang sama,
- gunakan load dan operating condition yang sebanding,
- gunakan analyzer setting yang konsisten.

---

# 19. Workflow Diagnosis yang Direkomendasikan

Gunakan alur berikut ketika menganalisis masalah vibrasi mesin yang belum diketahui.

## Langkah 1 — Konfirmasi Data Mesin

Catat:

- machine speed,
- load,
- process condition,
- bearing type,
- gear tooth count,
- blade/vane count,
- motor pole count,
- line frequency,
- coupling type.

## Langkah 2 — Review Overall Trend

Bandingkan:

- current overall amplitude,
- baseline,
- previous route data,
- alarm level,
- rate of change.

## Langkah 3 — Review Spectrum

Identifikasi:

- 1X,
- 2X,
- higher harmonics,
- subharmonics,
- bearing defect frequency,
- GMF,
- blade/vane pass,
- electrical frequency,
- sideband,
- broadband/high-frequency energy.

## Langkah 4 — Review Time Waveform

Cari:

- impact,
- clipping,
- modulation,
- looseness,
- rub,
- repeating defect.

## Langkah 5 — Gunakan Phase Bila Dibutuhkan

Gunakan phase untuk:

- unbalance,
- misalignment,
- bent shaft,
- resonance,
- looseness,
- structural motion.

## Langkah 6 — Bandingkan Arah dan Bearing

Bandingkan:

- horizontal,
- vertical,
- axial,
- inboard vs outboard,
- driver vs driven.

## Langkah 7 — Korelasikan dengan Fisika Mesin

Jangan mendiagnosis hanya berdasarkan pola.

Pastikan frekuensi yang dicurigai secara fisik memang dapat dihasilkan oleh komponen yang dianggap sebagai sumber kerusakan.

## Langkah 8 — Tentukan Severity

Gunakan:

- amplitude,
- trend rate,
- machine criticality,
- process risk,
- fault type,
- operating history,
- machine-specific alarm limit.

## Langkah 9 — Rekomendasikan Tindakan

Tindakan dapat berupa:

- lanjutkan monitoring normal,
- perpendek interval monitoring,
- lakukan additional diagnostic,
- inspeksi komponen,
- lubrication,
- alignment,
- balancing,
- perbaiki looseness,
- rencanakan outage repair,
- shutdown bila severity dan risk mengharuskan.

## Langkah 10 — Verifikasi Setelah Perbaikan

Ulangi measurement setelah corrective action dan dokumentasikan kondisi before/after.

---

# 20. Referensi Diagnosis Cepat

| Kondisi | Petunjuk Signature yang Umum | Konfirmasi yang Berguna |
|---|---|---|
| Unbalance | Dominant 1X, terutama radial | Stable phase, balance test |
| Couple unbalance | 1X pada kedua ujung | End-to-end phase |
| Misalignment | 1X/2X, axial dan/atau radial | Phase across coupling |
| Bent shaft | 1X kuat, sering ada axial influence | Axial phase pattern |
| Looseness | Multiple harmonics, waveform non-linear | Inspeksi bolt/base, phase |
| Resonance | Amplitudo besar dekat natural frequency | Phase shift, run-up/coastdown |
| Rotor rub | Harmonic/subharmonic/broadband | Time waveform, unstable phase |
| Rolling bearing defect | High-frequency energy, defect frequencies | Envelope/HFD/Spike Energy |
| Oil whirl/whip | Sub-synchronous vibration | Shaft orbit, speed relationship |
| Gear defect | GMF + harmonic/sideband | Tooth inspection, waveform |
| Cavitation | Random/high-frequency vibration | Process/NPSH correlation |
| Blade/vane pass | Blade/vane count × RPM | Process dan clearance |
| Belt problem | Belt frequency/pulley component | Kondisi dan alignment belt |
| Electrical motor fault | Line/slip/pole-related frequency | Current spectrum dan load |
| Soft foot | 1X/2X dan alignment sensitivity | Foot-lift test |

---

# 21. Prinsip Utama Training

1. **Trend lebih kuat daripada satu isolated reading.**
2. **Frekuensi membantu mengidentifikasi sumber; amplitudo membantu menilai severity.**
3. **Phase sangat penting ketika beberapa fault menghasilkan frekuensi yang sama.**
4. **Time waveform dan FFT sebaiknya digunakan bersama.**
5. **Metode high-frequency sangat baik untuk deteksi dini impact bearing/gear, tetapi bukan pengganti conventional vibration analysis.**
6. **Sensor mounting dan repeatability pengukuran langsung memengaruhi kualitas diagnosis.**
7. **Geometri mesin dan fisika operasi harus mendukung diagnosis.**
8. **Program predictive maintenance yang baik berakhir dengan verifikasi setelah perbaikan.**

---

# 22. Struktur yang Disarankan untuk Training AI / RAG

Jika file ini digunakan sebagai knowledge base AI vibration-analysis assistant, gunakan urutan reasoning:

```text
INPUT DATA MESIN
        ↓
IDENTIFIKASI RUNNING SPEED DAN COMPONENT FREQUENCY
        ↓
REVIEW OVERALL TREND
        ↓
REVIEW FFT SPECTRUM
        ↓
REVIEW TIME WAVEFORM
        ↓
CHECK PHASE / DIRECTION / LOCATION
        ↓
COCOKKAN SIGNATURE DENGAN PHYSICAL FAILURE MODE
        ↓
EVALUASI SEVERITY + TREND + CRITICALITY
        ↓
REKOMENDASIKAN CONFIRMATION TEST
        ↓
REKOMENDASIKAN MAINTENANCE ACTION
        ↓
VERIFIKASI SETELAH PERBAIKAN
```

## 22.1 Data Input Minimum untuk Diagnosis Otomatis

```yaml
mesin:
  nama:
  tipe:
  rpm:
  beban_persen:
  frekuensi_line_hz:
  jumlah_pole_motor:
  tipe_bearing:
  model_bearing:
  jumlah_gigi_driver:
  jumlah_gigi_driven:
  jumlah_blade_atau_vane:

pengukuran:
  titik:
  arah: horizontal | vertical | axial
  parameter: displacement | velocity | acceleration
  satuan:
  overall:
  fmax:
  fft_lines:
  waveform_tersedia: true | false
  phase_tersedia: true | false

peak_spectrum:
  - frekuensi_hz:
    order_x:
    amplitudo:

high_frequency:
  spike_energy_gse:
  hfd_g:
  shock_pulse_db:

histori:
  overall_sebelumnya:
  overall_baseline:
  trend_rate:
```

## 22.2 Template Output Diagnosis AI

```yaml
diagnosis:
  fault_utama:
  confidence:
  bukti:
    - pola_spectrum
    - pola_waveform
    - phase_relationship
    - trend
    - geometri_mesin

severity:
  level:
  alasan:

rekomendasi_konfirmasi:
  - test

rekomendasi_tindakan:
  - tindakan

interval_monitoring:

verifikasi_setelah_perbaikan:
  diperlukan: true
```

---

---

# 23. Metode Menentukan Spectral Alarm Band dan Narrowband Alarm

Bagian ini merangkum Chapter 7 dari materi sumber. Tujuannya adalah agar alarm tidak hanya bergantung pada **overall vibration**, tetapi juga mampu menangkap kenaikan energi pada kelompok frekuensi tertentu.

## 23.1 Dua Jenis Alarm Spektral

Materi membedakan dua konsep utama:

### A. Absolute threshold / narrowband peak alarm

Alarm aktif jika **satu peak** di dalam band sama dengan atau melewati batas amplitudo yang ditentukan.

Cocok ketika fault memiliki discrete frequency yang jelas.

### B. Power-band alarm

Alarm ditentukan dari **energi total semua FFT lines** di dalam sebuah band. Dengan cara ini, beberapa peak kecil dapat bersama-sama menaikkan band meskipun tidak ada satu peak yang melewati absolute threshold.

Untuk Hanning Window, materi memberikan:

```text
OA = sqrt( Σ(A_i²) / N_BF )
N_BF = 1.5 untuk Hanning Window

sehingga:
OA ≈ 0.8165 × sqrt(Σ(A_i²))
```

Keterangan:

- `OA` = overall level dari spectrum atau band,
- `A_i` = amplitudo setiap FFT line,
- `N_BF` = noise bandwidth factor window.

### Python

```python
from vibration_calculations import spectral_band_overall

amplitudo = [0.02, 0.04, 0.03, 0.01]  # satuan harus konsisten
band_oa = spectral_band_overall(amplitudo, noise_bandwidth=1.5)
print(band_oa)
```

**Aturan agen:** jangan menjumlahkan amplitudo FFT secara linear untuk mendapatkan overall band. Gunakan root-sum-square yang dikoreksi noise bandwidth sesuai metode sumber.

## 23.2 Overall Alarm Statistik dari Data Historis

Dalam materi sumber, level **ALARM 1** dibangun dari statistik populasi mesin sejenis:

```text
ALARM 1 = rata-rata + 3 × standar deviasi
ALARM 2 = 1.5 × ALARM 1
```

Materi juga menjelaskan pembulatan level overall ke increment sekitar `0.025 in/s` untuk sistem yang dibahas.

```python
from vibration_calculations import statistical_alarm_levels

histori = [0.12, 0.13, 0.11, 0.14, 0.12, 0.15, 0.13]
alarm = statistical_alarm_levels(histori)

print(alarm.average)
print(alarm.sigma)
print(alarm.alarm1)
print(alarm.alarm2)
```

**Peringatan penting untuk skill:** angka dan kriteria pada materi adalah metode/starting point dari sumber training. Jangan menggunakannya sebagai batas keselamatan universal untuk semua equipment. Jika user memberikan standar site, OEM, ISO, API, alarm historian, atau baseline spesifik mesin, data tersebut harus diprioritaskan.

## 23.3 Pemilihan Parameter: Displacement, Velocity, Acceleration

Materi Chapter 7 menunjukkan bahwa satu fault dapat terlihat sangat berbeda tergantung parameter yang digunakan.

Rumus sumber untuk sinyal sinusoidal:

```text
V = π D F / 60,000
D = 60,000 V / (π F)
A = D F² / 70,470,910
D = 70,470,910 A / F²
V = 3,690 A / F
A = V F / 3,690
```

Dengan:

- `A` = peak acceleration, g,
- `V` = peak velocity, in/s,
- `D` = peak-to-peak displacement, mils,
- `F` = frequency, CPM.

### Contoh validasi dari tabel sumber

Untuk `D = 1 mil p-p` pada `F = 6000 CPM`:

```python
from vibration_calculations import dva_from_displacement

hasil = dva_from_displacement(1.0, 6000)
print(hasil)
# velocity ≈ 0.314 in/s peak
# acceleration ≈ 0.511 g peak
```

### Implikasi diagnosis

- displacement paling sensitif ke frekuensi rendah,
- velocity merupakan indikator umum yang kuat untuk banyak masalah pada rotating machinery,
- acceleration menjadi lebih informatif pada frekuensi tinggi, gear mesh, bearing impact, dan harmonics tinggi.

Agen harus menghindari kesalahan seperti membandingkan amplitudo acceleration dengan alarm velocity tanpa konversi dan konteks yang benar.

## 23.4 FFT Resolution, FMAX, dan Kemampuan Memisahkan Peak

Salah memilih `FMAX` dapat menyembunyikan kerusakan. Materi Chapter 8 memperlihatkan satu gearbox yang tampak relatif normal pada FMAX rendah, tetapi ketika FMAX diperbesar muncul harmonics bearing defect, gear mesh, dan sidebands.

Dasar perhitungan:

```text
Line Resolution = FMAX / FFT Lines
```

Untuk Hanning Window, contoh sumber menggunakan kemampuan separation sekitar:

```text
Peak Separation ≈ 1.5 × Line Resolution
```

### Contoh dari materi

```text
FMAX = 12,000 CPM
FFT lines = 400
resolution = 30 CPM/line
minimum separation ≈ 45 CPM
```

Dengan 3200 lines:

```text
resolution = 3.75 CPM/line
minimum separation ≈ 5.625 CPM
```

### Python

```python
from vibration_calculations import (
    fft_line_resolution,
    hanning_min_peak_separation,
    required_fft_lines,
)

print(fft_line_resolution(12000, 400))
print(hanning_min_peak_separation(12000, 400))
print(required_fft_lines(12000, desired_peak_separation=10))
```

### Aturan agen saat memilih FMAX

Jangan memilih satu FMAX untuk semua tujuan. Pada kasus tertentu diperlukan minimal dua pengukuran:

1. low FMAX + high resolution untuk membedakan peak yang sangat berdekatan,
2. high FMAX untuk menangkap bearing, gear mesh, rotor bar pass, dan high-frequency phenomena.

Contoh yang dijelaskan pada materi adalah kebutuhan membedakan `2X motor RPM` dari `2X line frequency`, sementara spectrum lain dibutuhkan untuk melihat bearing/gear frequencies yang jauh lebih tinggi.

## 23.5 Enam Spectral Bands: Logika Umum

Materi Chapter 7 memberikan prosedur penggunaan hingga enam band. Detail band bergantung pada tipe mesin, tetapi logika umumnya adalah:

- band rendah untuk running-speed-related vibration,
- band menengah untuk harmonics dan fault mekanis tertentu,
- band tinggi untuk bearing/gear/blade/vane/electrical frequencies,
- batas tidak boleh dibuat hanya karena software menyediakan enam kotak band,
- band harus dibangun berdasarkan **possible fault frequencies** dari konfigurasi mesin.

Agen harus terlebih dahulu menghitung semua frekuensi yang secara fisik mungkin sebelum menyarankan boundary sebuah alarm band.

---

# 24. Kalkulasi Frekuensi Kerusakan untuk Agent

Semua kode berikut tersedia sebagai fungsi reusable di `vibration_calculations.py`.

## 24.1 Running Speed dan Order

```python
from vibration_calculations import order_frequency_cpm, frequency_to_order

rpm = 2980
print(order_frequency_cpm(rpm, 1))  # 1X
print(order_frequency_cpm(rpm, 2))  # 2X
print(frequency_to_order(5960, rpm))
```

Agen harus menyebut frekuensi dalam **Hz, CPM, dan order** jika hal itu membantu pengguna membaca spectrum.

## 24.2 Bearing Defect Frequencies

Rumus pada Illustrated Vibration Diagnostic Chart:

```text
BPFI = Nb/2 × (1 + Bd/Pd × cos θ) × RPM
BPFO = Nb/2 × (1 - Bd/Pd × cos θ) × RPM
BSF  = Pd/(2Bd) × [1 - (Bd/Pd × cos θ)²] × RPM
FTF  = 1/2 × (1 - Bd/Pd × cos θ) × RPM
```

Keterangan:

- `Nb` = jumlah ball/roller,
- `Bd` = diameter ball/roller,
- `Pd` = bearing pitch diameter,
- `θ` = contact angle.

```python
from vibration_calculations import bearing_defect_frequencies

bf = bearing_defect_frequencies(
    rpm=1480,
    number_of_rolling_elements=8,
    rolling_element_diameter=12.0,
    pitch_diameter=60.0,
    contact_angle_deg=0,
)
print(bf)
```

**Aturan diagnosis:** kecocokan satu peak dengan BPFO/BPFI belum cukup. Cari harmonics, sidebands, high-frequency energy, waveform impact, trend, dan konsistensi lokasi bearing.

## 24.3 Gear Mesh Frequency

```text
GMF = jumlah gigi × RPM gear tersebut
```

```python
from vibration_calculations import gear_mesh_frequency_cpm

print(gear_mesh_frequency_cpm(rpm=1200, number_of_teeth=48))
```

Gear mesh normal dapat tetap muncul. Diagnosis abnormal bergantung pada amplitude, harmonics, sidebands, modulation, trend, dan kondisi gigi.

## 24.4 Estimasi Intermediate Shaft Speed Bila Tidak Diketahui

Materi Chapter 7 memberikan pendekatan sementara untuk multistage gearbox jika yang diketahui hanya input speed, output speed, dan jumlah gear mesh.

```text
Speed Increment Factor = Gear Ratio^(1/m)
m = jumlah separate gear meshes
```

Contoh sumber untuk triple reduction gearbox:

```text
Input = 3594 RPM
Output = 230 RPM
Gear ratio = 15.625
m = 3
factor ≈ 2.50
Intermediate #1 ≈ 1438 RPM
Intermediate #2 ≈ 575 RPM
```

```python
from vibration_calculations import estimate_gearbox_shaft_speeds

estimasi = estimate_gearbox_shaft_speeds(3594, 230, 3)
print(estimasi)
```

**Wajib:** hasil ini hanya starting estimate. Begitu actual shaft speed atau tooth count tersedia, agen harus mengganti asumsi tersebut.

## 24.5 Blade / Vane Pass

```text
Blade/Vane Pass Frequency = jumlah blade/vane × RPM
```

```python
from vibration_calculations import blade_or_vane_pass_frequency_cpm
print(blade_or_vane_pass_frequency_cpm(985, 7))
```

## 24.6 Belt Frequency

Case history sumber memberikan:

```text
Belt Frequency = π × Pulley RPM × Pulley Pitch Diameter / Belt Length
```

Diameter dan panjang belt harus dalam satuan panjang yang sama.

```python
from vibration_calculations import belt_frequency_cpm
print(belt_frequency_cpm(1185, pulley_pitch_diameter=8.0, belt_length=80.0))
```

Pada case history, belt defects dapat menghasilkan harmonics seperti 2X belt frequency; namun jangan menganggap setiap 2X belt frequency otomatis berarti belt defect tanpa inspeksi dan korelasi spectrum.

## 24.7 AC Induction Motor: Synchronous, Slip, Pole Pass, Rotor Bar Pass

Diagnostic chart sumber memberikan:

```text
Ns = 120 × FL / P
Fs = Ns - RPM
Fp = Fs × P
RBPF = jumlah rotor bars × RPM
```

Dengan:

- `Ns` = synchronous speed RPM,
- `FL` = electrical line frequency Hz,
- `P` = number of poles,
- `Fs` = slip frequency dalam CPM ketika Ns dan RPM dinyatakan sebagai RPM,
- `Fp` = pole pass frequency CPM,
- `RBPF` = rotor bar pass frequency CPM.

```python
from vibration_calculations import (
    synchronous_speed_rpm,
    slip_frequency_cpm,
    pole_pass_frequency_cpm,
    rotor_bar_pass_frequency_cpm,
)

rpm = 3550
print(synchronous_speed_rpm(60, 2))
print(slip_frequency_cpm(60, 2, rpm))
print(pole_pass_frequency_cpm(60, 2, rpm))
print(rotor_bar_pass_frequency_cpm(rpm, 44))
```

Agen harus membedakan running-speed harmonics dengan electrical synchronous frequencies menggunakan resolution yang memadai.

---

# 25. Common Pitfalls dalam Pengukuran Vibrasi

Chapter 8 menekankan bahwa diagnosis bagus tidak mungkin lahir dari data yang buruk.

## 25.1 Lokasi Pengukuran

Prinsip yang harus diikuti agen ketika mengevaluasi kualitas dataset:

- titik sedekat mungkin dengan bearing,
- prioritaskan load zone bila relevan,
- horizontal sedekat mungkin dengan horizontal shaft centerline,
- vertical sedekat mungkin dengan vertical shaft centerline,
- axial sejajar shaft dan **lokasinya harus sama pada setiap survey**,
- jangan keliru mengambil titik pada seal padahal yang dimaksud bearing,
- hindari thin/weak sheet metal jika tujuannya adalah bearing/machine vibration,
- jangan mengorbankan keselamatan; permanent transducer lebih tepat pada titik berbahaya.

## 25.2 Naming Convention untuk Database Agent

Contoh konvensi materi:

```text
Motor outboard bearing  -> 1
Motor inboard bearing   -> 2
Driven inboard bearing  -> 3
Driven outboard bearing -> 4

A = Axial
H = Horizontal
V = Vertical
```

Untuk vertical machine, dua radial directions harus diberi orientasi plant seperti North/South dan East/West atau convention yang konsisten.

### Data model skill

```yaml
measurement_point:
  bearing_number: 1
  component: motor
  position: outboard
  direction: horizontal
  plant_direction: null
  parameter: velocity
  unit: mm/s_rms
```

Agen harus menolak trending langsung jika titik pengukuran historis ternyata berbeda secara fisik.

## 25.3 Marking dan Machine Drawing

Database condition monitoring idealnya memiliki:

- machine name yang sama dengan physical label,
- point label permanen,
- machine drawing,
- bearing model,
- RPM range,
- gear tooth count,
- blade/vane count,
- machine location map.

Informasi tersebut bukan administratif semata; data ini diperlukan untuk menghitung expected frequencies.

## 25.4 FMAX yang Terlalu Rendah

Materi menunjukkan contoh gearbox di mana:

- FMAX rendah hanya menunjukkan running-speed-related components,
- FMAX lebih tinggi mulai menunjukkan harmonics gearbox,
- FMAX sekitar 240,000 CPM mengungkap beberapa BPFO harmonics dan FTF sidebands,
- FMAX lebih tinggi lagi memperlihatkan GMF,
- spectrum acceleration high-frequency mengungkap 2X dan 3X GMF serta sidebands yang tidak terlihat pada spectrum velocity rendah.

**Kesimpulan skill:** jika user mengunggah spectrum dan meminta diagnosis, agen harus melihat FMAX sebelum menyatakan “tidak ada bearing/gear problem”.

## 25.5 Transducer dan Mounting Dapat Membuat Fault Palsu atau Menyembunyikan Fault

Sumber memperingatkan:

- probe memiliki natural frequency sendiri,
- di dekat resonance probe, noise floor dapat terangkat secara palsu,
- jauh di atas natural frequency, genuine machine vibration dapat teredam/hilang,
- magnet yang rocking atau walking menghasilkan false impacts/noise,
- loose sensor mount menurunkan usable frequency range dan dapat menghasilkan chattering,
- permukaan harus bersih,
- paint/adhesive dapat mengurangi high-frequency transmission,
- stud mount memberikan jalur terbaik untuk high-frequency response,
- magnetic mount lebih cepat tetapi dapat menurunkan high-frequency amplitude,
- handheld probe sangat sensitif terhadap hand pressure.

Untuk high-frequency bearing analysis, mounting method harus menjadi bagian dari confidence score diagnosis.

## 25.6 Instrument Setup Checklist

Sebelum mempercayai data:

```text
[ ] battery/data collector sehat
[ ] cable sehat
[ ] date/time benar
[ ] sensor sensitivity benar
[ ] parameter dan unit benar
[ ] auxiliary probe terhubung ke input yang benar
[ ] FMAX benar
[ ] FFT lines cukup
[ ] mounting sesuai frequency range
[ ] machine operating condition comparable
[ ] signal sudah settle sebelum disimpan
```

Materi juga mengingatkan adanya **instrument error stack-up** dan variasi akibat analyzer, transducer, calibration, attachment, position, environment, serta steady-state variation. Karena itu, agen tidak boleh menginterpretasikan perubahan amplitudo yang sangat kecil sebagai deterioration tanpa melihat repeatability.

## 25.7 Variasi Antar Pengambil Data

Hasil eksperimen dalam materi menunjukkan bahwa measurement technique, lokasi, sensor mount, dan orang yang mengambil data dapat menambah variability.

Rule untuk agent:

> Semakin kecil perubahan trend dibanding expected measurement variability, semakin rendah confidence bahwa perubahan tersebut benar-benar berasal dari kondisi mesin.

---

# 26. Setup dan Implementasi Program Predictive Maintenance

Chapter 9 membandingkan tiga pendekatan:

- breakdown maintenance,
- regular preventive maintenance,
- condition-based / predictive maintenance.

Condition monitoring bertujuan memberi cukup informasi untuk melakukan maintenance **berdasarkan kondisi aktual**, bukan terlalu cepat atau terlalu lambat.

## 26.1 Recommended Predictive Maintenance Program Flow

Flow chart sumber dapat diubah menjadi workflow agent berikut:

```text
1. Tentukan kompetensi/penanggung jawab PMP
        ↓
2. Siapkan hardware + software
        ↓
3. Pilih mesin yang masuk program
        ↓
4. Pilih teknik condition monitoring optimum
        ↓
5. Tentukan alarm criteria setiap parameter
        ↓
6. Bangun database mesin dan measurement points
        ↓
7. Ambil baseline measurement
        ↓
8. Apakah kondisi mesin acceptable?
   ├─ YA  -> store + trend -> survey berkala -> evaluasi lagi
   └─ TIDAK
        ↓
9. Print/review alarm report + vibration spectra
        ↓
10. Lakukan vibration signature analysis
        ↓
11. Tentukan fault + severity
        ↓
12. Correct faults + document findings
        ↓
13. Ambil baseline/verification baru
```

Agen yang dipakai dalam program ini harus mengikuti loop tersebut. Diagnosis tanpa post-maintenance verification dianggap belum selesai.

## 26.2 Machine Master Data Minimum

```yaml
machine:
  id:
  name:
  area:
  criticality:

  driver:
    type:
    rpm_min:
    rpm_max:
    manufacturer:
    model:
    power_hp:
    bearing_inboard:
    bearing_outboard:
    pulley_pitch_diameter:

  intermediate:
    type:
    ratio:
    input_rpm:
    output_rpm:
    bearing_models: []
    gear_teeth: []

  driven:
    type:
    rpm_min:
    rpm_max:
    bearing_inboard:
    bearing_outboard:
    blade_or_vane_count:

  coupling:
    type:

  electrical:
    line_frequency_hz:
    poles:
    rotor_bars:
```

Jika variabel penting belum ada, skill harus mengatakan **“frekuensi ini belum dapat dihitung karena ...”**, bukan mengarang tooth count/bearing geometry/blade count.

## 26.3 Kondisi dan Prioritas

Report sumber menggunakan kategori kondisi untuk membantu prioritas. Skill dapat mengadopsi konsep generik berikut tanpa menganggap threshold source sebagai universal:

```text
GOOD       -> tidak ada indikasi signifikan; trend normal
FAIR       -> monitor; ada kenaikan/ketidakidealan tetapi belum mendesak
ALARM 3    -> trend / investigate
ALARM 2    -> corrective action segera direncanakan
ALARM 1    -> attention prioritas tinggi / potensi severe
```

Nama severity harus disesuaikan dengan sistem user jika sistem plant menggunakan skala lain.

## 26.4 Rank-Ordered Problem Report

Agen sebaiknya dapat mengurutkan problem machines berdasarkan:

1. consequence/criticality,
2. severity vibrasi,
3. rate of deterioration,
4. confidence diagnosis,
5. ease/urgency corrective action.

Output harus memisahkan:

- **fault hypothesis**,
- **severity**,
- **recommended confirmation test**,
- **recommended corrective action**,
- **verification requirement**.

## 26.5 Estimasi Benefit / Energy Saving dari Contoh Sumber

Materi memberi contoh estimasi sederhana biaya energi:

```text
Annual Cost = HP × 0.746 kW/HP × operating hours × energy tariff
```

Kemudian saving dihitung sebagai persentase reduction dari annual cost.

```python
from vibration_calculations import (
    source_style_annual_energy_cost,
    source_style_energy_saving,
)

annual_cost = source_style_annual_energy_cost(
    motor_hp=66.83,
    annual_hours=8760,
    energy_price_per_kwh=0.046,
    number_of_motors=171,
)

saving = source_style_energy_saving(annual_cost, reduction_percent=1.6)
print(annual_cost, saving)
```

**Catatan:** formula ini adalah gaya estimasi pada materi sumber dan tidak memasukkan detail efficiency/load factor. Jangan menyajikannya sebagai audit energi presisi jika data tersebut tidak tersedia.

---

# 27. Case Histories: Belajar dari Diagnosis Dunia Nyata

Chapter 10 mengelompokkan kasus nyata menjadi:

- unbalance,
- misalignment,
- mechanical looseness,
- rolling-element bearing problems,
- belt-drive problems.

Daftar kasus mencakup blower, air-conditioner supply fan, water scrubber pump, vacuum pump, induced-draft fan, centrifugal compressor, motor, gearbox, process-water equipment, baghouse blower, serta berbagai belt problem.

## 27.1 Case: Air Handler — Unbalance + Belt + Resonance/Support

Kasus menunjukkan mengapa satu mesin dapat memiliki **lebih dari satu fault secara bersamaan**.

Observasi utama yang ditunjukkan materi:

- motor dan fan belt driven,
- fan speed sekitar `427 CPM`,
- axial response di fan sangat tinggi,
- komponen sekitar `2X belt frequency` muncul,
- 1X fan RPM juga besar,
- phase digunakan untuk membedakan dugaan unbalance,
- struktur/support memiliki natural frequency yang dapat memperbesar respons,
- setelah belt replacement, perubahan geometry, dan balancing, vibration turun,
- setelah frame/support diperkuat, response membaik lagi.

Contoh before/after pada salah satu titik yang ditampilkan:

```text
sebelum balancing ≈ 0.444 in/s
sesudah balancing ≈ 0.052 in/s
```

Python:

```python
from vibration_calculations import percent_reduction
print(percent_reduction(0.444, 0.052))  # sekitar 88.3%
```

**Pelajaran agent:** jangan berhenti ketika satu corrective action menurunkan vibrasi. Residual peak dapat menunjukkan fault kedua seperti structural resonance, belt problem, support weakness, atau alignment.

## 27.2 Case: Air Conditioner Supply Fan — Severe Unbalance

Dalam kasus lain:

- motor sekitar `1738 RPM`,
- fan sekitar `720 RPM`,
- horizontal 1X fan vibration mencapai level sangat tinggi,
- balancing dilakukan dengan correction weight sekitar `168 g`,
- outboard fan horizontal turun dari sekitar `1.74 in/s` menjadi sekitar `0.232 in/s`,
- inboard fan horizontal membaik dari sekitar `1.21 in/s` menjadi sekitar `0.448 in/s`,
- residual axial response dikaitkan dengan support/sheave/belt alignment issues.

```python
from vibration_calculations import percent_reduction
print(percent_reduction(1.74, 0.232))
```

Pelajarannya adalah **dominant fault** dapat diperbaiki tetapi mesin masih menyimpan secondary problems.

## 27.3 Case: Water Scrubber Pump — Coupling Misalignment

Materi memperlihatkan trend axial vibration yang meningkat pada sisi motor/pump. Setelah coupling dan alignment diperbaiki, axial vibration turun dan stabil pada level yang lebih dapat diterima.

Pelajaran:

- trend lebih berharga daripada satu snapshot,
- axial vibration harus dibandingkan across coupling,
- wear pada coupling dapat menjadi penyebab/kontributor,
- setelah alignment, lakukan follow-up untuk membuktikan stability.

## 27.4 Case Library untuk Agent

Ketika melakukan diagnosis, agen sebaiknya mencari analogi case history berdasarkan **evidence pattern**, bukan hanya nama mesin.

Contoh query internal:

```text
Apakah ada case dengan:
- dominant 1X radial?
- high axial across coupling?
- multiple running-speed harmonics?
- BPFO/BPFI harmonics + sidebands?
- belt-frequency component?
- high-frequency gear/bearing pattern?
```

Case history adalah pendukung reasoning, bukan rule absolut.

---

# 28. Referensi Pemilihan Accelerometer dari `rotor asses1.pdf`

Tabel sumber menunjukkan contoh **internally amplified general-purpose accelerometers** dan memperlihatkan tradeoff utama antara sensitivity, acceleration range, frequency response, temperature range, weight, dan mounting.

| Model | Sensitivity mV/g | Acceleration Range g | Frequency Response ±5% / ±10% Hz | Temperature °C | Weight g | Mounting |
|---|---:|---:|---|---:|---:|---|
| 756 | 100 | 0.0007–50 | 3–1000 / 2–5000 | -50–90 | 180 | three #8 screws |
| 762 | 10 | 0.0015–500 | 3–10000 / 2–12000 | -50–120 | 80 | 1/4-28 tapped hole |
| 766 | 100 | 0.00055–50 | 3–10000 / 2–12000 | -50–120 | 80 | 1/4-28 tapped hole |
| 768* | 500 | 0.00002–10 | 3–4000 / 2–6000 | -50–120 | 90 | 1/4-28 tapped hole |
| 776 | 100 | 0.0002–40 | 3–2500 / 2–5000 | 0–85 | 32 | 1/4-28 tapped hole |
| 793 | 100 | 0.0007–50 | 3–5000 / 2–7000 | -50–120 | 110 | 1/4-28 tapped hole |
| 793L* | 500 | 0.00001–10 | 0.6–700 / 0.4–1000 | -50–120 | 135 | 1/4-28 tapped hole |
| 793LS | 500 | 0.00001–10 | 0.6–700 / 0.4–1000 | -50–120 | 135 | 1/4-28 tapped hole |
| 793S | 100 | 0.0007–50 | 3–5000 / 2–7000 | -50–120 | 110 | 1/4-28 tapped hole |
| 796 | 100 | 0.0008–50 | 3–5000 / 2–7000 | -50–120 | 100 | 1/4-28 captive screw |

`*` pada tabel sumber menandai **ultra-low-noise sensor**.

## 28.1 Aturan Pemilihan Sensor oleh Agent

Jangan memilih sensor hanya berdasarkan sensitivity paling tinggi.

Evaluasi:

```text
1. frekuensi terendah yang harus dilihat
2. frekuensi tertinggi/fault frequency yang harus dilihat
3. expected amplitude / dynamic range
4. temperature
5. mounting
6. sensor mass vs structure
7. high-frequency transmission path
8. low-noise requirement
```

Untuk low-speed machinery, frequency response pada low end menjadi sangat penting. Untuk bearing/gear high frequency, sensor dan mounting harus memiliki usable high-frequency response yang memadai.

---

# 29. Protocol Operasional Skill untuk Agen

Bagian ini adalah instruksi kerja, bukan materi teori.

## 29.1 Tujuan Agen

Agen harus membantu user:

- membaca FFT spectrum,
- membaca time waveform,
- menghitung expected fault frequencies,
- mengevaluasi trend,
- menilai kualitas data,
- membangun differential diagnosis,
- menyarankan confirmation test,
- menyarankan maintenance action,
- membandingkan before/after repair.

## 29.2 Urutan Reasoning Wajib

```text
A. VALIDASI INPUT
   ↓
B. HITUNG FREKUENSI TEORITIS
   ↓
C. IDENTIFIKASI PEAK + HARMONICS + SIDEBANDS
   ↓
D. PERIKSA WAVEFORM / PHASE / DIRECTION
   ↓
E. PERIKSA TREND
   ↓
F. PERIKSA KUALITAS SENSOR & SETUP
   ↓
G. BANGUN 1–3 HIPOTESIS FAULT
   ↓
H. NILAI CONFIDENCE
   ↓
I. REKOMENDASIKAN CONFIRMATION TEST
   ↓
J. REKOMENDASIKAN ACTION
   ↓
K. VERIFIKASI AFTER REPAIR
```

## 29.3 Aturan Anti-Hallucination

Agen **dilarang**:

- mengarang bearing model,
- mengarang number of balls/rollers,
- mengarang tooth count,
- mengarang rotor-bar count,
- mengarang blade/vane count,
- mengarang RPM jika spectrum tidak memberi dasar cukup,
- menyatakan “bearing rusak” hanya karena overall tinggi,
- menyatakan “normal” ketika FMAX tidak cukup untuk melihat fault frequency,
- membandingkan peak dari parameter/unit berbeda tanpa konversi yang benar.

Jika data kurang:

```text
DATA TIDAK CUKUP UNTUK KONFIRMASI.
Data tambahan yang dibutuhkan:
1. ...
2. ...
3. ...
```

## 29.4 Confidence Score

Gunakan skema konservatif:

```text
0.90–1.00  sangat kuat: beberapa evidence independen konsisten
0.75–0.89  kuat: signature utama + supporting evidence
0.55–0.74  sedang: pattern cocok tetapi data konfirmasi kurang
0.30–0.54  rendah: hanya satu/dua indikasi lemah
<0.30      spekulatif: jangan jadikan diagnosis final
```

Confidence bukan severity. Fault dapat severe tetapi confidence rendah jika data acquisition buruk.

## 29.5 Evidence Weighting

Bukti yang memperkuat diagnosis:

- frequency match yang tepat,
- harmonic structure,
- sideband spacing yang sesuai,
- arah vibrasi sesuai fault mechanism,
- phase relationship sesuai,
- waveform mendukung,
- trend deterioration,
- same fault muncul pada point terkait,
- process condition mendukung,
- physical inspection mendukung.

Bukti yang menurunkan confidence:

- FMAX terlalu rendah,
- resolution buruk,
- probe berada dekat resonance,
- mounting tidak repeatable,
- operating load berbeda,
- RPM berubah dan order tracking tidak dilakukan,
- data hanya satu point,
- unit tidak diketahui.

---

# 30. Format Input Skill yang Direkomendasikan

```yaml
machine:
  name:
  type:
  criticality:
  rpm:
  load_percent:
  line_frequency_hz:
  poles:

geometry:
  bearing:
    model:
    rolling_elements:
    rolling_element_diameter:
    pitch_diameter:
    contact_angle_deg:
  gear:
    teeth: []
    ratio:
    meshes:
  rotor_bars:
  blades_or_vanes:
  belt:
    pitch_diameter:
    length:

measurement:
  date:
  point:
  direction:
  parameter:
  unit:
  overall:
  fmax:
  fft_lines:
  window:
  mounting:
  sensor_model:
  sensor_sensitivity_mv_g:

spectrum_peaks:
  - frequency_hz:
    frequency_cpm:
    amplitude:

waveform:
  available: false
  peak:
  rms:
  crest_factor:

phase:
  available: false
  reference:
  values: []

trend:
  baseline:
  previous:
  current:
```

---

# 31. Format Output Skill yang Direkomendasikan

```yaml
analysis:
  data_quality:
    status: good | limited | poor
    issues: []

  calculated_frequencies:
    running_speed_cpm:
    orders: {}
    bearing: {}
    gear_mesh: []
    blade_vane_pass: []
    electrical: {}
    belt: {}

  observations:
    dominant_peaks: []
    harmonics: []
    sidebands: []
    waveform_features: []
    phase_features: []
    trend_features: []

  differential_diagnosis:
    - fault:
      confidence:
      evidence_for: []
      evidence_against: []

  severity:
    level:
    basis:
    note: "Severity mengikuti alarm/standard yang tersedia, bukan confidence diagnosis."

  required_confirmation:
    - test:
      reason:

  action:
    immediate: []
    planned: []

  verification_after_repair:
    measurements_to_repeat: []
```

---

# 32. Contoh Workflow Agent dari Spectrum

Misalkan user memberikan:

```text
RPM = 1480
peak = 1480, 2960, 4440 CPM
arah = radial
1X jauh paling besar
phase stabil
```

Agen tidak langsung menjawab “unbalance”.

Agen melakukan:

```python
from vibration_calculations import frequency_to_order

rpm = 1480
for f in [1480, 2960, 4440]:
    print(f, frequency_to_order(f, rpm))
```

Kemudian reasoning:

```text
1. Peak berada pada 1X, 2X, 3X.
2. 1X dominan → mendukung unbalance tetapi harmonics memerlukan evaluasi looseness/misalignment.
3. Radial dominance → mendukung unbalance.
4. Stable phase → memperkuat unbalance dibanding rub/looseness yang phase-nya dapat tidak stabil.
5. Periksa mechanical looseness, eccentricity, dan resonance sebelum final.
```

Output terbaik:

```text
Hipotesis utama: rotor unbalance
Confidence: sedang-kuat
Supporting evidence: dominant 1X radial + stable phase
Alternative: looseness/eccentricity/resonance
Confirmation: inspect mounting/base, phase antar bearing, run-up/coastdown bila resonance dicurigai
```

---

# 33. Prinsip Akhir untuk Agent Vibration Analyst

1. **Hitung dulu sebelum menebak.**
2. **Jangan diagnosis dari overall saja.**
3. **Jangan diagnosis dari satu peak saja.**
4. **Spectrum harus dibaca relatif terhadap RPM dan geometri mesin.**
5. **Waveform memberi informasi yang spectrum dapat kehilangan.**
6. **Phase membedakan fault yang mempunyai frequency signature mirip.**
7. **Trend lebih kuat daripada snapshot.**
8. **High-frequency data hanya valid jika sensor + mounting + FMAX mendukung.**
9. **Resolution menentukan apakah dua peak benar-benar dapat dipisahkan.**
10. **Alarm level dan diagnosis adalah dua hal berbeda.**
11. **Corrective action harus diikuti verification measurement.**
12. **Jika data kurang, nyatakan data kurang. Jangan mengarang parameter mesin.**

---

# Akhir Basis Pengetahuan Skill Analisis Vibrasi
