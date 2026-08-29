import json
import os
from typing import Optional

import pandas as pd

from src.components.theme import render_page_header
from src.knowledge_processor import delete_knowledge_file, process_and_save_knowledge_file


def _to_str(x) -> str:
    if x is None:
        return ""
    return str(x)


def _normalize_v2(doc: dict) -> dict:
    sections = []
    raw_sections = doc.get("sections") if isinstance(doc, dict) else None
    if isinstance(raw_sections, list):
        for s in raw_sections:
            if not isinstance(s, dict):
                continue
            sections.append({
                "id": s.get("id"),
                "heading": _to_str(s.get("heading") or s.get("title") or "").strip(),
                "content": _to_str(s.get("content") or "").strip(),
            })
    return {
        "id": doc.get("id"),
        "title": _to_str(doc.get("title") or doc.get("name") or "").strip(),
        "tags": [_to_str(t).strip() for t in (doc.get("tags") or []) if _to_str(t).strip()],
        "level": _to_str(doc.get("level") or "").strip(),
        "source": _to_str(doc.get("source") or "").strip(),
        "language": _to_str(doc.get("language") or "").strip(),
        "sections": [s for s in sections if s.get("heading") or s.get("content")],
    }


def _normalize_v1(pages_list: list, fallback_title: str) -> dict:
    sections = []
    for item in pages_list:
        if not isinstance(item, dict):
            continue
        pg = item.get("page")
        heading = f"Halaman {pg}" if pg is not None else "Halaman"
        sections.append({
            "id": pg,
            "heading": heading,
            "content": _to_str(item.get("content") or "").strip(),
        })
    return {
        "id": None,
        "title": fallback_title,
        "tags": [],
        "level": "",
        "source": "",
        "language": "",
        "sections": [s for s in sections if s.get("content")],
    }


def _load_json_data(file_path: str, mtime_key: Optional[float]):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_materi_page(st):
    render_page_header(st, "Knowledge", "Knowledge base & materi training.")

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    materi_dir = os.path.join(base_dir, "Materi")
    os.makedirs(materi_dir, exist_ok=True)

    tab_read, tab_upload, tab_rag = st.tabs(["📖 Baca & Cari Materi", "📤 Upload & Kelola Knowledge Base", "🧠 RAG / Vector Search"])

    with tab_read:
        materi_files = [f for f in os.listdir(materi_dir) if f.lower().endswith(".json")]
        materi_files = sorted(materi_files, key=lambda s: s.lower())
        if not materi_files:
            st.info("Belum ada file materi (.json) di folder Materi. Gunakan tab **Upload** untuk menambahkan dokumen.")
        else:
            left, right = st.columns([2, 3])
            with left:
                prefer_contains = (st.session_state.get("materi_prefer_name_contains") or "").strip().lower()
                if prefer_contains:
                    st.session_state["materi_prefer_name_contains"] = ""
                    preferred = [i for i, f in enumerate(materi_files) if prefer_contains in f.lower()]
                    if preferred:
                        st.session_state["materi_selected_file"] = materi_files[preferred[0]]

                selected_file = st.selectbox(
                    "Pilih Materi",
                    materi_files,
                    key="materi_selected_file",
                )
                query = st.text_input("Cari (kata kunci)", value=st.session_state.get("materi_query", ""), key="_materi_q_input")
                st.session_state["materi_query"] = query
                show_mode = st.radio("Tampilan", ["Per Bagian", "Hasil Pencarian"], horizontal=True, key="_materi_view_mode")

            path = os.path.join(materi_dir, selected_file)
            mtime = None
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = None

            cached_load_json = st.cache_data(show_spinner=False)(_load_json_data)

            try:
                data = cached_load_json(path, mtime)
            except Exception as e:
                st.error(f"Gagal membaca materi: {e}")
                data = None

            if data:
                docs = []
                if isinstance(data, dict) and isinstance(data.get("sections"), list):
                    docs = [_normalize_v2(data)]
                elif isinstance(data, list):
                    if any(isinstance(x, dict) and isinstance(x.get("sections"), list) for x in data):
                        docs = [_normalize_v2(x) for x in data if isinstance(x, dict) and isinstance(x.get("sections"), list)]
                    else:
                        docs = [_normalize_v1(data, os.path.splitext(selected_file)[0])]
                elif isinstance(data, dict) and isinstance(data.get("pages"), list):
                    docs = [_normalize_v1(data.get("pages") or [], os.path.splitext(selected_file)[0])]

                docs = [d for d in docs if d.get("sections")]
                if not docs:
                    st.warning("Format materi tidak dikenali atau kosong.")
                else:
                    available_languages = sorted({
                        (d.get("language") or "").strip().lower()
                        for d in docs
                        if (d.get("language") or "").strip()
                    })
                    lang_options = ["All"] + [l.upper() for l in available_languages]
                    with left:
                        sel_lang = st.selectbox("Language", lang_options, index=0, key="_materi_lang_sel")

                    filtered_docs = docs
                    if sel_lang != "All":
                        want = sel_lang.strip().lower()
                        filtered_docs = [d for d in filtered_docs if (d.get("language") or "").strip().lower() == want]
                        if not filtered_docs:
                            filtered_docs = docs

                    if len(filtered_docs) > 1:
                        titles = []
                        for d in filtered_docs:
                            t = d.get("title") or d.get("id") or "Materi"
                            titles.append(t)
                        with left:
                            selected_doc_title = st.selectbox("Pilih Topik", titles, key="_materi_topic_sel")
                        selected_doc = next(
                            (d for d, t in zip(filtered_docs, titles) if t == selected_doc_title),
                            filtered_docs[0],
                        )
                    else:
                        selected_doc = filtered_docs[0]

                    with right:
                        st.caption(f"Sumber: {path}")

                        title = selected_doc.get("title") or os.path.splitext(selected_file)[0]
                        st.subheader(title)

                        meta = []
                        tags = selected_doc.get("tags") or []
                        if tags:
                            meta.append("Tags: " + ", ".join(tags))
                        if selected_doc.get("level"):
                            meta.append("Level: " + selected_doc.get("level"))
                        if selected_doc.get("source"):
                            meta.append("Source: " + selected_doc.get("source"))
                        if selected_doc.get("language"):
                            meta.append("Language: " + selected_doc.get("language"))
                        if meta:
                            st.caption(" | ".join(meta))

                        sections = selected_doc.get("sections") or []
                        query_text = query.strip().lower()

                        def _section_text(sec: dict) -> str:
                            return (sec.get("heading", "") + "\n" + sec.get("content", "") + "\n" + " ".join(tags)).lower()

                        if show_mode == "Hasil Pencarian" and query_text:
                            matches = [s for s in sections if query_text in _section_text(s)]
                            st.write(f"Ditemukan {len(matches)} bagian yang cocok.")
                            for s in matches[:50]:
                                heading = s.get("heading") or "Bagian"
                                with st.expander(heading, expanded=False):
                                    st.text(s.get("content", ""))
                        else:
                            st.write(f"Total bagian: {len(sections)}")
                            for s in sections[:200]:
                                heading = s.get("heading") or "Bagian"
                                with st.expander(heading, expanded=False):
                                    st.text(s.get("content", ""))

    with tab_upload:
        st.subheader("📤 Upload Dokumen ke Knowledge Base (Memori AI)")
        st.info(
            "Unggah dokumen SOP, manual alat ukur, standar vibrasi/MCSA, atau panduan teknis. "
            "Aplikasi akan mengekstrak isi dokumen menjadi unit memori dan indeks pencarian "
            "yang langsung dapat diakses oleh **Chatbot** dan **Analisis AI**.",
            icon="💡",
        )

        edit_mode = bool(st.session_state.get("edit_mode", False))
        if not edit_mode:
            st.warning("⚠️ **Mode Edit Nonaktif**: Aktifkan toggle 'Mode Edit' di sidebar untuk mengunggah atau mengelola dokumen.")

        c_up1, c_up2 = st.columns([3, 2])
        with c_up1:
            uploaded_file = st.file_uploader(
                "Pilih File Dokumen (PDF, Markdown, DOCX, JSON, TXT)",
                type=["pdf", "md", "docx", "json", "txt"],
                key="knowledge_file_uploader",
                disabled=not edit_mode,
            )

        with c_up2:
            custom_title = st.text_input("Judul Dokumen (Opsional)", placeholder="misal: SOP Vibrasi & Balancing", disabled=not edit_mode)
            custom_tags_str = st.text_input("Tags / Kategori (Pisahkan dengan koma)", placeholder="misal: SOP, Vibrasi, ISO 10816", disabled=not edit_mode)
            custom_source = st.text_input("Sumber / Referensi (Opsional)", placeholder="misal: Tim Predictive Maintenance", disabled=not edit_mode)

        if uploaded_file is not None and edit_mode:
            if st.button("🚀 Proses & Simpan ke Memori AI", type="primary", use_container_width=True):
                with st.spinner(f"Memproses dan mengekstrak '{uploaded_file.name}'..."):
                    tags_list = [t.strip() for t in custom_tags_str.split(",") if t.strip()] if custom_tags_str else None
                    success, msg, doc_data = process_and_save_knowledge_file(
                        file_name=uploaded_file.name,
                        file_bytes=uploaded_file.getvalue(),
                        custom_title=custom_title,
                        custom_tags=tags_list,
                        source=custom_source,
                    )
                    if success:
                        st.success(msg)
                        st.session_state["_last_uploaded_doc"] = doc_data
                        st.rerun()
                    else:
                        st.error(msg)

        # List existing knowledge files
        st.divider()
        st.subheader("📑 Daftar Dokumen Knowledge Base Tersedia")

        all_json_files = [f for f in os.listdir(materi_dir) if f.lower().endswith(".json")]
        if all_json_files:
            file_records = []
            for fn in sorted(all_json_files):
                f_path = os.path.join(materi_dir, fn)
                size_kb = round(os.path.getsize(f_path) / 1024, 1)
                mod_time = pd.to_datetime(os.path.getmtime(f_path), unit="s").strftime("%Y-%m-%d %H:%M")
                file_records.append({
                    "Nama File": fn,
                    "Ukuran (KB)": size_kb,
                    "Terakhir Diperbarui": mod_time,
                })

            st.dataframe(pd.DataFrame(file_records), use_container_width=True, hide_index=True)

            # Option to delete custom file
            with st.expander("🗑️ Hapus Dokumen Knowledge Base", expanded=False):
                del_file = st.selectbox("Pilih file yang ingin dihapus:", all_json_files, key="del_kb_file")
                if st.button(f"Hapus '{del_file}'", disabled=not edit_mode, type="secondary"):
                    ok, dmsg = delete_knowledge_file(del_file)
                    if ok:
                        st.success(dmsg)
                        st.rerun()
                    else:
                        st.error(dmsg)
        else:
            st.info("Belum ada dokumen knowledge base yang terdaftar.")

    with tab_rag:
        st.subheader("🧠 RAG / Vector Search (LangChain + FAISS)")
        st.info(
            "RAG (Retrieval Augmented Generation) menggunakan embeddings dan vector search untuk "
            "pencarian semantik yang lebih akurat dari materi VIBRASI dan TRIBOLOGY. "
            "Sistem akan mencari dokumen berdasarkan makna, bukan hanya kata kunci.",
            icon="💡",
        )

        rag_available = False
        try:
            from src.rag_engine import get_rag_engine, is_rag_available, RAG_INDEX_DIR
            rag_available = is_rag_available()
        except ImportError:
            pass

        if not rag_available:
            st.warning(
                "⚠️ **Package RAG belum terinstall.**\n\n"
                "Jalankan perintah berikut untuk menginstall:\n"
                "```\n"
                "pip install langchain langchain-community faiss-cpu sentence-transformers\n"
                "```"
            )
        else:
            engine = get_rag_engine()
            index_exists = os.path.exists(os.path.join(engine.index_dir, "index.faiss"))

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("### Status Index")
                if index_exists:
                    st.success("✅ Index RAG sudah tersedia.")
                    try:
                        index_size = os.path.getsize(os.path.join(engine.index_dir, "index.faiss"))
                        st.caption(f"Ukuran index: {index_size / 1024:.1f} KB")
                    except Exception:
                        pass
                else:
                    st.warning("⚠️ Index RAG belum dibuat.")

            with col2:
                if st.button("🔄 Build / Rebuild Index", type="primary", use_container_width=True):
                    with st.spinner("Membuat index RAG dari dokumen VIBRASI & TRIBOLOGY..."):
                        success, message = engine.build_index(force=True)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

            st.divider()

            st.markdown("### 🔍 Test Pencarian Semantik")
            test_query = st.text_input(
                "Masukkan pertanyaan atau kata kunci:",
                placeholder="misal: bagaimana cara analisis vibrasi bearing?",
                key="rag_test_query",
            )
            top_k = st.slider("Jumlah hasil", min_value=1, max_value=10, value=3, key="rag_top_k")

            if test_query and index_exists:
                if not engine.is_ready:
                    engine.load_index()

                if engine.is_ready:
                    results = engine.search(test_query, top_k=top_k)
                    if results:
                        st.write(f"Ditemukan **{len(results)}** hasil:")
                        for i, r in enumerate(results, 1):
                            with st.expander(f"{i}. {r['title']} — {r.get('heading', '')}", expanded=False):
                                st.caption(f"Source: {r['source']}")
                                st.text(r['content'][:1000] + ("..." if len(r['content']) > 1000 else ""))
                    else:
                        st.info("Tidak ada hasil ditemukan.")
                else:
                    st.warning("Index RAG belum dimuat. Klik 'Build / Rebuild Index' terlebih dahulu.")
            elif test_query and not index_exists:
                st.warning("Index RAG belum dibuat. Klik 'Build / Rebuild Index' terlebih dahulu.")

            st.divider()

            with st.expander("ℹ️ Informasi Teknis", expanded=False):
                st.markdown("""
**Cara Kerja RAG:**
1. **Document Loading**: Memuat semua file dari `Materi/VIBRASI/` dan `Materi/TRIBOLOGY/` (Markdown, PDF, JSON)
2. **Chunking**: Membagi dokumen menjadi potongan-potongan kecil (~1000 karakter)
3. **Embedding**: Mengubah setiap chunk menjadi vector menggunakan model `paraphrase-multilingual-MiniLM-L12-v2`
4. **Vector Store**: Menyimpan vector di FAISS index untuk pencarian cepat
5. **Semantic Search**: Mencari chunk yang paling mirip dengan query berdasarkan cosine similarity

**Keunggulan vs Keyword Search:**
- Memahami sinonim dan makna (misal: "getaran" = "vibrasi")
- Bisa menemukan informasi terkait meski kata kunci berbeda
- Lebih akurat untuk pertanyaan kompleks

**Lokasi Index:** `data/rag_index/`
                """)
