import io
import os
import pandas as pd
from datetime import datetime

from src.chatbot import MCSAChatbot
from src.components.theme import render_page_header
from src.knowledge_processor import process_and_save_knowledge_file
from src.llm_assistant import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENCODE_BASE_URL,
    DEFAULT_OPENCODE_MODEL,
    MCSALLMAssistant,
    resolve_provider_key,
)


def _extract_file_context(uploaded_file) -> str:
    """Extract text from uploaded attachment in chat."""
    if not uploaded_file:
        return ""

    fn = uploaded_file.name
    ext = os.path.splitext(fn)[1].lower()
    raw_bytes = uploaded_file.getvalue()

    try:
        if ext in {".csv"}:
            df = pd.read_csv(io.BytesIO(raw_bytes))
            return f"Data Tabel CSV '{fn}' ({len(df)} baris):\n" + df.head(50).to_string()
        elif ext in {".xlsx", ".xls"}:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            return f"Data Tabel Excel '{fn}' ({len(df)} baris):\n" + df.head(50).to_string()
        elif ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_bytes))
                texts = []
                for i, p in enumerate(reader.pages[:20]):
                    pt = p.extract_text()
                    if pt:
                        texts.append(f"[Halaman {i+1}]\n{pt.strip()}")
                return f"Dokumen PDF '{fn}' ({len(reader.pages)} halaman):\n" + "\n\n".join(texts)
            except Exception as e:
                return f"Gagal membaca PDF: {e}"
        elif ext in {".docx"}:
            try:
                import docx
                doc = docx.Document(io.BytesIO(raw_bytes))
                paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                return f"Dokumen Word '{fn}':\n" + "\n".join(paras[:100])
            except Exception as e:
                return f"Gagal membaca DOCX: {e}"
        else:
            # Markdown / TXT / JSON
            text = raw_bytes.decode("utf-8", errors="ignore")
            return f"Isi Dokumen '{fn}':\n{text[:5000]}"
    except Exception as exc:
        return f"Error membaca file '{fn}': {exc}"


def _basic_file_answer(filename: str, file_context: str) -> str:
    """Rule-based fallback description of an attached file when the LLM is off/unavailable."""
    preview = file_context.strip()
    if len(preview) > 1200:
        preview = preview[:1200].rstrip() + " ..."
    return (
        f"📎 **Ringkasan Dasar File '{filename}'** (Mode Rule-Based/Offline):\n\n"
        f"{preview}\n\n"
        "_Aktifkan Model LLM di sidebar untuk analisis file yang lebih mendalam._"
    )



MAX_CHAT_CONTEXT_TURNS = 6
MAX_CHAT_CONTEXT_CHARS = 3000


def _build_conversation_context(messages: list) -> str:
    """Rangkum beberapa giliran terakhir percakapan Streamlit menjadi teks konteks."""
    if not messages:
        return ""

    lines = []
    for msg in messages[-(MAX_CHAT_CONTEXT_TURNS * 2):]:
        text = str(msg.get("content") or "").strip()
        if not text:
            continue
        speaker = "User" if msg.get("role") == "user" else "Agent"
        if len(text) > 600:
            text = text[:600] + " ..."
        lines.append(f"{speaker}: {text}")

    context = "\n".join(lines)
    if len(context) > MAX_CHAT_CONTEXT_CHARS:
        context = context[-MAX_CHAT_CONTEXT_CHARS:]
    return context


def render_chatbot_page(st, df_latest_augmented: pd.DataFrame, df_all: pd.DataFrame):
    render_page_header(
        st,
        "Chatbot CBM AI",
        "Virtual Assistant Terpadu CBM & Keandalan Aset (MCSA, Vibrasi, Suhu, Oli, DGA).",
        badge="Multi-Domain Assistant",
    )

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    bot = MCSAChatbot(df_latest_augmented, df_all=df_all)

    # Provider & Settings resolution
    ai_active = bool(st.session_state.get("ai_enabled", False))
    provider = st.session_state.get("ai_provider", "gemini")

    gemini_key = resolve_provider_key("gemini", st.session_state.get("gemini_api_key"), st)
    gemini_model = st.session_state.get("gemini_model", DEFAULT_GEMINI_MODEL)

    groq_key = resolve_provider_key("groq", st.session_state.get("groq_api_key"), st)
    groq_model = st.session_state.get("groq_model", DEFAULT_GROQ_MODEL)

    opencode_key = resolve_provider_key("opencode", st.session_state.get("opencode_api_key"), st)
    opencode_url = st.session_state.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL)
    opencode_model = st.session_state.get("opencode_model", DEFAULT_OPENCODE_MODEL)

    ollama_host = st.session_state.get("ollama_host", DEFAULT_OLLAMA_HOST)
    ollama_model = st.session_state.get("ollama_model", DEFAULT_OLLAMA_MODEL)

    # Active provider metadata
    if provider == "groq":
        active_key = groq_key
        active_model = groq_model
        provider_name = "Groq (Ultra-Fast)"
        is_ready = bool(groq_key)
    elif provider == "opencode":
        active_key = opencode_key
        active_model = opencode_model
        provider_name = "OpenCode / OpenAI"
        is_ready = True
    elif provider == "ollama":
        active_key = None
        active_model = ollama_model
        provider_name = f"Ollama ({ollama_host})"
        is_ready = True
    else:
        active_key = gemini_key
        active_model = gemini_model
        provider_name = "Google Gemini"
        is_ready = bool(gemini_key)

    # Status Banner & Session Toolbar
    col_status, col_btn_save, col_btn_clear = st.columns([5, 2, 2])

    with col_status:
        if ai_active and is_ready:
            st.info(f"**Model LLM Aktif**: {provider_name} (`{active_model}`)", icon=":material/smart_toy:")
        elif ai_active and not is_ready:
            st.warning(f"**Model LLM ({provider_name})**: API Key belum diisi. Lengkapi di sidebar.", icon=":material/key:")
        else:
            st.caption(":material/info: *Mode Rule-Based (Lokal Offline). Aktifkan Model LLM melalui sidebar.*")

    with col_btn_save:
        messages = st.session_state.get("messages", [])
        if messages:
            chat_md = "# Riwayat Percakapan CBM AI Virtual Assistant\n"
            chat_md += f"Waktu Export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"
            for m in messages:
                role_name = "User" if m["role"] == "user" else f"Assistant ({provider_name})"
                chat_md += f"### 👤 {role_name}\n{m['content']}\n\n"
                if m.get("citations"):
                    chat_md += "> **Referensi Knowledge Base:**\n"
                    for cit in m["citations"]:
                        chat_md += f"> - {cit['title']} ({cit['source']})\n"
                    chat_md += "\n"

            st.download_button(
                "Simpan Chat (.md)",
                data=chat_md.encode("utf-8"),
                file_name=f"cbm_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                icon=":material/download:",
                width="stretch",
            )

    with col_btn_clear:
        if st.button("Hapus Chat", icon=":material/delete:", width="stretch"):
            st.session_state["messages"] = []
            st.session_state["_chat_file_context"] = ""
            st.session_state["_chat_attached_filename"] = ""
            st.session_state["_chat_attached_files_raw"] = []
            st.rerun()

    # Quick Action Chips
    st.markdown(
        """
        <div style="margin: 6px 0 4px 0; font-size: 0.82rem; font-weight: 600; color: #64748b;">
            ⚡ Pertanyaan Cepat (Quick Action):
        </div>
        """,
        unsafe_allow_html=True,
    )
    col_c1, col_c2, col_c3, col_c4, col_c5 = st.columns(5)
    chip_clicked = None
    with col_c1:
        if st.button("🚨 Aset Alarm", key="_qa_alarm", help="Tampilkan daftar peralatan yang mengalami alarm/warning", width="stretch"):
            chip_clicked = "List Alarm"
    with col_c2:
        if st.button("🔍 Korelasi CBM", key="_qa_corr", help="Panduan dan analisis korelasi vibrasi & arus", width="stretch"):
            chip_clicked = "Korelasi vibrasi dan arus"
    with col_c3:
        if st.button("🛢️ Analisis Oli", key="_qa_oil", help="Status pelumasan dan partikel keausan oli", width="stretch"):
            chip_clicked = "Status pelumas dan oli"
    with col_c4:
        if st.button("🌡️ Hotspot IRT", key="_qa_therm", help="Pemeriksaan kondisi suhu dan delta-T termal", width="stretch"):
            chip_clicked = "Status suhu dan hotspot"
    with col_c5:
        if st.button("⚡ Trafo DGA", key="_qa_dga", help="Standar IEEE C57.104 & Duval Triangle DGA", width="stretch"):
            chip_clicked = "Standar DGA trafo"

    # Handle pending prompt from Quick Action or previous navigation
    pending_prompt = None
    if chip_clicked:
        pending_prompt = chip_clicked
    elif st.session_state.get("_chatbot_quick_query"):
        pending_prompt = st.session_state.pop("_chatbot_quick_query")

    # Attached file banner + actions
    attached_fn = st.session_state.get("_chat_attached_filename")
    if attached_fn:
        c_info, c_save, c_clear = st.columns([5, 2, 1])
        with c_info:
            st.caption(f":material/attach_file: *File aktif dalam percakapan: **{attached_fn}*** (konteks otomatis disertakan dalam jawaban)")
        with c_save:
            if st.button("Simpan ke Knowledge Base", key="_save_chat_file_to_kb", icon=":material/save:", width="stretch"):
                for fname, fbytes in st.session_state.get("_chat_attached_files_raw", []):
                    ok, msg, _ = process_and_save_knowledge_file(file_name=fname, file_bytes=fbytes)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        with c_clear:
            if st.button("", key="_detach_chat_file", icon=":material/close:", help="Lepas file dari sesi chat", width="stretch"):
                st.session_state["_chat_file_context"] = ""
                st.session_state["_chat_attached_filename"] = ""
                st.session_state["_chat_attached_files_raw"] = []
                st.rerun()

    # Render conversation history
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("citations"):
                with st.expander(":material/menu_book: Referensi Knowledge Base Terkait", expanded=False):
                    for cit in message["citations"]:
                        st.markdown(f"**{cit['title']} — {cit['heading']}** ({cit['source']})")
                        st.caption(cit.get("preview", ""))

    # Chat Input & Response Loop
    chat_val = st.chat_input(
        "Tanya kondisi motor/pompa, getaran, suhu, pelumas, DGA, atau lampirkan file...",
        accept_file="multiple",
        file_type=["pdf", "md", "docx", "csv", "xlsx", "xls", "txt", "json"],
    )

    prompt = None
    uploaded_files = []
    if chat_val:
        prompt = (chat_val.text or "").strip()
        uploaded_files = list(chat_val.files or [])
    elif pending_prompt:
        prompt = str(pending_prompt).strip()
        uploaded_files = []

    if prompt:
        if uploaded_files:
            names = [uf.name for uf in uploaded_files]
            st.session_state["_chat_file_context"] = "\n\n---\n\n".join(
                _extract_file_context(uf) for uf in uploaded_files
            )
            st.session_state["_chat_attached_filename"] = ", ".join(names)
            st.session_state["_chat_attached_files_raw"] = [(uf.name, uf.getvalue()) for uf in uploaded_files]
            if not prompt:
                prompt = f"Analisakan file '{', '.join(names)}' yang baru saya lampirkan."

        with st.chat_message("user"):
            st.markdown(prompt)
            for uf in uploaded_files:
                st.caption(f":material/attach_file: {uf.name}")
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # 1. Rule-based analysis & intent processing
        rule_response = bot.process_query(prompt)

        # 2. History dataframe if equipment matched
        matched_eq = bot.last_matched_equipment
        df_history = df_all[df_all["Equipment"] == matched_eq] if matched_eq and not df_all.empty else None

        # 3. LLM enhancement with Multi-provider + RAG + Attached File Context
        extra_context = st.session_state.get("_chat_file_context", "")

        # Riwayat percakapan (tanpa pesan yang sedang diproses) supaya pertanyaan
        # lanjutan seperti "kenapa begitu?" tetap merujuk topik sebelumnya.
        conversation_context = _build_conversation_context(st.session_state.get("messages", [])[:-1])

        llm = MCSALLMAssistant(
            enabled=ai_active,
            provider=provider,
            api_key=active_key,
            model=active_model,
            base_url=opencode_url if provider == "opencode" else None,
            ollama_host=ollama_host,
        )
        response = llm.enhance_answer(
            question=prompt,
            rule_answer=rule_response,
            df_context=df_latest_augmented,
            df_history=df_history,
            include_knowledge=True,
            extra_file_context=extra_context,
            conversation_context=conversation_context,
        )

        # Rule-based fallback: when the LLM is off/unavailable, don't answer a
        # file question with the generic "no match" message - give at least a
        # basic local preview of the attached file instead.
        if (
            extra_context
            and response.strip() == rule_response.strip()
            and rule_response.startswith("Maaf, saya belum menemukan")
        ):
            response = _basic_file_answer(st.session_state.get("_chat_attached_filename", ""), extra_context)

        with st.chat_message("assistant"):
            st.markdown(response)

            if llm.last_citations:
                with st.expander(":material/menu_book: Referensi Knowledge Base Terkait", expanded=False):
                    for cit in llm.last_citations:
                        st.markdown(f"**{cit['title']} — {cit['heading']}** ({cit['source']})")
                        st.caption(cit.get("preview", ""))

            if ai_active and llm.last_error:
                st.caption(f"ℹ️ Fallback ke Rule-Based ({provider.upper()}): {llm.last_error}")

            if getattr(bot, "last_export", None):
                st.download_button(
                    "Download CSV (Jawaban)",
                    data=str(bot.last_export).encode("utf-8"),
                    file_name="chatbot_export.csv",
                    mime="text/csv",
                )

        st.session_state["messages"].append({
            "role": "assistant",
            "content": response,
            "citations": llm.last_citations if ai_active else None,
        })
