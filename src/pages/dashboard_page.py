from typing import Optional

import pandas as pd

from src.components.mcsa_dashboard_detail_views import (
    get_cached_esa_quick,
    render_deep_analysis_view,
    render_recommendation_view,
    render_spectrum_view,
    render_summary_view,
)
from src.components.mcsa_dashboard_view_model import (
    build_equipment_detail_model,
    build_equipment_selection_model,
)
from src.components.mcsa_dashboard_sections import (
    render_condition_summary,
    render_sampling_compliance,
)
from src.components.mcsa_dashboard_trends import (
    render_comparison_view,
    render_trend_view,
)
from src.components.status_colors import STATUS_BADGE_BG, STATUS_BADGE_FG
from src.components.theme import render_page_header


def render_dashboard_page(
    st,
    df: pd.DataFrame,
    df_latest: pd.DataFrame,
    df_latest_all: pd.DataFrame,
    filtered_df: pd.DataFrame,
    df_month: Optional[pd.DataFrame],
    date_start: str,
    date_end: str,
    sel_unit: str,
    sel_volt: str,
    sel_equipment: list,
    standby_enabled: bool,
    standby_report: Optional[dict],
    eq_master_df: pd.DataFrame,
    master_norm_to_unit: dict,
    master_norm_to_volt: dict,
    materi_page=None,
):
    render_page_header(st, "MCSA", "Overview kondisi equipment MCSA.")

    st.caption(f"Periode: {date_start} s/d {date_end}")

    unit_label = sel_unit if sel_unit != "All" else "PLTU Jeranjang"
    volt_label = sel_volt if sel_volt != "All" else "Semua Voltage"
    st.caption(f"{unit_label} | {volt_label}")

    render_sampling_compliance(st, standby_report, df_month)

    status_by_norm = render_condition_summary(
        st,
        filtered_df=filtered_df,
        unit_label=unit_label,
        standby_enabled=standby_enabled,
        standby_report=standby_report,
    )

    # Detail Table
    st.subheader("Data Detail")
    selection_model = build_equipment_selection_model(
        df_latest,
        selected_unit=sel_unit,
        selected_voltage=sel_volt,
        selected_equipment=sel_equipment,
        equipment_master=eq_master_df,
        master_norm_to_unit=master_norm_to_unit,
        master_norm_to_voltage=master_norm_to_volt,
    )
    display_map = selection_model.display_map
    if display_map:
        labels = list(display_map.keys())
        if "dashboard_eq" in st.session_state and st.session_state.dashboard_eq not in labels:
            st.session_state.dashboard_eq = labels[0]
        selected_label = st.selectbox("Pilih Equipment:", labels, key="dashboard_eq")
        selected_eq = display_map[selected_label]
        detail_model = build_equipment_detail_model(
            history=df,
            detail_df=selection_model.detail_df,
            selected_equipment=selected_eq,
            master_by_norm=selection_model.master_by_norm,
            master_norm_to_unit=master_norm_to_unit,
            master_norm_to_voltage=master_norm_to_volt,
            status_by_norm=status_by_norm,
        )
        eq_data = detail_model.eq_data
        eq_history = detail_model.history
        f_name = detail_model.full_name
        u_name = detail_model.unit_name
        u_volt = detail_model.voltage_level
        eq_status = detail_model.status
        badge_bg = STATUS_BADGE_BG.get(eq_status, STATUS_BADGE_BG["Unknown"])
        badge_fg = STATUS_BADGE_FG.get(eq_status, STATUS_BADGE_FG["Unknown"])
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px;">
              <h3 style="margin:0;">{f_name}</h3>
              <span style="padding:4px 10px; border-radius:999px; background:{badge_bg}; color:{badge_fg}; font-weight:700; border:1px solid rgba(0,0,0,0.08);">{eq_status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"**Code:** {selected_eq} | **Unit:** {u_name} | **Voltage:** {u_volt}")

        detail_view = st.radio(
            "Tampilan Detail",
            ["Ringkasan", "Rekomendasi ESA/MCSA", "Analisa Mendalam", "Trend", "Spektrum", "Perbandingan"],
            horizontal=True,
            key="dashboard_detail_view",
        )

        table_df = detail_model.table_df
        health_summary = detail_model.health_summary
        anomaly_rows = detail_model.anomaly_rows

        hm1, hm2, hm3 = st.columns(3)
        hm1.metric("Health Score", int(health_summary["score"]))
        hm2.metric("Risk Drivers", len(health_summary["drivers"]))
        hm3.metric("Anomali Trend", len(anomaly_rows))

        if health_summary["drivers"]:
            st.caption("Driver utama: " + ", ".join(health_summary["drivers"]))
        if anomaly_rows:
            st.dataframe(pd.DataFrame(anomaly_rows), width="stretch", hide_index=True)

        def _style_status_cell(v: str) -> str:
            bg = STATUS_BADGE_BG.get(str(v), STATUS_BADGE_BG["Unknown"])
            fg = STATUS_BADGE_FG.get(str(v), STATUS_BADGE_FG["Unknown"])
            return f"background-color: {bg}; color: {fg}; font-weight: 700;"

        # pandas >= 2.1 memakai Styler.map, versi lama masih Styler.applymap.
        styler = table_df.style
        style_cells = getattr(styler, "map", None) or styler.applymap

        st.dataframe(
            style_cells(_style_status_cell, subset=["Status"]),
            width="stretch",
            hide_index=True,
        )

        if detail_view == "Analisa Mendalam":
            render_deep_analysis_view(st, eq_data, eq_history, selected_eq)

        condition_class = detail_model.condition_class

        esa_cache_key = (
            st.session_state.get("_mcsa_data_key"),
            selected_eq,
            date_start,
            date_end,
            sel_unit,
            sel_volt,
            tuple(sel_equipment),
        )

        if detail_view == "Rekomendasi ESA/MCSA":
            esa_quick = get_cached_esa_quick(st, eq_data, esa_cache_key)
            render_recommendation_view(st, esa_quick)

        if detail_view == "Ringkasan":
            esa_quick = get_cached_esa_quick(st, eq_data, esa_cache_key)
            render_summary_view(
                st,
                eq_data=eq_data,
                df_latest_all=df_latest_all,
                selected_equipment=selected_eq,
                esa_quick=esa_quick,
                condition_class=condition_class,
                materi_page=materi_page,
            )

        if detail_view == "Spektrum":
            render_spectrum_view(st, selected_eq)

        if detail_view == "Trend":
            render_trend_view(st, df, selected_eq)

        if detail_view == "Perbandingan":
            render_comparison_view(st, df, selected_eq)
    else:
        st.warning("Tidak ada equipment yang sesuai filter.")
