"""Settings page: consolidates configuration that used to live scattered in the
sidebar (LLM provider settings) plus a read view of the pple/ engineering module
registry. Categories without a real backend yet (Database, Security, Notifications,
etc. - see docs/desain.png) render as "coming soon" placeholders instead of being
half-built.
"""

from src.components.theme import render_page_header

PLACEHOLDER_CATEGORIES = [
    ("Appearance", ":material/palette:", "Tema, kepadatan tampilan, dan preferensi UI."),
    ("Local AI", ":material/dns:", "Konfigurasi Ollama/LM Studio lanjutan (host, model default, embedding)."),
    ("API Keys", ":material/vpn_key:", "Manajemen terpusat API key untuk semua provider."),
    ("Agent", ":material/smart_toy:", "Identitas agent, level otonomi, dan kebijakan keamanan."),
    ("Database", ":material/database:", "Konfigurasi koneksi database (saat ini masih file-based)."),
    ("Knowledge & RAG", ":material/menu_book:", "Pengaturan index RAG, vector store, dan sumber knowledge."),
    ("Notifications", ":material/notifications:", "Notifikasi in-app, email, Telegram, WhatsApp."),
    ("Reports", ":material/description:", "Logo, nama perusahaan, template laporan default."),
    ("Security", ":material/shield:", "Autentikasi, role, session timeout, audit log."),
    ("Integrations", ":material/hub:", "Integrasi EAM/CMMS, SCADA/Historian, REST API eksternal."),
    ("Backup", ":material/cloud_upload:", "Jadwal backup otomatis dan retensi."),
    ("Developer", ":material/code:", "Developer mode, API docs, logging level, debug flags."),
    ("System", ":material/monitor_heart:", "Status kesehatan sistem, reload modules, rebuild index."),
    ("Administration", ":material/admin_panel_settings:", "Konfigurasi Plant/Unit/Equipment dan Users & Roles."),
]


def _render_general(st):
    from src.data_loader import get_data_path

    st.subheader("Informasi aplikasi")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Data root", get_data_path())
        df = st.session_state.get("_mcsa_df")
        st.metric("Total baris data", len(df) if df is not None else 0)
    with col2:
        min_date = st.session_state.get("_mcsa_min_date")
        max_date = st.session_state.get("_mcsa_max_date")
        st.metric("Rentang data", f"{min_date} s/d {max_date}" if min_date and max_date else "-")
        st.metric("Mode Edit", "Aktif" if st.session_state.get("edit_mode") else "Nonaktif")


def _render_ai_llm(st):
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

    from src import ai_settings

    st.subheader("Pengaturan Model LLM")
    st.caption("Mengatur provider AI yang dipakai oleh Chatbot dan Analisis Mendalam di Dashboard.")

    # Seed session_state from disk on first load of this session, so the
    # provider/model choice survives a fresh browser session instead of
    # always resetting to "gemini" / the hardcoded defaults. Never seeds an
    # API key - those never get written to this file (see src/ai_settings.py).
    persisted = ai_settings.load()
    if "ai_enabled" not in st.session_state:
        st.session_state.ai_enabled = persisted.get("ai_enabled", is_any_ai_configured(st))
    if "ai_provider" not in st.session_state:
        st.session_state.ai_provider = persisted.get("ai_provider", "gemini")
    for field, default in {
        "gemini_model": DEFAULT_GEMINI_MODEL,
        "groq_model": DEFAULT_GROQ_MODEL,
        "opencode_model": DEFAULT_OPENCODE_MODEL,
        "opencode_base_url": DEFAULT_OPENCODE_BASE_URL,
        "ollama_model": DEFAULT_OLLAMA_MODEL,
        "ollama_host": DEFAULT_OLLAMA_HOST,
    }.items():
        if field not in st.session_state:
            st.session_state[field] = persisted.get(field, default)

    st.checkbox(
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
    provider_map = {"gemini": 0, "groq": 1, "opencode": 2, "ollama": 3}
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
            st.caption(f":material/key: Key Terdeteksi ({resolved[:6]}...{resolved[-4:]})")
        else:
            st.caption(":material/radio_button_unchecked: Belum ada API Key (menggunakan Rule-Based)")

        if st.button("Tes Koneksi Gemini", icon=":material/wifi_tethering:"):
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
            st.caption(f":material/key: Key Terdeteksi ({resolved[:6]}...{resolved[-4:]})")
        else:
            st.caption(":material/radio_button_unchecked: Belum ada Groq API Key")

        if st.button("Tes Koneksi Groq", icon=":material/speed:"):
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

        if st.button("Tes Koneksi Endpoint", icon=":material/hub:"):
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

        if st.button("Tes & Scan Model Ollama", icon=":material/refresh:"):
            with st.spinner("Menghubungi server Ollama lokal..."):
                success, msg, detected = test_ollama_connection(st.session_state.ollama_host, st.session_state.ollama_model)
                if detected:
                    st.session_state["_ollama_discovered_models"] = detected
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    # Persist the preference fields (never API keys - ai_settings.save() only
    # accepts its own allowlist, see src/ai_settings.py) so this survives past
    # the current browser session.
    _persisted_fields = (
        "ai_enabled", "ai_provider",
        "gemini_model", "groq_model",
        "opencode_model", "opencode_base_url",
        "ollama_model", "ollama_host",
    )
    ai_settings.save({field: st.session_state[field] for field in _persisted_fields if field in st.session_state})


def _render_engineering_modules(st):
    from pple.engineering.equipment_modules import EquipmentModuleStore
    from pple.engineering.loader import load_modules_from_manifests

    st.subheader("Engineering modules")
    st.caption("Module engineering yang termuat dari pple/engineering/manifests, dan status enable/disable per-equipment.")

    registry, load_results = load_modules_from_manifests()

    st.markdown("**Status load manifest**")
    if load_results:
        st.dataframe(
            [r.to_dict() for r in load_results],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Belum ada manifest module yang termuat.")

    st.markdown("**Module aktif**")
    modules = registry.list()
    if not modules:
        st.info("Tidak ada engineering module terdaftar.")
        return
    st.dataframe(
        [
            {"ID": m.id, "Nama": m.name, "Versi": m.version, "Equipment berlaku": ", ".join(m.applicable_equipment)}
            for m in modules
        ],
        hide_index=True,
        width="stretch",
    )

    st.markdown("**Override per-equipment**")
    equipment_id = st.text_input(
        "ID Equipment",
        placeholder="Contoh: PBFP-1A",
        help="Masukkan ID equipment untuk melihat/mengubah module mana yang aktif untuknya.",
        key="_settings_eq_module_id",
    )
    if equipment_id:
        store = EquipmentModuleStore()
        for module_id, enabled in store.list_for_equipment(equipment_id, registry):
            module = registry.get(module_id)
            new_enabled = st.checkbox(f"{module.name} ({module_id})", value=enabled, key=f"_settings_eq_mod_{equipment_id}_{module_id}")
            if new_enabled != enabled:
                from pple.core import audit
                store.set_enabled(
                    equipment_id, module_id, new_enabled, source=audit.SOURCE_STREAMLIT
                )
                st.rerun()


def _render_placeholder(st, title, description):
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
        st.info("Kategori ini akan hadir di rilis mendatang.")


def render_settings_page(st):
    render_page_header(st, "Settings", "Konfigurasi aplikasi, provider AI, dan engineering module.")

    real_categories = ["General", "AI & LLM", "Engineering Modules"]
    placeholder_labels = [label for label, _icon, _desc in PLACEHOLDER_CATEGORIES]

    col_tabs, col_more = st.columns([3, 2])
    with col_tabs:
        quick_pick = st.segmented_control(
            "Kategori",
            real_categories,
            default=real_categories[0],
            label_visibility="collapsed",
            key="_settings_category_quick",
        )
    with col_more:
        more_pick = st.selectbox(
            "Kategori lain",
            ["-"] + placeholder_labels,
            label_visibility="collapsed",
            key="_settings_category_more",
        )

    category = more_pick if more_pick and more_pick != "-" else (quick_pick or real_categories[0])

    st.divider()

    if category == "General":
        _render_general(st)
    elif category == "AI & LLM":
        _render_ai_llm(st)
    elif category == "Engineering Modules":
        _render_engineering_modules(st)
    else:
        for label, _icon, description in PLACEHOLDER_CATEGORIES:
            if label == category:
                _render_placeholder(st, label, description)
                break
