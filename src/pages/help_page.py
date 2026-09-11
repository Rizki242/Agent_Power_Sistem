"""Help, Documentation, and CBM Engineering Standards Page for Streamlit UI."""

import streamlit as st
from src.components.theme import render_page_header


def render_help_page(st_context=st):
    render_page_header(
        st_context,
        "Help, Panduan Operasional & Standar CBM",
        "Pusat bantuan sistem PPLE Agent, referensi standar teknik keandalan pembangkit, dan arsitektur Multi-Agent",
    )

    tab_quickstart, tab_standards, tab_agents, tab_cli = st_context.tabs([
        ":material/rocket_launch: Panduan Cepat",
        ":material/menu_book: Standar Engineering",
        ":material/smart_toy: Arsitektur Multi-Agent",
        ":material/terminal: Perintah CLI PPLE",
    ])

    with tab_quickstart:
        st_context.markdown("### 🚀 Panduan Memulai CBM Assistant")
        st_context.markdown("""
        Selamat datang di **PPLE Reliability Engineering Agent** (PLTU Jeranjang 3 × 25 MW). Sistem ini dirancang untuk membantu teknisi, engineer, dan supervisor dalam memantau kesehatan peralatan secara terpadu.

        #### Alur Kerja Utama:
        1. **Command Center (Agent Dashboard)**:
           - Pantau kesehatan armada peralatan secara keseluruhan pada *Fleet Health Overview*.
           - Periksa *Critical Watchlist* untuk melihat mesin yang membutuhkan perhatian prioritas.
           - Lakukan drill-down diagnosa per-peralatan dengan fusi bukti multi-domain (Vibrasi, MCSA, Thermal, Tribologi, DGA, PD).
        2. **Condition Monitoring (PdM)**:
           - Buka tab domain teknis terkait (misal: **MCSA**, **Vibrasi**, **DGA**, dll.) untuk melihat grafik tren, spektrum FFT, rasio gas Duval, atau viskositas pelumas.
        3. **Work Orders**:
           - Tinjau rekomendasi pemeliharaan otomatis dari sistem.
           - Setujui (*Approve*) perintah kerja untuk diteruskan ke tim mekanik/listrik lapangan.
        4. **Pelaporan**:
           - Buat laporan berkala PPT atau Word siap pakai pada menu **Laporan PPT** dan **Laporan Word**.
        """)

    with tab_standards:
        st_context.markdown("### 📚 Standar Engineering yang Digunakan")
        st_context.markdown("""
        Seluruh evaluasi status dan ambang batas (threshold) dalam sistem ini mengacu pada standar internasional:

        | Domain CBM | Standar Acuan | Parameter Utama & Metode Evaluasi |
        |---|---|---|
        | **Vibrasi** | **ISO 10816-3** | Overall Velocity RMS (mm/s), FFT 1X/2X, Bearing Fault Frequency (BPFO, BPFI, BSF, FTF) |
        | **MCSA** | **IEEE 519 / EPRI** | Sideband rotor bar amplitude (dBc), deviasi arus/tegangan, Total Harmonic Distortion (THD) |
        | **DGA** | **IEEE C57.104 / IEC 60599** | TDCG, Konsentrasi Gas Terlarut (H2, CH4, C2H2, C2H4, C2H6, CO, CO2), Duval Triangle 1, Rogers Ratios |
        | **Tribologi** | **ASTM D445 / ISO 4406** | Viskositas kinematik 40°C, TAN (mg KOH/g), Water Content (ppm), Partikel Wear (Fe, Cu), Kode Kebersihan ISO 4406 |
        | **Thermal** | **ISO 18434-1 / NETA** | Suhu absolut (°C), Delta-T terhadap ambient (ΔT1), Delta-T antarfasa/komponen sejenis (ΔT2) |
        | **Partial Discharge** | **IEC 60270** | Pulse magnitude (pC), Normalized Quantity Number (NQN), Pola Phase Resolved Partial Discharge (PRPD) |
        """)

    with tab_agents:
        st_context.markdown("### 🤖 Ekosistem Multi-Agent & Safety Guardrail")
        st_context.markdown("""
        Sistem ini mengorkestrasi 8 agen spesialis otonom yang bekerja sama menganalisis bukti:
        
        - 🌐 **Vibration Specialist**: Deteksi unbalance, misalignment, looseness, dan degradasi bantalan roller/journal.
        - ⚡ **MCSA Specialist**: Deteksi broken rotor bar, dynamic eccentricity, dan ketidakseimbangan stator.
        - 🧪 **DGA Transformer Specialist**: Diagnosa pelepasan energi tinggi (*arcing*), termal minyak/kertas (*hotspot*), dan *partial discharge*.
        - ⚡ **PD Specialist**: Isolasi tegangan tinggi, tracking, dan korona pada belitan stator generator & trafo.
        - 🛢️ **Tribology Specialist**: Kualitas pelumasan, keausan mekanis (wear debris), dan kontaminasi air/debu.
        - 🌡️ **Thermal Specialist**: Deteksi rugi termal pada koneksi listrik (*loose connection*) dan overheat bearing.
        - 🧠 **Reliability Fusion Agent**: Menggabungkan bukti multi-disiplin menjadi nilai tunggal **Health Index (0–100)**, **Failure Mode**, dan proyeksi **RUL**.
        - 🛡️ **Safety Guardrail Sub-Agent**: Memastikan rekomendasi tindakan kritis selalu memerlukan konfirmasi manusia (*Human-in-the-Loop*).
        """)

    with tab_cli:
        st_context.markdown("### 💻 Panduan Perintah CLI PPLE")
        st_context.markdown("""
        PPLE dapat dioperasikan langsung melalui terminal tanpa membuka browser:

        ```bash
        # Cek kesehatan sistem dan status data
        pple status
        pple doctor

        # Analisis modul teknik langsung pada file data
        pple analyze vibration CWP-1A vibration_data.csv
        pple analyze dga GT-U1 dga_sample.xlsx

        # Chatbot teknik MCSA rule-based offline
        pple chat

        # Shell interaktif natural language
        pple shell

        # Manajemen modul dan aset
        pple assets list
        pple module list
        ```
        """)
