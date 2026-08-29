from calendar import month_name
from datetime import date

from src.components.theme import get_modern_theme_css


NAV_GROUPS = {
    "Monitoring": [("Dashboard", ":material/dashboard:"), ("Quality Check Laporan", ":material/fact_check:")],
    "Data": [("Manajemen Data", ":material/database:"), ("Sync Laporan Word", ":material/upload_file:")],
    "Laporan": [("Laporan PPT", ":material/slideshow:"), ("Laporan Word", ":material/description:")],
    "Referensi": [("Materi Training", ":material/menu_book:"), ("Chatbot", ":material/smart_toy:")],
}


def _inject_styles(st):
    st.markdown(get_modern_theme_css(), unsafe_allow_html=True)


def render_sidebar(st, nav_options, min_date, max_date):
    _inject_styles(st)
    
    # Modern brand card with live status indicator
    st.sidebar.markdown(
        """
        <div class="mcsa-header-card">
            <div class="mcsa-header-title">
                <span class="mcsa-pulse-dot"></span>
                <span>MCSA Control</span>
            </div>
            <div class="mcsa-header-sub">PLTU Predictive Maintenance Suite</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "page" not in st.session_state or st.session_state.page not in nav_options:
        st.session_state.page = nav_options[0]

    for group, items in NAV_GROUPS.items():
        visible = [(page, icon) for page, icon in items if page in nav_options]
        if not visible:
            continue
        st.sidebar.markdown(f'<div class="mcsa-nav-section-title">{group}</div>', unsafe_allow_html=True)
        for page, icon in visible:
            if page == st.session_state.page:
                st.sidebar.markdown(f'<div class="mcsa-nav-active_item mcsa-nav-active-item"><span>●</span> {page}</div>', unsafe_allow_html=True)
            elif st.sidebar.button(page, key=f"nav_{page}", icon=icon, use_container_width=True):
                st.session_state.page = page
                st.rerun()

    st.sidebar.divider()
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

    if st.sidebar.button("Reset filter", icon=":material/restart_alt:", use_container_width=True):
        for key in ["filter_year", "filter_month", "filter_date_range_widget", "filter_unit", "filter_volt", "filter_equipment"]:
            st.session_state.pop(key, None)
        st.rerun()

    period_days = (date_end - date_start).days + 1
    st.sidebar.markdown(f'<div class="mcsa-period"><strong>{date_start.strftime("%d %b %Y")} - {date_end.strftime("%d %b %Y")}</strong><br>{period_days} hari data</div>', unsafe_allow_html=True)
    st.sidebar.divider()
    st.sidebar.toggle("Mode Edit", key="edit_mode", help="Izinkan perubahan data dan upload laporan")

    # --- LLM AI Settings (Multi-Provider) ---
    with st.sidebar.expander("🤖 Pengaturan Model LLM", expanded=False):
        from src.llm_assistant import (
            AVAILABLE_GEMINI_MODELS,
            AVAILABLE_GROQ_MODELS,
            AVAILABLE_OLLAMA_MODELS,
            AVAILABLE_OPENCODE_MODELS,
            DEFAULT_GEMINI_MODEL,
            DEFAULT_GROQ_MODEL,
            DEFAULT_OLLAMA_HOST,
            DEFAULT_OLLAMA_MODEL,
            DEFAULT_OPENCODE_BASE_URL,
            DEFAULT_OPENCODE_MODEL,
            is_any_ai_configured,
            resolve_provider_key,
            test_gemini_connection,
            test_groq_connection,
            test_ollama_connection,
            test_opencode_connection,
        )

        # Auto-activate if any key is found in environment or secrets
        if "ai_enabled" not in st.session_state:
            st.session_state.ai_enabled = is_any_ai_configured(st)
        if "ai_provider" not in st.session_state:
            st.session_state.ai_provider = "gemini"

        ai_active = st.checkbox(
            "Aktifkan Model LLM",
            key="ai_enabled",
            help="Mengaktifkan asistensi Model LLM untuk Chatbot dan Analisis Mendalam.",
        )

        providers = [
            "Google Gemini (Cloud)",
            "Groq (Ultra-Fast Cloud)",
            "OpenCode / OpenAI / OpenRouter",
            "Ollama (Lokal / Offline)",
        ]
        provider_map = {
            "gemini": 0,
            "groq": 1,
            "opencode": 2,
            "ollama": 3,
        }
        current_p = st.session_state.get("ai_provider", "gemini")
        default_p_idx = provider_map.get(current_p, 0)

        selected_provider_label = st.selectbox(
            "Pilih Provider LLM:",
            providers,
            index=default_p_idx,
            key="_llm_provider_sel",
        )
        if "Gemini" in selected_provider_label:
            st.session_state.ai_provider = "gemini"
        elif "Groq" in selected_provider_label:
            st.session_state.ai_provider = "groq"
        elif "OpenCode" in selected_provider_label:
            st.session_state.ai_provider = "opencode"
        else:
            st.session_state.ai_provider = "ollama"

        active_prov = st.session_state.ai_provider

        # 1. Google Gemini
        if active_prov == "gemini":
            current_key = st.session_state.get("gemini_api_key", "")
            resolved = resolve_provider_key("gemini", current_key, st)

            api_key_val = st.text_input(
                "Gemini API Key",
                value=current_key,
                type="password",
                placeholder="Masukkan API Key (atau via .env)",
                help="Jika dikosongkan, otomatis membaca GEMINI_API_KEY dari .env atau secrets.toml.",
                key="_gemini_key_widget",
            )
            if api_key_val != current_key:
                st.session_state.gemini_api_key = api_key_val.strip()

            gemini_choices = AVAILABLE_GEMINI_MODELS + ["Custom..."]
            current_model = st.session_state.get("gemini_model", DEFAULT_GEMINI_MODEL)
            default_idx = gemini_choices.index(current_model) if current_model in gemini_choices else 0
            selected_model_choice = st.selectbox("Pilih Model Gemini", gemini_choices, index=default_idx, key="_gemini_model_sel")

            if selected_model_choice == "Custom...":
                custom_model = st.text_input("Nama Model Custom", value=current_model if current_model not in AVAILABLE_GEMINI_MODELS else DEFAULT_GEMINI_MODEL, key="_custom_model_input")
                st.session_state.gemini_model = custom_model.strip() or DEFAULT_GEMINI_MODEL
            else:
                st.session_state.gemini_model = selected_model_choice

            if resolved:
                st.caption(f"🔑 Key Terdeteksi ({resolved[:6]}...{resolved[-4:]})")
            else:
                st.caption("⚪ Belum ada API Key (menggunakan Rule-Based)")

            if st.button("Tes Koneksi Gemini", icon=":material/wifi_tethering:", use_container_width=True):
                with st.spinner("Menguji koneksi ke Gemini..."):
                    active_key = resolve_provider_key("gemini", st.session_state.get("gemini_api_key"), st)
                    success, msg = test_gemini_connection(active_key, st.session_state.get("gemini_model", DEFAULT_GEMINI_MODEL))
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        # 2. Groq
        elif active_prov == "groq":
            current_key = st.session_state.get("groq_api_key", "")
            resolved = resolve_provider_key("groq", current_key, st)

            api_key_val = st.text_input(
                "Groq API Key",
                value=current_key,
                type="password",
                placeholder="gsk_... (atau via .env GROQ_API_KEY)",
                key="_groq_key_widget",
            )
            if api_key_val != current_key:
                st.session_state.groq_api_key = api_key_val.strip()

            groq_choices = AVAILABLE_GROQ_MODELS + ["Custom..."]
            current_model = st.session_state.get("groq_model", DEFAULT_GROQ_MODEL)
            default_idx = groq_choices.index(current_model) if current_model in groq_choices else 0
            selected_model_choice = st.selectbox("Pilih Model Groq", groq_choices, index=default_idx, key="_groq_model_sel")

            if selected_model_choice == "Custom...":
                custom_model = st.text_input("Nama Model Groq", value=current_model if current_model not in AVAILABLE_GROQ_MODELS else DEFAULT_GROQ_MODEL, key="_custom_groq_model_input")
                st.session_state.groq_model = custom_model.strip() or DEFAULT_GROQ_MODEL
            else:
                st.session_state.groq_model = selected_model_choice

            if resolved:
                st.caption(f"🔑 Key Terdeteksi ({resolved[:6]}...{resolved[-4:]})")
            else:
                st.caption("⚪ Belum ada Groq API Key")

            if st.button("Tes Koneksi Groq", icon=":material/speed:", use_container_width=True):
                with st.spinner("Menguji koneksi ke Groq..."):
                    active_key = resolve_provider_key("groq", st.session_state.get("groq_api_key"), st)
                    success, msg = test_groq_connection(active_key, st.session_state.get("groq_model", DEFAULT_GROQ_MODEL))
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        # 3. OpenCode / OpenAI Compatible
        elif active_prov == "opencode":
            base_url_val = st.text_input(
                "Base URL Endpoint",
                value=st.session_state.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL),
                placeholder="https://api.openai.com/v1 atau http://localhost:8000/v1",
                key="_opencode_base_url_widget",
            )
            st.session_state.opencode_base_url = base_url_val.strip() or DEFAULT_OPENCODE_BASE_URL

            current_key = st.session_state.get("opencode_api_key", "")
            resolved = resolve_provider_key("opencode", current_key, st)
            api_key_val = st.text_input(
                "API Key (Opsional jika endpoint lokal)",
                value=current_key,
                type="password",
                placeholder="Bearer Token / API Key",
                key="_opencode_key_widget",
            )
            if api_key_val != current_key:
                st.session_state.opencode_api_key = api_key_val.strip()

            opencode_choices = AVAILABLE_OPENCODE_MODELS + ["Custom..."]
            current_model = st.session_state.get("opencode_model", DEFAULT_OPENCODE_MODEL)
            default_idx = opencode_choices.index(current_model) if current_model in opencode_choices else 0
            selected_model_choice = st.selectbox("Pilih Model", opencode_choices, index=default_idx, key="_opencode_model_sel")

            if selected_model_choice == "Custom...":
                custom_model = st.text_input("Nama Model Endpoint", value=current_model if current_model not in AVAILABLE_OPENCODE_MODELS else DEFAULT_OPENCODE_MODEL, key="_custom_opencode_model_input")
                st.session_state.opencode_model = custom_model.strip() or DEFAULT_OPENCODE_MODEL
            else:
                st.session_state.opencode_model = selected_model_choice

            if st.button("Tes Koneksi Endpoint", icon=":material/hub:", use_container_width=True):
                with st.spinner("Menguji koneksi ke endpoint..."):
                    active_key = resolve_provider_key("opencode", st.session_state.get("opencode_api_key"), st)
                    success, msg = test_opencode_connection(st.session_state.opencode_base_url, active_key, st.session_state.opencode_model)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

        # 4. Ollama Local
        else:
            ollama_host = st.text_input(
                "Ollama Host URL",
                value=st.session_state.get("ollama_host", DEFAULT_OLLAMA_HOST),
                help="URL server Ollama lokal. Default: http://localhost:11434",
                key="_ollama_host_widget",
            )
            st.session_state.ollama_host = ollama_host.strip() or DEFAULT_OLLAMA_HOST

            discovered_models = st.session_state.get("_ollama_discovered_models", [])
            ollama_choices = list(dict.fromkeys(discovered_models + AVAILABLE_OLLAMA_MODELS + ["Custom..."]))
            current_ollama_model = st.session_state.get("ollama_model", DEFAULT_OLLAMA_MODEL)
            default_o_idx = ollama_choices.index(current_ollama_model) if current_ollama_model in ollama_choices else 0
            selected_ollama_choice = st.selectbox("Pilih Model Ollama", ollama_choices, index=default_o_idx, key="_ollama_model_sel")

            if selected_ollama_choice == "Custom...":
                custom_o_model = st.text_input("Nama Model Ollama", value=current_ollama_model if current_ollama_model not in AVAILABLE_OLLAMA_MODELS else DEFAULT_OLLAMA_MODEL, key="_custom_ollama_input")
                st.session_state.ollama_model = custom_o_model.strip() or DEFAULT_OLLAMA_MODEL
            else:
                st.session_state.ollama_model = selected_ollama_choice

            if st.button("Tes & Scan Model Ollama", icon=":material/refresh:", use_container_width=True):
                with st.spinner("Menghubungi server Ollama lokal..."):
                    success, msg, detected = test_ollama_connection(st.session_state.ollama_host, st.session_state.ollama_model)
                    if detected:
                        st.session_state["_ollama_discovered_models"] = detected
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    return {"page": st.session_state.page, "edit_mode": bool(st.session_state.get("edit_mode", False)), "date_start": date_start, "date_end": date_end}



