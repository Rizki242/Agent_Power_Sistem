import streamlit as st
import os
import sys
import traceback


def _fatal_dependency_error(dep_name: str, exc: BaseException) -> "None":
    st.set_page_config(page_title="MCSA Dashboard & Chatbot", layout="wide")
    st.title("MCSA Condition Monitoring")
    st.error(f"Gagal memuat dependensi: {dep_name}")
    st.write(
        "Biasanya terjadi karena virtual environment (.venv) tercampur versi Python "
        "(mis. cp311 vs cp313) atau instalasi NumPy/Pandas rusak."
    )
    st.info(f"Python: {sys.version.split()[0]} | Executable: {sys.executable}")
    _project_dir = os.path.dirname(os.path.abspath(__file__))
    st.write("Perbaikan cepat (rekomendasi):")
    st.write("PowerShell:")
    st.code(
        f'cd "{_project_dir}"\n'
        "Remove-Item -Recurse -Force .venv\n"
        "py -3.11 -m venv .venv\n"
        ".\\.venv\\Scripts\\activate\n"
        "python -m pip install --upgrade pip setuptools wheel\n"
        "python -m pip install -r requirements.txt\n"
        "python -m streamlit run app.py"
    )
    st.write("CMD:")
    st.code(
        f'cd "{_project_dir}"\n'
        "rmdir /s /q .venv\n"
        "py -3.11 -m venv .venv\n"
        ".\\.venv\\Scripts\\activate.bat\n"
        "python -m pip install --upgrade pip setuptools wheel\n"
        "python -m pip install -r requirements.txt\n"
        "python -m streamlit run app.py"
    )
    st.write("Detail error:")
    st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    st.stop()


try:
    import pandas as pd
except BaseException as exc:
    _fatal_dependency_error("pandas / numpy", exc)

try:
    import plotly.express as px
except BaseException as exc:
    _fatal_dependency_error("plotly", exc)

try:
    from src.data_loader import (
        audit_mcsa_dataframe,
        fix_mcsa_dataframe,
        get_data_path,
        get_folder_metadata,
        get_latest_data,
        filter_mcsa_data,
        load_mcsa_data,
        load_nameplate_csv,
        save_mcsa_data,
    )
    from src.docx_parser import parse_all_reports_with_report
    from src.ppt_generator import create_ppt
    from src.docx_generator import create_docx
    from src.equipment_canon import (
        build_master_norm_maps,
        canon_unit_name,
        canon_voltage_level,
        load_equipment_master,
        norm_equipment,
    )
    from src.standby import compute_standby
    from src.components.sidebar import render_sidebar, render_sidebar_brand
    from src.pages.agent_dashboard_page import render_agent_dashboard_page
    from src.pages.asset_registry_page import render_asset_registry_page
    from src.pages.asset_reports_page import render_asset_reports_page
    from src.pages.chatbot_page import render_chatbot_page
    from src.pages.condition_control_page import render_condition_control_page
    from src.pages.dashboard_page import render_dashboard_page
    from src.pages.data_management_page import render_data_management_page
    from src.pages.dga_page import render_dga_page
    from src.pages.materi_page import render_materi_page
    from src.pages.placeholder_page import render_placeholder_page
    from src.pages.quality_page import render_quality_check_page
    from src.pages.report_page import render_ppt_page, render_word_page
    from src.pages.pd_page import render_pd_page
    from src.pages.settings_page import render_settings_page
    from src.pages.sync_word_page import render_sync_word_page
    from src.pages.thermal_page import render_thermal_page
    from src.pages.tribology_page import render_tribology_page
    from src.pages.vibration_page import render_vibration_page
except BaseException as exc:
    _fatal_dependency_error("modul internal (src/*)", exc)
from typing import Optional
from datetime import datetime

# Page Config
st.set_page_config(page_title="MCSA Dashboard & Chatbot", layout="wide")

# Data Loading
@st.cache_data(show_spinner=False)
def _load_data_cached(excel_path: str, excel_mtime_key: Optional[float], csv_mtime_key: Optional[float]):
    return load_mcsa_data(excel_path)

def _get_data_key():
    file_path = get_data_path('Report MCSA.xls')
    csv_path = os.path.join(os.path.dirname(file_path), 'mcsa_updated.csv')
    try:
        excel_mtime = os.path.getmtime(file_path) if os.path.exists(file_path) else None
    except Exception:
        excel_mtime = None
    try:
        csv_mtime = os.path.getmtime(csv_path) if os.path.exists(csv_path) else None
    except Exception:
        csv_mtime = None
    return file_path, excel_mtime, csv_mtime


def load_data():
    file_path, excel_mtime, csv_mtime = _get_data_key()
    df_loaded = _load_data_cached(file_path, excel_mtime, csv_mtime)
    return df_loaded.copy()

if 'data_changed' not in st.session_state:
    st.session_state.data_changed = False

_file_path, _excel_mtime, _csv_mtime = _get_data_key()
_data_key = (_file_path, _excel_mtime, _csv_mtime)

if st.session_state.get('_mcsa_data_key') != _data_key:
    df = load_data()
    if df.empty:
        st.error("Gagal memuat data atau file tidak ditemukan.")
        st.stop()

    df['Date'] = pd.to_datetime(df.get('Date', pd.NaT), errors='coerce')
    _min_date = df['Date'].min()
    _max_date = df['Date'].max()
    if pd.isna(_min_date) or pd.isna(_max_date):
        min_date = datetime.now().date()
        max_date = datetime.now().date()
    else:
        min_date = _min_date.date()
        max_date = _max_date.date()

    df_latest_all = get_latest_data(df)
    st.session_state['_mcsa_data_key'] = _data_key
    st.session_state['_mcsa_df'] = df
    st.session_state['_mcsa_df_latest_all'] = df_latest_all
    st.session_state['_mcsa_min_date'] = min_date
    st.session_state['_mcsa_max_date'] = max_date
else:
    df = st.session_state.get('_mcsa_df')
    df_latest_all = st.session_state.get('_mcsa_df_latest_all')
    min_date = st.session_state.get('_mcsa_min_date')
    max_date = st.session_state.get('_mcsa_max_date')

if df is None or df_latest_all is None or min_date is None or max_date is None:
    st.error("Cache data tidak valid. Silakan refresh aplikasi.")
    st.stop()

st.session_state["_mcsa_available_dates"] = df["Date"].dropna().tolist()
render_sidebar_brand(st)

# Nav destinations, grouped to match docs/desain.png's target information
# architecture. Each entry is a closure so it can be built now and reference
# variables (df_latest_augmented, filtered_df, ...) that this script only
# finishes computing further down - Python resolves those names at call time,
# and .run() is only invoked at the very end of the script.
PAGES = {}


def _agent_dashboard_entry():
    render_agent_dashboard_page(
        st,
        df_latest_all=df_latest_all,
        mcsa_page=PAGES.get("mcsa"),
    )


def _dashboard_entry():
    render_dashboard_page(
        st,
        df=df,
        df_latest=df_latest,
        df_latest_all=df_latest_all,
        filtered_df=filtered_df,
        df_month=df_month,
        date_start=date_start,
        date_end=date_end,
        sel_unit=sel_unit,
        sel_volt=sel_volt,
        sel_equipment=sel_equipment,
        standby_enabled=standby_enabled,
        standby_report=standby_report,
        eq_master_df=eq_master_df,
        master_norm_to_unit=master_norm_to_unit,
        master_norm_to_volt=master_norm_to_volt,
        materi_page=PAGES.get("materi"),
    )


def _data_management_entry():
    render_data_management_page(
        st,
        df=df,
        df_latest_all=df_latest_all,
        edit_mode=bool(st.session_state.get('edit_mode', False)),
    )


def _sync_word_entry():
    render_sync_word_page(
        st,
        df=df,
        edit_mode=bool(st.session_state.get('edit_mode', False)),
        get_data_path=get_data_path,
        get_folder_metadata=get_folder_metadata,
        parse_all_reports_with_report=parse_all_reports_with_report,
        save_mcsa_data=save_mcsa_data,
        load_mcsa_data=load_mcsa_data,
        dashboard_page=PAGES.get("mcsa"),
    )


def _quality_entry():
    render_quality_check_page(
        st,
        get_data_path=get_data_path,
        get_folder_metadata=get_folder_metadata,
        parse_all_reports_with_report=parse_all_reports_with_report,
    )


def _asset_registry_entry():
    render_asset_registry_page(
        st,
        edit_mode=bool(st.session_state.get('edit_mode', False)),
    )


def _asset_reports_entry():
    render_asset_reports_page(st)


def _materi_entry():
    render_materi_page(st)


def _condition_control_entry():
    render_condition_control_page(st)


def _vibration_entry():
    render_vibration_page(st)


def _dga_entry():
    render_dga_page(st)


def _tribology_entry():
    render_tribology_page(st)


def _thermal_entry():
    render_thermal_page(st)


def _pd_entry():
    render_pd_page(st)


def _chatbot_entry():
    render_chatbot_page(st, df_latest_augmented=df_latest_augmented, df_all=df)


def _ppt_entry():
    render_ppt_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end, create_ppt,
                    history_df=df_period)


def _word_entry():
    render_word_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end, standby_report, create_docx)


def _settings_entry():
    render_settings_page(st)


def _reliability_entry():
    render_placeholder_page(st, "Reliability", "Fusion engine (health index, risk, RUL, work order) kini terintegrasi di halaman Agent Dashboard pada menu Command Center.")


def _work_orders_entry():
    render_placeholder_page(st, "Work Orders", "Integrasi Work Order / EAM belum tersedia di Streamlit UI.")


def _help_entry():
    render_placeholder_page(st, "Help & Support", "Dokumentasi dan bantuan akan hadir di rilis mendatang.")


PAGES["agent_dashboard"] = st.Page(_agent_dashboard_entry, title="Agent Dashboard", icon=":material/dashboard:", default=True)
PAGES["mcsa"] = st.Page(_dashboard_entry, title="MCSA", icon=":material/electric_bolt:")
PAGES["data_management"] = st.Page(_data_management_entry, title="Manajemen Data", icon=":material/database:")
PAGES["sync_word"] = st.Page(_sync_word_entry, title="Sync Laporan Word", icon=":material/upload_file:")
PAGES["quality"] = st.Page(_quality_entry, title="Quality Check Laporan", icon=":material/fact_check:")
PAGES["asset_registry"] = st.Page(_asset_registry_entry, title="Register Aset", icon=":material/inventory_2:")
PAGES["asset_reports"] = st.Page(_asset_reports_entry, title="Laporan Kondisi", icon=":material/summarize:")
PAGES["vibrasi"] = st.Page(_vibration_entry, title="Vibrasi", icon=":material/vibration:")
PAGES["dga"] = st.Page(_dga_entry, title="DGA", icon=":material/science:")
PAGES["tribology"] = st.Page(_tribology_entry, title="Tribology", icon=":material/oil_barrel:")
PAGES["thermal"] = st.Page(_thermal_entry, title="Thermal", icon=":material/thermostat:")
PAGES["partial_discharge"] = st.Page(_pd_entry, title="Partial Discharge", icon=":material/bolt:")
PAGES["condition_control"] = st.Page(_condition_control_entry, title="Control condition", icon=":material/tune:")
PAGES["reliability"] = st.Page(_reliability_entry, title="Reliability", icon=":material/insights:")
PAGES["chatbot"] = st.Page(_chatbot_entry, title="Chatbot", icon=":material/smart_toy:")
PAGES["materi"] = st.Page(_materi_entry, title="Materi Training", icon=":material/menu_book:")
PAGES["ppt"] = st.Page(_ppt_entry, title="Laporan PPT", icon=":material/slideshow:")
PAGES["word"] = st.Page(_word_entry, title="Laporan Word", icon=":material/description:")
PAGES["work_orders"] = st.Page(_work_orders_entry, title="Work Orders", icon=":material/assignment:")
PAGES["settings"] = st.Page(_settings_entry, title="Settings", icon=":material/settings:")
PAGES["help"] = st.Page(_help_entry, title="Help & Support", icon=":material/help:")

active_page = st.navigation(
    {
        "Command Center": [PAGES["agent_dashboard"]],
        "Asset Management": [PAGES["asset_registry"], PAGES["asset_reports"], PAGES["data_management"], PAGES["sync_word"], PAGES["quality"]],
        "Engineering": [PAGES["mcsa"], PAGES["vibrasi"], PAGES["dga"], PAGES["tribology"], PAGES["thermal"], PAGES["partial_discharge"], PAGES["condition_control"]],
        "Reliability": [PAGES["reliability"]],
        "AI Agent": [PAGES["chatbot"]],
        "Knowledge": [PAGES["materi"]],
        "Reports": [PAGES["ppt"], PAGES["word"]],
        "Work Orders": [PAGES["work_orders"]],
        "Settings": [PAGES["settings"]],
        "Help & Support": [PAGES["help"]],
    },
    expanded=True,
)

MCSA_FILTER_PAGES = (PAGES["mcsa"], PAGES["ppt"], PAGES["word"])
show_data_filters = active_page in MCSA_FILTER_PAGES
sidebar_state = render_sidebar(st, min_date, max_date, show_filters=show_data_filters)
if show_data_filters:
    date_start = sidebar_state["date_start"]
    date_end = sidebar_state["date_end"]
else:
    date_start, date_end = min_date, max_date

period_key = (st.session_state.get('_mcsa_data_key'), date_start, date_end)
df_period = st.session_state.get('_mcsa_df_period')
df_latest = st.session_state.get('_mcsa_df_latest')
if st.session_state.get('_mcsa_period_key') != period_key or df_period is None or df_latest is None:
    df_period = filter_mcsa_data(df, date_start=date_start, date_end=date_end)
    df_latest = get_latest_data(df_period)
    st.session_state['_mcsa_period_key'] = period_key
    st.session_state['_mcsa_df_period'] = df_period
    st.session_state['_mcsa_df_latest'] = df_latest
df_latest_for_filters = df_latest if not df_latest.empty else df_latest_all

master_path = get_data_path('config', 'equipment_master.json')
try:
    master_mtime = os.path.getmtime(master_path) if os.path.exists(master_path) else None
except Exception:
    master_mtime = None
master_key = (master_path, master_mtime)
if st.session_state.get('_mcsa_master_key') != master_key:
    eq_master_df = load_equipment_master(master_path)
    st.session_state['_mcsa_master_key'] = master_key
    st.session_state['_mcsa_master_df'] = eq_master_df
else:
    _cached_master_df = st.session_state.get('_mcsa_master_df')
    eq_master_df = _cached_master_df if isinstance(_cached_master_df, pd.DataFrame) else pd.DataFrame()

master_norm_to_unit = st.session_state.get('_mcsa_master_norm_to_unit') or {}
master_norm_to_volt = st.session_state.get('_mcsa_master_norm_to_volt') or {}
if not eq_master_df.empty and st.session_state.get('_mcsa_master_norm_to_key') != master_key:
    master_norm_to_unit, master_norm_to_volt = build_master_norm_maps(eq_master_df)
    st.session_state['_mcsa_master_norm_to_unit'] = master_norm_to_unit
    st.session_state['_mcsa_master_norm_to_volt'] = master_norm_to_volt
    st.session_state['_mcsa_master_norm_to_key'] = master_key

if show_data_filters:
    # Get unique values for filters
    unit_choices = ['All', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'UNIT COMMON', 'Unknown']
    units_present = set(canon_unit_name(x) for x in df_latest_for_filters.get('Unit_Name', pd.Series(dtype=str)).unique())
    if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty and 'Unit_Name' in eq_master_df.columns:
        units_present = units_present.union(set(eq_master_df['Unit_Name'].astype(str).map(canon_unit_name).unique()))
    all_units = [u for u in unit_choices if u == 'All' or u in units_present] + sorted([u for u in units_present if u not in set(unit_choices)])
    if 'filter_unit' not in st.session_state:
        st.session_state.filter_unit = 'All'
    if st.session_state.filter_unit not in all_units:
        st.session_state.filter_unit = 'All'
    sel_unit = st.sidebar.selectbox("Unit", all_units, key="filter_unit")

    volt_choices = ['All', '380/400 V', '6.3 KV', 'Unknown']
    volts_present = set(canon_voltage_level(x) for x in df_latest_for_filters.get('Voltage_Level', pd.Series(dtype=str)).unique())
    if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty and 'Voltage_Level' in eq_master_df.columns:
        volts_present = volts_present.union(set(eq_master_df['Voltage_Level'].astype(str).map(canon_voltage_level).unique()))
    all_volts = [v for v in volt_choices if v == 'All' or v in volts_present] + sorted([v for v in volts_present if v not in set(volt_choices)])
    if 'filter_volt' not in st.session_state:
        st.session_state.filter_volt = 'All'
    if st.session_state.filter_volt not in all_volts:
        st.session_state.filter_volt = 'All'
    sel_volt = st.sidebar.selectbox("Voltage", all_volts, key="filter_volt")

    # Equipment is a global, cascading filter after period, unit, and voltage.
    equipment_filter_df = df_latest_for_filters.copy()
    if sel_unit != 'All':
        _eq_unit = equipment_filter_df.get('Unit_Name', pd.Series(dtype=str)).astype(str).map(canon_unit_name)
        _eq_norm = equipment_filter_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(norm_equipment)
        equipment_filter_df = equipment_filter_df[_eq_norm.map(master_norm_to_unit).fillna(_eq_unit) == sel_unit]
    if sel_volt != 'All':
        _eq_volt = equipment_filter_df.get('Voltage_Level', pd.Series(dtype=str)).astype(str).map(canon_voltage_level)
        _eq_norm = equipment_filter_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(norm_equipment)
        equipment_filter_df = equipment_filter_df[_eq_norm.map(master_norm_to_volt).fillna(_eq_volt) == sel_volt]
    equipment_options = sorted(equipment_filter_df.get('Equipment', pd.Series(dtype=str)).dropna().astype(str).unique())
    focus_equipment = st.session_state.pop('filter_focus_equipment', None)
    if focus_equipment is not None:
        st.session_state.filter_equipment = [eq for eq in focus_equipment if eq in equipment_options]
    if 'filter_equipment' not in st.session_state:
        st.session_state.filter_equipment = []
    st.session_state.filter_equipment = [eq for eq in st.session_state.filter_equipment if eq in equipment_options]
    sel_equipment = st.sidebar.multiselect(
        "Equipment",
        equipment_options,
        key="filter_equipment",
        placeholder="Semua equipment",
        help="Kosong berarti semua equipment dalam Unit dan Voltage terpilih.",
    )
else:
    sel_unit = 'All'
    sel_volt = 'All'
    sel_equipment = []

standby_enabled = False
standby_scope = None
required_month_params = ['Kondisi']
if active_page in (PAGES["mcsa"], PAGES["word"]):
    standby_enabled = st.sidebar.checkbox('Standby otomatis jika tidak ada data bulan ini', value=True)
    if standby_enabled:
        standby_scope = st.sidebar.selectbox('Cakupan Standby', ['Per Unit (mengikuti filter Unit/Voltage)', 'Semua Unit (abaikan filter Unit)'])

        update_param_candidates = ['Kondisi', 'Load', 'Dev Voltage', 'Dev Current', 'THD Voltage %', 'THD Current %', 'Rotorbar Health', 'Upper Sideband', 'Lower Sideband', 'Bearing']
        present_params = set(df.get('Parameter', pd.Series(dtype=str)).astype(str).unique())
        update_param_options = [p for p in update_param_candidates if p in present_params] + sorted([p for p in present_params if p not in set(update_param_candidates)])
        _wajib_params = ['Dev Voltage', 'Dev Current', 'THD Voltage %', 'THD Current %', 'Upper Sideband', 'Lower Sideband', 'Load']
        default_required = [p for p in _wajib_params if p in update_param_options]
        if not default_required:
            default_required = [p for p in ['Kondisi'] if p in update_param_options]
        required_month_params = st.sidebar.multiselect('Parameter wajib update bulanan', update_param_options, default=default_required)
        if not required_month_params:
            required_month_params = ['Kondisi']

df_latest_augmented = df_latest.copy()
standby_report = None
df_month = None
meta_df = None
if active_page in (PAGES["mcsa"], PAGES["word"]) and standby_enabled:
    standby_key = (period_key, standby_scope, sel_unit, sel_volt, tuple(required_month_params))
    cached_key = st.session_state.get('_mcsa_standby_key')
    cached_aug = st.session_state.get('_mcsa_df_latest_augmented')
    cached_report = st.session_state.get('_mcsa_standby_report')
    cached_month = st.session_state.get('_mcsa_df_month')
    cached_meta = st.session_state.get('_mcsa_meta_df')
    if cached_key == standby_key and cached_aug is not None and cached_report is not None and cached_month is not None and cached_meta is not None:
        df_latest_augmented = cached_aug
        standby_report = cached_report
        df_month = cached_month
        meta_df = cached_meta
    else:
        df_latest_augmented, standby_report, df_month, meta_df = compute_standby(
            df,
            df_latest,
            df_latest_all,
            eq_master_df,
            master_norm_to_unit,
            master_norm_to_volt,
            date_end,
            standby_scope,
            sel_unit,
            sel_volt,
            required_month_params,
        )
        st.session_state['_mcsa_standby_key'] = standby_key
        st.session_state['_mcsa_standby_report'] = standby_report
        st.session_state['_mcsa_df_latest_augmented'] = df_latest_augmented
        st.session_state['_mcsa_df_month'] = df_month
        st.session_state['_mcsa_meta_df'] = meta_df

# Apply filters
filtered_key_base = st.session_state.get('_mcsa_standby_key') if (active_page is PAGES["mcsa"] and standby_enabled) else period_key
filtered_key = (filtered_key_base, sel_unit, sel_volt, tuple(sel_equipment))
filtered_df = st.session_state.get('_mcsa_filtered_df')
if st.session_state.get('_mcsa_filtered_key') != filtered_key or filtered_df is None:
    filtered_df = df_latest_augmented.copy()
    if sel_unit != 'All':
        _unit_series = filtered_df.get('Unit_Name', pd.Series(dtype=str)).astype(str).map(canon_unit_name)
        _norm_series = filtered_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(norm_equipment)
        _unit_series = _norm_series.map(master_norm_to_unit).fillna(_unit_series)
        filtered_df = filtered_df[_unit_series == sel_unit]
    if sel_volt != 'All':
        _volt_series = filtered_df.get('Voltage_Level', pd.Series(dtype=str)).astype(str).map(canon_voltage_level)
        _norm_series = filtered_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(norm_equipment)
        _volt_series = _norm_series.map(master_norm_to_volt).fillna(_volt_series)
        filtered_df = filtered_df[_volt_series == sel_volt]
    if sel_equipment:
        filtered_df = filter_mcsa_data(filtered_df, equipment=sel_equipment)
    st.session_state['_mcsa_filtered_key'] = filtered_key
    st.session_state['_mcsa_filtered_df'] = filtered_df

# Use filtered_df for Dashboard, but keep full df for management if needed (or filter there too)

# All the nav entry closures defined above reference these variables by name,
# so they only need to be correct now, at the point .run() actually calls them.
active_page.run()

