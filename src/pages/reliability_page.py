"""Fleet Reliability Analytics Page for Streamlit UI.

Provides high-level engineering reliability insights across the entire plant:
- Fleet-wide Health Index distribution and average
- Critical Watchlist of high-risk assets
- Cross-domain reliability matrix (Equipment, Unit, Criticality, Failure Mode, RUL, Risk)
- Multi-unit comparison and filtering
"""

import pandas as pd
import streamlit as st

from pple.application.fleet import FleetReliabilityUseCase
from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.components.theme import render_page_header
from src.fleet_reliability import build_fleet_reliability

HEALTH_COLORS = {
    "HEALTHY": "#10B981",
    "WATCH": "#3B82F6",
    "WARNING": "#F59E0B",
    "ALERT": "#F97316",
    "CRITICAL": "#EF4444",
}


def render_reliability_page(st_context=st, df_latest_all: pd.DataFrame = None):
    render_page_header(
        st_context,
        "Reliability Command & Fleet Analytics",
        "Pemantauan komprehensif keandalan armada pembangkit, distribusi kondisi kesehatan, dan proyeksi Remaining Useful Life (RUL)",
    )

    if df_latest_all is None:
        try:
            from src.data_loader import get_latest_data
            df_latest_all = get_latest_data()
        except Exception:
            df_latest_all = None

    if df_latest_all is None or df_latest_all.empty:
        st_context.warning("Data pengukuran terbaru belum tersedia untuk analisis fleet reliability.")
        return

    # Compute fleet reliability
    try:
        use_case = FleetReliabilityUseCase()
        fleet_data = use_case.execute(df_latest_all, limit=80)
    except Exception:
        fusion_agent = ReliabilityFusionAgent()
        asset_graph = AssetKnowledgeGraph()
        fleet_data = build_fleet_reliability(df_latest_all, fusion_agent, asset_graph, limit=80)

    total_assets = fleet_data.get("total_assets", 0)
    avg_health = fleet_data.get("fleet_health_average", 90.0)
    summary = fleet_data.get("health_summary", {})
    watchlist = fleet_data.get("critical_watchlist", [])
    matrix = fleet_data.get("asset_matrix", [])

    # KPI Top Row
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st_context.columns(5)
    with kpi_col1:
        st_context.metric("Total Aset Terpantau", total_assets)
    with kpi_col2:
        st_context.metric("Rata-rata Health Index", f"{avg_health:.1f}%")
    with kpi_col3:
        st_context.metric("Kondisi Normal / Sehat", summary.get("HEALTHY", 0) + summary.get("WATCH", 0))
    with kpi_col4:
        st_context.metric("Perlu Perhatian (Warning/Alert)", summary.get("WARNING", 0) + summary.get("ALERT", 0))
    with kpi_col5:
        crit = summary.get("CRITICAL", 0)
        st_context.metric("Kritis (Immediate Action)", crit, delta=f"{crit} kritis" if crit > 0 else None, delta_color="inverse")

    st_context.markdown("---")

    # Critical Watchlist Section
    if watchlist:
        st_context.subheader("⚠️ Critical Watchlist (Aset Prioritas Tinggi)")
        st_context.caption("Peralatan dengan Health Index terendah atau terindikasi failure mode aktif yang membutuhkan tindakan segera.")

        watch_cols = st_context.columns(min(len(watchlist), 3))
        for idx, item in enumerate(watchlist[:3]):
            col = watch_cols[idx % 3]
            color = HEALTH_COLORS.get(item.get("health_status", "WARNING"), "#F59E0B")
            with col:
                with st_context.container(border=True):
                    st_context.markdown(
                        f"<div style='border-left: 4px solid {color}; padding-left: 8px;'>"
                        f"<h4 style='margin:0;'>{item.get('equipment', '-')}</h4>"
                        f"<span style='font-size:0.85rem;color:#64748b;'>{item.get('unit', '-')} · {item.get('system', '-')}</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st_context.markdown(f"**Health Index:** {item.get('health_index', 0):.1f}% · Status: **{item.get('health_status', '-')}**")
                    st_context.markdown(f"**Failure Mode:** {item.get('primary_failure_mode', '-')}")
                    st_context.markdown(f"⏳ **RUL:** {item.get('rul_days', '-')} hari · Risiko: **{item.get('risk_level', '-')}**")

    # Tab views: Fleet Distribution & Asset Matrix
    tab_matrix, tab_dist = st_context.tabs([":material/table_chart: Matriks Keandalan Aset (Full Fleet)", ":material/bar_chart: Distribusi Status & Unit"])

    with tab_matrix:
        # Filter controls
        with st_context.container(border=True):
            f_col1, f_col2, f_col3 = st_context.columns(3)
            with f_col1:
                units = ["Semua Unit"] + sorted(list({m.get("unit", "") for m in matrix if m.get("unit")}))
                sel_unit = st_context.selectbox("Filter Unit Pembangkit", units)
            with f_col2:
                statuses = ["Semua Status", "CRITICAL", "ALERT", "WARNING", "WATCH", "HEALTHY"]
                sel_status = st_context.selectbox("Filter Status Kesehatan", statuses)
            with f_col3:
                search_eq = st_context.text_input("Cari Nama Peralatan", placeholder="Ketik nama alat...")

        # Filter dataset
        filtered_matrix = []
        for m in matrix:
            if sel_unit != "Semua Unit" and m.get("unit") != sel_unit:
                continue
            if sel_status != "Semua Status" and m.get("health_status") != sel_status:
                continue
            if search_eq and search_eq.lower() not in m.get("equipment", "").lower():
                continue
            filtered_matrix.append(m)

        if filtered_matrix:
            df_display = pd.DataFrame([
                {
                    "Equipment": row.get("equipment", ""),
                    "Unit": row.get("unit", ""),
                    "Sistem": row.get("system", ""),
                    "Kritisitas": row.get("criticality", ""),
                    "Health Index": f"{row.get('health_index', 0):.1f}%",
                    "Status": row.get("health_status", ""),
                    "Failure Mode Utama": row.get("primary_failure_mode", ""),
                    "RUL (Hari)": row.get("rul_days", ""),
                    "Tingkat Risiko": row.get("risk_level", ""),
                }
                for row in filtered_matrix
            ])
            st_context.dataframe(df_display, width="stretch", hide_index=True)
            st_context.caption(f"Menampilkan {len(filtered_matrix)} dari total {len(matrix)} peralatan.")
        else:
            st_context.info("Tidak ada aset yang sesuai kriteria filter.")

    with tab_dist:
        st_context.subheader("Distribusi Status Kesehatan Armada")
        status_df = pd.DataFrame([
            {"Status": k, "Jumlah": v}
            for k, v in summary.items()
        ])
        st_context.bar_chart(status_df.set_index("Status"), y="Jumlah", color="#3B82F6")
