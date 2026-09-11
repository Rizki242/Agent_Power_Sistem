"""Tribology dashboard - lube oil condition & wear debris."""

import plotly.express as px

from src.agents.specialist_agents import TribologyAgent
from src.components.agent_result import render_agent_result
from src.components.domain_workspace import DomainWorkspaceConfig, render_domain_workspace
from src.components.status_colors import (
    STATUS_PIE_COLORS,
    canon_condition_status,
    render_status_badge,
)
from src.components.theme import render_detail_view_toggle
from src.tribology_data import (
    build_tribology_agent_input,
    get_tribology_sample_detail,
    search_tribology_samples,
)

_TRIBOLOGY_METRIC_LABELS = {
    "viscosity_40c": "Viskositas 40°C (cSt)",
    "viscosity_dev_pct": "Deviasi viskositas (%)",
    "tan_mgkoh_g": "TAN (mg KOH/g)",
    "water_ppm": "Air (ppm)",
    "fe_ppm": "Fe (ppm)",
    "cu_ppm": "Cu (ppm)",
    "iso_cleanliness": "ISO cleanliness",
}


def render_tribology_page(st) -> None:
    render_domain_workspace(st, DomainWorkspaceConfig(
        domain="TRIBOLOGY",
        title="Tribology",
        subtitle="Analisa Oli Pelumas & Wear Debris",
        agent_factory=TribologyAgent,
        metric_labels=_TRIBOLOGY_METRIC_LABELS,
        summary_renderer=_render_tribology_summary,
        disclaimer="Data Contoh - Belum Terverifikasi dari Sumber Asli",
    ))


def _render_tribology_summary(st) -> None:
    """The pre-existing read-only view, unchanged in behavior."""

    samples = search_tribology_samples()
    if not samples:
        st.warning("Data sampel tribology tidak tersedia.")
        return

    for s in samples:
        s["_status_canon"] = canon_condition_status(s.get("status"))

    status_counts = {}
    for s in samples:
        status_counts[s["_status_canon"]] = status_counts.get(s["_status_canon"], 0) + 1

    # --- KPI cards -----------------------------------------------------------
    cols = st.columns(5)
    cols[0].metric("Total Sampel", len(samples))
    cols[1].metric("Normal (Hijau)", status_counts.get("Normal", 0))
    cols[2].metric("Standby", status_counts.get("Standby", 0))
    cols[3].metric("Alarm (Kuning)", status_counts.get("Alarm", 0), delta_color="inverse")
    cols[4].metric("High (Merah)", status_counts.get("High", 0), delta_color="inverse")

    # --- Pie chart -------------------------------------------------------------
    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = [{"Status": s, "Count": status_counts.get(s, 0)} for s in plot_order if status_counts.get(s, 0) > 0]
    if plot_df:
        fig = px.pie(
            plot_df, names="Status", values="Count", title="Status Sampel Oli",
            color="Status", color_discrete_map=STATUS_PIE_COLORS,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, width="stretch")

    # --- Filter + selector -------------------------------------------------
    units = ["All"] + sorted({s["unit"] for s in samples})
    sel_unit = st.selectbox("Unit", units, key="tribology_unit_filter")
    scoped = samples if sel_unit == "All" else [s for s in samples if s["unit"] == sel_unit]

    if not scoped:
        st.info("Tidak ada sampel pada unit ini.")
        return

    label_by_id = {s["sample_id"]: f"{s['equipment']} ({s['sample_id']})" for s in scoped}
    ids = list(label_by_id.keys())
    if st.session_state.get("tribology_selected_sample") not in ids:
        st.session_state["tribology_selected_sample"] = ids[0]
    selected_id = st.selectbox(
        "Pilih Sampel:", ids, key="tribology_selected_sample",
        format_func=lambda sid: label_by_id.get(sid, sid),
    )

    detail = get_tribology_sample_detail(selected_id)
    if not detail:
        st.warning("Detail sampel tidak ditemukan.")
        return

    status = canon_condition_status(detail.get("status"))
    render_status_badge(st, detail["equipment"], status)
    st.caption(f"**Sample ID:** {selected_id} | **Unit:** {detail.get('unit', '-')} | **Oli:** {detail.get('oil_brand', '-')} ({detail.get('oil_type', '-')})")

    detail_view = render_detail_view_toggle(st, key="tribology_detail_view")

    if detail_view == "Ringkasan":
        st.markdown("**Parameter Fisikokimia**")
        st.dataframe(
            [
                {"Parameter": "Viskositas 40°C (cSt)", "Nilai": str(detail.get("viscosity_40c", "-"))},
                {"Parameter": "TAN (mg KOH/g)", "Nilai": str(detail.get("tan", "-"))},
                {"Parameter": "Air (ppm)", "Nilai": str(detail.get("water_ppm", "-"))},
                {"Parameter": "ISO Cleanliness", "Nilai": str(detail.get("iso_cleanliness", "-"))},
                {"Parameter": "Wear Fe (ppm)", "Nilai": str(detail.get("wear_fe", "-"))},
                {"Parameter": "Wear Cu (ppm)", "Nilai": str(detail.get("wear_cu", "-"))},
                {"Parameter": "Flash Point (°C)", "Nilai": str(detail.get("flash_point", "-"))},
            ],
            hide_index=True, width="stretch",
        )
        eval_res = detail["evaluation"]
        st.markdown("**Evaluasi**")
        cols = st.columns(4)
        cols[0].metric("Viskositas", eval_res["viscosity_eval"])
        cols[1].metric("TAN", eval_res["tan_eval"])
        cols[2].metric("Air", eval_res["water_eval"])
        cols[3].metric("Wear Debris", eval_res["wear_eval"])
        if detail.get("analysis"):
            st.caption(f"Analisa: {detail['analysis']}")

    elif detail_view == "Rekomendasi":
        agent_input = build_tribology_agent_input(detail)
        result = TribologyAgent().evaluate(detail["equipment"], agent_input)
        render_agent_result(st, result, _TRIBOLOGY_METRIC_LABELS)
