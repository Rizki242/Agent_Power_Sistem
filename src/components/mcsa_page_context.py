"""Lazy Streamlit context for pages that consume the MCSA dataset.

The application shell imports this module at startup, but no data file is read
until ``load_mcsa_base_context`` is called for an active MCSA consumer page.
This keeps specialist, knowledge, settings, and placeholder pages independent
from the legacy MCSA bootstrap while the UI is migrated incrementally.
"""

from dataclasses import dataclass
from datetime import date, datetime
import os
from typing import Optional

import pandas as pd
import streamlit as st

from src.components.sidebar import render_sidebar
from src.data_loader import filter_mcsa_data, get_data_path, get_latest_data, load_mcsa_data
from src.equipment_canon import (
    build_master_norm_maps,
    canon_unit_name,
    canon_voltage_level,
    load_equipment_master,
    norm_equipment,
)
from src.standby import compute_standby


MCSA_DATA_PAGE_KEYS = frozenset(
    {
        "agent_dashboard",
        "asset_360",
        "mcsa",
        "data_management",
        "sync_word",
        "chatbot",
        "ppt",
        "word",
    }
)
MCSA_FILTER_PAGE_KEYS = frozenset({"mcsa", "ppt", "word"})


def page_requires_mcsa_data(page_key: str) -> bool:
    return page_key in MCSA_DATA_PAGE_KEYS


def page_uses_mcsa_filters(page_key: str) -> bool:
    return page_key in MCSA_FILTER_PAGE_KEYS


@dataclass(frozen=True)
class McsaBaseContext:
    df: pd.DataFrame
    df_latest_all: pd.DataFrame
    min_date: date
    max_date: date
    data_key: tuple


@dataclass(frozen=True)
class McsaFilteredContext:
    df_period: pd.DataFrame
    df_latest: pd.DataFrame
    df_latest_augmented: pd.DataFrame
    filtered_df: pd.DataFrame
    df_month: Optional[pd.DataFrame]
    date_start: date
    date_end: date
    sel_unit: str
    sel_volt: str
    sel_equipment: list[str]
    standby_enabled: bool
    standby_report: object
    eq_master_df: pd.DataFrame
    master_norm_to_unit: dict
    master_norm_to_volt: dict


@st.cache_data(show_spinner=False)
def _load_data_cached(
    excel_path: str,
    excel_mtime_key: Optional[float],
    csv_mtime_key: Optional[float],
) -> pd.DataFrame:
    # The mtime arguments intentionally participate in Streamlit's cache key.
    del excel_mtime_key, csv_mtime_key
    return load_mcsa_data(excel_path)


def _safe_mtime(path: str) -> Optional[float]:
    try:
        return os.path.getmtime(path) if os.path.exists(path) else None
    except OSError:
        return None


def _get_data_key() -> tuple[str, Optional[float], Optional[float]]:
    file_path = get_data_path("Report MCSA.xls")
    csv_path = os.path.join(os.path.dirname(file_path), "mcsa_updated.csv")
    return file_path, _safe_mtime(file_path), _safe_mtime(csv_path)


def load_mcsa_base_context(streamlit=st) -> McsaBaseContext:
    """Load and cache base MCSA data only when an active page requires it."""
    streamlit.session_state.setdefault("data_changed", False)

    data_key = _get_data_key()
    if streamlit.session_state.get("_mcsa_data_key") != data_key:
        df = _load_data_cached(*data_key).copy()
        if df.empty:
            streamlit.error("Gagal memuat data atau file tidak ditemukan.")
            streamlit.stop()

        df["Date"] = pd.to_datetime(df.get("Date", pd.NaT), errors="coerce")
        min_value = df["Date"].min()
        max_value = df["Date"].max()
        if pd.isna(min_value) or pd.isna(max_value):
            min_date = datetime.now().date()
            max_date = min_date
        else:
            min_date = min_value.date()
            max_date = max_value.date()

        df_latest_all = get_latest_data(df)
        streamlit.session_state["_mcsa_data_key"] = data_key
        streamlit.session_state["_mcsa_df"] = df
        streamlit.session_state["_mcsa_df_latest_all"] = df_latest_all
        streamlit.session_state["_mcsa_min_date"] = min_date
        streamlit.session_state["_mcsa_max_date"] = max_date
    else:
        df = streamlit.session_state.get("_mcsa_df")
        df_latest_all = streamlit.session_state.get("_mcsa_df_latest_all")
        min_date = streamlit.session_state.get("_mcsa_min_date")
        max_date = streamlit.session_state.get("_mcsa_max_date")

    if df is None or df_latest_all is None or min_date is None or max_date is None:
        streamlit.error("Cache data tidak valid. Silakan refresh aplikasi.")
        streamlit.stop()

    streamlit.session_state["_mcsa_available_dates"] = df["Date"].dropna().tolist()
    return McsaBaseContext(df, df_latest_all, min_date, max_date, data_key)


def render_non_filter_sidebar(streamlit=st, base: Optional[McsaBaseContext] = None) -> None:
    fallback_date = datetime.now().date()
    min_date = base.min_date if base else fallback_date
    max_date = base.max_date if base else fallback_date
    render_sidebar(streamlit, min_date, max_date, show_filters=False)


def _load_equipment_context(streamlit=st):
    master_path = get_data_path("config", "equipment_master.json")
    master_key = (master_path, _safe_mtime(master_path))
    if streamlit.session_state.get("_mcsa_master_key") != master_key:
        eq_master_df = load_equipment_master(master_path)
        streamlit.session_state["_mcsa_master_key"] = master_key
        streamlit.session_state["_mcsa_master_df"] = eq_master_df
    else:
        cached = streamlit.session_state.get("_mcsa_master_df")
        eq_master_df = cached if isinstance(cached, pd.DataFrame) else pd.DataFrame()

    unit_map = streamlit.session_state.get("_mcsa_master_norm_to_unit") or {}
    volt_map = streamlit.session_state.get("_mcsa_master_norm_to_volt") or {}
    if not eq_master_df.empty and streamlit.session_state.get("_mcsa_master_norm_to_key") != master_key:
        unit_map, volt_map = build_master_norm_maps(eq_master_df)
        streamlit.session_state["_mcsa_master_norm_to_unit"] = unit_map
        streamlit.session_state["_mcsa_master_norm_to_volt"] = volt_map
        streamlit.session_state["_mcsa_master_norm_to_key"] = master_key
    return eq_master_df, unit_map, volt_map


def prepare_mcsa_filtered_context(
    base: McsaBaseContext,
    *,
    enable_standby: bool,
    streamlit=st,
) -> McsaFilteredContext:
    """Render MCSA filters and derive the active page's filtered view."""
    sidebar_state = render_sidebar(
        streamlit,
        base.min_date,
        base.max_date,
        show_filters=True,
    )
    date_start = sidebar_state["date_start"]
    date_end = sidebar_state["date_end"]

    period_key = (base.data_key, date_start, date_end)
    df_period = streamlit.session_state.get("_mcsa_df_period")
    df_latest = streamlit.session_state.get("_mcsa_df_latest")
    if (
        streamlit.session_state.get("_mcsa_period_key") != period_key
        or df_period is None
        or df_latest is None
    ):
        df_period = filter_mcsa_data(base.df, date_start=date_start, date_end=date_end)
        df_latest = get_latest_data(df_period)
        streamlit.session_state["_mcsa_period_key"] = period_key
        streamlit.session_state["_mcsa_df_period"] = df_period
        streamlit.session_state["_mcsa_df_latest"] = df_latest
    df_latest_for_filters = df_latest if not df_latest.empty else base.df_latest_all

    eq_master_df, unit_map, volt_map = _load_equipment_context(streamlit)

    unit_choices = ["All", "UNIT 1", "UNIT 2", "UNIT 3", "UNIT COMMON", "Unknown"]
    units_present = set(
        canon_unit_name(value)
        for value in df_latest_for_filters.get("Unit_Name", pd.Series(dtype=str)).unique()
    )
    if not eq_master_df.empty and "Unit_Name" in eq_master_df.columns:
        units_present.update(eq_master_df["Unit_Name"].astype(str).map(canon_unit_name).unique())
    all_units = [value for value in unit_choices if value == "All" or value in units_present]
    all_units += sorted(units_present.difference(unit_choices))
    if streamlit.session_state.get("filter_unit") not in all_units:
        streamlit.session_state.filter_unit = "All"
    sel_unit = streamlit.sidebar.selectbox("Unit", all_units, key="filter_unit")

    volt_choices = ["All", "380/400 V", "6.3 KV", "Unknown"]
    volts_present = set(
        canon_voltage_level(value)
        for value in df_latest_for_filters.get("Voltage_Level", pd.Series(dtype=str)).unique()
    )
    if not eq_master_df.empty and "Voltage_Level" in eq_master_df.columns:
        volts_present.update(
            eq_master_df["Voltage_Level"].astype(str).map(canon_voltage_level).unique()
        )
    all_volts = [value for value in volt_choices if value == "All" or value in volts_present]
    all_volts += sorted(volts_present.difference(volt_choices))
    if streamlit.session_state.get("filter_volt") not in all_volts:
        streamlit.session_state.filter_volt = "All"
    sel_volt = streamlit.sidebar.selectbox("Voltage", all_volts, key="filter_volt")

    equipment_df = df_latest_for_filters.copy()
    if sel_unit != "All":
        unit_series = equipment_df.get("Unit_Name", pd.Series(dtype=str)).astype(str).map(canon_unit_name)
        norm_series = equipment_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
        equipment_df = equipment_df[norm_series.map(unit_map).fillna(unit_series) == sel_unit]
    if sel_volt != "All":
        volt_series = equipment_df.get("Voltage_Level", pd.Series(dtype=str)).astype(str).map(canon_voltage_level)
        norm_series = equipment_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
        equipment_df = equipment_df[norm_series.map(volt_map).fillna(volt_series) == sel_volt]
    equipment_options = sorted(
        equipment_df.get("Equipment", pd.Series(dtype=str)).dropna().astype(str).unique()
    )
    focus_equipment = streamlit.session_state.pop("filter_focus_equipment", None)
    if focus_equipment is not None:
        streamlit.session_state.filter_equipment = [
            equipment for equipment in focus_equipment if equipment in equipment_options
        ]
    selected_equipment = streamlit.session_state.get("filter_equipment", [])
    streamlit.session_state.filter_equipment = [
        equipment for equipment in selected_equipment if equipment in equipment_options
    ]
    sel_equipment = streamlit.sidebar.multiselect(
        "Equipment",
        equipment_options,
        key="filter_equipment",
        placeholder="Semua equipment",
        help="Kosong berarti semua equipment dalam Unit dan Voltage terpilih.",
    )

    standby_enabled = False
    standby_scope = None
    required_month_params = ["Kondisi"]
    if enable_standby:
        standby_enabled = streamlit.sidebar.checkbox(
            "Standby otomatis jika tidak ada data bulan ini",
            value=True,
        )
        if standby_enabled:
            standby_scope = streamlit.sidebar.selectbox(
                "Cakupan Standby",
                [
                    "Per Unit (mengikuti filter Unit/Voltage)",
                    "Semua Unit (abaikan filter Unit)",
                ],
            )
            candidates = [
                "Kondisi",
                "Load",
                "Dev Voltage",
                "Dev Current",
                "THD Voltage %",
                "THD Current %",
                "Rotorbar Health",
                "Upper Sideband",
                "Lower Sideband",
                "Bearing",
            ]
            present = set(base.df.get("Parameter", pd.Series(dtype=str)).astype(str).unique())
            options = [item for item in candidates if item in present]
            options += sorted(present.difference(candidates))
            required_defaults = [
                item
                for item in (
                    "Dev Voltage",
                    "Dev Current",
                    "THD Voltage %",
                    "THD Current %",
                    "Upper Sideband",
                    "Lower Sideband",
                    "Load",
                )
                if item in options
            ]
            if not required_defaults:
                required_defaults = [item for item in ["Kondisi"] if item in options]
            required_month_params = streamlit.sidebar.multiselect(
                "Parameter wajib update bulanan",
                options,
                default=required_defaults,
            ) or ["Kondisi"]

    df_latest_augmented = df_latest.copy()
    standby_report = None
    df_month = None
    if standby_enabled:
        standby_key = (
            period_key,
            standby_scope,
            sel_unit,
            sel_volt,
            tuple(required_month_params),
        )
        cached_values = (
            streamlit.session_state.get("_mcsa_df_latest_augmented"),
            streamlit.session_state.get("_mcsa_standby_report"),
            streamlit.session_state.get("_mcsa_df_month"),
            streamlit.session_state.get("_mcsa_meta_df"),
        )
        if streamlit.session_state.get("_mcsa_standby_key") == standby_key and all(
            value is not None for value in cached_values
        ):
            df_latest_augmented, standby_report, df_month, _ = cached_values
        else:
            df_latest_augmented, standby_report, df_month, meta_df = compute_standby(
                base.df,
                df_latest,
                base.df_latest_all,
                eq_master_df,
                unit_map,
                volt_map,
                date_end,
                standby_scope,
                sel_unit,
                sel_volt,
                required_month_params,
            )
            streamlit.session_state["_mcsa_standby_key"] = standby_key
            streamlit.session_state["_mcsa_standby_report"] = standby_report
            streamlit.session_state["_mcsa_df_latest_augmented"] = df_latest_augmented
            streamlit.session_state["_mcsa_df_month"] = df_month
            streamlit.session_state["_mcsa_meta_df"] = meta_df

    filtered_key_base = (
        streamlit.session_state.get("_mcsa_standby_key") if standby_enabled else period_key
    )
    filtered_key = (filtered_key_base, sel_unit, sel_volt, tuple(sel_equipment))
    filtered_df = streamlit.session_state.get("_mcsa_filtered_df")
    if streamlit.session_state.get("_mcsa_filtered_key") != filtered_key or filtered_df is None:
        filtered_df = df_latest_augmented.copy()
        if sel_unit != "All":
            unit_series = filtered_df.get("Unit_Name", pd.Series(dtype=str)).astype(str).map(canon_unit_name)
            norm_series = filtered_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
            filtered_df = filtered_df[norm_series.map(unit_map).fillna(unit_series) == sel_unit]
        if sel_volt != "All":
            volt_series = filtered_df.get("Voltage_Level", pd.Series(dtype=str)).astype(str).map(canon_voltage_level)
            norm_series = filtered_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
            filtered_df = filtered_df[norm_series.map(volt_map).fillna(volt_series) == sel_volt]
        if sel_equipment:
            filtered_df = filter_mcsa_data(filtered_df, equipment=sel_equipment)
        streamlit.session_state["_mcsa_filtered_key"] = filtered_key
        streamlit.session_state["_mcsa_filtered_df"] = filtered_df

    return McsaFilteredContext(
        df_period=df_period,
        df_latest=df_latest,
        df_latest_augmented=df_latest_augmented,
        filtered_df=filtered_df,
        df_month=df_month,
        date_start=date_start,
        date_end=date_end,
        sel_unit=sel_unit,
        sel_volt=sel_volt,
        sel_equipment=list(sel_equipment),
        standby_enabled=standby_enabled,
        standby_report=standby_report,
        eq_master_df=eq_master_df,
        master_norm_to_unit=unit_map,
        master_norm_to_volt=volt_map,
    )

