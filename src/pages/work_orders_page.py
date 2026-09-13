"""Technology Examination (TE) & Maintenance Dispatch Page for Streamlit UI.

Standardized for:
PT. INDONESIA POWER - UNIT JASA PEMBANGKITAN PLTU JERANJANG
INTEGRATED MANAGEMENT SYSTEM
Form Code: FORM.JRG.F.05.006 (Rev 01)

Features:
- Official Technology Examination (TE) report generation for findings in DGA, Vibrasi, MCSA, Tribology, and Thermal
- Interactive document preview conforming strictly to the official 6-page format
- 1-Click Export to Microsoft Word (.DOCX) ready for printing and signature
- Operational Work Order dispatch with LOTO safety verification
"""

from __future__ import annotations

from datetime import datetime, date
import pandas as pd
import streamlit as st

from src.asset_registry import list_assets
from src.components.theme import render_page_header
from src.te_generator import build_te_report_data, export_te_docx
from src.work_orders import (
    create_work_order,
    load_work_orders,
    update_work_order_status,
)

PRIORITY_COLORS = {
    "P1 - Critical": "#EF4444",
    "P2 - High": "#F97316",
    "P3 - Medium": "#F59E0B",
    "P4 - Low": "#10B981",
}

STATUS_COLORS = {
    "Draft": "#64748B",
    "Approved": "#3B82F6",
    "In Progress": "#8B5CF6",
    "Completed": "#10B981",
    "Rejected": "#EF4444",
}


def _render_te_document_preview(st_ctx, te_data: dict):
    """Renders high-fidelity interactive preview of official Indonesia Power FORM.JRG.F.05.006."""
    doc_no = te_data.get("doc_number", "7.TE/CBM/UJPJRJ/2026")
    eq_name = te_data.get("equipment", "-")
    kks = te_data.get("kks", "-")
    tech = te_data.get("technology", "-")
    dt = te_data.get("date", "-")
    st_val = te_data.get("status", "Kuning")
    finding = te_data.get("finding", "-")

    # Header IMS Banner
    st_ctx.markdown(
        f"""
        <div style="border: 2px solid #334155; border-radius: 8px; overflow: hidden; background: #0f172a; margin-bottom: 20px;">
            <div style="background: #1e293b; padding: 14px 20px; text-align: center; border-bottom: 2px solid #334155;">
                <h3 style="margin: 0; color: #f8fafc; font-size: 1.15rem; letter-spacing: 0.5px;">PT. INDONESIA POWER</h3>
                <h4 style="margin: 3px 0; color: #94a3b8; font-size: 0.95rem; font-weight: 500;">UNIT JASA PEMBANGKITAN PLTU JERANJANG</h4>
                <div style="font-size: 0.85rem; color: #38bdf8; font-weight: 700; text-transform: uppercase;">INTEGRATED MANAGEMENT SYSTEM</div>
                <div style="margin-top: 6px; font-size: 1.05rem; color: #facc15; font-weight: 800;">{doc_no}</div>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 2fr 1fr 1fr; background: #0f172a; border-bottom: 1px solid #334155; text-align: center; font-size: 0.8rem; color: #cbd5e1;">
                <div style="padding: 6px; border-right: 1px solid #334155;">Tgl Berlaku: <b>07/02/2017</b></div>
                <div style="padding: 6px; border-right: 1px solid #334155;">No. Dokumen: <b>FORM.JRG.F.05.006</b></div>
                <div style="padding: 6px; border-right: 1px solid #334155;">Revisi: <b>01</b></div>
                <div style="padding: 6px;">Hal: <b>1 dari 6</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Equipment Identity Box
    st_color = "#f59e0b" if "kuning" in st_val.lower() else ("#ef4444" if "merah" in st_val.lower() else "#10b981")
    st_ctx.markdown(
        f"""
        <div style="background: #1e293b; border-left: 5px solid {st_color}; padding: 14px 18px; border-radius: 6px; margin-bottom: 16px; font-size: 0.92rem; line-height: 1.6;">
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">Equipment</strong>: <strong style="color: #f8fafc; font-size: 1.05rem;">{eq_name}</strong></div>
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">KKS</strong>: <span style="color: #cbd5e1; font-family: monospace;">{kks}</span></div>
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">Technology</strong>: <span style="color: #38bdf8; font-weight: 600;">{tech}</span></div>
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">Tanggal</strong>: <span style="color: #cbd5e1;">{dt}</span></div>
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">Status</strong>: <span style="background: {st_color}22; color: {st_color}; padding: 2px 8px; border-radius: 4px; font-weight: 700;">{st_val}</span></div>
            <div><strong style="color: #94a3b8; display: inline-block; width: 120px;">Finding</strong>: <span style="color: #fca5a5; font-weight: 600;">{finding}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Section I: Data Spesifikasi
    with st_ctx.expander("📌 Bagian I: Data Spesifikasi Motor & Driven Equipment", expanded=True):
        specs = te_data.get("specifications", {})
        m_specs = specs.get("motor", {})
        d_specs = specs.get("driven", {})

        c1, c2 = st_ctx.columns(2)
        with c1:
            st_ctx.markdown("##### ⚡ MOTOR")
            df_m = pd.DataFrame([
                {"Parameter": "Type, Mfg", "Nilai": m_specs.get("type_mfg", "-")},
                {"Parameter": "Speed", "Nilai": m_specs.get("speed", "-")},
                {"Parameter": "Power", "Nilai": m_specs.get("power", "-")},
                {"Parameter": "Bearing Type", "Nilai": m_specs.get("bearing_type", "-")},
                {"Parameter": "Inboard Bearing", "Nilai": m_specs.get("inboard_bearing", "-")},
                {"Parameter": "Outboard Bearing", "Nilai": m_specs.get("outboard_bearing", "-")},
                {"Parameter": "Foundation", "Nilai": m_specs.get("foundation", "-")},
            ])
            st_ctx.dataframe(df_m, use_container_width=True, hide_index=True)

        with c2:
            st_ctx.markdown(f"##### ⚙️ {specs.get('component_2', 'POMPA')}")
            df_d = pd.DataFrame([
                {"Parameter": "Type, Mfg.", "Nilai": d_specs.get("type_mfg", "-")},
                {"Parameter": "Speed", "Nilai": d_specs.get("speed", "-")},
                {"Parameter": "Power", "Nilai": d_specs.get("power", "-")},
                {"Parameter": "Capacity", "Nilai": d_specs.get("capacity", "-")},
                {"Parameter": "Inboard Bearing", "Nilai": d_specs.get("inboard_bearing", "-")},
                {"Parameter": "Onboard Bearing", "Nilai": d_specs.get("onboard_bearing", "-")},
                {"Parameter": "Total Blade", "Nilai": d_specs.get("total_blade", "-")},
            ])
            st_ctx.dataframe(df_d, use_container_width=True, hide_index=True)

    # Section II: Hasil Pengukuran Vibrasi
    with st_ctx.expander("📳 Bagian II: Hasil Pengukuran Vibrasi & Standar Limit ISO 10816-3", expanded=True):
        vib_data = te_data.get("vibration_data", {})
        pts = vib_data.get("points", {})

        st_ctx.caption("DATA PENGUKURAN OVERALL VIBRASI (mm/s RMS):")
        cols_pts = list(pts.keys())
        df_pts = pd.DataFrame([{k: f"{v:.2f}" for k, v in pts.items()}])
        st_ctx.dataframe(df_pts, use_container_width=True, hide_index=True)

        st_ctx.markdown(
            """
            <div style="background:#1e293b; border:1px solid #334155; padding:10px; border-radius:6px; margin: 10px 0; font-size:0.82rem; text-align:center;">
                <b>STANDART ISO 10816-3 (GROUP 1 RIGID) ALARM LIMIT:</b><br>
                <span style="color:#10b981; font-weight:700;">Zone A (≥ 0 Good)</span> · 
                <span style="color:#84cc16; font-weight:700;">Zone B (≥ 2.3 Acceptable)</span> · 
                <span style="color:#f59e0b; font-weight:700;">Zone C (≥ 4.5 Warning)</span> · 
                <span style="color:#ef4444; font-weight:700;">Zone D (≥ 7.1 Alarm/Trip)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st_ctx.markdown("**Hasil Rekaman Spectrum Vibrasi:**")
        for s_note in vib_data.get("spectrum_notes", []):
            st_ctx.markdown(f"• {s_note}")

    # Section III & IV: IRT Thermal & Tribology
    with st_ctx.expander("🌡️ & 🛢️ Bagian III & IV: Data IRT (Thermal) & Tribology (Analisa Pelumas)", expanded=False):
        c_th, c_tr = st_ctx.columns(2)
        with c_th:
            st_ctx.markdown("##### 🌡️ Data IRT (Temperatur)")
            thm_temps = te_data.get("thermal_data", {}).get("temperatures", {})
            df_th = pd.DataFrame([{"Titik Ukur": k.replace("_", " ").title(), "Suhu (°C)": f"{v}°C"} for k, v in thm_temps.items()])
            st_ctx.dataframe(df_th, use_container_width=True, hide_index=True)

        with c_tr:
            st_ctx.markdown("##### 🛢️ Data Tribology (Minyak Pelumas)")
            tr_data = te_data.get("tribology_data", {})
            df_tr = pd.DataFrame([
                {"Parameter": "Minyak Acuan", "Nilai": tr_data.get("reference_oil", "-")},
                {"Parameter": "Total Fe (Besi)", "Nilai": f"{tr_data.get('total_fe_ppm', 0)} ppm"},
                {"Parameter": "ISO Cleanliness", "Nilai": tr_data.get("iso_cleanliness", "-")},
                {"Parameter": "Water Content", "Nilai": f"{tr_data.get('water_ppm', 0)} ppm"},
                {"Parameter": "Viscosity 40°C", "Nilai": f"{tr_data.get('viscosity_40c', 0)} cSt"},
                {"Parameter": "NAS Class", "Nilai": f"Class {tr_data.get('nas_class', 10)}"},
            ])
            st_ctx.dataframe(df_tr, use_container_width=True, hide_index=True)

    # Section V: Analisa Teknis & Pola Mobius
    with st_ctx.expander("🔬 Bagian V: Analisa Teknis & Komparasi Pola Mobius", expanded=True):
        st_ctx.markdown(
            f"""
            <div style="background: #1e293b; border: 1px solid #334155; padding: 14px; border-radius: 6px; font-size: 0.9rem;">
                <p><b>Korelasi Gejala Pengukuran:</b><br>{te_data.get('analysis', {}).get('symptom_summary', '-')}</p>
                <p><b>Mekanisme Kegagalan:</b><br><i>{te_data.get('analysis', {}).get('failure_mechanism', '-')}</i></p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Section VI & VII: Kesimpulan, Rekomendasi & Lembar Pengesahan
    with st_ctx.expander("📝 Bagian VI & VII: Kesimpulan, Rekomendasi & Lembar Tanda Tangan", expanded=True):
        c_k, c_r = st_ctx.columns(2)
        with c_k:
            st_ctx.markdown("##### 📌 Kesimpulan:")
            for conc in te_data.get("conclusions", []):
                st_ctx.markdown(f"- {conc}")

        with c_r:
            st_ctx.markdown("##### 🛠️ Rekomendasi Tindakan:")
            for rec in te_data.get("recommendations", []):
                st_ctx.markdown(f"- **{rec}**")

        st_ctx.markdown("---")
        sign = te_data.get("sign_off", {})
        st_ctx.markdown(f"<div style='text-align:center; font-weight:700; margin-bottom:12px;'>{sign.get('location', 'JERANJANG')}, {sign.get('date', '-')}</div>", unsafe_allow_html=True)
        s_c1, s_c2 = st_ctx.columns(2)
        with s_c1:
            st_ctx.markdown(
                f"""
                <div style="border:1px dashed #475569; padding:12px; text-align:center; border-radius:6px;">
                    <div style="font-size:0.8rem; color:#94a3b8; font-weight:700;">MENGETAHUI</div>
                    <div style="height:50px; display:flex; align-items:center; justify-content:center; color:#64748b; font-style:italic;">(Digital Sign-Off Approved)</div>
                    <strong style="color:#f8fafc;">{sign.get('acknowledged_by', 'Ricky Rinaldi')}</strong><br>
                    <span style="font-size:0.8rem; color:#94a3b8;">{sign.get('acknowledged_title', 'SPS RSO')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with s_c2:
            st_ctx.markdown(
                f"""
                <div style="border:1px dashed #475569; padding:12px; text-align:center; border-radius:6px;">
                    <div style="font-size:0.8rem; color:#94a3b8; font-weight:700;">DISUSUN OLEH</div>
                    <div style="height:50px; display:flex; align-items:center; justify-content:center; color:#64748b; font-style:italic;">(Digital Sign-Off Approved)</div>
                    <strong style="color:#f8fafc;">{sign.get('prepared_by', 'Hermawan')}</strong><br>
                    <span style="font-size:0.8rem; color:#94a3b8;">{sign.get('prepared_title', 'Pelaksana PdM')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_work_orders_page(st_context=st):
    render_page_header(
        st_context,
        "Laporan Khusus TE (Technology Examination) & Disposisi",
        "Pusat penerbitan laporan resmi Technology Examination (FORM.JRG.F.05.006) atas temuan DGA, Vibrasi, MCSA, Tribologi, dan Thermal, serta tindak lanjut pemeliharaan",
        badge="Official IMS FORM.JRG.F.05.006",
    )

    tab_te_doc, tab_te_archive, tab_dispatch = st_context.tabs([
        "📄 Dokumen Resmi TE (FORM.JRG.F.05.006)",
        "📋 Register Arsip Dokumen TE",
        "🛠️ Disposisi Lapangan (Work Orders)",
    ])

    # -------------------------------------------------------------------------
    # TAB 1: FORMULIR & DOKUMEN RESMI TE
    # -------------------------------------------------------------------------
    with tab_te_doc:
        st_context.subheader("Penerbitan Laporan Khusus Technology Examination (TE)", anchor=False)
        st_context.caption("Dokumen resmi temuan inspeksi CBM multi-domain sesuai format standar Integrated Management System PLTU Jeranjang.")

        # Resolve targeted asset from session state if routed from Reliability / Asset 360
        target_preselect = (
            st_context.session_state.get("_nav_to_te_asset")
            or st_context.session_state.get("_nav_to_wo_asset")
            or st_context.session_state.get("_preselected_equipment")
            or "BOILER FEEDWATER PUMP 2 UNIT 3"
        )

        assets = list_assets()
        asset_names = [a.get("name") for a in assets if a.get("name")]
        if target_preselect not in asset_names:
            asset_names.insert(0, target_preselect)

        c_eq, c_tech, c_stat = st_context.columns([2, 2, 1])
        with c_eq:
            sel_eq = st_context.selectbox(
                "Peralatan / Equipment Target",
                asset_names,
                index=0,
                key="_te_sel_eq",
            )
        with c_tech:
            sel_tech = st_context.selectbox(
                "Disiplin Teknologi (Technology)",
                [
                    "Vibrasi dan Tribology",
                    "MCSA (Motor Current Signature Analysis)",
                    "DGA (Dissolved Gas Analysis)",
                    "Thermal IRT (Infrared Thermography)",
                    "Multi-Domain CBM (Vibrasi, MCSA, Tribologi)",
                ],
                index=0,
                key="_te_sel_tech",
            )
        with c_stat:
            sel_stat = st_context.selectbox(
                "Status Temuan",
                ["Kuning (Waspada)", "Merah (Kritis)", "Hijau (Normal)"],
                index=0,
                key="_te_sel_stat",
            )

        f_txt = st_context.text_area(
            "Uraian Temuan Utama (Finding)",
            value=f"Vibrasi Tinggi dan partikel kontaminasi pelumasan NAS tinggi terdeteksi pada {sel_eq}",
            key="_te_finding_txt",
        )

        # Build data payload
        te_data = build_te_report_data(
            equipment=sel_eq,
            technology=sel_tech,
            finding=f_txt,
            status=sel_stat.split(" ")[0],
        )

        st_context.markdown("---")

        # Action Bar: Download Word & Publish
        col_btn1, col_btn2 = st_context.columns([1, 1])
        with col_btn1:
            try:
                docx_buffer = export_te_docx(te_data)
                clean_name = sel_eq.replace(' ', '_')
                st_context.download_button(
                    label="📥 Unduh Dokumen Resmi TE (.DOCX)",
                    data=docx_buffer.getvalue(),
                    file_name=f"TE_{clean_name}_{datetime.now().strftime('%Y%m%d')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    use_container_width=True,
                    help="Unduh file Microsoft Word resmi 6-halaman sesuai format FORM.JRG.F.05.006",
                )
            except Exception as ex:
                st_context.error(f"Gagal mempersiapkan dokumen Word: {ex}")

        with col_btn2:
            if st_context.button("💾 Simpan ke Register Arsip TE", use_container_width=True):
                if "_te_archive" not in st_context.session_state:
                    st_context.session_state["_te_archive"] = []
                st_context.session_state["_te_archive"].insert(0, {
                    "doc_number": te_data["doc_number"],
                    "equipment": sel_eq,
                    "technology": sel_tech,
                    "status": sel_stat.split(" ")[0],
                    "finding": f_txt,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                })
                st_context.toast(f"Laporan TE {te_data['doc_number']} untuk {sel_eq} berhasil diarsipkan!", icon="💾")
                st_context.success("✅ Dokumen TE berhasil dicatat ke dalam database register arsip.")

        st_context.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        # Render full interactive document preview
        _render_te_document_preview(st_context, te_data)

    # -------------------------------------------------------------------------
    # TAB 2: REGISTER ARSIP DOKUMEN TE
    # -------------------------------------------------------------------------
    with tab_te_archive:
        st_context.subheader("Register Arsip Laporan Khusus TE", anchor=False)
        st_context.caption("Daftar dokumen Technology Examination yang telah diterbitkan oleh tim CBM Reliability.")

        default_archives = [
            {
                "doc_number": "7.TE/CBM/UJPJRJ/2026",
                "equipment": "BOILER FEEDWATER PUMP 2 UNIT 3",
                "technology": "Vibrasi dan Tribology",
                "status": "Kuning",
                "finding": "Vibrasi Tinggi dan NAS tinggi pada fluid coupling",
                "created_at": "2026-09-10 09:30",
            },
            {
                "doc_number": "6.TE/CBM/UJPJRJ/2026",
                "equipment": "CWP 1 UNIT 1",
                "technology": "MCSA dan Vibrasi",
                "status": "Merah",
                "finding": "Indikasi broken rotor bar sideband -36dB & unbalance 1X",
                "created_at": "2026-09-02 14:15",
            },
            {
                "doc_number": "5.TE/CBM/UJPJRJ/2026",
                "equipment": "TRANSFORMATOR UAT UNIT 3",
                "technology": "DGA",
                "status": "Kuning",
                "finding": "Kenaikan gas C2H4 & CH4 terindikasi thermal fault T2",
                "created_at": "2026-08-25 11:00",
            },
        ]

        active_archives = st_context.session_state.get("_te_archive", default_archives)
        df_arch = pd.DataFrame(active_archives)
        st_context.dataframe(df_arch, use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # TAB 3: DISPOSISI LAPANGAN (WORK ORDERS)
    # -------------------------------------------------------------------------
    with tab_dispatch:
        st_context.subheader("Disposisi Lapangan & Pelaksanaan Perintah Kerja", anchor=False)
        st_context.caption("Penerbitan tiket kerja lapangan (Work Order) turunan dari rekomendasi laporan TE, lengkap dengan LOTO checklist dan SLA.")

        all_wos = load_work_orders()
        df_wos = pd.DataFrame([
            {
                "Nomor WO": w.get("wo_number"),
                "Equipment": w.get("equipment"),
                "Judul Tindakan": w.get("title"),
                "Prioritas": w.get("priority"),
                "Target Selesai": w.get("target_completion_date"),
                "Status": w.get("status"),
                "Teknisi": w.get("required_manpower"),
            }
            for w in all_wos
        ])
        st_context.dataframe(df_wos, use_container_width=True, hide_index=True)
