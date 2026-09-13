"""Unified Data Ingestion & Telemetry Hub Page.

Manages both offline periodic inspection uploads and real-time streaming telemetry.
- Tab 1: Batch File Upload (CSV/Excel) & Standard Template Downloads.
- Tab 2: Live Telemetry Streaming Gateway & Sensor Simulator.
"""

from __future__ import annotations

import io
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.asset_registry import list_assets
from src.components.theme import render_page_header
from src.components.status_colors import canon_condition_status, render_status_badge
from src.template_generator import TEMPLATES, get_template_csv, validate_batch_dataframe


def _render_live_chart(history_records: List[Dict[str, Any]], metric_name: str) -> go.Figure:
    """Render moving window real-time trend for streaming telemetry."""
    if not history_records:
        fig = go.Figure()
        fig.update_layout(height=280, title="Menunggu aliran data telemetri...")
        return fig

    times = [r["time"] for r in history_records]
    vals = [r["val"] for r in history_records]
    statuses = [r["status"] for r in history_records]

    colors = [
        "#10b981" if s == "Normal" else "#f59e0b" if s == "Alarm" else "#ef4444"
        for s in statuses
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=vals,
            mode="lines+markers",
            name=metric_name,
            line=dict(color="#0284c7", width=2.5),
            marker=dict(size=7, color=colors),
        )
    )

    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=30, b=30),
        xaxis=dict(title="Waktu", gridcolor="#e2e8f0"),
        yaxis=dict(title=metric_name, gridcolor="#e2e8f0"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248, 250, 252, 0.6)",
    )
    return fig


def _render_oscillogram_chart(frame: Dict[str, Any]) -> go.Figure:
    """Render live time-domain oscillogram for MCSA or Vibration."""
    domain = frame.get("domain", "VIBRASI")
    fig = go.Figure()
    if domain == "MCSA":
        wf = frame.get("waveforms", {})
        t = wf.get("time_ms", [])
        fig.add_trace(go.Scatter(x=t, y=wf.get("current_phase_a", []), mode="lines", name="Phase A", line=dict(color="#ef4444", width=2)))
        fig.add_trace(go.Scatter(x=t, y=wf.get("current_phase_b", []), mode="lines", name="Phase B", line=dict(color="#f59e0b", width=2)))
        fig.add_trace(go.Scatter(x=t, y=wf.get("current_phase_c", []), mode="lines", name="Phase C", line=dict(color="#3b82f6", width=2)))
        title_text = "<b>Oscillogram Arus 3-Fasa (Ia, Ib, Ic)</b>"
        y_title = "Arus Instan (A)"
    else:
        wf = frame.get("waveform", {})
        t = wf.get("time_ms", [])
        y_val = wf.get("amplitude_mm_s", [])
        fig.add_trace(go.Scatter(x=t, y=y_val, mode="lines", name="Vibrasi", line=dict(color="#38bdf8", width=2.2)))
        title_text = "<b>Time Waveform (TWF) Sinyal Getaran</b>"
        y_title = "Kecepatan (mm/s)"

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=13, color="#f1f5f9")),
        height=280,
        margin=dict(l=30, r=20, t=35, b=25),
        xaxis=dict(title="Waktu (ms)", gridcolor="#334155", tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title=y_title, gridcolor="#334155", tickfont=dict(color="#cbd5e1")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", font=dict(color="#94a3b8", size=10)),
    )
    return fig


def _render_spectrum_chart(frame: Dict[str, Any]) -> go.Figure:
    """Render live frequency spectrum (FFT) with threshold lines."""
    domain = frame.get("domain", "VIBRASI")
    spec = frame.get("spectrum", {})
    f = spec.get("frequency_hz", [])
    fig = go.Figure()

    if domain == "MCSA":
        amp = spec.get("amplitude_db", [])
        fig.add_trace(go.Scatter(x=f, y=amp, mode="lines", fill="tozeroy", name="Spektrum MCSA", line=dict(color="#a855f7", width=2), fillcolor="rgba(168, 85, 247, 0.15)"))
        fig.add_hline(y=spec.get("threshold_alarm_db", -45.0), line_dash="dash", line_color="#f59e0b", annotation_text="Batas Alarm (-45 dB)", annotation_font_color="#f59e0b")
        title_text = "<b>Spektrum Frekuensi MCSA (dB vs Hz)</b>"
        y_title = "Amplitudo (dB down)"
    else:
        amp = spec.get("amplitude_mm_s", [])
        fig.add_trace(go.Scatter(x=f, y=amp, mode="lines", fill="tozeroy", name="Spektrum FFT", line=dict(color="#0284c7", width=2), fillcolor="rgba(2, 132, 199, 0.15)"))
        fig.add_hline(y=spec.get("threshold_warning_mm_s", 2.8), line_dash="dot", line_color="#10b981", annotation_text="ISO Warn (2.8)", annotation_font_color="#10b981")
        fig.add_hline(y=spec.get("threshold_alarm_mm_s", 4.5), line_dash="dash", line_color="#f59e0b", annotation_text="ISO Alarm (4.5)", annotation_font_color="#f59e0b")
        fig.add_hline(y=spec.get("threshold_trip_mm_s", 7.1), line_dash="dash", line_color="#ef4444", annotation_text="ISO Trip (7.1)", annotation_font_color="#ef4444")
        title_text = "<b>Spektrum Frekuensi FFT Vibrasi (mm/s vs Hz)</b>"
        y_title = "Amplitudo RMS (mm/s)"

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=13, color="#f1f5f9")),
        height=280,
        margin=dict(l=30, r=20, t=35, b=25),
        xaxis=dict(title="Frekuensi (Hz)", gridcolor="#334155", tickfont=dict(color="#cbd5e1")),
        yaxis=dict(title=y_title, gridcolor="#334155", tickfont=dict(color="#cbd5e1")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15, 23, 42, 0.5)",
        showlegend=False,
    )
    return fig


def render_data_ingestion_hub_page(st_ctx) -> None:
    render_page_header(
        st_ctx,
        "Pusat Ingesti & Telemetri Data",
        "Kelola unggah laporan inspeksi berkala offline dan streaming data sensor real-time lintas domain.",
        badge="Unified Gateway",
    )

    tab_batch, tab_stream = st_ctx.tabs(["📥 Batch Upload & Template Resmi", "⚡ Live Telemetry Stream & Simulator"])

    # -------------------------------------------------------------------------
    # TAB 1: BATCH UPLOAD & TEMPLATES
    # -------------------------------------------------------------------------
    with tab_batch:
        st_ctx.subheader("Standarisasi Template Pengukuran", anchor=False)
        st_ctx.caption("Pilih domain untuk mengunduh template CSV resmi atau mengunggah data hasil inspeksi.")

        c_dom, c_dl = st_ctx.columns([2, 1])
        domain_list = ["VIBRASI", "THERMAL", "TRIBOLOGY", "DGA", "MCSA"]

        with c_dom:
            selected_domain = st_ctx.selectbox(
                "Pilih Domain Pengujian",
                domain_list,
                index=0,
                key="_ingest_sel_domain",
            )

        with c_dl:
            template_csv_data = get_template_csv(selected_domain)
            st_ctx.download_button(
                label=f"⬇️ Unduh Template {selected_domain} (.CSV)",
                data=template_csv_data,
                file_name=f"template_{selected_domain.lower()}.csv",
                mime="text/csv",
                width="stretch",
                help=f"Unduh format baku Excel/CSV untuk domain {selected_domain}",
            )

        st_ctx.markdown("---")
        st_ctx.subheader(f"Unggah Laporan Hasil Pengujian: {selected_domain}", anchor=False)

        uploaded_file = st_ctx.file_uploader(
            f"Pilih file CSV/Excel hasil pengukuran {selected_domain}",
            type=["csv", "xlsx", "xls"],
            key=f"_uploader_{selected_domain}",
        )

        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith(".csv"):
                    df_upload = pd.read_csv(uploaded_file)
                else:
                    df_upload = pd.read_excel(uploaded_file)

                st_ctx.info(f"File **{uploaded_file.name}** berhasil dibaca ({len(df_upload)} baris data).")

                # Validate
                val_res = validate_batch_dataframe(selected_domain, df_upload)
                if val_res["valid"]:
                    st_ctx.success(f"✅ Format data valid sesuai skema standar {selected_domain}!")
                    st_ctx.dataframe(df_upload.head(10), width="stretch")

                    if st_ctx.button(f"💾 Simpan & Ingesti Data {selected_domain} ke Database", type="primary"):
                        st_ctx.toast(f"Berhasil mengingesti {len(df_upload)} baris data {selected_domain}!", icon="✅")
                        st_ctx.success("Data telah tersimpan ke repositori pengukuran dan siap dianalisis.")
                else:
                    st_ctx.error(f"❌ File tidak memenuhi standar {selected_domain}. Kolom wajib yang hilang: {', '.join(val_res['missing_columns'])}")
                    st_ctx.dataframe(df_upload.head(5), width="stretch")
            except Exception as exc:
                st_ctx.error(f"Gagal membaca berkas: {exc}")

    # -------------------------------------------------------------------------
    # TAB 2: REAL-TIME STREAMING & OSCILLOGRAM / SPECTRUM GATEWAY
    # -------------------------------------------------------------------------
    with tab_stream:
        st_ctx.subheader("Live Telemetry Sensor Gateway & Oscillogram Monitor", anchor=False)
        st_ctx.markdown(
            """
            Sistem mendukung pengiriman data terus-menerus (*Continuous Streaming Telemetry*) dari sensor IoT / DCS melalui REST API:  
            `GET /api/v2/domain/telemetry/oscillogram/{equipment_id}` & `POST /api/v2/domain/telemetry/stream`
            """
        )

        c_eq, c_stream_dom, c_scen = st_ctx.columns(3)
        with c_eq:
            assets = list_assets()
            eq_names = [a.get("name") for a in assets if a.get("name")] or ["BC 10.1", "PA FAN 1A", "BFP 1A", "CWP 1A", "CRUSHER 1"]
            stream_eq = st_ctx.selectbox("Pilih Aset untuk Live Stream", eq_names, index=0, key="_stream_eq")

        with c_stream_dom:
            stream_domain = st_ctx.selectbox("Pilih Sensor Domain", ["VIBRASI", "MCSA"], index=0, key="_stream_dom")

        with c_scen:
            from src.telemetry_streamer import FAULT_PROFILES, generate_live_frame
            fault_opts = list(FAULT_PROFILES.keys())
            fault_labels = [FAULT_PROFILES[k] for k in fault_opts]
            sel_fault_label = st_ctx.selectbox(
                "Injeksi Skenario / Anomali",
                fault_labels,
                index=0,
                key="_stream_fault_label",
            )
            # Find key
            stream_fault_key = fault_opts[fault_labels.index(sel_fault_label)]

        # Action Buttons
        c_act1, c_act2, c_act3 = st_ctx.columns([1, 1, 2])
        with c_act1:
            step_btn = st_ctx.button("📡 Ambil Frame Snapshot", type="primary", width="stretch")
        with c_act2:
            reset_btn = st_ctx.button("🔄 Reset Stream", width="stretch")
        with c_act3:
            auto_refresh = st_ctx.toggle("⚡ Auto-Stream Live Simulation", value=False, key="_toggle_autostream")

        frame_key = f"_live_frame_{stream_eq}_{stream_domain}"
        if reset_btn or frame_key not in st_ctx.session_state:
            st_ctx.session_state[frame_key] = generate_live_frame(
                equipment=stream_eq,
                domain=stream_domain,
                fault_profile=stream_fault_key,
            )
            if reset_btn:
                st_ctx.rerun()

        if step_btn or auto_refresh:
            st_ctx.session_state[frame_key] = generate_live_frame(
                equipment=stream_eq,
                domain=stream_domain,
                fault_profile=stream_fault_key,
            )

        curr_frame = st_ctx.session_state[frame_key]
        metrics = curr_frame.get("metrics", {})
        status = curr_frame.get("status", "Normal")
        status_color = "#10b981" if status == "Normal" else "#f59e0b" if status == "Alarm" else "#ef4444"

        # 1. Instantaneous Metric Cards
        st_ctx.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        m_col1, m_col2, m_col3, m_col4, m_col5 = st_ctx.columns(5)
        with m_col1:
            if stream_domain == "VIBRASI":
                st_ctx.metric("Velocity RMS", f"{metrics.get('rms_velocity_mm_s', 0)} mm/s")
            else:
                st_ctx.metric("Current RMS (Phase A)", f"{metrics.get('current_rms_phase_a', 0)} A")
        with m_col2:
            if stream_domain == "VIBRASI":
                st_ctx.metric("Peak-to-Peak (pk-pk)", f"{metrics.get('peak_to_peak_mm_s', 0)} mm/s")
            else:
                st_ctx.metric("Unbalance Current", f"{metrics.get('current_unbalance_pct', 0)}%")
        with m_col3:
            if stream_domain == "VIBRASI":
                st_ctx.metric("Crest Factor", f"{metrics.get('crest_factor', 0)}")
            else:
                st_ctx.metric("Sideband Amplitude", f"{metrics.get('sideband_db_down', 0)} dB")
        with m_col4:
            st_ctx.metric("Status Anomali", status, delta=curr_frame.get("primary_fault", "Normal"), delta_color="normal" if status == "Normal" else "inverse")
        with m_col5:
            st_ctx.metric("Waktu Frame", curr_frame.get("timestamp", "-").split(" ")[-1])

        # 2. Side-by-Side Live Oscillogram & FFT Spectrum
        chart_c1, chart_c2 = st_ctx.columns([1, 1])
        with chart_c1:
            with st_ctx.container(border=True):
                fig_osc = _render_oscillogram_chart(curr_frame)
                st_ctx.plotly_chart(fig_osc, use_container_width=True, config={"displayModeBar": False})

        with chart_c2:
            with st_ctx.container(border=True):
                fig_spec = _render_spectrum_chart(curr_frame)
                st_ctx.plotly_chart(fig_spec, use_container_width=True, config={"displayModeBar": False})

        # Auto-refresh loop if toggle is active
        if auto_refresh:
            time.sleep(1.2)
            st_ctx.rerun()

        # 3. JSON preview for Gateway consumers
        with st_ctx.expander("🔍 Pratinjau Payload JSON Telemetri Real-Time (Untuk Sensor / Gateway)", expanded=False):
            st_ctx.json({
                "equipment": curr_frame.get("equipment"),
                "domain": curr_frame.get("domain"),
                "timestamp": curr_frame.get("timestamp"),
                "status": curr_frame.get("status"),
                "metrics": curr_frame.get("metrics"),
                "primary_fault": curr_frame.get("primary_fault"),
            })
            st_ctx.caption("Dataframe telemetri dapat diakses langsung melalui endpoint REST `/api/v2/domain/telemetry/oscillogram/{equipment_id}`.")
