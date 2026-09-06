"""Partial Discharge dashboard - PRPD pulse magnitude / discharge type.

Unlike Thermal, this domain has a real render_data_disclaimer_banner: there
is no source data of any kind for PD (no Excel export, no register) - see
src.pd_data's module docstring. The schema was designed from scratch to
match PDAgent.evaluate()'s input directly, so the Rekomendasi tab can call
the agent for real (status shown elsewhere always agrees with it, since both
use the same thresholds - see src.pd_data._pd_status).
"""

import plotly.express as px

from src.agents.specialist_agents import PDAgent
from src.components.agent_result import render_agent_result
from src.components.domain_workspace import DomainWorkspaceConfig, render_domain_workspace
from src.components.status_colors import (
    STATUS_PIE_COLORS,
    canon_condition_status,
    render_status_badge,
)
from src.components.theme import render_detail_view_toggle
from src.pd_data import get_pd_sample_detail, search_pd_samples

_PD_METRIC_LABELS = {
    "pulse_magnitude_pc": "Pulse Magnitude (pC)",
    "nqn": "NQN",
    "pd_type": "Tipe Discharge",
    "phase_clustering_deg": "Phase Clustering (deg)",
}


def render_pd_page(st) -> None:
    render_domain_workspace(st, DomainWorkspaceConfig(
        domain="PD",
        title="Partial Discharge",
        subtitle="PRPD Pattern & Pulse Magnitude Monitoring",
        agent_factory=PDAgent,
        metric_labels=_PD_METRIC_LABELS,
        summary_renderer=_render_pd_summary,
        disclaimer="Data Contoh - Belum Terverifikasi dari Sumber Asli",
    ))


def _render_pd_summary(st) -> None:
    """The pre-existing read-only view, unchanged in behavior."""

    samples = search_pd_samples()
    if not samples:
        st.warning("Data sampel Partial Discharge tidak tersedia.")
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
            plot_df, names="Status", values="Count", title="Status Sampel PD",
            color="Status", color_discrete_map=STATUS_PIE_COLORS,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, width="stretch")

    # --- Filter + selector -------------------------------------------------
    units = ["All"] + sorted({s["unit"] for s in samples})
    sel_unit = st.selectbox("Unit", units, key="pd_unit_filter")
    scoped = samples if sel_unit == "All" else [s for s in samples if s["unit"] == sel_unit]

    if not scoped:
        st.info("Tidak ada sampel pada unit ini.")
        return

    label_by_id = {s["sample_id"]: f"{s['equipment']} ({s['sample_id']})" for s in scoped}
    ids = list(label_by_id.keys())
    if st.session_state.get("pd_selected_sample") not in ids:
        st.session_state["pd_selected_sample"] = ids[0]
    selected_id = st.selectbox(
        "Pilih Sampel:", ids, key="pd_selected_sample",
        format_func=lambda sid: label_by_id.get(sid, sid),
    )

    detail = get_pd_sample_detail(selected_id)
    if not detail:
        st.warning("Detail sampel tidak ditemukan.")
        return

    status = canon_condition_status(detail.get("status"))
    render_status_badge(st, detail["equipment"], status)
    st.caption(f"**Sample ID:** {selected_id} | **Unit:** {detail.get('unit', '-')} | **Metode:** {detail.get('method', '-')}")

    detail_view = render_detail_view_toggle(st, key="pd_detail_view")

    if detail_view == "Ringkasan":
        st.markdown("**Parameter PRPD**")
        st.dataframe(
            [
                {"Parameter": "Pulse Magnitude (pC)", "Nilai": detail.get("pulse_magnitude_pc")},
                {"Parameter": "Tipe Discharge", "Nilai": detail.get("pd_type")},
                {"Parameter": "Phase Clustering (deg)", "Nilai": detail.get("phase_clustering_deg")},
                {"Parameter": "NQN", "Nilai": detail.get("nqn")},
                {"Parameter": "Tanggal Uji", "Nilai": detail.get("test_date")},
            ],
            hide_index=True, width="stretch",
        )

    elif detail_view == "Rekomendasi":
        result = PDAgent().evaluate(detail["equipment"], detail)
        render_agent_result(st, result, _PD_METRIC_LABELS)
