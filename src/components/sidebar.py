from calendar import month_name
from datetime import date

from src.components.theme import get_modern_theme_css


def _inject_styles(st):
    st.markdown(get_modern_theme_css(), unsafe_allow_html=True)


def render_sidebar_brand(st):
    """Modern brand card with live status indicator. Injects the shared theme CSS
    as a side effect, so this must run before any other themed sidebar content."""
    _inject_styles(st)
    st.sidebar.markdown(
        """
        <div class="mcsa-header-card">
            <div class="mcsa-header-title">
                <span class="mcsa-pulse-dot"></span>
                <span>CBM AI Hub</span>
            </div>
            <div class="mcsa-header-sub">Asset Reliability & Condition Monitoring</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(st, min_date, max_date, show_filters=True):
    st.sidebar.divider()
    if not show_filters:
        st.sidebar.toggle("Mode Edit", key="edit_mode", help="Izinkan perubahan data dan upload laporan")
        return {"edit_mode": bool(st.session_state.get("edit_mode", False)), "date_start": min_date, "date_end": max_date}
    st.sidebar.markdown('<div class="mcsa-group">Filter data</div>', unsafe_allow_html=True)
    focus_range = st.session_state.pop("filter_focus_range", None)
    if focus_range:
        st.session_state.filter_date_range_widget = focus_range
        st.session_state.filter_year = focus_range[1].year
        st.session_state.filter_month = focus_range[1].month if focus_range[0].month == focus_range[1].month else 0

    clean_dates = []
    for value in st.session_state.get("_mcsa_available_dates", []):
        try:
            clean_dates.append(value.date() if hasattr(value, "date") else value)
        except (TypeError, ValueError):
            continue
    years = sorted({value.year for value in clean_dates}) or list(range(min_date.year, max_date.year + 1))
    year_options = [0] + years
    if "filter_year" not in st.session_state or st.session_state.filter_year not in year_options:
        st.session_state.filter_year = 0
    selected_year = st.sidebar.selectbox("Tahun", year_options, key="filter_year", format_func=lambda value: "Semua tahun" if value == 0 else str(value))

    if selected_year and clean_dates:
        month_options = sorted({value.month for value in clean_dates if value.year == selected_year})
    else:
        month_options = list(range(1, 13))
        if selected_year == min_date.year:
            month_options = [m for m in month_options if m >= min_date.month]
        if selected_year == max_date.year:
            month_options = [m for m in month_options if m <= max_date.month]
    month_options = [0] + month_options
    if "filter_month" not in st.session_state or st.session_state.filter_month not in month_options:
        st.session_state.filter_month = 0
    selected_month = st.sidebar.selectbox("Bulan", month_options, key="filter_month", disabled=selected_year == 0, format_func=lambda value: "Semua bulan" if value == 0 else month_name[value])

    period_min, period_max = min_date, max_date
    if selected_year:
        period_min = max(min_date, date(selected_year, 1, 1))
        period_max = min(max_date, date(selected_year, 12, 31))
    if selected_year and selected_month:
        import calendar
        period_min = max(min_date, date(selected_year, selected_month, 1))
        period_max = min(max_date, date(selected_year, selected_month, calendar.monthrange(selected_year, selected_month)[1]))

    current = st.session_state.get("filter_date_range_widget", (period_min, period_max))
    if not isinstance(current, (list, tuple)) or len(current) != 2 or current[0] < period_min or current[1] > period_max:
        current = (period_min, period_max)
        st.session_state.filter_date_range_widget = current
    selected_range = st.sidebar.date_input("Rentang tanggal", value=current, min_value=period_min, max_value=period_max, key="filter_date_range_widget")
    if isinstance(selected_range, (list, tuple)) and len(selected_range) == 2:
        date_start, date_end = selected_range
    else:
        date_start, date_end = current

    if st.sidebar.button("Reset filter", icon=":material/restart_alt:", width="stretch"):
        for key in ["filter_year", "filter_month", "filter_date_range_widget", "filter_unit", "filter_volt", "filter_equipment"]:
            st.session_state.pop(key, None)
        st.rerun()

    period_days = (date_end - date_start).days + 1
    st.sidebar.markdown(f'<div class="mcsa-period"><strong>{date_start.strftime("%d %b %Y")} - {date_end.strftime("%d %b %Y")}</strong><br>{period_days} hari data</div>', unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.toggle("Mode Edit", key="edit_mode", help="Izinkan perubahan data dan upload laporan")

    return {"edit_mode": bool(st.session_state.get("edit_mode", False)), "date_start": date_start, "date_end": date_end}



