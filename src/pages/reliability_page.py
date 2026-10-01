"""Fleet Reliability Analytics Page for Streamlit UI.

Provides executive-grade engineering reliability insights across the entire plant:
- Plant-wide Health Index distribution and multi-unit scorecards
- Interactive 2D Risk & Criticality Heatmap Matrix (Plotly)
- Top 10 Bad Actors Ranking with multi-domain triage & 1-click prescriptive dispatch
- Cross-domain reliability matrix (Equipment, Unit, Criticality, Failure Mode, RUL, Risk)
- Management CSV export
"""

from __future__ import annotations

from typing import Any, Dict, List
import pandas as pd
import plotly.graph_objects as go
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


def _build_risk_heatmap_figure(risk_grid: Dict[str, Any]) -> go.Figure:
    """Builds an interactive 2D Risk & Criticality Heatmap (Consequence vs Probability of Failure)."""
    x_cats = risk_grid.get("x", ["Class C (Low)", "Class B (Medium)", "Class A (Critical)"])
    y_cats = risk_grid.get("y", ["CRITICAL", "ALERT", "WARNING", "HEALTHY / WATCH"])
    z_vals = risk_grid.get("z", [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]])
    text_vals = risk_grid.get("text", [["0", "0", "0"], ["0", "0", "0"], ["0", "0", "0"], ["0", "0", "0"]])
    hover_vals = risk_grid.get("hover", [["", "", ""], ["", "", ""], ["", "", ""], ["", "", ""]])

    # Enterprise risk gradient: deep slate for 0 assets, emerald, amber, orange, ruby red for max
    colorscale = [
        [0.0, "rgba(30, 41, 59, 0.7)"],
        [0.15, "rgba(16, 185, 129, 0.75)"],
        [0.45, "rgba(245, 158, 11, 0.85)"],
        [0.75, "rgba(249, 115, 22, 0.9)"],
        [1.0, "rgba(239, 68, 68, 0.95)"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=x_cats,
            y=y_cats,
            text=text_vals,
            texttemplate="%{text}",
            textfont=dict(size=18, color="#ffffff", family="Inter, sans-serif"),
            hovertext=hover_vals,
            hoverinfo="text",
            colorscale=colorscale,
            showscale=False,
            xgap=4,
            ygap=4,
        )
    )

    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=25, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            title="<b>Consequence of Failure (Kritisitas Aset)</b>",
            title_font=dict(color="#94a3b8", size=12),
            tickfont=dict(color="#f1f5f9", size=11),
            side="bottom",
            showgrid=False,
        ),
        yaxis=dict(
            title="<b>Probability of Failure (Kondisi Degradasi)</b>",
            title_font=dict(color="#94a3b8", size=12),
            tickfont=dict(color="#f1f5f9", size=11),
            showgrid=False,
        ),
    )
    return fig


def render_reliability_page(st_context=st, df_latest_all: pd.DataFrame = None):
    render_page_header(
        st_context,
        "Executive Fleet Reliability & Risk Command Center",
        "Pemantauan komprehensif keandalan armada pembangkit, 2D Risk Heatmap Matrix, analisis multi-unit, dan mitigasi proaktif Bad Actors",
        badge="Executive Reliability",
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

    # Compute fleet reliability using UseCase or fallback
    try:
        use_case = FleetReliabilityUseCase()
        fleet_data = use_case.execute(df_latest_all, limit=80, include_multi_domain=True)
    except Exception:
        fusion_agent = ReliabilityFusionAgent()
        asset_graph = AssetKnowledgeGraph()
        fleet_data = build_fleet_reliability(df_latest_all, fusion_agent, asset_graph, limit=80, include_multi_domain=True)

    coverage = fleet_data.get("coverage") or {}
    contract = fleet_data.get("parity_contract") or {}
    if coverage.get("headline"):
        st_context.info(coverage["headline"])
    if contract.get("ownership_note"):
        st_context.caption(contract["ownership_note"])

    total_assets = fleet_data.get("total_assets", 0)
    avg_health = fleet_data.get("fleet_health_average")
    health_label = fleet_data.get("fleet_health_label") or ("UNKNOWN" if avg_health is None else f"{avg_health:.1f}")
    summary = fleet_data.get("health_summary", {})
    unit_summary = fleet_data.get("unit_summary", {})
    risk_grid = fleet_data.get("risk_grid", {})
    bad_actors = fleet_data.get("bad_actors", [])
    matrix = fleet_data.get("asset_matrix", [])

    # 1. Top Executive Metric Ribbon
    kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st_context.columns(5)
    with kpi_col1:
        st_context.metric("Total Aset Terpantau", f"{total_assets} Aset", help="Total unit motor dan pompa terpantau secara berkala")
    with kpi_col2:
        st_context.metric("Rata-rata Plant Health", health_label if avg_health is None else f"{health_label}%")
    with kpi_col3:
        normal_cnt = summary.get("HEALTHY", 0) + summary.get("WATCH", 0)
        st_context.metric("Armada Sehat / Siap", f"{normal_cnt} Aset", delta="Kondisi Prima", delta_color="normal")
    with kpi_col4:
        warn_cnt = summary.get("WARNING", 0) + summary.get("ALERT", 0)
        st_context.metric("Perhatian & Waspada", f"{warn_cnt} Aset", delta=f"{warn_cnt} Terdegradasi" if warn_cnt > 0 else None, delta_color="off")
    with kpi_col5:
        crit_cnt = summary.get("CRITICAL", 0)
        st_context.metric("Kritis (Butuh Tindakan Segera)", f"{crit_cnt} Aset", delta=f"{crit_cnt} Kritis Aktif" if crit_cnt > 0 else None, delta_color="inverse")

    st_context.markdown("---")

    # 2. Multi-Unit Fleet Scorecard
    st_context.markdown("### 🏢 Multi-Unit Fleet Scorecards")
    st_context.caption("Ringkasan komparasi keandalan dan ketersediaan aset per unit pembangkit PLTU Jeranjang")

    unit_cols = st_context.columns(4)
    unit_display_map = [
        ("UNIT 1", "⚡ Unit 1 (PLTU)", "#38bdf8"),
        ("UNIT 2", "⚡ Unit 2 (PLTU)", "#818cf8"),
        ("UNIT 3", "⚡ Unit 3 (PLTU)", "#a855f7"),
        ("COMMON", "⚙️ Balance of Plant (BOP)", "#94a3b8"),
    ]

    for idx, (u_key, u_title, accent_col) in enumerate(unit_display_map):
        u_info = unit_summary.get(u_key, {"total": 0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0})
        with unit_cols[idx]:
            with st_context.container(border=True):
                st_context.markdown(
                    f"<div style='border-left: 3px solid {accent_col}; padding-left: 8px; margin-bottom: 8px;'>"
                    f"<strong style='font-size: 0.95rem; color: #f8fafc;'>{u_title}</strong>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                u_avg = u_info.get("avg_health")
                u_label = "UNKNOWN" if not u_info.get("health_known") else f"{u_avg:.1f}%"
                u_crit = u_info.get("CRITICAL", 0)
                u_warn = u_info.get("WARNING", 0) + u_info.get("ALERT", 0)
                u_ok = u_info.get("HEALTHY", 0) + u_info.get("WATCH", 0)
                u_tot = u_info.get("total", 0)

                m_col1, m_col2 = st_context.columns([1, 1])
                with m_col1:
                    st_context.metric("Health Index", u_label)
                with m_col2:
                    st_context.metric("Total Aset", f"{u_tot}")

                # Status pill breakdown
                st_context.markdown(
                    f"<div style='display:flex; gap:6px; font-size:0.78rem; margin-top:4px;'>"
                    f"<span style='background:rgba(16,185,129,0.15); color:#10B981; padding:2px 6px; border-radius:4px;'>✔ {u_ok} Sehat</span>"
                    f"<span style='background:rgba(245,158,11,0.15); color:#F59E0B; padding:2px 6px; border-radius:4px;'>▲ {u_warn} Warning</span>"
                    f"<span style='background:rgba(239,68,68,0.15); color:#EF4444; padding:2px 6px; border-radius:4px;'>✖ {u_crit} Kritis</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    st_context.markdown("---")

    # 3. Interactive 2D Risk & Criticality Heatmap Matrix
    st_context.markdown("### 🎯 Matriks Risiko & Kritisitas Armada (2D Risk Heatmap)")
    st_context.caption("Pemetaan probabilitas kegagalan (Probability of Failure) terhadap tingkat dampak kritisitas aset (Consequence of Failure). Arahkan kursor pada sel matriks untuk melihat daftar aset terkait.")

    heat_col, desc_col = st_context.columns([3, 2])

    with heat_col:
        with st_context.container(border=True):
            if risk_grid:
                fig_hm = _build_risk_heatmap_figure(risk_grid)
                st_context.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})
            else:
                st_context.info("Data matriks risiko belum terkomputasi.")

    with desc_col:
        with st_context.container(border=True):
            st_context.markdown("#### 🧭 Panduan Interpretasi & Mitigasi Risiko")
            st_context.markdown(
                """
                - 🔴 **Zona Risiko Ekstrem (Class A & Critical/Alert)**:
                  Aset vital sistem pembangkit dengan degradasi parah. Potensi trip unit tinggi jika tidak segera ditangani.
                - 🟠 **Zona Risiko Tinggi (Class A/B & Warning)**:
                  Memerlukan jadwal investigasi lanjutan (vibrasi spectrum / thermography) dalam siklus mingguan.
                - 🟡 **Zona Risiko Sedang (Class C & Warning/Alert)**:
                  Peralatan pembantu (auxiliary) non-kritis. Masuk ke backlog pemeliharaan preventif.
                - 🟢 **Zona Risiko Rendah (Healthy / Watch)**:
                  Peralatan beroperasi dalam batas parameter normal. Lanjutkan pemantauan rutin.
                """
            )
            total_high_risk = len([a for a in matrix if a.get("criticality") == "A" and a.get("health_status") in ["CRITICAL", "ALERT"]])
            if total_high_risk > 0:
                st_context.error(f"🚨 Terdapat **{total_high_risk} aset Class A** dalam zona risiko kritis/tinggi yang butuh prioritas Work Order!")
            else:
                st_context.success("✅ Tidak ada aset Class A dalam zona risiko kritis saat ini.")

    st_context.markdown("---")

    # 4. Top 10 Bad Actors & Priority Mitigation Hub
    st_context.markdown("### 🚨 Top 10 Bad Actors & Priority Mitigation Hub")
    st_context.caption("Peringkat peralatan dengan skor risiko komposit tertinggi lintas domain (Gap Health Index × Bobot Kritisitas + Severity + Anomali Multi-Domain).")

    if bad_actors:
        for b_idx, item in enumerate(bad_actors[:10]):
            eq_name = item.get("equipment", "-")
            h_stat = item.get("health_status", "WARNING")
            color = HEALTH_COLORS.get(h_stat, "#F59E0B")
            h_idx_val = item.get("health_index", 0.0)
            crit = item.get("criticality", "A")
            unit_val = item.get("unit", "-")
            sys_val = item.get("system", "-")
            fm = item.get("primary_failure_mode", "-")
            rul = item.get("rul_days", "-")
            c_score = item.get("composite_risk_score", 0.0)
            d_alerts = item.get("domain_alerts", {})

            with st_context.container(border=True):
                c_head, c_hi, c_fm, c_acts = st_context.columns([3, 2, 3, 2])

                with c_head:
                    st_context.markdown(
                        f"<div style='border-left: 4px solid {color}; padding-left: 10px;'>"
                        f"<div style='display:flex; align-items:center; gap:8px;'>"
                        f"<span style='background:#1e293b; color:#cbd5e1; font-size:0.75rem; padding:2px 6px; border-radius:4px; font-weight:600;'>#{b_idx+1}</span>"
                        f"<strong style='font-size:1.05rem; color:#f8fafc;'>{eq_name}</strong>"
                        f"</div>"
                        f"<span style='font-size:0.82rem; color:#94a3b8;'>{unit_val} · {sys_val} · <b>Class {crit}</b></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                with c_hi:
                    st_context.markdown(f"**Health Index:** <span style='color:{color}; font-weight:700;'>{h_idx_val:.1f}%</span>", unsafe_allow_html=True)
                    st_context.progress(max(0.0, min(1.0, h_idx_val / 100.0)))
                    st_context.caption(f"Risk Score: {c_score:.1f} · Status: {h_stat}")

                with c_fm:
                    st_context.markdown(f"**Failure Mode:** {fm}")
                    st_context.markdown(f"⏳ **Est. RUL:** {rul} hari")

                    # Multi-domain anomaly badges
                    m_badge = "⚡ MCSA" if d_alerts.get("mcsa") else ""
                    v_badge = "〰️ VIB" if d_alerts.get("vibration") else ""
                    t_badge = "🌡️ THM" if d_alerts.get("thermal") else ""
                    o_badge = "🛢️ OIL" if d_alerts.get("tribology") else ""
                    active_badges = [b for b in [m_badge, v_badge, t_badge, o_badge] if b]

                    if active_badges:
                        badges_html = " ".join([f"<span style='background:rgba(239,68,68,0.2); color:#fca5a5; padding:1px 5px; border-radius:3px; font-size:0.75rem;'>{b}</span>" for b in active_badges])
                        st_context.markdown(f"<div style='margin-top:2px;'>{badges_html}</div>", unsafe_allow_html=True)
                    else:
                        st_context.markdown("<span style='color:#64748b; font-size:0.75rem;'>Domain anomali: MCSA terisolasi</span>", unsafe_allow_html=True)

                with c_acts:
                    st_context.markdown("<div style='display:flex; flex-direction:column; gap:4px;'>", unsafe_allow_html=True)
                    if st_context.button("📄 Rilis TE", key=f"btn_rel_te_{eq_name}", help=f"Terbitkan Laporan Khusus Technology Examination (FORM.JRG.F.05.006) untuk {eq_name}", use_container_width=True):
                        st_context.session_state["_nav_to_te_asset"] = eq_name
                        st_context.session_state["_nav_to_wo_asset"] = eq_name
                        st_context.session_state["_preselected_equipment"] = eq_name
                        st_context.toast(f"Mengarahkan ke Laporan Khusus TE untuk {eq_name}...", icon="📄")
                        try:
                            st_context.switch_page("src/pages/work_orders_page.py")
                        except Exception:
                            st_context.info(f"Buka menu Technology Examination (TE) untuk menerbitkan laporan {eq_name}.")


                    if st_context.button("🔍 Asset 360°", key=f"btn_rel_a360_{eq_name}", help=f"Lihat profil multi-domain 360° {eq_name}", use_container_width=True):
                        st_context.session_state["_a360_equipment"] = eq_name
                        st_context.toast(f"Membuka Asset 360° untuk {eq_name}...", icon="🔍")
                        try:
                            st_context.switch_page("src/pages/asset_360_page.py")
                        except Exception:
                            st_context.info(f"Buka menu Asset 360° untuk melihat {eq_name}.")
                    st_context.markdown("</div>", unsafe_allow_html=True)
    else:
        st_context.info("Seluruh aset berada dalam kondisi sehat. Tidak ada Bad Actor prioritas tinggi saat ini.")

    st_context.markdown("---")

    # 5. Full Fleet Reliability Matrix & Management Export
    st_context.markdown("### 📋 Matriks Keandalan Aset Lengkap (Full Fleet Matrix)")

    with st_context.container(border=True):
        f_col1, f_col2, f_col3 = st_context.columns([1, 1, 1])
        with f_col1:
            units = ["Semua unit"] + sorted(list({m.get("unit", "") for m in matrix if m.get("unit")}))
            sel_unit = st_context.segmented_control("Filter unit pembangkit", units, default="Semua unit")
        with f_col2:
            crits = ["Semua Kritisitas", "A", "B", "C"]
            sel_crit = st_context.pills("Filter kritisitas aset", crits, default="Semua Kritisitas")
        with f_col3:
            statuses = ["Semua status", "CRITICAL", "ALERT", "WARNING", "WATCH", "HEALTHY"]
            sel_status = st_context.pills("Filter status kesehatan", statuses, default="Semua status")

        search_eq = st_context.text_input("Cari nama peralatan", placeholder="Ketik nama peralatan (e.g. CWP, PA FAN, BFP)...", label_visibility="collapsed")

    # Filter dataset
    filtered_matrix = []
    for m in matrix:
        if sel_unit and sel_unit != "Semua unit" and m.get("unit") != sel_unit:
            continue
        if sel_crit and sel_crit != "Semua Kritisitas" and m.get("criticality") != sel_crit:
            continue
        if sel_status and sel_status != "Semua status" and m.get("health_status") != sel_status:
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
                "Kritisitas": f"Class {row.get('criticality', '')}",
                "Health Index": f"{row.get('health_index', 0):.1f}%",
                "Status": row.get("health_status", ""),
                "Failure Mode Utama": row.get("primary_failure_mode", ""),
                "RUL (Hari)": row.get("rul_days", ""),
                "Tingkat Risiko": row.get("risk_level", ""),
                "Anomali Domain": ", ".join([k.upper() for k, v in row.get("domain_alerts", {}).items() if v]) or "None",
            }
            for row in filtered_matrix
        ])

        st_context.dataframe(df_display, use_container_width=True, hide_index=True)
        st_context.caption(f"Menampilkan {len(filtered_matrix)} dari total {len(matrix)} peralatan armada.")

        # Download CSV
        csv_data = df_display.to_csv(index=False).encode("utf-8")
        st_context.download_button(
            label="📥 Unduh Data Fleet Matrix (CSV)",
            data=csv_data,
            file_name=f"fleet_reliability_matrix_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            key="btn_download_fleet_csv",
        )
    else:
        st_context.info("Tidak ada aset yang sesuai kriteria filter.")
