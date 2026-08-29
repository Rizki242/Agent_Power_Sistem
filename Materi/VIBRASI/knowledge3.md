from pathlib import Path

CALC_PY = r'''
import math

try:
    from math import lcm
except ImportError:
    def lcm(a, b):
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // math.gcd(a, b)


# =====================================================================
# Konstanta dasar
# =====================================================================

G_M_S2 = 9.80665
IN_S2_PER_G = 386.089
IN_PER_M = 39.3700787402
MM_PER_IN = 25.4
MICRON_PER_MIL = 25.4

# Referensi dB berdasarkan dokumen Mobius / praktik umum.
# Jika standar internal berbeda, ganti nilai referensi ini.
VD_REF_M_S = 1.0e-8
VD_REF_IN_S_PEAK = 5.568e-7
AD_REF_IN_S2_RMS = 3.861e-4


# =====================================================================
# Konversi frekuensi, speed, order
# =====================================================================

def hz_to_cpm(hz):
    return hz * 60.0


def cpm_to_hz(cpm):
    return cpm / 60.0


def rpm_to_hz(rpm):
    return rpm / 60.0


def hz_to_rpm(hz):
    return hz * 60.0


def order_to_frequency_hz(order, rpm):
    return order * rpm / 60.0


def frequency_hz_to_order(freq_hz, rpm):
    if rpm == 0:
        raise ValueError("rpm tidak boleh nol")
    return freq_hz / (rpm / 60.0)


# =====================================================================
# Konversi amplitudo sinusoidal
# =====================================================================

def peak_to_rms(peak):
    return peak / math.sqrt(2.0)


def rms_to_peak(rms):
    return rms * math.sqrt(2.0)


def pkpk_to_peak(pkpk):
    return pkpk / 2.0


def peak_to_pkpk(peak):
    return peak * 2.0


def pkpk_to_rms_sine(pkpk):
    return pkpk / (2.0 * math.sqrt(2.0))


def rms_to_pkpk_sine(rms):
    return rms * 2.0 * math.sqrt(2.0)


# =====================================================================
# Konversi displacement - velocity - acceleration
# =====================================================================

def displacement_pp_mils_to_velocity_in_s_peak(disp_pp_mils, rpm):
    f_hz = rpm_to_hz(rpm)
    if f_hz == 0:
        return 0.0
    disp_pp_in = disp_pp_mils / 1000.0
    return math.pi * f_hz * disp_pp_in


def velocity_in_s_peak_to_displacement_pp_mils(v_peak_in_s, rpm):
    f_hz = rpm_to_hz(rpm)
    if f_hz == 0:
        raise ValueError("rpm tidak boleh nol")
    return v_peak_in_s / (math.pi * f_hz) * 1000.0


def velocity_rms_in_s_to_displacement_pp_mils(v_rms_in_s, rpm):
    v_peak = rms_to_peak(v_rms_in_s)
    return velocity_in_s_peak_to_displacement_pp_mils(v_peak, rpm)


def displacement_pp_mils_to_velocity_mm_s_peak(disp_pp_mils, rpm):
    v_in_s_peak = displacement_pp_mils_to_velocity_in_s_peak(disp_pp_mils, rpm)
    return v_in_s_peak * MM_PER_IN


def velocity_rms_in_s_to_acceleration_g_rms(v_rms_in_s, rpm):
    f_hz = rpm_to_hz(rpm)
    a_rms_in_s2 = 2.0 * math.pi * f_hz * v_rms_in_s
    return a_rms_in_s2 / IN_S2_PER_G


def acceleration_g_rms_to_velocity_rms_in_s(a_g_rms, rpm):
    f_hz = rpm_to_hz(rpm)
    if f_hz == 0:
        raise ValueError("rpm tidak boleh nol")
    a_rms_in_s2 = a_g_rms * IN_S2_PER_G
    return a_rms_in_s2 / (2.0 * math.pi * f_hz)


def displacement_pp_mils_to_acceleration_g_rms(disp_pp_mils, rpm):
    v_peak = displacement_pp_mils_to_velocity_in_s_peak(disp_pp_mils, rpm)
    v_rms = peak_to_rms(v_peak)
    return velocity_rms_in_s_to_acceleration_g_rms(v_rms, rpm)


# =====================================================================
# Konversi unit dasar
# =====================================================================

def g_to_m_s2(g_value):
    return g_value * G_M_S2


def m_s2_to_g(a_m_s2):
    return a_m_s2 / G_M_S2


def g_to_in_s2(g_value):
    return g_value * IN_S2_PER_G


def in_s2_to_g(a_in_s2):
    return a_in_s2 / IN_S2_PER_G


def mil_to_micron(mils):
    return mils * MICRON_PER_MIL


def micron_to_mil(microns):
    return microns / MICRON_PER_MIL


def inch_to_mm(inch):
    return inch * MM_PER_IN


def mm_to_inch(mm):
    return mm / MM_PER_IN


# =====================================================================
# dB calculation
# =====================================================================

def db10(power_ratio):
    if power_ratio <= 0:
        return float("-inf")
    return 10.0 * math.log10(power_ratio)


def db20(value, reference):
    if reference <= 0:
        raise ValueError("reference harus positif")
    if value == 0:
        return float("-inf")
    return 20.0 * math.log10(abs(value) / reference)


def velocity_db_si(v_m_s, reference=VD_REF_M_S):
    return db20(v_m_s, reference)


def velocity_db_in_peak(v_in_s_peak, reference=VD_REF_IN_S_PEAK):
    return db20(v_in_s_peak, reference)


def acceleration_db_in_rms(a_in_s2_rms, reference=AD_REF_IN_S2_RMS):
    return db20(a_in_s2_rms, reference)


# =====================================================================
# FFT, sampling, resolution, aliasing
# =====================================================================

def frequency_resolution(fmin, fmax, lines):
    if lines <= 0:
        raise ValueError("lines harus lebih besar dari nol")
    return (fmax - fmin) / lines


def fmax_from_resolution(fmin, lines, resolution):
    if lines <= 0:
        raise ValueError("lines harus lebih besar dari nol")
    return fmin + lines * resolution


def lines_required(fmin, fmax, resolution):
    if resolution <= 0:
        raise ValueError("resolution harus lebih besar dari nol")
    return int(math.ceil((fmax - fmin) / resolution))


def minimum_sample_rate(fmax):
    return 2.0 * fmax


def maximum_analyzable_frequency(sample_rate):
    return sample_rate / 2.0


# =====================================================================
# Bearing rolling element frequencies
# =====================================================================

def bearing_defect_orders(n_elements, ball_diameter, pitch_diameter, contact_angle_deg=0.0):
    if n_elements <= 0:
        raise ValueError("jumlah ball/roller harus positif")
    if ball_diameter <= 0 or pitch_diameter <= 0:
        raise ValueError("ball diameter dan pitch diameter harus positif")

    ratio = ball_diameter / pitch_diameter
    cos_beta = math.cos(math.radians(contact_angle_deg))
    c = ratio * cos_beta

    bpi_order = 0.5 * n_elements * (1.0 + c)
    bpo_order = 0.5 * n_elements * (1.0 - c)
    ft_order = 0.5 * (1.0 - c)
    bs_order = (pitch_diameter / (2.0 * ball_diameter)) * (1.0 - c * c)

    return dict(
        BPI=bpi_order,
        BPO=bpo_order,
        FT=ft_order,
        BS=bs_order
    )


def bearing_defect_frequencies(n_elements, ball_diameter, pitch_diameter,
                                contact_angle_deg=0.0, shaft_frequency_hz=1.0):
    orders = bearing_defect_orders(
        n_elements=n_elements,
        ball_diameter=ball_diameter,
        pitch_diameter=pitch_diameter,
        contact_angle_deg=contact_angle_deg
    )

    return dict(
        BPI=orders["BPI"] * shaft_frequency_hz,
        BPO=orders["BPO"] * shaft_frequency_hz,
        FT=orders["FT"] * shaft_frequency_hz,
        BS=orders["BS"] * shaft_frequency_hz
    )


def bearing_rule_of_thumb_orders(n_elements):
    return dict(
        BPI=0.6 * n_elements,
        BPO=0.4 * n_elements
    )


# =====================================================================
# Gear calculations
# =====================================================================

def gear_mesh_frequency(speed, number_of_teeth):
    if number_of_teeth <= 0:
        raise ValueError("jumlah gigi harus positif")
    return speed * number_of_teeth


def gear_output_speed(input_speed, input_teeth, output_teeth):
    if input_teeth <= 0 or output_teeth <= 0:
        raise ValueError("jumlah gigi harus positif")
    return input_speed * input_teeth / output_teeth


def hunting_tooth_frequency(gear_mesh_freq, teeth1, teeth2):
    common = lcm(int(teeth1), int(teeth2))
    if common == 0:
        raise ValueError("jumlah gigi tidak boleh nol")
    return gear_mesh_freq / common


# =====================================================================
# Belt / sheave calculations
# =====================================================================

def driven_sheave_rpm(driving_rpm, driving_diameter, driven_diameter):
    if driven_diameter <= 0:
        raise ValueError("diameter driven harus positif")
    return driving_rpm * driving_diameter / driven_diameter


def belt_rate_frequency(sheave_speed, sheave_diameter, belt_length):
    if sheave_diameter <= 0:
        raise ValueError("diameter sheave harus positif")
    if belt_length <= 0:
        raise ValueError("panjang belt harus positif")
    return math.pi * sheave_speed * sheave_diameter / belt_length


def timing_belt_frequency_from_belt_rate(belt_rate, teeth_on_belt):
    if teeth_on_belt <= 0:
        raise ValueError("jumlah gigi belt harus positif")
    return belt_rate * teeth_on_belt


def timing_belt_frequency_from_sheave(sheave_speed, teeth_on_sheave):
    if teeth_on_sheave <= 0:
        raise ValueError("jumlah gigi sheave harus positif")
    return sheave_speed * teeth_on_sheave


# =====================================================================
# Motor listrik, pole pass, rotor bar
# =====================================================================

def synchronous_speed_rpm(line_frequency_hz, number_of_poles):
    if number_of_poles <= 0:
        raise ValueError("jumlah pole harus positif")
    return 120.0 * line_frequency_hz / number_of_poles


def slip_rpm(synchronous_rpm, actual_rpm):
    return abs(synchronous_rpm - actual_rpm)


def slip_frequency_hz(synchronous_rpm, actual_rpm):
    return slip_rpm(synchronous_rpm, actual_rpm) / 60.0


def pole_pass_frequency_hz(synchronous_rpm, actual_rpm, number_of_poles):
    if number_of_poles <= 0:
        raise ValueError("jumlah pole harus positif")
    return slip_frequency_hz(synchronous_rpm, actual_rpm) * number_of_poles


def rotor_bar_pass_frequency(speed, number_of_bars):
    if number_of_bars <= 0:
        raise ValueError("jumlah rotor bar harus positif")
    return speed * number_of_bars


def twice_line_frequency(line_frequency_hz):
    return 2.0 * line_frequency_hz


# =====================================================================
# Pump / fan blade / vane pass
# =====================================================================

def vane_pass_frequency(speed, number_of_vanes):
    if number_of_vanes <= 0:
        raise ValueError("jumlah vane harus positif")
    return speed * number_of_vanes


def blade_pass_frequency(speed, number_of_blades):
    if number_of_blades <= 0:
        raise ValueError("jumlah blade harus positif")
    return speed * number_of_blades


# =====================================================================
# Reciprocating machine
# =====================================================================

def reciprocating_firing_frequency(speed, stroke_type):
    if stroke_type == 2:
        return speed
    if stroke_type == 4:
        return speed / 2.0
    raise ValueError("stroke_type harus 2 atau 4")


# =====================================================================
# Overall, beats, reliability, amplification, transmissibility
# =====================================================================

def overall_rms_from_spectrum(amplitudes_rms):
    total = 0.0
    for a in amplitudes_rms:
        total += a * a
    return math.sqrt(total)


def beat_frequency(f1, f2):
    return abs(f1 - f2)


def mtbf(total_operating_time, number_of_failures):
    if number_of_failures == 0:
        raise ValueError("jumlah failure tidak boleh nol")
    return total_operating_time / number_of_failures


def mttf(total_operating_time, number_of_failures):
    if number_of_failures == 0:
        raise ValueError("jumlah failure tidak boleh nol")
    return total_operating_time / number_of_failures


def synchronous_amplification_factor(resonant_amplitude, amplitude_above_resonance):
    if amplitude_above_resonance == 0:
        raise ValueError("amplitude di atas resonance tidak boleh nol")
    return resonant_amplitude / amplitude_above_resonance


def transmissibility(output_motion, input_motion):
    if input_motion == 0:
        raise ValueError("input motion tidak boleh nol")
    return output_motion / input_motion


# =====================================================================
# Klasifikasi berbasis threshold dan pemilihan parameter pengukuran
# =====================================================================

def classify_by_threshold(value, thresholds):
    if not thresholds:
        return "Unknown"
    for limit, label in thresholds:
        if value <= limit:
            return label
    return thresholds[-1][1]


def recommended_measurement_parameter(speed_rpm):
    if speed_rpm < 600:
        return "Displacement"
    if speed_rpm <= 120000:
        return "Velocity"
    return "Acceleration"
'''


MD = f"""
# Knowledge.md — Mobius Vibration Training Quick Reference

Dokumen ini dibuat dari isi file **Mobius Vibration Training_under10MB.pdf**.  
Fokus dokumen:

1. Glossary vibration training.
2. Diagnostic guide fault / gejala vibrasi.
3. Useful charts and tables.
4. Semua rumus/perhitungan penting dibuat dalam kode Python.

> Catatan: beberapa chart pada PDF asli berupa grafik/OCR yang tidak sepenuhnya terbaca sebagai angka. Untuk bagian tersebut, dokumen ini mempertahankan struktur, aturan pakai, dan rumus terkait, sementara threshold numerik exact sebaiknya diverifikasi langsung ke grafik asli.

---

## 1. Struktur Dokumen Asli

Dokumen Mobius Vibration Training berisi tiga bagian utama:

1. **Glossary**  
   Daftar istilah vibration analysis.

2. **Diagnostic Guide**  
   Panduan diagnosa fault berdasarkan gejala spectrum, frekuensi dominan, phase, arah pengukuran, dan pola sideband/harmonic.

3. **Useful Charts and Tables**  
   Tabel konversi unit, vibration severity chart, ISO 10816 chart, bearing forcing frequencies, transducer range, dan grafik efektivitas sensor.

---

## 2. Glossary Vibration

Berikut glossary ringkas tetapi detail dari dokumen.

| Term | Definisi / Catatan Penting |
|---|---|
| Absorber | Device untuk mengurangi intensitas vibrasi. |
| Acceleration | Perubahan velocity terhadap waktu. Umumnya dinyatakan dalam g atau m/s2. 1 g = 9.80665 m/s2 = 980.665 cm/s2 = 386.089 in/s2 = 32.174 ft/s2. |
| Accelerometer | Transducer yang menghasilkan sinyal listrik proporsional terhadap acceleration. Piezoelectric accelerometer paling umum digunakan untuk vibrasi mesin. |
| ICP Amplifier | Amplifier built-in pada accelerometer ICP untuk conditioning sinyal. |
| Accuracy | Kedekatan hasil pengukuran terhadap nilai sebenarnya. |
| A/D Converter | Mengubah sinyal analog menjadi digital. |
| Aliasing | High frequency signal muncul sebagai low frequency palsu karena sampling rate tidak cukup. Dicegah dengan anti-aliasing filter. |
| Alignment | Kondisi komponen mesin sesuai design: coincident, parallel, atau perpendicular. Misalignment menyebabkan vibrasi abnormal. |
| Amplification Factor, Synchronous | Rasio amplitude pada resonant peak terhadap amplitude di atas resonance. Menunjukkan sensitivitas rotor terhadap imbalance saat melewati natural frequency. |
| Amplitude | Besaran displacement, velocity, atau acceleration dari posisi diam. Dapat berupa peak, peak-to-peak, atau RMS. |
| Angular Frequency | Frekuensi angular, rad/s atau Hz; sering disebut circular frequency. |
| Anti-Aliasing Filter | Low-pass filter untuk membuang frekuensi di atas setengah sample rate. |
| Anti-Friction Bearing | Lihat rolling element bearing. |
| Asymmetrical Support | Support rotor dengan stiffness tidak sama pada arah radial berbeda. |
| Asynchronous | Komponen vibrasi yang tidak sinkron dengan running speed. |
| Attachment Pad | Pad mounting transducer untuk memastikan transfer vibrasi konsisten dan posisi pengukuran sama. |
| Auto Spectral Density | Acceleration per Hz bandwidth; dikenal juga sebagai PSD. Area di bawah kurva ASD adalah gRMS. |
| Auto Spectrum | Spectrum magnitude tanpa phase; dihasilkan dari RMS averaging. |
| Averaging | Rata-rata spectrum untuk menstabilkan sinyal acak. Linear averaging dan time synchronous averaging penting dalam vibration analysis. |
| Axial | Arah sejajar centerline shaft atau axis rotasi. |
| Balance | Kondisi mass centerline dan rotational centerline coincident. |
| Balancing | Adjust mass distribution rotor agar gaya centrifugal pada bearing berkurang. |
| Band Alarm | Alarm limit pada band frekuensi tertentu, misalnya sekitar 1X, 2X, 3X-6X. |
| Bandwidth | Selisih upper dan lower cutoff frequency. |
| Baseline Spectrum | Spectrum referensi dari mesin dalam kondisi baik. |
| Beats | Variasi amplitude periodik akibat dua frekuensi berdekatan. |
| Beat Frequency | Selisih dua frekuensi yang berdekatan. |
| Bias | Kecenderungan pengukuran terlalu besar atau terlalu kecil secara sistematis. |
| BIN | Bandwidth frekuensi per line of resolution. |
| Blade Pass Frequency | Number of blades/vanes dikalikan shaft rotating frequency. |
| Bode Plot | Plot magnitude dan phase 1X terhadap speed; penting untuk balancing dan critical speed. |
| Bow | Shaft centerline tidak lurus; dapat disebabkan thermal atau mechanical condition. |
| Broadband | Overall vibration level pada range frekuensi lebar. |
| Bump Test | Impact test untuk mencari natural frequency. |
| Calibration | Verifikasi akurasi instrumen dengan input/getaran yang diketahui. |
| Campbell Diagram | Diagram untuk mengecek coincidence antara excitation frequencies dan natural frequencies. |
| Centre Frequency | Tengah transmission band pada band-pass filter. |
| Cavitation | Bubble collapse akibat low pressure vaporization; menghasilkan noise/vibrasi random dan dapat merusak. |
| Channel | Sensor + signal conditioner + monitor/recorder. |
| Charge Amplifier | Amplifier untuk accelerometer charge output; mengurangi pengaruh cable capacitance. |
| Coherence | Ukuran kesamaan sinyal antar channel; membantu menentukan cause-effect. |
| Complete Machine | Assembly lengkap mesin dan komponen untuk menjalankan fungsi tertentu. |
| Cross Axis Sensitivity | Respons sensor terhadap arah di luar sumbu utama. |
| Crossover Frequency | Frekuensi di mana displacement dan acceleration requirement saling memenuhi dalam sinusoidal testing. |
| Cycle | Satu siklus lengkap waveform. |
| Damping | Reduksi amplitude gerakan tiap cycle; mengubah mechanical energy menjadi panas. |
| Decade | Interval frekuensi dengan rasio 10:1. |
| Decibel, dB | Ukuran logaritmik rasio. dB = 10 log power ratio = 20 log amplitude ratio. |
| Degrees of Freedom | Jumlah variabel independen untuk mendeskripsikan sistem vibrasi. |
| Demodulation | Teknik menghilangkan komponen low frequency dominan untuk menonjolkan bearing fault; dikenal juga enveloping. |
| Digital Filter | Filter yang bekerja pada data setelah sampled/digitized. |
| Differentiation | Operasi mendapatkan rate of change; velocity dapat menjadi acceleration. |
| Digital Signal Processor | Mikroprosesor untuk manipulasi sinyal digital. |
| Discrete Fourier Transform | Transformasi sampled time data menjadi discrete frequency components. |
| Displacement | Jarak pergerakan vibrasi; biasanya peak-to-peak, mils atau micron/mm. |
| Distortion | Komponen yang tidak diinginkan; harmonic, subharmonic, hash, atau noise. |
| Dynamic Mass | Uji untuk melihat apakah massa accelerometer memengaruhi pengukuran. |
| Dynamic Motion | Vibratory motion rotor yang hanya aktif di atas slow roll speed. |
| Dynamic Range | Selisih level tertinggi dan terendah yang dapat diukur; biasanya dB. |
| Eccentricity, Mechanical | Offset center of rotation terhadap geometric centerline. |
| Eccentricity Ratio | Vector difference antara bearing centerline dan steady state journal centerline. |
| Eddy Current | Arus pada material konduktif saat terkena electromagnetic field proximity probe. |
| Engineering Units | Unit pengukuran, misalnya mm/s, in/s, g, mils. |
| Enveloping | Lihat demodulation. |
| Envelopes | Band alarm pada reference spectrum. |
| FFT | Fast Fourier Transform; mengubah time waveform menjadi frequency spectrum. |
| FFT Analyzer | Analyzer yang menggunakan FFT untuk menampilkan komponen frekuensi. |
| Field Balancing | Balancing rotor pada bearing dan struktur mesin sendiri. |
| Filter | Perangkat untuk pass/reject band frekuensi tertentu. |
| Flat Top Window | Window untuk amplitude accuracy baik, frequency resolution lebih terbatas. |
| Flexible Rotor | Rotor yang deformasi signifikan pada running speed; biasanya dekat/atas first critical speed. |
| FMAX | Maximum frequency limit spectrum. |
| Finite Element Analysis | Teknik prediksi dynamic behavior struktur/mesin. |
| First Order Vibration / 1X | Vibrasi akibat shaft unbalance; frekuensi = RPM/60 Hz. |
| FMIN | Minimum frequency limit spectrum. |
| Forced Vibration | Vibrasi akibat forcing function; biasanya pada frekuensi excitation. |
| Forcing Frequency | Frekuensi gaya dari moving parts; penting untuk diagnosa fault. |
| Fourier | Matematikawan asal nama Fourier Transform. |
| Free Vibration | Vibrasi setelah initial force; biasanya pada natural frequency. |
| Frequency | Kebalikan period; Hz = cycles per second. cpm = Hz x 60. Orders = frequency / running speed. |
| Frequency Domain | Presentasi amplitude vs frequency. |
| Frequency Range | FMAX - FMIN. |
| Frequency Resolution | Spacing minimum data point spectrum = frequency range / lines. |
| Frequency Response | Amplitude dan phase response sistem. |
| Fundamental Frequency | Komponen dasar dari periodic signal; harmonic adalah kelipatannya. |
| Fundamental Mode | Mode dengan natural frequency terendah. |
| g | Acceleration akibat gravitasi; 1 g = 9.80665 m/s2 = 386.089 in/s2. |
| Gear Mesh Frequency | Number of teeth x shaft speed. |
| Hamming Window | Window mirip Hanning tetapi amplitude tidak dipaksa nol di ujung time record. |
| Hanning Window | Window paling umum untuk vibration data collection; mengurangi leakage. |
| Harmonics | Kelipatan integer dari fundamental frequency. |
| Heavy Spot | Lokasi angular imbalance vector pada shaft; biasanya tidak berubah dengan speed. |
| Hertz | Satuan frekuensi, 1 cycle per second. |
| High Spot | Lokasi angular shaft terdekat dengan probe; dapat berubah dengan dynamic condition. |
| High-Pass Filter | Melewatkan komponen di atas frekuensi tertentu. |
| Hysteresis | Dead-band; perubahan input tidak menghasilkan perubahan output pada region tertentu. |
| Imbalance | Center of mass tidak berada pada center of rotation; menghasilkan gaya 1X. |
| Static Imbalance | Principal inertia axis offset dan parallel terhadap rotation axis; dapat dikoreksi satu correction mass. |
| Couple Imbalance | Principal inertia axis memotong rotation axis di CG; butuh dua correction mass; phase berlawanan. |
| Dynamic Imbalance | Kombinasi static dan couple imbalance; paling umum; butuh minimal dua correction mass. |
| Impact Test | Test menggunakan impact untuk membangkitkan broad frequency range. |
| Mechanical Impedance | Properti mass, stiffness, damping yang menentukan respons terhadap forcing function. |
| Impulse | Integral force terhadap waktu. |
| Influence Coefficients | Koefisien matematis pengaruh loading terhadap defleksi sistem. |
| Integration | Proses mengubah acceleration ke velocity atau velocity ke displacement. |
| Integrator | Circuitry untuk konversi acceleration ke velocity atau velocity ke displacement. |
| Isolation | Pengurangan severity vibrasi dengan resilient support. |
| Key-Phasor | Sinyal referensi sekali per revolusi untuk phase, balancing, dan order tracking. |
| Leakage | Smearing/broadening peak akibat finite time record tidak berisi cycle lengkap. |
| Line Amplitude Limit | Limit amplitude maksimum untuk line resolution dalam band. |
| Linearity | Kedekatan calibration curve terhadap straight line. |
| Linear Non-Overlapping Average | Averaging time block yang tidak overlap; setiap sample diberi bobot sama. |
| Linear System | Response proporsional terhadap excitation. |
| Line of Resolution | Single data point spectrum yang berisi amplitude band frekuensi. |
| Lines | Jumlah total data point spectrum, misalnya 400, 800, 1600. |
| Machine Running Speed | Nominal speed dan actual RPM mesin saat pengukuran. |
| Mean | Nilai tengah antara maximum dan minimum parameter. |
| Mean-Time-Between-Failure | Waktu operasi rata-rata antar failure. |
| Mean-Time-To-Failure | Total waktu operasi dibagi jumlah failure; indikasi reliability. |
| Measurement Point | Lokasi pengukuran vibrasi pada mesin/component. |
| Mechanical Impedance | Ratio force terhadap velocity akibat force tersebut. |
| Micrometer/Micron | 1 micron = 1e-6 m = 0.03937 mils, sering dibulatkan 0.04 mils. |
| Mil | 1 mil = 0.001 inch = 25.4 microns. |
| Modal Analysis | Proses memecah motion struktur menjadi mode-mode vibrasi. |
| Mode | Pola karakteristik sistem vibrasi. |
| Narrow Band Analysis | Nama lain FFT analysis. |
| Natural Frequency | Frekuensi free vibration sistem saat impact excitation. |
| Noise | Interferensi total dalam sistem pengukuran. |
| Nominal Speed | Estimated running speed mesin saat setup route/database. |
| Nonlinearity | Deviasi output aktual dari best fit straight line. |
| Normalization | Pembagian sumbu frekuensi dengan turning speed; menghasilkan orders. |
| Nyquist Criterion | Sampling rate harus lebih besar dari 2 kali highest frequency yang diukur. |
| Nyquist Plot | Plot real vs imaginary spectral components; jangan disamakan polar plot 1X. |
| Octave | Interval frekuensi rasio 2:1. |
| Oil Whirl/Whip | Instability fluid film bearing; whirl biasanya 0.38-0.48X; whip terkunci pada shaft resonant frequency. |
| Orbit | Path shaft centerline motion selama rotasi; dilihat dari x-y displacement probe. |
| Orders | Kelipatan running speed; memudahkan perbandingan spectrum saat speed berubah. |
| Order Analysis | Frequency analysis dengan sumbu frekuensi dalam orders. |
| Order Tracking | Kontrol sampling rate agar komponen 1X, 2X, 3X lebih mudah diidentifikasi. |
| Orthogonal | Arah pengukuran independen, biasanya 90 derajat satu sama lain. |
| Oscillation | Variasi quantity terhadap waktu; force, displacement, velocity, acceleration. |
| Oscillator-Demodulator | Signal conditioner untuk eddy current displacement probe. |
| Overall Level | Total vibration amplitude pada range frekuensi lebar; dapat acceleration, velocity, atau displacement. |
| Peak | Maximum excursion satu arah dari zero. |
| Peak Hold | Averaging yang menyimpan peak level tiap frequency component. |
| Peak-to-Peak | Selisih highest positive peak dan lowest negative peak; umum untuk displacement. |
| Period | Waktu untuk satu cycle lengkap. |
| Periodic | Sinyal yang polanya berulang terhadap waktu. |
| Phase | Relative time difference antara dua sinyal dengan frekuensi sama; dinyatakan dalam derajat. |
| Phase Reference Probe | Perangkat sinyal sekali per revolusi. |
| Pickup | Istilah lama untuk vibration transducer. |
| Piezoelectric | Material menghasilkan electrical charge saat mechanical stress. |
| Piezoelectric Transducer | Transducer berbasis crystal/ceramic deformation. |
| Piezoresistive Transducer | Output berdasarkan perubahan resistive semiconductor element. |
| Pitch | Rotasi pada plane forward motion; dalam musik terkait frequency. |
| Polar Plot | Representasi polar locus 1X vector terhadap speed. |
| Power Spectrum | Auto spectrum magnitude; phase diabaikan. |
| Power Spectral Density | Power random vibration per frequency unit, misalnya g2/Hz. |
| Precision | Smallest distinguishable increment/resolution. |
| Preload, Bearing | Beban pada bearing/shaft; dari nol sampai maksimum line contact. |
| Preload, External | Beban eksternal pada bearing: proses fluid, gravity, gear contact, misalignment, rub. |
| Probability Distribution | Probabilitas statistik event; umumnya bell-shaped. |
| Probe | Sensor yang mounted pada mesin, sering internal. |
| Proximity Sensor | Displacement sensor untuk mengukur gap housing-shaft. |
| Root Cause Analysis | Menentukan penyebab failure sebenarnya. |
| Root Mean Square, RMS | Ukuran energi sinyal; RMS sine = 0.707 x peak. |
| Rotational Speed | Jumlah revolusi per satuan waktu, misalnya RPM. |
| Sampling Rate | Jumlah reading A/D converter per detik. |
| Seismic | Sensor berbasis inertia mass, misalnya accelerometer/velocity pickup. |
| Sensitivity | Rasio electrical output terhadap mechanical input. |
| Sensor | Nama lain transducer. |
| Shaker | Device penghasil vibrasi terkontrol untuk testing. |
| Shock Pulse | Transmisi kinetic energy dalam waktu singkat; biasanya diikuti decay. |
| Sidebands | Komponen spectrum akibat amplitude/frequency modulation; spacing = modulating frequency. |
| Signal | Electrical voltage/current analog dari vibrasi yang diukur. |
| Signal Conditioner | Amplifier setelah sensor untuk menyiapkan sinyal. |
| Signature | Spectrum/waveform khas mesin pada kondisi dan waktu tertentu. |
| Simple Harmonic Motion | Single frequency constant amplitude; waveform sinus. |
| Sine Wave | Gelombang sinus; satu frekuensi constant amplitude. |
| Ski Slope | Spectrum low frequency tinggi melandai; indikasi sensor problem, thermal transient, shock, atau electrical issue. |
| Soft Foot | Feet mesin tidak satu bidang; menyebabkan frame distortion saat bolt dikencangkan. |
| Sound Intensity | Average rate sound energy flow melalui area perpendicular. |
| Strain-Gage Transducer | Sensor berbasis perubahan resistance akibat deformation. |
| Sub-Harmonic | Frekuensi integral sub-multiple dari fundamental. |
| Sub-Synchronous | Komponen di bawah shaft rotation frequency. |
| Swept-Sine Testing | Sine shaking dengan frequency diubah terus-menerus. |
| Synchronous | Komponen integer multiple fundamental frequency. |
| Synchronous Sampling | Kontrol effective sampling rate untuk order tracking. |
| SI | Systeme Internationale, penerus metric system. |
| Tangential | Arah tangent terhadap rotating shaft; perpendicular terhadap radial. |
| Time Averaging | Averaging time record untuk mengurangi asynchronous components. |
| Time Domain | Vibrasi sebagai fungsi waktu; waveform. |
| Time Record | Sampled time data sebelum FFT; sering 1024 samples. |
| Torsional Vibration | Amplitude modulation torque dalam degrees peak-to-peak. |
| Tracking Filter | Filter mengikuti input signal; aliasing protection saat external sampling. |
| Transducer | Device mengubah satu energi menjadi energi lain, biasanya vibration ke electrical signal. |
| Transient Vibration | Vibrasi sementara akibat perubahan kondisi operasi. |
| Transmissibility | Ratio response motion/input motion; maksimum saat resonance. |
| Trigger | Event timing reference untuk memulai measurement. |
| True Peak | Peak sebenarnya dari complex waveform; diukur di time domain. |
| Uniform Window | Window tanpa weighting; tidak melindungi leakage; cocok untuk transient penuh dalam time record. |
| Unit | Besaran terdefinisi seperti volt, meter, inch. |
| VdB | Decibel velocity level; referensi dapat berbeda antar standar. |
| Vector | Quantity dengan magnitude dan direction/phase. |
| Velocity | Rate of change position; umum dalam in/s atau mm/s. |
| Vibration | Oscillation point/object围绕 rest position. |
| Vibration Meter | Apparatus untuk mengukur electrical signal dari vibration sensor. |
| Vibration Signature | Pola vibrasi karakteristik mesin saat beroperasi. |
| Waveform | Shape time domain signal; dapat menunjukkan impacting/random noise. |
| Waterfall Plot | 3D plot amplitude spectrum vs time/rpm; dikenal spectral map. |
| Window | Fungsi mengurangi leakage akibat finite time record; Hanning paling umum. |

---

## 3. Diagnostic Guide — Gejala dan Indikasi Fault

Tabel berikut merangkum diagnostic guide dari dokumen.

| Fault | Page | Frekuensi / Gejala Utama | Phase / Catatan Penting |
|---|---:|---|---|
| Ski-Slope | D-3 | Spectrum tinggi dekat 0 Hz lalu decay ke kanan. | Sensor long, kabel, overheating, temperature transient, shock, electrical transient. Jika transducer saturated dapat muncul raised noise floor di high frequency. |
| Raised Noise Floor | D-4 | Noise floor spectrum naik. | Extreme bearing wear stage lanjut. Jika noise ke high frequency, possible process/flow noise atau cavitation. Humps bisa resonance atau closely spaced sidebands. |
| Dynamic Imbalance | D-6 | 1X radial vertical/horizontal. | Level tertinggi biasanya horizontal karena flexibility terbesar. Phase across machine 0-180 derajat; vertical-horizontal sekitar 90 ± 40 derajat. |
| Static Imbalance | D-7 | 1X radial vertical/horizontal. | In-phase across machine; vertical-horizontal sekitar 90 ± 30 derajat. |
| Couple Imbalance | D-8 | 1X radial vertical/horizontal. | Out of phase across machine; vertical-horizontal sekitar 90 ± 30 derajat. |
| Imbalance: Overhung Machines | D-9 | 1X axial kuat plus 1X radial. | Axial phase in-phase. Imbalance menciptakan bending moment sehingga housing bergerak axial. |
| Imbalance: Vertical Machines | D-10 | 1X radial horizontal/tangential. | Phase similar pada titik arah sama. Untuk isolasi motor vs pump, bisa break coupling dan run motor solo. |
| Eccentric Rotor or Gear | D-11 | 1X radial. | Kuat pada arah parallel rotor/gear. Mimics imbalance. |
| Eccentric Sheaves | D-12 | 1X radial. | Tertinggi pada arah belt tension. Phase vertical-horizontal bisa 0 atau 180 derajat. Cek dengan melepas belt. |
| Misalignment | D-13 | 1X dan 2X; severe dapat 3X, 4X. | Axial dan radial. Kombinasi angular dan parallel umum terjadi. |
| Angular Misalignment | D-14 | Axial vibration tinggi; 1X kuat, 2X/3X dapat muncul. | 180 derajat across coupling pada axial; radial components cenderung in-phase. |
| Parallel Misalignment | D-15 | 2X radial kuat, 1X radial lebih kecil. | 180 derajat across coupling pada radial. Pure parallel biasanya axial rendah. Severe dapat memunculkan 3X-8X. |
| Bent Shaft | D-16 | 1X axial dominan; 2X jika bend dekat coupling. | Phase axial antar bearing mendekati 180 derajat. |
| Cocked Bearing | D-17 | 1X, 2X, 3X axial. | 180 derajat phase pada sisi berlawanan shaft; dapat menyerupai misalignment. |
| Looseness | D-18 | Rotating looseness: 1X harmonics; structural: 1X horizontal; pedestal: 1X, 2X, 3X. | Looseness meningkatkan vibrasi pada arah least stiffness. |
| Rotating Looseness | D-19 | 1X harmonics radial; severe dapat 0.5X harmonics. | Excessive clearance journal/rolling bearing; harmonics dapat melebihi 10X. |
| Structural Looseness | D-20 | 1X meningkat pada arah least stiffness, sering horizontal. | 180 derajat phase antara machine dan base pada vertical. Loose bolt, corrosion, cracking. |
| Pedestal Bearing Looseness | D-21 | 1X, 2X, 3X radial; severe dapat 0.5X. | 180 derajat phase antara bearing dan base. |
| Rotor Rub | D-22 | 1X harmonics radial; 0.5X harmonics saat severe. | Dapat excite resonance. Mirip rotating looseness. |
| Journal Bearing Clearance | D-23 | 1X harmonics; 0.5X/subharmonic saat severe. | Excessive clearance pada journal bearing. |
| Oil Whirl | D-24 | 0.38-0.48X radial. | Tidak tepat 0.5X; akibat excessive clearance dan light radial loading. Oil whip terkunci ke shaft resonant frequency. |
| Resonance | D-25 | Hump/peak tinggi, sering satu arah. | Amplitude turun jika speed diubah menjauh resonance; natural frequency tidak ikut bergerak dengan speed. |
| Rolling Element Bearing Wear | D-26 | Non-synchronous peaks, harmonics, sidebands. | Stage awal high frequency ringing; stage lanjut BPI, BPO, FT, BS dan sidebands 1X/cage. |
| Pumps/Fans Blade/Vane Pass | D-29 | Peak pada vane pass/blade pass frequency. | Number of vanes/blades x RPM. Naik jika gap tidak equal, obstruction, sharp bends. |
| Flow Turbulence | D-30 | Random vibration rendah, sekitar 50-2000 CPM. | Variasi pressure/velocity flow. |
| Cavitation | D-31 | Random high frequency noise/hump. | Insufficient suction pressure; waveform dapat terdengar seperti gravel. |
| Reciprocating Machines | D-32 | 0.5X untuk four-stroke; 1X untuk two-stroke. | Vibration level sering sangat tinggi. |
| Stator Eccentricity | D-33 | 2x line frequency, 100/120 Hz radial. | Uneven stationary air gap antara rotor dan stator. |
| Soft Foot | D-34 | 2x line frequency radial. | Soft foot/warped base dapat menghasilkan eccentric stator. |
| Eccentric Rotor | D-35 | Pole pass sidebands sekitar 1X dan 100/120 Hz. | Rotating variable air gap antara rotor dan stator. |
| Rotor Bow | D-36 | 1X radial. | Thermal rotor bow; hilang saat motor cold. |
| Cracked or Broken Rotor Bars | D-37 | Pole pass sidebands sekitar 1X dan harmonics. | Beating pada twice slip frequency; motor current analysis membantu. |
| Loose Rotor Bars | D-38 | Rotor bar pass frequency dengan sidebands 100/120 Hz. | Rotor bar pass frequency = number of rotor bars x running speed. |
| Loose Rotor | D-39 | 1X dan harmonics tinggi. | Rotor dapat slip pada shaft, sering intermittent tergantung temperature. |
| Loose Stator Windings | D-40 | Electrical/stator related; umumnya line frequency/2x line frequency area. | Verifikasi spectrum asli; sering terkait electrical fault dan sidebands. |
| Lamination Problems | D-41 | 100/120 Hz radial tinggi. | Shorted laminations menyebabkan local heating, thermal warping, 1X naik, pole pass sidebands dapat muncul. |
| Loose Connections | D-42 | 100/120 Hz tinggi dengan sidebands 33/40 Hz. | Phasing problem akibat loose connector. |
| Gear Faults | D-43 | Shaft speed dan gear mesh frequency. | Spur gears radial; helical gears axial. Time waveform dapat menunjukkan tooth pulse. |
| Gear Tooth Wear | D-44 | 1X sidebands sekitar gear mesh; gear natural frequency muncul. | Sidebands sesuai speed gear yang aus. |
| Gear Tooth Load | D-45 | Gear mesh frequency tinggi. | Bergantung alignment dan load; tidak selalu fault. |
| Gear Backlash | D-46 | 1X sidebands sekitar gear mesh; gear natural frequency tinggi. | Peak dapat turun saat load naik. |
| Eccentric Gears | D-47 | 1X sideband sekitar gear mesh. | Sering hanya single sideband, bukan keluarga sideband penuh. |
| Misaligned Gears | D-48 | Gear mesh tinggi dengan sidebands; harmonics 2GM/3GM. | Fmax harus cukup tinggi untuk melihat harmonics. |
| Cracked or Broken Tooth | D-49 | 1X gear bersangkutan tinggi; gear natural frequency excited. | 1X sidebands sekitar gear mesh. |
| Hunting Tooth Frequency | D-51 | Hunting tooth frequency dan 2HT. | HT = gear mesh frequency / LCM jumlah gigi kedua gear. Dapat terdengar growling. |
| Coupling Faults | D-52 | 1X dan 2X. | Non-parallel flange faces menyerupai angular misalignment. Coupling imbalance menghasilkan 1X/2X radial. Wear dapat menyerupai misalignment/looseness. |
| Worn or Loose Belts | D-53 | Belt rate dan harmonics; 2BR sering tertinggi. | Belt rate adalah rate titik belt melewati fixed reference. Selalu lebih rendah dari speed kedua sheave. |
| Eccentric Sheaves/Pulleys | D-54 | 1X radial tinggi. | Tertinggi pada arah parallel belts; cek dengan melepas belts. |
| Misaligned Sheaves/Pulleys | D-55 | 1X axial tinggi. | Kadang belt rate harmonics muncul axial. |
| Belt Resonance | D-56 | 1X radial tinggi. | Belt natural frequency coincides dengan driving/driven sheave RPM; ubah length/tension. |
| External Noise | D-57 | Non-synchronous peak. | Stop machine atau vary speed; cek mesin sekitar. Brinnelling dapat terjadi jika mesin lama berhenti. |

---

## 4. Reference by Symptom

### 4.1 Gejala 1X

Fault yang sering muncul dengan dominan 1X:

- Dynamic imbalance.
- Static imbalance.
- Couple imbalance.
- Imbalance pada overhung machine.
- Imbalance pada vertical machine.
- Eccentric rotor/gear.
- Eccentric sheaves.
- Misalignment.
- Angular misalignment.
- Parallel misalignment.
- Bent shaft.
- Cocked bearing.
- Looseness.
- Rotating looseness.
- Structural looseness.
- Pedestal bearing looseness.
- Rotor rub.
- Journal bearing clearance.
- Resonance at 1X.
- Reciprocating machine.
- Eccentric rotor.
- Rotor bow.
- Cracked/broken rotor bars.
- Loose rotor.
- Cracked/broken gear tooth.
- Coupling faults.
- Eccentric sheaves/pulleys.
- Misaligned sheaves/pulleys.
- Belt resonance.

### 4.2 Gejala 2X

Fault yang sering muncul dengan 2X:

- Misalignment.
- Angular misalignment.
- Parallel misalignment.
- Bent shaft.
- Cocked bearing.
- Looseness.
- Rotating looseness.
- Pedestal bearing looseness.
- Rotor rub.
- Journal bearing clearance.
- Coupling faults.

### 4.3 Gejala 3X-8X

Fault yang dapat memunculkan harmonic 3X sampai 8X:

- Misalignment severe.
- Angular misalignment.
- Parallel misalignment.
- Cocked bearing.
- Looseness.
- Rotating looseness.
- Pedestal bearing looseness.
- Rotor rub.
- Journal bearing clearance.
- Pump/fan blade/vane pass.
- Coupling faults.
- Gear faults.
- Gear tooth wear.
- Gear tooth load.
- Gear backlash.
- Eccentric gears.
- Misaligned gears.
- Cracked/broken tooth.
- Hunting tooth frequency.
- Worn/loose belts.

### 4.4 Gejala Sub-Synchronous / 0.5X

Fault dengan komponen di bawah 1X:

- Oil whirl: 0.38-0.48X.
- Flow turbulence: random low frequency.
- Reciprocating machines: 0.5X four-stroke.
- Worn/loose belts.
- Rotating looseness severe: 0.5X harmonics.
- Rotor rub severe: 0.5X harmonics.
- Journal bearing clearance severe.
- Rolling element bearing wear dapat memiliki komponen non-synchronous/sub-synchronous.

### 4.5 Gejala Non-Synchronous

Fault dengan peak tidak tepat kelipatan running speed:

- Rolling element bearing wear.
- External noise.
- Hunting tooth frequency.
- Oil whirl.
- Bearing natural frequencies.
- Cavitation/random flow noise.

### 4.6 Gejala Sidebands

Sidebands penting untuk:

- Gear faults: sidebands shaft speed sekitar gear mesh.
- Gear tooth wear.
- Gear backlash.
- Eccentric gears.
- Misaligned gears.
- Cracked/broken tooth.
- Rolling element bearing wear: sidebands 1X/cage.
- Eccentric rotor: pole pass sidebands.
- Cracked/broken rotor bars: pole pass sidebands sekitar 1X/harmonics.
- Loose rotor bars: 100/120 Hz sidebands sekitar rotor bar pass frequency.
- Loose connections: 33/40 Hz sidebands sekitar 100/120 Hz.
- Worn/loose belts: sidebands pada belt rate.

### 4.7 Gejala Raised Noise Floor

- Bearing wear stage lanjut.
- Cavitation.
- Flow turbulence.
- External process noise.
- Transducer saturation.

### 4.8 Gejala Ski Slope

- Sensor long.
- Loose wire.
- Overheated sensor.
- Temperature transient.
- Physical overload/shock.
- Electrical transient.

### 4.9 Gejala Line Frequency / Electrical

- Stator eccentricity: 2x line frequency.
- Soft foot: 2x line frequency.
- Eccentric rotor: pole pass sidebands sekitar 1X dan 2x line frequency.
- Rotor bow: 1X mechanical akibat thermal.
- Cracked/broken rotor bars: pole pass sidebands.
- Loose rotor bars: rotor bar pass frequency dengan 2x line frequency sidebands.
- Loose rotor: 1X dan harmonics.
- Lamination problems: 100/120 Hz tinggi.
- Loose connections: 100/120 Hz dengan 33/40 Hz sidebands.

---

## 5. Useful Charts and Tables

### 5.1 Unit Conversions

Konversi penting:

- 1 g = 9.80665 m/s2.
- 1 g = 980.665 cm/s2.
- 1 g = 386.089 in/s2.
- 1 g = 32.174 ft/s2.
- 1 mil = 0.001 inch.
- 1 mil = 25.4 micron.
- 1 micron = 1e-6 m.
- 1 micron = 0.03937 mils, sering dibulatkan 0.04 mils.
- 1 inch = 25.4 mm.
- Hz x 60 = CPM/RPM.
- CPM / 60 = Hz.
- Frequency in orders = frequency / running speed.

### 5.2 Vibration Amplitude Conventions

Konvensi umum:

- Displacement biasanya peak-to-peak.
- Velocity biasanya peak atau RMS tergantung chart; banyak ISO chart memakai RMS.
- Acceleration biasanya RMS.
- Untuk sine wave:
  - RMS = peak / sqrt(2).
  - Peak-to-peak = 2 x peak.
  - RMS = peak-to-peak / (2 x sqrt(2)).

### 5.3 Hubungan Displacement, Velocity, Acceleration

Untuk sinusoidal single frequency:

- Velocity peak = 2 x pi x f x displacement peak.
- Acceleration peak = 2 x pi x f x velocity peak.
- Jika displacement peak-to-peak dalam inch:
  - velocity peak in/s = pi x f x displacement p-p inch.
- Jika displacement p-p dalam mils:
  - velocity peak in/s = pi x f x displacement p-p mils / 1000.

### 5.4 dB Calculation

Dari dokumen:

- dB = 10 log(P2/P1)
- dB = 20 log(A2/A1) untuk acceleration, velocity, voltage, amplitude.
- 6 dB mewakili perubahan 2 kali.
- 20 dB mewakili perubahan 10 kali.

Referensi dB harus konsisten. Dokumen menyebut referensi velocity kecil, misalnya VdB dengan referensi SI dan referensi US Navy yang berbeda 20 dB. Jika menggunakan standar tertentu, pastikan reference value sesuai.

### 5.5 FFT dan Frequency Resolution

Rumus penting:

- Frequency Resolution = (FMAX - FMIN) / Number of Lines.
- BIN bandwidth = frequency resolution.
- Nyquist: sample rate > 2 x highest frequency.
- Anti-aliasing filter membuang frekuensi di atas setengah sample rate.
- FMAX menentukan maximum frequency yang dianalisis.
- FMIN menentukan minimum frequency yang dianalisis.

### 5.6 Orders dan Normalization

- Order = frequency / running speed.
- 1X = running speed.
- 2X = twice running speed.
- 0.5X = half running speed.
- Order tracking membantu membandingkan spectrum saat speed berubah.

### 5.7 Bearing Forcing Frequencies

Empat bearing defect frequency utama:

- BPI: Ball Pass Inner Race.
- BPO: Ball Pass Outer Race.
- FT: Fundamental Train / Cage Frequency.
- BS: Ball Spin.

Rumus:

- BPI order = n/2 x (1 + d/D x cos alpha)
- BPO order = n/2 x (1 - d/D x cos alpha)
- FT order = 1/2 x (1 - d/D x cos alpha)
- BS order = D/(2d) x (1 - (d/D x cos alpha)^2)

Keterangan:

- n = jumlah balls/rollers.
- d = ball/roller diameter.
- D = pitch diameter.
- alpha = contact angle.

Rule of thumb:

- BPI approx 0.6 x number of balls/rollers.
- BPO approx 0.4 x number of balls/rollers.

### 5.8 Gear Calculations

Rumus gear:

- Gear mesh frequency = number of teeth x shaft speed.
- Output speed = input speed x input teeth / output teeth.
- Hunting tooth frequency = gear mesh frequency / LCM(teeth1, teeth2).

Catatan:

- Spur gears sering terlihat radial.
- Helical gears sering terlihat axial.
- Gear fault sering menghasilkan sidebands shaft speed sekitar gear mesh.
- Gear natural frequency dapat muncul dengan sidebands.

### 5.9 Belt Calculations

Rumus belt:

- Driven RPM = Driving RPM x Driving sheave diameter / Driven sheave diameter.
- Belt frequency = pi x sheave RPM x sheave diameter / belt length.
- Timing belt frequency = belt frequency x number of teeth on belt.
- Alternatif timing belt frequency = sheave RPM x number of teeth on sheave.

Gejala:

- Worn/loose belt: belt rate peak dan harmonics, sering 2BR tertinggi.
- Eccentric sheave: 1X radial.
- Misaligned sheave: 1X axial.
- Belt resonance: high 1X saat belt natural frequency coincides dengan sheave RPM.

### 5.10 Motor Electrical Calculations

Rumus motor:

- Synchronous speed RPM = 120 x line frequency / number of poles.
- Slip frequency = synchronous speed - actual speed, dibagi 60 jika ingin Hz.
- Pole pass frequency = slip frequency x number of poles.
- Rotor bar pass frequency = number of rotor bars x running speed.
- Twice line frequency = 2 x line frequency, yaitu 100 Hz untuk 50 Hz system atau 120 Hz untuk 60 Hz system.

Gejala electrical:

- Stator eccentricity: 2x line frequency radial.
- Eccentric rotor: pole pass sidebands sekitar 1X dan 2x line frequency.
- Broken rotor bars: pole pass sidebands sekitar 1X/harmonics.
- Loose rotor bars: 2x line frequency sidebands sekitar rotor bar pass frequency.
- Loose connections: 2x line frequency dengan sidebands 1/3 line frequency.

### 5.11 Pump/Fan Blade/Vane Pass

Rumus:

- Vane pass frequency = number of vanes x RPM.
- Blade pass frequency = number of blades x RPM.

Catatan:

- Peak vane/blade pass normal pada pump/fan/compressor.
- Amplitude naik jika gap blade/vane tidak equal, ada obstruction, atau sharp bends di flow path.

### 5.12 Reciprocating Machines

- Four-stroke engine fires every other rotation: peak kuat 0.5X.
- Two-stroke engine fires every stroke: peak kuat 1X.
- Vibration level reciprocating machinery sering sangat tinggi.

### 5.13 Vibration Severity dan ISO Charts

Dokumen memuat:

- Vibration Severity Chart.
- ISO 10816-1 Vibration Severity Chart.
- ISO 10816-3 Vibration Severity Chart - Velocity.
- ISO 10816-3 Vibration Severity Chart - Displacement.

Karena chart berbentuk grafik dan OCR tidak menghasilkan angka lengkap, gunakan fungsi `classify_by_threshold` pada `vibration_calculations.py` dengan threshold yang disalin dari chart resmi/lokal.

Contoh penggunaan threshold tanpa menulis curly braces:

```python
import vibration_calculations as vc

thresholds = [
    (1.0, "Good"),
    (2.8, "Acceptable"),
    (4.5, "Alarm"),
    (999999, "Danger")
]

result = vc.classify_by_threshold(2.1, thresholds)
print(result)