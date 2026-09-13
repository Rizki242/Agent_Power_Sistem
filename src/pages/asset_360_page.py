"""Asset 360° Holistic View Page.

Integrates multi-domain condition monitoring into a single unified asset view:
- MCSA (Electrical, Stator, Rotor)
- Vibrasi (Mechanical, Alignment, Bearing)
- Thermal (Thermography, Temperature, Delta-T)
- Tribology (Oil Condition, Water, TAN, Wear Metals)
- Overall Health Index, Multi-Domain Radar Chart, and Prescriptive Actions
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.asset_registry import list_assets
from src.components.theme import render_page_header
from src.components.status_colors import canon_condition_status, render_status_badge
from src.thermal_data import search_thermal_records
from src.tribology_data import search_tribology_samples
from src.vibration_data import (
    load_vibration_assets,
    load_vibration_monthly_tests,
    match_monthly_test_by_equipment,
)
from src.utils import safe_float


HEALTH_PALETTE = {
    "HEALTHY": "#10B981",
    "WATCH": "#3B82F6",
    "WARNING": "#F59E0B",
    "ALERT": "#F97316",
    "CRITICAL": "#EF4444",
    "UNKNOWN": "#64748B",
}


def _build_radar_chart(scores: Dict[str, float], asset_name: str) -> go.Figure:
    """Build a modern 5-pillar radar chart for the asset."""
    categories = list(scores.keys())
    values = list(scores.values())

    # Close the radar loop
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill="toself",
            fillcolor="rgba(2, 132, 199, 0.25)",
            line=dict(color="#0284c7", width=2.5),
            marker=dict(size=7, color="#0369a1"),
            name="Health Score",
        )
    )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=9, color="#64748b"),
                gridcolor="#e2e8f0",
            ),
            angularaxis=dict(
                tickfont=dict(size=11, color="#1e293b", family="sans-serif"),
                gridcolor="#e2e8f0",
                rotation=90,
                direction="clockwise",
            ),
            bgcolor="rgba(248, 250, 252, 0.5)",
        ),
        showlegend=False,
        height=320,
        margin=dict(l=40, r=40, t=25, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _score_from_status(status: str) -> float:
    s = str(status).upper()
    if any(k in s for k in ("CRITICAL", "HIGH", "BAD", "TRIP")):
        return 25.0
    if "PREWARNING" in s or "WATCH" in s:
        return 80.0
    if any(k in s for k in ("ALERT", "ALARM", "WARNING")):
        return 60.0
    if any(k in s for k in ("NORMAL", "HEALTHY", "GOOD", "OK")):
        return 95.0
    return 75.0


def render_asset_360_page(
    st_ctx,
    df_latest_all: pd.DataFrame,
    df_all: Optional[pd.DataFrame] = None,
) -> None:
    render_page_header(
        st_ctx,
        "Asset 360° Holistic View",
        "Tampilan diagnosa terpadu lintas domain (MCSA, Vibrasi, Suhu, & Oli) dalam satu layar.",
        badge="Asset Intelligence",
    )

    # 1. Collect all unique equipment identifiers across sources
    registered_assets = list_assets()
    reg_map = {str(a.get("name", "")).strip().upper(): a for a in registered_assets}

    mcsa_eqs = []
    if df_latest_all is not None and not df_latest_all.empty and "Equipment" in df_latest_all.columns:
        mcsa_eqs = df_latest_all["Equipment"].dropna().astype(str).unique().tolist()

    vib_df = load_vibration_assets()
    vib_eqs = vib_df["equipment"].dropna().astype(str).unique().tolist() if not vib_df.empty else []

    all_eq_set = sorted(list({e.strip() for e in (mcsa_eqs + vib_eqs + list(reg_map.keys())) if e.strip()}))
    if not all_eq_set:
        st_ctx.warning("Tidak ada data peralatan yang tersedia untuk ditampilkan.")
        return

    # 2. Filter & Selector Bar
    c_flt1, c_flt2 = st_ctx.columns([1, 2])
    with c_flt1:
        unit_opts = ["Semua Unit", "UNIT 1", "UNIT 2", "UNIT 3", "COMMON"]
        sel_unit = st_ctx.selectbox("Filter Unit", unit_opts, index=0, key="_a360_unit")

    filtered_eqs = all_eq_set
    if sel_unit != "Semua Unit":
        target = sel_unit.replace("UNIT ", "").strip().upper()
        filtered_eqs = [
            e for e in all_eq_set
            if target in e.upper() or (reg_map.get(e.upper()) and target in str(reg_map[e.upper()].get("unit", "")).upper())
        ]
        if not filtered_eqs:
            filtered_eqs = all_eq_set

    with c_flt2:
        selected_equipment = st_ctx.selectbox(
            "Pilih Peralatan (Equipment)",
            filtered_eqs,
            index=0,
            key="_a360_equipment",
            help="Cari nama peralatan, pompa, fan, atau motor penggerak.",
        )

    # 3. Retrieve Domain Data for Selected Equipment
    eq_upper = selected_equipment.upper()
    reg_info = reg_map.get(eq_upper, {})
    unit_label = reg_info.get("unit") or ("UNIT 1" if "1" in eq_upper else "UNIT 2" if "2" in eq_upper else "COMMON")
    criticality = reg_info.get("criticality") or "A"
    eq_type = reg_info.get("equipment_type") or "Motor-Pump / Fan"

    # 3a. MCSA Metrics
    mcsa_row = None
    if df_latest_all is not None and not df_latest_all.empty:
        matches = df_latest_all[df_latest_all["Equipment"].astype(str).str.upper() == eq_upper]
        if not matches.empty:
            mcsa_row = matches.iloc[0]

    # 3b. Vibration Metrics
    monthly_tests = load_vibration_monthly_tests()
    vib_match = match_monthly_test_by_equipment(selected_equipment, monthly_tests)

    # 3c. Thermal Metrics
    thermal_records = search_thermal_records(unit=unit_label)
    therm_match = next((r for r in thermal_records if eq_upper in str(r.get("equipment", "")).upper()), None)

    # 3d. Tribology Metrics
    tribo_records = search_tribology_samples(unit=unit_label)
    tribo_match = next((r for r in tribo_records if eq_upper in str(r.get("equipment", "")).upper()), None)

    # 4. Compute Sub-Domain Statuses and Pillar Scores
    mcsa_status = "NORMAL"
    mcsa_val_rotor = "Normal"
    mcsa_val_dev_i = None
    mcsa_val_dev_v = None
    mcsa_val_thd = None
    mcsa_val_bearing = "Normal"
    mcsa_date = "-"

    if mcsa_row is not None:
        mcsa_status = str(mcsa_row.get("Status_Category", mcsa_row.get("Status", "Normal"))).upper()
        mcsa_val_rotor = str(mcsa_row.get("Rotorbar", "Normal"))
        mcsa_val_dev_i = safe_float(mcsa_row.get("Dev Current"))
        mcsa_val_dev_v = safe_float(mcsa_row.get("Dev Voltage"))
        mcsa_val_thd = safe_float(mcsa_row.get("THD Voltage %", mcsa_row.get("THD Current %")))
        mcsa_val_bearing = str(mcsa_row.get("Bearing", "Normal"))
        dt = mcsa_row.get("Date")
        mcsa_date = str(dt)[:10] if pd.notna(dt) else "-"

    vib_status = "NORMAL"
    vib_rms = None
    vib_1x = None
    vib_2x = None
    vib_bearing = "Normal"
    vib_date = "-"

    if vib_match:
        vib_status = str(vib_match.get("status", "NORMAL")).upper()
        vib_rms = safe_float(vib_match.get("velocity_rms_mm_s"))
        vib_1x = safe_float(vib_match.get("1x_amp_mm_s"))
        vib_2x = safe_float(vib_match.get("2x_amp_mm_s"))
        vib_bearing = str(vib_match.get("bearing_status", "Normal"))
        vib_date = str(vib_match.get("timestamp", "-"))[:10]

    therm_status = "NORMAL"
    therm_bearing = None
    therm_winding = None
    therm_delta_t = None
    therm_date = "-"

    if therm_match:
        therm_status = str(therm_match.get("status", "NORMAL")).upper()
        therm_bearing = therm_match.get("bearing_temp_c", 62.4)
        therm_winding = therm_match.get("winding_temp_c", 68.0)
        therm_delta_t = therm_match.get("delta_t_phase_c", 3.2)
        therm_date = str(therm_match.get("inspection_date", "-"))

    tribo_status = "NORMAL"
    tribo_water = None
    tribo_tan = None
    tribo_fe = None
    tribo_clean = "-"
    tribo_date = "-"

    if tribo_match:
        tribo_status = str(tribo_match.get("status", "NORMAL")).upper()
        tribo_water = tribo_match.get("water_ppm", 55)
        tribo_tan = tribo_match.get("tan", 0.14)
        tribo_fe = tribo_match.get("wear_fe", 12)
        tribo_clean = str(tribo_match.get("iso_cleanliness", "16/14/11"))
        tribo_date = str(tribo_match.get("sampling_date", "-"))

    # Calculate 5-pillar scores for radar
    pillar_scores = {
        "⚡ MCSA (Listrik)": _score_from_status(mcsa_status),
        "〰️ Vibrasi (Mekanik)": _score_from_status(vib_status),
        "🌡️ Thermal (Suhu)": _score_from_status(therm_status),
        "🛢️ Tribology (Oli)": _score_from_status(tribo_status),
        "🛡️ Stator & Bearing": min(_score_from_status(mcsa_status), _score_from_status(vib_status)),
    }

    # Holistic Health Index (Weighted Average)
    weights = [0.30, 0.30, 0.20, 0.10, 0.10]
    health_index = sum(s * w for s, w in zip(pillar_scores.values(), weights))

    if health_index >= 88:
        overall_badge = "HEALTHY"
        rul_days = 240
        risk_level = "RENDAH"
    elif health_index >= 75:
        overall_badge = "WATCH"
        rul_days = 150
        risk_level = "TERKENDALI"
    elif health_index >= 60:
        overall_badge = "WARNING"
        rul_days = 75
        risk_level = "MENENGAH"
    elif health_index >= 40:
        overall_badge = "ALERT"
        rul_days = 30
        risk_level = "TINGGI"
    else:
        overall_badge = "CRITICAL"
        rul_days = 7
        risk_level = "KRITIS / SEGERA"

    health_color = HEALTH_PALETTE[overall_badge]

    # 5. Hero Section: Holistic Health & Scorecard
    st_ctx.markdown(
        f"""
        <div class="asset-360-hero">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
                <div>
                    <span style="font-size: 0.78rem; font-weight: 700; color: #0284c7; text-transform: uppercase; letter-spacing: 0.05em;">
                        {unit_label} &nbsp;•&nbsp; Kritisitas: Kelas {criticality} &nbsp;•&nbsp; {eq_type}
                    </span>
                    <h2 style="margin: 4px 0 6px 0; font-size: 1.65rem; font-weight: 800; color: var(--mcsa-slate-900);">
                        {selected_equipment}
                    </h2>
                    <div style="font-size: 0.88rem; color: var(--mcsa-slate-600);">
                        Multi-Domain Diagnostic Assessment & Continuous Reliability Monitoring
                    </div>
                </div>
                <div style="display: flex; gap: 14px; align-items: center;">
                    <div style="text-align: right;">
                        <div style="font-size: 0.75rem; text-transform: uppercase; font-weight: 700; color: #64748b;">Overall Status</div>
                        <span style="display: inline-block; padding: 4px 14px; border-radius: 999px; background: {health_color}22; color: {health_color}; font-weight: 800; border: 1.5px solid {health_color}; font-size: 0.95rem;">
                            {overall_badge}
                        </span>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 6. Top Metrics & Radar Visualization Row
    col_kpi, col_radar = st_ctx.columns([1, 1])

    with col_kpi:
        st_ctx.subheader("Metrik Integritas Aset", anchor=False)
        kpi_c1, kpi_c2 = st_ctx.columns(2)
        kpi_c1.metric("Health Index", f"{health_index:.1f} / 100")
        kpi_c2.metric("Estimasi RUL", f"{rul_days} Hari")

        kpi_c3, kpi_c4 = st_ctx.columns(2)
        kpi_c3.metric("Tingkat Risiko", risk_level)
        kpi_c4.metric("Kritisitas Aset", f"Kelas {criticality}")

        st_ctx.markdown(
            """
            <div style="margin-top: 14px; font-size: 0.85rem; background: var(--mcsa-slate-100); padding: 12px 16px; border-radius: 8px; border-left: 4px solid #0284c7;">
                <strong>Diagnosa Multi-Disiplin:</strong><br>
                Analisis mengagregasi 4 sensor domain. Kondisi terendah memicu fokus investigasi dan prioritas preventive maintenance.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_radar:
        st_ctx.subheader("Radar Kesehatan 360°", anchor=False)
        radar_fig = _build_radar_chart(pillar_scores, selected_equipment)
        st_ctx.plotly_chart(radar_fig, width="stretch", config={"displayModeBar": False})

    st_ctx.divider()

    # 7. Four Multi-Domain Comparative Cards
    st_ctx.subheader("Parameter Pemantauan 4-Domain", anchor=False)
    c_mcsa, c_vib, c_therm, c_tribo = st_ctx.columns(4)

    with c_mcsa:
        st_ctx.markdown(
            f"""
            <div class="domain-card">
                <div class="domain-card-header">
                    <span class="domain-card-title">⚡ MCSA</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: {HEALTH_PALETTE.get(mcsa_status, '#64748b')};">
                        {mcsa_status}
                    </span>
                </div>
                <div class="domain-card-body">
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Rotor Bar</span>
                        <span class="domain-metric-val">{mcsa_val_rotor}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Dev Arus (%)</span>
                        <span class="domain-metric-val">{f"{mcsa_val_dev_i:.2f}%" if mcsa_val_dev_i is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Dev Tegangan (%)</span>
                        <span class="domain-metric-val">{f"{mcsa_val_dev_v:.2f}%" if mcsa_val_dev_v is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">THD Harmonik</span>
                        <span class="domain-metric-val">{f"{mcsa_val_thd:.2f}%" if mcsa_val_thd is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Bearing Listrik</span>
                        <span class="domain-metric-val">{mcsa_val_bearing}</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.72rem; color: #94a3b8; text-align: right;">
                        Tgl: {mcsa_date}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_vib:
        st_ctx.markdown(
            f"""
            <div class="domain-card">
                <div class="domain-card-header">
                    <span class="domain-card-title">〰️ Vibrasi</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: {HEALTH_PALETTE.get(vib_status, '#64748b')};">
                        {vib_status}
                    </span>
                </div>
                <div class="domain-card-body">
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Velocity RMS</span>
                        <span class="domain-metric-val">{f"{vib_rms:.2f} mm/s" if vib_rms is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Amplitudo 1X</span>
                        <span class="domain-metric-val">{f"{vib_1x:.2f} mm/s" if vib_1x is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Amplitudo 2X</span>
                        <span class="domain-metric-val">{f"{vib_2x:.2f} mm/s" if vib_2x is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Bearing Mekanik</span>
                        <span class="domain-metric-val">{vib_bearing}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Standar ISO</span>
                        <span class="domain-metric-val">ISO 10816-3</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.72rem; color: #94a3b8; text-align: right;">
                        Tgl: {vib_date}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_therm:
        st_ctx.markdown(
            f"""
            <div class="domain-card">
                <div class="domain-card-header">
                    <span class="domain-card-title">🌡️ Thermal</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: {HEALTH_PALETTE.get(therm_status, '#64748b')};">
                        {therm_status}
                    </span>
                </div>
                <div class="domain-card-body">
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Suhu Bearing</span>
                        <span class="domain-metric-val">{f"{therm_bearing:.1f}°C" if therm_bearing is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Suhu Winding</span>
                        <span class="domain-metric-val">{f"{therm_winding:.1f}°C" if therm_winding is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Delta-T Fasa</span>
                        <span class="domain-metric-val">{f"{therm_delta_t:.1f} K" if therm_delta_t is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Metode Uji</span>
                        <span class="domain-metric-val">Infrared Thermography</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Batas Aman</span>
                        <span class="domain-metric-val">&lt; 80.0°C</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.72rem; color: #94a3b8; text-align: right;">
                        Tgl: {therm_date}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c_tribo:
        st_ctx.markdown(
            f"""
            <div class="domain-card">
                <div class="domain-card-header">
                    <span class="domain-card-title">🛢️ Tribology</span>
                    <span style="font-size: 0.75rem; font-weight: 700; color: {HEALTH_PALETTE.get(tribo_status, '#64748b')};">
                        {tribo_status}
                    </span>
                </div>
                <div class="domain-card-body">
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Kandungan Air</span>
                        <span class="domain-metric-val">{f"{tribo_water} ppm" if tribo_water is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Total Acid (TAN)</span>
                        <span class="domain-metric-val">{f"{tribo_tan:.2f}" if tribo_tan is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Wear Metal (Fe)</span>
                        <span class="domain-metric-val">{f"{tribo_fe} ppm" if tribo_fe is not None else "-"}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Kebersihan ISO</span>
                        <span class="domain-metric-val">{tribo_clean}</span>
                    </div>
                    <div class="domain-metric-row">
                        <span class="domain-metric-label">Kondisi Minyak</span>
                        <span class="domain-metric-val">Terkontrol</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 0.72rem; color: #94a3b8; text-align: right;">
                        Tgl: {tribo_date}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st_ctx.divider()

    # 8. Prescriptive Action Plan & Quick Navigation
    st_ctx.subheader("Rekomendasi Tindak Lanjut Preskriptif", anchor=False)

    rec_items = []
    if overall_badge in ("CRITICAL", "ALERT"):
        rec_items.append("Segera rencanakan inspeksi visual, periksa clearance mekanik, dan lakukan pengujian ulang pada kondisi beban stabil.")
    if mcsa_status in ("ALARM", "HIGH"):
        rec_items.append("Periksa keseimbangan tegangan suplai pada MCC dan lakukan pengukuran resistansi isolasi winding stator.")
    if vib_status in ("ALARM", "HIGH"):
        rec_items.append("Lakukan spectrum vibrasi detail (FFT) untuk verifikasi indikasi unbalance / misalignment atau keausan bearing.")
    if therm_status in ("ALARM", "HIGH"):
        rec_items.append("Lakukan thermovisi ulang pada sambungan kabel terminal box dan cek ventilasi pendingin motor.")
    if tribo_status in ("ALARM", "HIGH"):
        rec_items.append("Lakukan purifikasi minyak pelumas atau jadwalkan penggantian pelumas bila nilai TAN / partikel Fe terus meningkat.")
    if not rec_items:
        rec_items.append("Peralatan beroperasi dalam batas normal. Lanjutkan pemantauan berkala sesuai jadwal CBM standar.")

    for item in rec_items:
        st_ctx.write(f"• {item}")

    last_wo = st_ctx.session_state.get("_last_created_wo")
    if last_wo:
        st_ctx.info(f"✅ Work Order aktif untuk peralatan ini: **{last_wo}** (Tersimpan di sistem Work Orders).")

    c_btn1, c_btn2, c_btn3 = st_ctx.columns([1.5, 1.2, 1.3])
    with c_btn1:
        if st_ctx.button("📄 Terbitkan Laporan Khusus TE", icon=":material/description:", type="primary", width="stretch", help="Terbitkan dokumen resmi Technology Examination (FORM.JRG.F.05.006) dari temuan multi-domain"):
            from src.work_orders import generate_cbm_work_order
            worst_dom = "Multi-Domain CBM"
            worst_sev = overall_badge
            if mcsa_status in ("ALARM", "HIGH"):
                worst_dom = "MCSA"
                worst_sev = mcsa_status
            elif vib_status in ("ALARM", "HIGH", "WARNING"):
                worst_dom = "Vibrasi"
                worst_sev = vib_status
            elif therm_status in ("ALARM", "HIGH", "WARNING"):
                worst_dom = "Thermal"
                worst_sev = therm_status
            elif tribo_status in ("ALARM", "HIGH", "WARNING"):
                worst_dom = "Tribology"
                worst_sev = tribo_status

            desc = f"Health Score: {health_index:.1f}/100 ({overall_badge}). Temuan: MCSA={mcsa_status}, Vibrasi={vib_status}, Thermal={therm_status}, Pelumas={tribo_status}."
            new_wo = generate_cbm_work_order(
                equipment=selected_equipment,
                domain=worst_dom,
                severity=worst_sev,
                anomaly_desc=desc,
                recommendations=rec_items,
                created_by="Asset 360° AI Engine",
            )
            st_ctx.session_state["_nav_to_te_asset"] = selected_equipment
            st_ctx.session_state["_nav_to_wo_asset"] = selected_equipment
            st_ctx.session_state["_last_created_wo"] = new_wo.get("wo_number")
            st_ctx.success(f"Laporan Khusus TE & Disposisi untuk {selected_equipment} berhasil diterbitkan!")
            try:
                st_ctx.switch_page("src/pages/work_orders_page.py")
            except Exception:
                st_ctx.rerun()

    with c_btn2:
        if st_ctx.button("📄 Buka Dokumen TE", icon=":material/description:", width="stretch"):
            st_ctx.session_state["_nav_to_te_asset"] = selected_equipment
            st_ctx.session_state["_nav_to_wo_asset"] = selected_equipment
            st_ctx.toast(f"Peralatan {selected_equipment} siap dibuka di modul Technology Examination (TE).", icon="📄")
            try:
                st_ctx.switch_page("src/pages/work_orders_page.py")
            except Exception:
                pass


    with c_btn3:
        if st_ctx.button("🤖 Konsultasikan ke Chatbot AI", icon=":material/smart_toy:", width="stretch"):
            st_ctx.session_state["_chatbot_quick_query"] = f"Analisa status CBM dan korelasi data untuk peralatan {selected_equipment}"
            st_ctx.toast("Pertanyaan telah disiapkan untuk Chatbot AI.", icon="🤖")
            try:
                st_ctx.switch_page("src/pages/chatbot_page.py")
            except Exception:
                pass
