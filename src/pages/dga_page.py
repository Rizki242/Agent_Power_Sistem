"""DGA (Dissolved Gas Analysis) dashboard - transformer fleet."""

import plotly.express as px

from src.agents.specialist_agents import DGAAgent
from src.components.agent_result import render_agent_result
from src.components.status_colors import (
    STATUS_PIE_COLORS,
    canon_condition_status,
    render_status_badge,
)
from src.components.theme import render_data_disclaimer_banner, render_page_header
from src.dga_data import get_dga_transformer_detail, search_dga_transformers

_DGA_METRIC_LABELS = {
    "tdcg_ppm": "TDCG (ppm)",
    "h2_ppm": "H2 (ppm)",
    "ch4_ppm": "CH4 (ppm)",
    "c2h2_ppm": "C2H2 (ppm)",
    "c2h4_ppm": "C2H4 (ppm)",
    "c2h6_ppm": "C2H6 (ppm)",
    "co_ppm": "CO (ppm)",
    "co2_ppm": "CO2 (ppm)",
    "duval_zone": "Zona diagnosis",
}


def render_dga_page(st) -> None:
    render_data_disclaimer_banner(st)
    render_page_header(st, "DGA", "Dissolved Gas Analysis - Transformer", badge="")

    transformers = search_dga_transformers()
    if not transformers:
        st.warning("Data transformer DGA tidak tersedia.")
        return

    for t in transformers:
        t["_status_canon"] = canon_condition_status(t.get("status"))

    status_counts = {}
    for t in transformers:
        status_counts[t["_status_canon"]] = status_counts.get(t["_status_canon"], 0) + 1

    # --- KPI cards -----------------------------------------------------------
    cols = st.columns(5)
    cols[0].metric("Total Transformer", len(transformers))
    cols[1].metric("Normal (Hijau)", status_counts.get("Normal", 0))
    cols[2].metric("Standby", status_counts.get("Standby", 0))
    cols[3].metric("Alarm (Kuning)", status_counts.get("Alarm", 0), delta_color="inverse")
    cols[4].metric("High (Merah)", status_counts.get("High", 0), delta_color="inverse")

    # --- Pie chart -------------------------------------------------------------
    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = [{"Status": s, "Count": status_counts.get(s, 0)} for s in plot_order if status_counts.get(s, 0) > 0]
    if plot_df:
        fig = px.pie(
            plot_df, names="Status", values="Count", title="Status Transformer",
            color="Status", color_discrete_map=STATUS_PIE_COLORS,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, width="stretch")

    # --- Filter + selector -------------------------------------------------
    units = ["All"] + sorted({t["unit"] for t in transformers})
    sel_unit = st.selectbox("Unit", units, key="dga_unit_filter")
    scoped = transformers if sel_unit == "All" else [t for t in transformers if t["unit"] == sel_unit]

    if not scoped:
        st.info("Tidak ada transformer pada unit ini.")
        return

    label_by_id = {t["transformer_id"]: f"{t['name']} ({t['transformer_id']})" for t in scoped}
    ids = list(label_by_id.keys())
    if st.session_state.get("dga_selected_transformer") not in ids:
        st.session_state["dga_selected_transformer"] = ids[0]
    selected_id = st.selectbox(
        "Pilih Transformer:", ids, key="dga_selected_transformer",
        format_func=lambda tid: label_by_id.get(tid, tid),
    )

    detail = get_dga_transformer_detail(selected_id)
    if not detail:
        st.warning("Detail transformer tidak ditemukan.")
        return

    status = canon_condition_status(detail.get("status"))
    render_status_badge(st, detail["name"], status)
    st.caption(f"**ID:** {selected_id} | **Unit:** {detail.get('unit', '-')} | **Rasio Tegangan:** {detail.get('voltage_ratio', '-')}")

    detail_view = st.radio("Tampilan Detail", ["Ringkasan", "Rekomendasi"], horizontal=True, key="dga_detail_view")

    if detail_view == "Ringkasan":
        st.markdown("**Konsentrasi Gas Terlarut (ppm)**")
        st.dataframe(
            [{"Gas": k, "Konsentrasi (ppm)": v} for k, v in detail["gases"].items()],
            hide_index=True, width="stretch",
        )
        diag = detail["diagnosis"]
        st.markdown("**Hasil Kalkulasi**")
        cols = st.columns(3)
        cols[0].metric("TDCG (ppm)", diag["tdcg"])
        cols[1].metric("Kondisi IEEE C57.104", diag["ieee_condition"])
        cols[2].metric("CO2/CO Ratio", diag["co2_co_ratio"])
        cols = st.columns(2)
        cols[0].metric("Diagnosis Duval Triangle 1", diag["duval_diagnosis"])
        cols[1].metric("Diagnosis Rogers Ratio", diag["rogers_diagnosis"])
        st.caption(f"Status kertas isolasi: {diag['paper_status']}")
        history = detail.get("history") or []
        if history:
            st.markdown("**Trend Historis DGA**")
            hist_fig = px.line(
                history,
                x="date",
                y=["tdcg", "H2", "C2H4", "CO"],
                markers=True,
                title="Trend TDCG dan Gas Kunci",
            )
            hist_fig.update_layout(height=360, margin=dict(l=10, r=10, t=45, b=10), legend_title_text="Parameter")
            st.plotly_chart(hist_fig, width="stretch")
            st.dataframe(history, hide_index=True, width="stretch")

    elif detail_view == "Rekomendasi":
        result = DGAAgent().evaluate(detail["name"], detail["gases"])
        render_agent_result(st, result, _DGA_METRIC_LABELS)
