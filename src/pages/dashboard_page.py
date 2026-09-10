from typing import Optional

import pandas as pd

from src.components.mcsa_dashboard_detail_section import (
    render_equipment_detail_section,
)
from src.components.mcsa_dashboard_sections import (
    render_condition_summary,
    render_sampling_compliance,
)
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

    render_equipment_detail_section(
        st=st,
        df=df,
        df_latest=df_latest,
        df_latest_all=df_latest_all,
        sel_unit=sel_unit,
        sel_volt=sel_volt,
        sel_equipment=sel_equipment,
        eq_master_df=eq_master_df,
        master_norm_to_unit=master_norm_to_unit,
        master_norm_to_volt=master_norm_to_volt,
        status_by_norm=status_by_norm,
        date_start=date_start,
        date_end=date_end,
        materi_page=materi_page,
    )

