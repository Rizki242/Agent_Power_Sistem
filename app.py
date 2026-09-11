from importlib import import_module
import os
import sys
import traceback

import streamlit as st


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
    from src.components.mcsa_page_context import (
        load_mcsa_base_context,
        page_requires_mcsa_data,
        page_uses_mcsa_filters,
        prepare_mcsa_filtered_context,
        render_non_filter_sidebar,
    )
    from src.components.sidebar import render_sidebar_brand
except BaseException as exc:
    _fatal_dependency_error("modul internal (src/*)", exc)


st.set_page_config(page_title="CBM AI — Asset Reliability Management", layout="wide")
render_sidebar_brand(st)

PAGES = {}
mcsa_base = None
mcsa_filtered = None


def _load_page_symbol(module_name: str, symbol_name: str):
    """Import a page dependency only when its navigation entry is active."""
    try:
        module = import_module(module_name)
        symbol = getattr(module, symbol_name)
    except Exception as exc:
        st.error("Halaman ini gagal dimuat. Halaman lain tetap dapat digunakan.")
        st.caption(f"Modul: {module_name} · Komponen: {symbol_name}")
        st.exception(exc)
        st.stop()
    return symbol


def _require_base_context():
    if mcsa_base is None:
        raise RuntimeError("Halaman ini membutuhkan context data MCSA.")
    return mcsa_base


def _require_filtered_context():
    if mcsa_filtered is None:
        raise RuntimeError("Halaman ini membutuhkan filter data MCSA.")
    return mcsa_filtered


def _agent_dashboard_entry():
    render_agent_dashboard_page = _load_page_symbol(
        "src.pages.agent_dashboard_page", "render_agent_dashboard_page"
    )
    context = _require_base_context()
    render_agent_dashboard_page(
        st,
        df_latest_all=context.df_latest_all,
        mcsa_page=PAGES.get("mcsa"),
    )


def _dashboard_entry():
    render_dashboard_page = _load_page_symbol(
        "src.pages.dashboard_page", "render_dashboard_page"
    )
    base = _require_base_context()
    context = _require_filtered_context()
    render_dashboard_page(
        st,
        df=base.df,
        df_latest=context.df_latest,
        df_latest_all=base.df_latest_all,
        filtered_df=context.filtered_df,
        df_month=context.df_month,
        date_start=context.date_start,
        date_end=context.date_end,
        sel_unit=context.sel_unit,
        sel_volt=context.sel_volt,
        sel_equipment=context.sel_equipment,
        standby_enabled=context.standby_enabled,
        standby_report=context.standby_report,
        eq_master_df=context.eq_master_df,
        master_norm_to_unit=context.master_norm_to_unit,
        master_norm_to_volt=context.master_norm_to_volt,
        materi_page=PAGES.get("materi"),
    )


def _data_ingestion_hub_entry():
    render_data_ingestion_hub_page = _load_page_symbol(
        "src.pages.data_ingestion_hub_page", "render_data_ingestion_hub_page"
    )
    render_data_ingestion_hub_page(st)


def _data_management_entry():
    render_data_management_page = _load_page_symbol(
        "src.pages.data_management_page", "render_data_management_page"
    )
    context = _require_base_context()
    render_data_management_page(
        st,
        df=context.df,
        df_latest_all=context.df_latest_all,
        edit_mode=bool(st.session_state.get("edit_mode", False)),
    )


def _sync_word_entry():
    render_sync_word_page = _load_page_symbol(
        "src.pages.sync_word_page", "render_sync_word_page"
    )
    data_loader = import_module("src.data_loader")
    parse_all_reports_with_report = _load_page_symbol(
        "src.docx_parser", "parse_all_reports_with_report"
    )
    context = _require_base_context()
    render_sync_word_page(
        st,
        df=context.df,
        edit_mode=bool(st.session_state.get("edit_mode", False)),
        get_data_path=data_loader.get_data_path,
        get_folder_metadata=data_loader.get_folder_metadata,
        parse_all_reports_with_report=parse_all_reports_with_report,
        save_mcsa_data=data_loader.save_mcsa_data,
        load_mcsa_data=data_loader.load_mcsa_data,
        dashboard_page=PAGES.get("mcsa"),
    )


def _quality_entry():
    render_quality_check_page = _load_page_symbol(
        "src.pages.quality_page", "render_quality_check_page"
    )
    data_loader = import_module("src.data_loader")
    parse_all_reports_with_report = _load_page_symbol(
        "src.docx_parser", "parse_all_reports_with_report"
    )
    render_quality_check_page(
        st,
        get_data_path=data_loader.get_data_path,
        get_folder_metadata=data_loader.get_folder_metadata,
        parse_all_reports_with_report=parse_all_reports_with_report,
    )



def _asset_360_entry():
    render_asset_360_page = _load_page_symbol(
        "src.pages.asset_360_page", "render_asset_360_page"
    )
    context = _require_base_context()
    render_asset_360_page(
        st,
        df_latest_all=context.df_latest_all,
        df_all=context.df,
    )


def _asset_registry_entry():
    render_asset_registry_page = _load_page_symbol(
        "src.pages.asset_registry_page", "render_asset_registry_page"
    )
    render_asset_registry_page(
        st,
        edit_mode=bool(st.session_state.get("edit_mode", False)),
    )


def _asset_reports_entry():
    render_asset_reports_page = _load_page_symbol(
        "src.pages.asset_reports_page", "render_asset_reports_page"
    )
    render_asset_reports_page(st)


def _vibration_entry():
    render_vibration_page = _load_page_symbol(
        "src.pages.vibration_page", "render_vibration_page"
    )
    render_vibration_page(st)


def _dga_entry():
    render_dga_page = _load_page_symbol("src.pages.dga_page", "render_dga_page")
    render_dga_page(st)


def _tribology_entry():
    render_tribology_page = _load_page_symbol(
        "src.pages.tribology_page", "render_tribology_page"
    )
    render_tribology_page(st)


def _thermal_entry():
    render_thermal_page = _load_page_symbol(
        "src.pages.thermal_page", "render_thermal_page"
    )
    render_thermal_page(st)


def _pd_entry():
    render_pd_page = _load_page_symbol("src.pages.pd_page", "render_pd_page")
    render_pd_page(st)


def _condition_control_entry():
    render_condition_control_page = _load_page_symbol(
        "src.pages.condition_control_page", "render_condition_control_page"
    )
    render_condition_control_page(st)


def _materi_entry():
    render_materi_page = _load_page_symbol(
        "src.pages.materi_page", "render_materi_page"
    )
    render_materi_page(st)


def _settings_entry():
    render_settings_page = _load_page_symbol(
        "src.pages.settings_page", "render_settings_page"
    )
    render_settings_page(st)


def _chatbot_entry():
    render_chatbot_page = _load_page_symbol(
        "src.pages.chatbot_page", "render_chatbot_page"
    )
    context = _require_base_context()
    render_chatbot_page(
        st,
        df_latest_augmented=context.df_latest_all,
        df_all=context.df,
    )


def _ppt_entry():
    render_ppt_page = _load_page_symbol("src.pages.report_page", "render_ppt_page")
    create_ppt = _load_page_symbol("src.ppt_generator", "create_ppt")
    context = _require_filtered_context()
    render_ppt_page(
        st,
        context.filtered_df,
        context.df_latest,
        context.sel_unit,
        context.sel_volt,
        context.date_start,
        context.date_end,
        create_ppt,
        history_df=context.df_period,
    )


def _word_entry():
    render_word_page = _load_page_symbol("src.pages.report_page", "render_word_page")
    create_docx = _load_page_symbol("src.docx_generator", "create_docx")
    context = _require_filtered_context()
    render_word_page(
        st,
        context.filtered_df,
        context.df_latest,
        context.sel_unit,
        context.sel_volt,
        context.date_start,
        context.date_end,
        context.standby_report,
        create_docx,
    )


def _reliability_entry():
    render_reliability_page = _load_page_symbol(
        "src.pages.reliability_page", "render_reliability_page"
    )
    render_reliability_page(st)



def _work_orders_entry():
    render_work_orders_page = _load_page_symbol(
        "src.pages.work_orders_page", "render_work_orders_page"
    )
    render_work_orders_page(st)


def _help_entry():
    render_help_page = _load_page_symbol(
        "src.pages.help_page", "render_help_page"
    )
    render_help_page(st)



PAGE_SPECS = {
    "agent_dashboard": (_agent_dashboard_entry, "Agent Dashboard", ":material/dashboard:", True),
    "asset_360": (_asset_360_entry, "Asset 360° View", ":material/radar:", False),
    "mcsa": (_dashboard_entry, "MCSA", ":material/electric_bolt:", False),
    "data_ingestion_hub": (_data_ingestion_hub_entry, "Pusat Ingesti & Telemetri", ":material/upload:", False),
    "data_management": (_data_management_entry, "Manajemen Data", ":material/database:", False),
    "sync_word": (_sync_word_entry, "Sync Laporan Word", ":material/upload_file:", False),
    "quality": (_quality_entry, "Quality Check Laporan", ":material/fact_check:", False),
    "asset_registry": (_asset_registry_entry, "Register Aset", ":material/inventory_2:", False),
    "asset_reports": (_asset_reports_entry, "Laporan Kondisi", ":material/summarize:", False),
    "vibrasi": (_vibration_entry, "Vibrasi", ":material/vibration:", False),
    "dga": (_dga_entry, "DGA", ":material/science:", False),
    "tribology": (_tribology_entry, "Tribology", ":material/oil_barrel:", False),
    "thermal": (_thermal_entry, "Thermal", ":material/thermostat:", False),
    "partial_discharge": (_pd_entry, "Partial Discharge", ":material/bolt:", False),
    "condition_control": (_condition_control_entry, "Control condition", ":material/tune:", False),
    "reliability": (_reliability_entry, "Reliability", ":material/insights:", False),
    "chatbot": (_chatbot_entry, "Chatbot", ":material/smart_toy:", False),
    "materi": (_materi_entry, "Materi Training", ":material/menu_book:", False),
    "ppt": (_ppt_entry, "Laporan PPT", ":material/slideshow:", False),
    "word": (_word_entry, "Laporan Word", ":material/description:", False),
    "work_orders": (_work_orders_entry, "Work Orders", ":material/assignment:", False),
    "settings": (_settings_entry, "Settings", ":material/settings:", False),
    "help": (_help_entry, "Help & Support", ":material/help:", False),
}

for page_key, (entrypoint, title, icon, default) in PAGE_SPECS.items():
    PAGES[page_key] = st.Page(
        entrypoint,
        title=title,
        icon=icon,
        default=default,
    )

active_page = st.navigation(
    {
        "Command Center": [
            PAGES["agent_dashboard"],
            PAGES["chatbot"],
            PAGES["materi"],
        ],
        "Asset Management": [
            PAGES["asset_360"],
            PAGES["asset_registry"],
            PAGES["asset_reports"],
            PAGES["reliability"],
            PAGES["work_orders"],
        ],
        "Condition Monitoring (PdM)": [
            PAGES["mcsa"],
            PAGES["vibrasi"],
            PAGES["dga"],
            PAGES["tribology"],
            PAGES["thermal"],
            PAGES["partial_discharge"],
            PAGES["condition_control"],
        ],
        "Data Ingestion & Sync": [
            PAGES["data_ingestion_hub"],
            PAGES["sync_word"],
            PAGES["quality"],
            PAGES["data_management"],
        ],
        "Laporan & Dokumen": [PAGES["ppt"], PAGES["word"]],
        "Pengaturan & Bantuan": [PAGES["settings"], PAGES["help"]],
    },
    expanded=False,
)

active_page_key = next(
    page_key for page_key, page in PAGES.items() if active_page is page
)
if page_requires_mcsa_data(active_page_key):
    mcsa_base = load_mcsa_base_context(st)

if page_uses_mcsa_filters(active_page_key):
    mcsa_filtered = prepare_mcsa_filtered_context(
        mcsa_base,
        enable_standby=active_page_key in {"mcsa", "word"},
        streamlit=st,
    )
else:
    render_non_filter_sidebar(st, mcsa_base)

active_page.run()
