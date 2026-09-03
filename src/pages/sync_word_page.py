import os

import pandas as pd

from src.analytics import summarize_word_report_quality
from src.components.theme import render_page_header
from src.data_loader import load_equipment_master
from src.report_batches import commit_batch, create_batch, list_recent_batches, preview_batch

REQUIRED_PARAMETERS = ["Load", "Current 1", "Current 2", "Current 3", "Dev Current", "Voltage 1", "Voltage 2", "Voltage 3", "Dev Voltage", "power factor", "THD Current %", "THD Voltage %", "Real Power", "Rotorbar Health", "Upper Sideband", "Lower Sideband", "Bearing", "Kondisi"]


def _preview_rows(preview_df, manifest):
    counts = {}
    if isinstance(preview_df, pd.DataFrame) and not preview_df.empty:
        counts = preview_df.groupby("Equipment")["Parameter"].nunique().to_dict()
    return [{"File": item.get("original_name"), "Equipment": item.get("equipment") or "-", "Tanggal": item.get("report_date") or "-", "Unit": item.get("metadata", {}).get("unit", "-"), "Voltage": item.get("metadata", {}).get("voltage", "-"), "Parameter": counts.get(item.get("equipment"), 0), "Status": item.get("parse_status", "pending"), "Catatan": item.get("error", "")} for item in manifest.get("files", [])]


def _quarantine_rows(manifest):
    rows = []
    for item in manifest.get("files", []):
        if item.get("parse_status") != "quarantined":
            continue
        rows.append({
            "File": item.get("original_name", "-"),
            "Alasan karantina": item.get("error") or "Tidak ada parameter MCSA yang dapat diekstrak.",
            "Tindakan": "Periksa nama equipment di master dan struktur tabel laporan, lalu unggah ulang.",
        })
    return rows


def _render_sync_flow(st):
    st.caption("Alur kerja laporan")
    steps = [
        ("1. Pilih laporan", "Unggah file .docx atau .docm yang akan diperbarui."),
        ("2. Periksa preview", "Pastikan equipment, tanggal, parameter, dan karantina sudah benar."),
        ("3. Konfirmasi", "Simpan hanya laporan valid ke data dashboard."),
        ("4. Tinjau dashboard", "Dashboard otomatis difokuskan pada equipment dan tanggal batch."),
    ]
    columns = st.columns(len(steps))
    for column, (title, description) in zip(columns, steps):
        column.markdown(f"**{title}**\n\n{description}")


def render_sync_word_page(st, df, edit_mode, get_data_path, get_folder_metadata, parse_all_reports_with_report, save_mcsa_data, load_mcsa_data, dashboard_page=None):
    render_page_header(st, "Sync Laporan Word", "Sinkronisasi laporan Word.")
    st.caption("Unggah, periksa, lalu konfirmasi laporan sebelum data masuk ke dashboard.")
    _render_sync_flow(st)
    if not edit_mode:
        st.warning("Mode Edit belum aktif. Aktifkan Mode Edit untuk mulai mengunggah dan menyinkronkan laporan.")

    laporan_root = get_data_path("Laporan")
    os.makedirs(laporan_root, exist_ok=True)
    file_path = get_data_path("Report MCSA.xls")
    st.subheader("Upload laporan baru")
    uploaded_files = st.file_uploader("Pilih file laporan", type=["docx", "docm"], accept_multiple_files=True, help="Setiap proses upload disimpan sebagai satu batch terpisah.")
    if not uploaded_files and "word_batch_manifest" not in st.session_state:
        st.info("Belum ada laporan dipilih. Tambahkan satu atau beberapa laporan Word, lalu pilih **Siapkan preview**.")
    if st.button("Siapkan preview", type="primary", disabled=not edit_mode or not uploaded_files, width="stretch"):
        with st.spinner("Menyimpan batch dan memeriksa isi laporan..."):
            batch_path, _ = create_batch(laporan_root, uploaded_files)
            preview_df, manifest = preview_batch(batch_path, master_df=load_equipment_master(), folder_metadata=get_folder_metadata(laporan_root))
        st.session_state["word_batch_path"] = str(batch_path)
        st.session_state["word_batch_preview"] = preview_df
        st.session_state["word_batch_manifest"] = manifest

    batch_path = st.session_state.get("word_batch_path")
    preview_df = st.session_state.get("word_batch_preview")
    manifest = st.session_state.get("word_batch_manifest")
    if batch_path and isinstance(manifest, dict):
        preview_rows = _preview_rows(preview_df, manifest)
        valid_count = sum(row["Status"] == "valid" for row in preview_rows)
        failed_count = len(preview_rows) - valid_count
        c1, c2, c3 = st.columns(3)
        c1.metric("File batch", len(preview_rows))
        c2.metric("Siap disimpan", valid_count)
        c3.metric("Karantina", failed_count)
        st.dataframe(pd.DataFrame(preview_rows), width="stretch", hide_index=True)
        if failed_count:
            st.warning("File karantina tetap tersimpan di arsip batch, tetapi tidak masuk dashboard.")
            st.subheader("Alasan karantina")
            st.dataframe(pd.DataFrame(_quarantine_rows(manifest)), width="stretch", hide_index=True)
        elif valid_count:
            st.success("Preview siap. Tinjau data di atas, lalu konfirmasi untuk memperbarui dashboard.")
        if valid_count == 0:
            st.error("Tidak ada laporan yang siap dikonfirmasi. Perbaiki alasan karantina, lalu unggah ulang file tersebut.")
        if st.button("Konfirmasi dan perbarui dashboard", disabled=not edit_mode or valid_count == 0, width="stretch"):
            with st.spinner("Menyimpan data batch..."):
                _, committed = commit_batch(batch_path, preview_df, df, save_mcsa_data, file_path)
            valid_items = [item for item in committed["files"] if item.get("parse_status") == "valid"]
            dates = [pd.to_datetime(item.get("report_date"), errors="coerce") for item in valid_items]
            dates = [item.date() for item in dates if not pd.isna(item)]
            if dates:
                st.session_state["filter_focus_range"] = (min(dates), max(dates))
            st.session_state["filter_focus_equipment"] = sorted({item.get("equipment") for item in valid_items if item.get("equipment")})
            for key in ["word_batch_path", "word_batch_preview", "word_batch_manifest", "_mcsa_data_key"]:
                st.session_state.pop(key, None)
            if dashboard_page is not None:
                st.switch_page(dashboard_page)
            else:
                st.rerun()

    st.markdown("---")
    st.subheader("Riwayat batch")
    recent = list_recent_batches(laporan_root)
    if recent:
        history = []
        for batch in recent:
            files = batch.get("files", [])
            history.append({"Batch": batch.get("batch_id"), "Waktu upload": batch.get("uploaded_at"), "Status": batch.get("status"), "File": len(files), "Valid": sum(item.get("parse_status") == "valid" for item in files), "Karantina": sum(item.get("parse_status") == "quarantined" for item in files)})
        st.dataframe(pd.DataFrame(history), width="stretch", hide_index=True)
    else:
        st.info("Belum ada riwayat batch. Setelah preview dikonfirmasi, batch akan tampil di sini untuk audit.")

    with st.expander("Pemeliharaan dan scan arsip lama"):
        if st.button("Scan semua file di folder Laporan", disabled=not edit_mode):
            with st.spinner("Memproses laporan Word..."):
                meta = get_folder_metadata(laporan_root)
                df_word, rep = parse_all_reports_with_report(laporan_root, meta)
                summary = summarize_word_report_quality(df_word, rep, REQUIRED_PARAMETERS)
            st.write(f"Total {rep.get('total_files', 0)} file; berhasil {rep.get('parsed_files', 0)}; gagal {rep.get('failed_files', 0)}.")
            if summary["failed_files"]:
                st.dataframe(pd.DataFrame(summary["failed_files"]), width="stretch", hide_index=True)
            if not df_word.empty:
                merged = pd.concat([df, df_word], ignore_index=True)
                merged["Date"] = pd.to_datetime(merged.get("Date", pd.NaT), errors="coerce")
                merged = merged.drop_duplicates(subset=["Equipment", "Parameter", "Date"], keep="last")
                save_mcsa_data(merged, file_path)
                st.success("Scan arsip selesai dan database diperbarui.")
                st.rerun()
            else:
                st.error("Tidak ada data valid dari scan arsip. Buka Quality Check untuk melihat file dan alasan kegagalannya.")
        if st.button("Reload dari Excel (Reset)", disabled=not edit_mode):
            with st.spinner("Membaca ulang data dari Excel dan Word..."):
                df_new = load_mcsa_data(file_path, force_excel=True)
                save_mcsa_data(df_new, file_path)
            st.success("Database berhasil dimuat ulang dari sumber.")
            st.rerun()
