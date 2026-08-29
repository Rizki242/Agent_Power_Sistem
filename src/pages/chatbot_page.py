import io
import os
import pandas as pd
from datetime import datetime

from src.chatbot import MCSAChatbot
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


def render_chatbot_page(st, df_latest_augmented: pd.DataFrame, df_all: pd.DataFrame):
    st.header("💬 MCSA Virtual Assistant")

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
            st.info(f"🟢 **Model LLM Aktif**: {provider_name} (`{active_model}`)", icon="✨")
        elif ai_active and not is_ready:
            st.warning(f"⚠️ **Model LLM ({provider_name})**: API Key belum diisi. Lengkapi di sidebar.", icon="🔑")
        else:
            st.caption("ℹ️ *Mode Rule-Based (Lokal Offline). Aktifkan Model LLM melalui sidebar.*")

    with col_btn_save:
        messages = st.session_state.get("messages", [])
        if messages:
            chat_md = "# Riwayat Percakapan MCSA Virtual Assistant\n"
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
                "💾 Simpan Chat (.md)",
                data=chat_md.encode("utf-8"),
                file_name=f"mcsa_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    with col_btn_clear:
        if st.button("🗑️ Hapus Chat", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["_chat_file_context"] = ""
            st.session_state["_chat_attached_filename"] = ""
            st.rerun()

    # File attachment expander
    with st.expander("📎 Lampirkan Dokumen / Data ke Chat (PDF, Markdown, Excel, CSV, DOCX, TXT)", expanded=False):
        chat_file = st.file_uploader(
            "Upload file untuk dianalisa langsung dalam chat",
            type=["pdf", "md", "docx", "csv", "xlsx", "xls", "txt", "json"],
            key="_chat_file_uploader",
        )
        if chat_file is not None:
            extracted_text = _extract_file_context(chat_file)
            st.session_state["_chat_file_context"] = extracted_text
            st.session_state["_chat_attached_filename"] = chat_file.name
            st.success(f"📄 File '{chat_file.name}' berhasil dilampirkan ke sesi chat ({round(len(chat_file.getvalue())/1024, 1)} KB).")

            c_perm1, c_perm2 = st.columns([3, 2])
            with c_perm1:
                st.caption("Ingin menyimpan dokumen ini permanen ke Knowledge Base / Memori AI?")
            with c_perm2:
                if st.button("💾 Simpan ke Knowledge Base", key="_save_chat_file_to_kb"):
                    ok, msg, _ = process_and_save_knowledge_file(
                        file_name=chat_file.name,
                        file_bytes=chat_file.getvalue(),
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    # Attached file banner
    attached_fn = st.session_state.get("_chat_attached_filename")
    if attached_fn:
        st.caption(f"📎 *File aktif dalam percakapan: **{attached_fn}*** (Konteks otomatis disertakan dalam prompt LLM)")

    # Render conversation history
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("citations"):
                with st.expander("📚 Referensi Knowledge Base Terkait", expanded=False):
                    for cit in message["citations"]:
                        st.markdown(f"**{cit['title']} — {cit['heading']}** ({cit['source']})")
                        st.caption(cit.get("preview", ""))

    # Chat Input & Response Loop
    if prompt := st.chat_input("Tanya kondisi motor, SOP, atau analisis file (contoh: 'Status BC 10.1', 'Jelaskan isi file lampiran')..."):
        st.chat_message("user").markdown(prompt)
        st.session_state["messages"].append({"role": "user", "content": prompt})

        # 1. Rule-based analysis & intent processing
        rule_response = bot.process_query(prompt)

        # 2. History dataframe if equipment matched
        matched_eq = bot.last_matched_equipment
        df_history = df_all[df_all["Equipment"] == matched_eq] if matched_eq and not df_all.empty else None

        # 3. LLM enhancement with Multi-provider + RAG + Attached File Context
        extra_context = st.session_state.get("_chat_file_context", "")

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
        )

        with st.chat_message("assistant"):
            st.markdown(response)

            if llm.last_citations:
                with st.expander("📚 Referensi Knowledge Base Terkait", expanded=False):
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
