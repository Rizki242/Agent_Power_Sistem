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
    from src.standards import calculate_condition, generate_esa_mcsa_quick_recommendations, generate_initial_analysis
    from src.analytics import calculate_equipment_health_score, detect_equipment_anomalies
    from src.components.sidebar import render_sidebar, render_sidebar_brand
    from src.pages.chatbot_page import render_chatbot_page
    from src.pages.condition_control_page import render_condition_control_page
    from src.pages.dashboard_page import render_dashboard_page
    from src.pages.data_management_page import render_data_management_page
    from src.pages.materi_page import render_materi_page
    from src.pages.placeholder_page import render_placeholder_page
    from src.pages.quality_page import render_quality_check_page
    from src.pages.report_page import render_ppt_page, render_word_page
    from src.pages.settings_page import render_settings_page
    from src.pages.sync_word_page import render_sync_word_page
except BaseException as exc:
    _fatal_dependency_error("modul internal (src/*)", exc)
import json
import re
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
        dashboard_page=PAGES.get("dashboard"),
    )


def _quality_entry():
    render_quality_check_page(
        st,
        get_data_path=get_data_path,
        get_folder_metadata=get_folder_metadata,
        parse_all_reports_with_report=parse_all_reports_with_report,
    )


def _materi_entry():
    render_materi_page(st)


def _condition_control_entry():
    render_condition_control_page(st)


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
    render_placeholder_page(st, "Reliability", "Reliability fusion engine (health index, risk, RUL) belum tersedia di Streamlit UI.")


def _work_orders_entry():
    render_placeholder_page(st, "Work Orders", "Integrasi Work Order / EAM belum tersedia di Streamlit UI.")


def _help_entry():
    render_placeholder_page(st, "Help & Support", "Dokumentasi dan bantuan akan hadir di rilis mendatang.")


PAGES["dashboard"] = st.Page(_dashboard_entry, title="Command Center", icon=":material/dashboard:", default=True)
PAGES["data_management"] = st.Page(_data_management_entry, title="Manajemen Data", icon=":material/database:")
PAGES["sync_word"] = st.Page(_sync_word_entry, title="Sync Laporan Word", icon=":material/upload_file:")
PAGES["quality"] = st.Page(_quality_entry, title="Quality Check Laporan", icon=":material/fact_check:")
PAGES["engineering"] = st.Page(_condition_control_entry, title="Control condition", icon=":material/tune:")
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
        "Command Center": [PAGES["dashboard"]],
        "Asset Management": [PAGES["data_management"], PAGES["sync_word"], PAGES["quality"]],
        "Engineering": [PAGES["engineering"]],
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

sidebar_state = render_sidebar(st, min_date, max_date)
date_start = sidebar_state["date_start"]
date_end = sidebar_state["date_end"]

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
    eq_master_df = pd.DataFrame()
    try:
        if os.path.exists(master_path):
            with open(master_path, 'r', encoding='utf-8') as fp:
                eq_master = json.load(fp) or []
            eq_master_df = pd.DataFrame(eq_master)
    except Exception:
        eq_master_df = pd.DataFrame()
    if not eq_master_df.empty:
        for col in ['Equipment', 'Unit_Name', 'Voltage_Level']:
            if col not in eq_master_df.columns:
                eq_master_df[col] = ''
        if 'Full_Name' not in eq_master_df.columns:
            eq_master_df['Full_Name'] = eq_master_df.get('Equipment', '')
        eq_master_df['Equipment'] = eq_master_df['Equipment'].astype(str)
        eq_master_df['Unit_Name'] = eq_master_df['Unit_Name'].astype(str)
        eq_master_df['Voltage_Level'] = eq_master_df['Voltage_Level'].astype(str)
        eq_master_df['Full_Name'] = eq_master_df['Full_Name'].astype(str)
    st.session_state['_mcsa_master_key'] = master_key
    st.session_state['_mcsa_master_df'] = eq_master_df
else:
    _cached_master_df = st.session_state.get('_mcsa_master_df')
    eq_master_df = _cached_master_df if isinstance(_cached_master_df, pd.DataFrame) else pd.DataFrame()

def _norm_equipment(x) -> str:
    return re.sub(r'[^A-Za-z0-9]', '', str(x or '')).upper()

def _canon_unit_name(x) -> str:
    s = str(x or '').strip().upper()
    s = re.sub(r'\s+', ' ', s)
    s0 = s.replace(' ', '')
    if s0 == 'UNIT1':
        return 'UNIT 1'
    if s0 == 'UNIT2':
        return 'UNIT 2'
    if s0 == 'UNIT3':
        return 'UNIT 3'
    if s0 == 'UNITCOMMON':
        return 'UNIT COMMON'
    return s if s else 'Unknown'

def _canon_voltage_level(x) -> str:
    s = str(x or '').strip().upper()
    if not s:
        return 'Unknown'
    s0 = re.sub(r'\s+', '', s)
    if '6.3' in s0 and 'KV' in s0:
        return '6.3 KV'
    if any(k in s0 for k in ['380/400', '380-400', '380400', '400V', '400/380']):
        return '380/400 V'
    if s0 == 'UNKNOWN':
        return 'Unknown'
    return s

def _canon_condition_status(x) -> str:
    s = str(x or '').strip().lower()
    if any(k in s for k in ['high', 'bad', 'critical', 'rusak', 'damage', 'trip']):
        return 'High'
    if any(k in s for k in ['alarm', 'warning']):
        return 'Alarm'
    if 'standby' in s:
        return 'Standby'
    if any(k in s for k in ['normal', 'ok', 'good']):
        return 'Normal'
    return 'Unknown'


def _compute_overall_status_from_rows(rows: pd.DataFrame) -> str:
    if rows is None or rows.empty:
        return 'Unknown'

    def _safe_float(v):
        try:
            if v is None:
                return None
            if isinstance(v, float) and pd.isna(v):
                return None
            s = str(v).strip()
            if s == '' or s.lower() in {'nan', 'none'}:
                return None
            return float(s)
        except Exception:
            return None

    def _get_param(name: str):
        g = rows[rows['Parameter'] == name]
        if g.empty:
            return None
        r = g.iloc[0]
        v = r.get('Value', None)
        v2 = _safe_float(v)
        if v2 is not None:
            return v2
        return r.get('Raw_Value', None)

    params = {
        'Dev Voltage': _get_param('Dev Voltage'),
        'Dev Current': _get_param('Dev Current'),
        'THD Voltage %': _get_param('THD Voltage %'),
        'THD Current %': _get_param('THD Current %'),
        'Upper Sideband': _get_param('Upper Sideband'),
        'Lower Sideband': _get_param('Lower Sideband'),
        'Rotorbar Health': _get_param('Rotorbar Health'),
        'Se Fund': _get_param('Se Fund'),
        'Se Harm': _get_param('Se Harm'),
        'Rotorbar Level %': _get_param('Rotorbar Level %'),
        'Bearing': _get_param('Bearing'),
    }

    try:
        result = calculate_condition(params)
        return str(result.get('Overall', 'Normal'))
    except Exception:
        k_rows = rows[rows['Parameter'] == 'Kondisi']
        if not k_rows.empty:
            val = k_rows['Raw_Value'].astype(str).iloc[0]
            return _canon_condition_status(val)
        return 'Unknown'

master_norm_to_unit = st.session_state.get('_mcsa_master_norm_to_unit') or {}
master_norm_to_volt = st.session_state.get('_mcsa_master_norm_to_volt') or {}
if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty and st.session_state.get('_mcsa_master_norm_to_key') != master_key:
    _tmp = eq_master_df.copy()
    _tmp['_norm'] = _tmp['Equipment'].astype(str).map(_norm_equipment)
    _tmp['_unit'] = _tmp['Unit_Name'].astype(str).map(_canon_unit_name)
    _tmp['_volt'] = _tmp['Voltage_Level'].astype(str).map(_canon_voltage_level)
    _tmp = _tmp.drop_duplicates(subset=['_norm'], keep='first')
    master_norm_to_unit = _tmp.set_index('_norm')['_unit'].to_dict()
    master_norm_to_volt = _tmp.set_index('_norm')['_volt'].to_dict()
    st.session_state['_mcsa_master_norm_to_unit'] = master_norm_to_unit
    st.session_state['_mcsa_master_norm_to_volt'] = master_norm_to_volt
    st.session_state['_mcsa_master_norm_to_key'] = master_key

# Get unique values for filters
unit_choices = ['All', 'UNIT 1', 'UNIT 2', 'UNIT 3', 'UNIT COMMON', 'Unknown']
units_present = set(_canon_unit_name(x) for x in df_latest_for_filters.get('Unit_Name', pd.Series(dtype=str)).unique())
if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty and 'Unit_Name' in eq_master_df.columns:
    units_present = units_present.union(set(eq_master_df['Unit_Name'].astype(str).map(_canon_unit_name).unique()))
all_units = [u for u in unit_choices if u == 'All' or u in units_present] + sorted([u for u in units_present if u not in set(unit_choices)])
if 'filter_unit' not in st.session_state:
    st.session_state.filter_unit = 'All'
if st.session_state.filter_unit not in all_units:
    st.session_state.filter_unit = 'All'
sel_unit = st.sidebar.selectbox("Unit", all_units, key="filter_unit")

volt_choices = ['All', '380/400 V', '6.3 KV', 'Unknown']
volts_present = set(_canon_voltage_level(x) for x in df_latest_for_filters.get('Voltage_Level', pd.Series(dtype=str)).unique())
if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty and 'Voltage_Level' in eq_master_df.columns:
    volts_present = volts_present.union(set(eq_master_df['Voltage_Level'].astype(str).map(_canon_voltage_level).unique()))
all_volts = [v for v in volt_choices if v == 'All' or v in volts_present] + sorted([v for v in volts_present if v not in set(volt_choices)])
if 'filter_volt' not in st.session_state:
    st.session_state.filter_volt = 'All'
if st.session_state.filter_volt not in all_volts:
    st.session_state.filter_volt = 'All'
sel_volt = st.sidebar.selectbox("Voltage", all_volts, key="filter_volt")

# Equipment is a global, cascading filter after period, unit, and voltage.
equipment_filter_df = df_latest_for_filters.copy()
if sel_unit != 'All':
    _eq_unit = equipment_filter_df.get('Unit_Name', pd.Series(dtype=str)).astype(str).map(_canon_unit_name)
    _eq_norm = equipment_filter_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(_norm_equipment)
    equipment_filter_df = equipment_filter_df[_eq_norm.map(master_norm_to_unit).fillna(_eq_unit) == sel_unit]
if sel_volt != 'All':
    _eq_volt = equipment_filter_df.get('Voltage_Level', pd.Series(dtype=str)).astype(str).map(_canon_voltage_level)
    _eq_norm = equipment_filter_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(_norm_equipment)
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

standby_enabled = False
standby_scope = None
required_month_params = ['Kondisi']
if active_page in (PAGES["dashboard"], PAGES["word"]):
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
if active_page in (PAGES["dashboard"], PAGES["word"]) and standby_enabled:
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
        ref_dt = pd.Timestamp(date_end)
        month_start = ref_dt.replace(day=1)
        month_end = month_start + pd.offsets.MonthEnd(0)

        df_month = df.copy()
        df_month['Date'] = pd.to_datetime(df_month.get('Date', pd.NaT), errors='coerce')
        df_month = df_month[(df_month['Date'] >= month_start) & (df_month['Date'] <= month_end)]

        if 'Unit_Name' in df_month.columns:
            df_month['_unit_canon'] = df_month['Unit_Name'].astype(str).map(_canon_unit_name)
        if 'Voltage_Level' in df_month.columns:
            df_month['_volt_canon'] = df_month['Voltage_Level'].astype(str).map(_canon_voltage_level)
        df_month['_norm'] = df_month.get('Equipment', pd.Series(dtype=str)).astype(str).map(_norm_equipment)
        df_month['_unit_master'] = df_month['_norm'].map(master_norm_to_unit)
        df_month['_volt_master'] = df_month['_norm'].map(master_norm_to_volt)
        df_month['_unit_scope'] = df_month['_unit_master']
        if '_unit_canon' in df_month.columns:
            df_month['_unit_scope'] = df_month['_unit_scope'].fillna(df_month['_unit_canon'])
        df_month['_volt_scope'] = df_month['_volt_master']
        if '_volt_canon' in df_month.columns:
            df_month['_volt_scope'] = df_month['_volt_scope'].fillna(df_month['_volt_canon'])

        base_meta_df = eq_master_df if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty else df_latest_all
        meta_df = base_meta_df.copy()
        if 'Unit_Name' in meta_df.columns:
            meta_df['_unit_canon'] = meta_df['Unit_Name'].astype(str).map(_canon_unit_name)
        if 'Voltage_Level' in meta_df.columns:
            meta_df['_volt_canon'] = meta_df['Voltage_Level'].astype(str).map(_canon_voltage_level)
        if standby_scope and standby_scope.startswith('Per Unit'):
            if sel_unit != 'All':
                if '_unit_canon' in meta_df.columns:
                    meta_df = meta_df[meta_df['_unit_canon'] == sel_unit]
                df_month = df_month[df_month['_unit_scope'] == sel_unit]
            if sel_volt != 'All':
                if '_volt_canon' in meta_df.columns:
                    meta_df = meta_df[meta_df['_volt_canon'] == sel_volt]
                df_month = df_month[df_month['_volt_scope'] == sel_volt]
        else:
            if sel_volt != 'All':
                if '_volt_canon' in meta_df.columns:
                    meta_df = meta_df[meta_df['_volt_canon'] == sel_volt]
                df_month = df_month[df_month['_volt_scope'] == sel_volt]

        meta_eq = meta_df.get('Equipment', pd.Series(dtype=str)).astype(str)
        meta_norm = meta_eq.map(_norm_equipment)
        meta_df = meta_df.assign(_norm=meta_norm)
        norm_to_eq = meta_df.drop_duplicates(subset=['_norm']).set_index('_norm')['Equipment'].to_dict() if not meta_df.empty else {}
        eq_universe_norm = set(norm_to_eq.keys())

        df_month_req = df_month.copy()
        raw_ok = pd.Series([False] * len(df_month_req), index=df_month_req.index)
        val_ok = pd.Series([False] * len(df_month_req), index=df_month_req.index)
        if 'Raw_Value' in df_month_req.columns:
            rv = df_month_req['Raw_Value']
            raw_ok = rv.notna() & rv.astype(str).str.strip().ne('')
        if 'Value' in df_month_req.columns:
            vv = df_month_req['Value']
            val_ok = vv.notna()
        df_month_req = df_month_req[raw_ok | val_ok]
        eq_present_raw = df_month_req.get('Equipment', pd.Series(dtype=str)).astype(str)
        eq_present_norm = set(eq_present_raw.map(_norm_equipment))
        missing_norm = sorted([n for n in (eq_universe_norm - eq_present_norm) if n and n.lower() not in {'nan', 'none'}])
        standby_eq = [norm_to_eq.get(n, n) for n in missing_norm]
        eq_present = sorted([norm_to_eq.get(n, n) for n in (eq_universe_norm & eq_present_norm) if n and n.lower() not in {'nan', 'none'}])
        eq_universe = sorted([norm_to_eq.get(n, n) for n in eq_universe_norm if n and n.lower() not in {'nan', 'none'}])

        reasons_path = get_data_path('config', 'standby_reasons.json')
        reasons_data = {}
        try:
            if os.path.exists(reasons_path):
                with open(reasons_path, 'r', encoding='utf-8') as fp:
                    reasons_data = json.load(fp)
        except:
            reasons_data = {}

        month_key = month_start.strftime('%Y-%m')
        reasons_for_month = reasons_data.get(month_key, {})

        standby_report = {
            'month_start': month_start,
            'month_end': month_end,
            'required_params': required_month_params,
            'scope': standby_scope,
            'sel_unit': sel_unit,
            'sel_volt': sel_volt,
            'eq_universe': eq_universe,
            'eq_present': eq_present,
            'eq_missing': standby_eq,
            'standby_reasons': reasons_for_month,
        }

        if standby_eq:
            meta_map = meta_df.drop_duplicates(subset=['Equipment']).set_index('Equipment') if 'Equipment' in meta_df.columns else pd.DataFrame()
            month_name = month_start.strftime('%b').upper()
            year_val = int(month_start.year)
            standby_rows = []
            for eq in standby_eq:
                unit_name = 'Unknown'
                volt_name = 'Unknown'
                full_name = eq
                if not meta_map.empty and eq in meta_map.index:
                    r = meta_map.loc[eq]
                    if isinstance(r, pd.DataFrame):
                        r = r.iloc[0]
                    unit_name = r.get('Unit_Name', unit_name)
                    volt_name = r.get('Voltage_Level', volt_name)
                    full_name = r.get('Full_Name', full_name)
                standby_rows.append({
                    'Equipment': eq,
                    'Parameter': 'Kondisi',
                    'Month': month_name,
                    'Year': year_val,
                    'Month_Name': month_name,
                    'Date': str(month_end.date()),
                    'Raw_Value': 'Standby',
                    'Value': None,
                    'Unit': '',
                    'Limit': '',
                    'Status': 'Standby',
                    'Status_Category': 'Standby',
                    'Status_Level': 0,
                    'Unit_Name': unit_name,
                    'Voltage_Level': volt_name,
                    'Full_Name': full_name
                })
            df_latest_augmented = pd.concat([df_latest_augmented, pd.DataFrame(standby_rows)], ignore_index=True)

        st.session_state['_mcsa_standby_key'] = standby_key
        st.session_state['_mcsa_standby_report'] = standby_report
        st.session_state['_mcsa_df_latest_augmented'] = df_latest_augmented
        st.session_state['_mcsa_df_month'] = df_month
        st.session_state['_mcsa_meta_df'] = meta_df

# Apply filters
filtered_key_base = st.session_state.get('_mcsa_standby_key') if (active_page is PAGES["dashboard"] and standby_enabled) else period_key
filtered_key = (filtered_key_base, sel_unit, sel_volt, tuple(sel_equipment))
filtered_df = st.session_state.get('_mcsa_filtered_df')
if st.session_state.get('_mcsa_filtered_key') != filtered_key or filtered_df is None:
    filtered_df = df_latest_augmented.copy()
    if sel_unit != 'All':
        _unit_series = filtered_df.get('Unit_Name', pd.Series(dtype=str)).astype(str).map(_canon_unit_name)
        _norm_series = filtered_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(_norm_equipment)
        _unit_series = _norm_series.map(master_norm_to_unit).fillna(_unit_series)
        filtered_df = filtered_df[_unit_series == sel_unit]
    if sel_volt != 'All':
        _volt_series = filtered_df.get('Voltage_Level', pd.Series(dtype=str)).astype(str).map(_canon_voltage_level)
        _norm_series = filtered_df.get('Equipment', pd.Series(dtype=str)).astype(str).map(_norm_equipment)
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

