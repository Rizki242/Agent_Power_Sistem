"""Predictive Maintenance Scheduling & Outage Planning Page for Streamlit UI.

Provides executive outage planning and turnaround work bundling:
- Dynamic RUL vs Outage Timeline (Plotly Gantt Chart)
- Pre-Outage Trip Risk identification & urgent mitigation
- Bundled Outage Work Packages per Unit (Unit 1, Unit 2, Unit 3, BOP)
- Downtime reduction optimization & 1-click Turnaround Package dispatch
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.components.theme import render_page_header
from src.fleet_reliability import build_fleet_reliability
from src.outage_planner import (
    DEFAULT_OUTAGE_SCHEDULE,
    generate_outage_turnaround_package,
    plan_outage_maintenance,
)


def _build_gantt_chart(gantt_df: pd.DataFrame) -> go.Figure:
    """Builds an interactive dark-mode Gantt timeline using Plotly."""
    if gantt_df.empty:
        fig = go.Figure()
        fig.update_layout(height=260, title="Tidak ada data timeline outage.")
        return fig

    # Custom color map
    color_map = {
        "Jendela Outage Unit": "#0284c7",
        "🚨 Risiko Trip Pra-Outage": "#ef4444",
        "📦 Paket Ideal Outage": "#f59e0b",
        "🟢 Aman Pasca-Outage": "#10b981",
    }

    fig = px.timeline(
        gantt_df,
        x_start="Start",
        x_end="Finish",
        y="Task",
        color="Category",
        color_discrete_map=color_map,
        hover_data={"Start": True, "Finish": True, "Detail": True, "Category": False},
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=380,
        margin=dict(l=20, r=20, t=25, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            gridcolor="#334155",
            title="<b>Proyeksi Garis Waktu (Timeline) Outage & Depletion RUL</b>",
            title_font=dict(color="#94a3b8", size=12),
            tickfont=dict(color="#f1f5f9", size=11),
        ),
        yaxis=dict(
            gridcolor="#334155",
            title="",
            tickfont=dict(color="#f1f5f9", size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#cbd5e1", size=11),
        ),
    )
    return fig


def render_outage_planning_page(st_context=st, df_latest_all: pd.DataFrame = None):
    render_page_header(
        st_context,
        "Predictive Maintenance Scheduling & Outage Planning",
        "Optimasi penjadwalan pemeliharaan prediktif berbasis RUL (Remaining Useful Life), pengelompokan pekerjaan (Work Bundling), dan mitigasi risiko trip unit pembangkit",
        badge="Turnaround Optimization",
    )

    if df_latest_all is None:
        try:
            from src.data_loader import get_latest_data
            df_latest_all = get_latest_data()
        except Exception:
            df_latest_all = None

    if df_latest_all is None or df_latest_all.empty:
        st_context.warning("Data pengukuran terbaru belum tersedia untuk perencanaan outage.")
        return

    # Compute fleet reliability data
    fusion_agent = ReliabilityFusionAgent()
    asset_graph = AssetKnowledgeGraph()
    fleet_data = build_fleet_reliability(
        df_latest_all, fusion_agent, asset_graph, limit=80, include_multi_domain=True
    )
    asset_matrix = fleet_data.get("asset_matrix", [])

    # Correlate with Outage Planner Engine
    outage_plan = plan_outage_maintenance(asset_matrix)

    outage_schedules = outage_plan.get("outage_schedules", [])
    pre_outage_critical = outage_plan.get("pre_outage_critical", [])
    bundled_by_unit = outage_plan.get("bundled_by_unit", {})
    total_bundled = outage_plan.get("total_bundled_count", 0)
    saved_hours = outage_plan.get("saved_downtime_hours", 0)
    gantt_data = outage_plan.get("gantt_data", pd.DataFrame())

    # 1. Top Executive Metric Ribbon
    k1, k2, k3, k4 = st_context.columns(4)
    with k1:
        next_outage = outage_schedules[0] if outage_schedules else {}
        st_context.metric(
            "Outage Terdekat",
            f"{next_outage.get('unit', 'UNIT 1')} ({next_outage.get('days_until_outage', 45)} Hari)",
            help=f"Target: {next_outage.get('name', 'SI')}, Durasi: {next_outage.get('duration_days', 10)} hari",
        )
    with k2:
        st_context.metric(
            "Paket Aset Terkelompok (Bundled)",
            f"{total_bundled} Aset",
            help="Pekerjaan korektif & preventif yang dikelompokkan ke dalam jendela outage",
        )
    with k3:
        st_context.metric(
            "Estimasi Saved Downtime",
            f"{saved_hours} Jam",
            delta="Efisiensi Biaya Operasi",
            delta_color="normal",
            help="Jam downtime pembangkit yang dihemat melalui konsolidasi perbaikan dalam 1 shutdown terencana",
        )
    with k4:
        crit_count = len(pre_outage_critical)
        st_context.metric(
            "Risiko Trip Pra-Outage",
            f"{crit_count} Aset",
            delta=f"{crit_count} Butuh Mitigasi Cepat" if crit_count > 0 else "Nol Risiko Trip",
            delta_color="inverse" if crit_count > 0 else "normal",
            help="Aset yang RUL-nya habis sebelum jadwal outage dimulai (potensi trip paksa jika dibiarkan)",
        )

    st_context.markdown("---")

    # 2. Interactive Timeline / Gantt Chart
    st_context.markdown("### 📅 Garis Waktu Outage & Proyeksi RUL Peralatan (Predictive Gantt)")
    st_context.caption("Visualisasi perbandingan antara jendela jadwal Overhaul / Outage unit (balok biru) terhadap sisa umur manfaat (RUL) peralatan kritis.")

    with st_context.container(border=True):
        if not gantt_data.empty:
            fig_gantt = _build_gantt_chart(gantt_data)
            st_context.plotly_chart(fig_gantt, use_container_width=True, config={"displayModeBar": False})
        else:
            st_context.info("Data timeline sedang dikomputasi...")

    st_context.markdown("---")

    # 3. Pre-Outage Urgent Mitigation (High Risk Trip Mitigation)
    if pre_outage_critical:
        st_context.markdown("### 🚨 Aset Risiko Trip Pra-Outage (Urgent Action)")
        st_context.error(
            f"Perhatian: Terdapat **{len(pre_outage_critical)} peralatan** dengan estimasi RUL lebih pendek daripada hari menuju jadwal outage unit. "
            "Peralatan ini berisiko menyebabkan *Unplanned Outage* / *Trip Unit* bila menunggu jadwal shutdown reguler."
        )

        for p_idx, p_item in enumerate(pre_outage_critical):
            eq_name = p_item.get("equipment", "-")
            h_stat = p_item.get("health_status", "CRITICAL")
            rul_days = p_item.get("rul_lower_bound_days", 14)
            days_out = p_item.get("days_to_outage", 45)
            u_name = p_item.get("unit_normalized", "-")
            fm = p_item.get("primary_failure_mode", "-")
            rec = p_item.get("recommended_action", "-")

            with st_context.container(border=True):
                p_c1, p_c2, p_c3 = st_context.columns([3, 4, 2])
                with p_c1:
                    st_context.markdown(
                        f"<div style='border-left: 4px solid #ef4444; padding-left: 8px;'>"
                        f"<h4 style='margin:0; color:#f8fafc;'>{eq_name}</h4>"
                        f"<span style='font-size:0.82rem; color:#94a3b8;'>{u_name} · <b>Class {p_item.get('criticality', 'A')}</b> · Status: <span style='color:#ef4444;'>{h_stat}</span></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st_context.markdown(f"**Failure Mode:** {fm}")
                with p_c2:
                    st_context.markdown(
                        f"⏳ **RUL Sisa:** **{rul_days} hari** vs **Jadwal Outage:** **{days_out} hari lagi**  \n"
                        f"<span style='color:#fca5a5; font-size:0.85rem;'>⚠️ {rec}</span>",
                        unsafe_allow_html=True,
                    )
                with p_c3:
                    if st_context.button("📄 Rilis Dokumen TE", key=f"btn_pre_outage_{eq_name}", type="primary", use_container_width=True):
                        st_context.session_state["_nav_to_te_asset"] = eq_name
                        st_context.session_state["_nav_to_wo_asset"] = eq_name
                        st_context.session_state["_preselected_equipment"] = eq_name
                        st_context.toast(f"Membuka Laporan Khusus TE untuk {eq_name}...", icon="📄")
                        try:
                            st_context.switch_page("src/pages/work_orders_page.py")
                        except Exception:
                            st_context.info("Buka halaman Technology Examination (TE) untuk menyelesaikan laporan.")


        st_context.markdown("---")

    # 4. Unit Outage Work Packages (Work Bundling)
    st_context.markdown("### 📦 Pengelompokan Paket Kerja Outage (Work Bundling Hub)")
    st_context.caption("Peralatan yang telah dikelompokkan secara otomatis ke dalam jadwal outage masing-masing unit untuk dikerjakan serentak.")

    tab_u1, tab_u2, tab_u3, tab_bop = st_context.tabs([
        "⚡ Unit 1 (Simple Inspection)",
        "⚡ Unit 2 (Minor Overhaul)",
        "⚡ Unit 3 (Serious Inspection)",
        "⚙️ Balance of Plant (BOP)",
    ])

    unit_tabs_data = [
        ("UNIT 1", tab_u1, outage_schedules[0] if len(outage_schedules) > 0 else {}),
        ("UNIT 2", tab_u2, outage_schedules[1] if len(outage_schedules) > 1 else {}),
        ("UNIT 3", tab_u3, outage_schedules[2] if len(outage_schedules) > 2 else {}),
        ("COMMON", tab_bop, outage_schedules[3] if len(outage_schedules) > 3 else {}),
    ]

    for u_key, u_tab, out_info in unit_tabs_data:
        with u_tab:
            bundled_items = bundled_by_unit.get(u_key, [])

            # Outage Card Info
            with st_context.container(border=True):
                i_c1, i_c2, i_c3 = st_context.columns([3, 2, 2])
                with i_c1:
                    st_context.markdown(f"#### 🏷️ {out_info.get('name', u_key)}")
                    st_context.caption(out_info.get("description", "Pemeliharaan terjadwal"))
                with i_c2:
                    st_context.markdown(f"**Jadwal Mulai:** {out_info.get('start_date', '-')}")
                    st_context.markdown(f"**Durasi:** {out_info.get('duration_days', 14)} Hari")
                with i_c3:
                    st_context.markdown(f"**Sisa Waktu:** {out_info.get('days_until_outage', 60)} Hari")
                    st_context.markdown(f"**Total Scope Aset:** {len(bundled_items)} Peralatan")

            if bundled_items:
                st_context.markdown("##### 📋 Daftar Scope Peralatan yang Dibundel:")
                df_bundle = pd.DataFrame([
                    {
                        "Equipment": b.get("equipment"),
                        "Kritisitas": f"Class {b.get('criticality')}",
                        "Health Index": f"{b.get('health_index', 0):.1f}%",
                        "Status": b.get("health_status"),
                        "Failure Mode Utama": b.get("primary_failure_mode"),
                        "RUL (Hari)": b.get("rul_lower_bound_days"),
                        "Kategori Urgensi": b.get("urgency_label"),
                    }
                    for b in bundled_items
                ])
                st_context.dataframe(df_bundle, use_container_width=True, hide_index=True)

                # Package Generation Action
                pkg = generate_outage_turnaround_package(u_key, bundled_items, out_info)
                p_col1, p_col2 = st_context.columns([2, 1])
                with p_col1:
                    st_context.markdown(
                        f"**Suku Cadang Utama yang Harus Siap:**  \n"
                        + "\n".join([f"• {part}" for part in pkg.get("required_parts", [])[:4]])
                    )
                with p_col2:
                    st_context.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
                    if st_context.button(
                        f"📄 Terbitkan Dokumen TE Outage {u_key}",
                        key=f"btn_pkg_{u_key}",
                        type="primary",
                        use_container_width=True,
                        help=f"Terbitkan dokumen resmi Technology Examination outage {pkg.get('package_id')}",
                    ):
                        st_context.session_state["_last_outage_package"] = pkg
                        st_context.session_state["_nav_to_te_asset"] = bundled_items[0].get("equipment")
                        st_context.session_state["_nav_to_wo_asset"] = bundled_items[0].get("equipment")
                        st_context.toast(f"Dokumen TE Outage {pkg.get('package_id')} berhasil dikompilasi!", icon="📄")
                        st_context.success(f"✅ Dokumen TE Turnaround **{pkg.get('package_id')}** siap diunduh dan diterbitkan. Silakan buka halaman Technology Examination.")

            else:
                st_context.info(f"Tidak ada aset di {u_key} yang membutuhkan perbaikan mendesak saat outage terdekat.")

