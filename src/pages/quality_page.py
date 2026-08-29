import os
import pandas as pd

from src.analytics import build_word_qc_export, summarize_word_report_quality
from src.components.theme import render_page_header


def render_quality_check_page(st, get_data_path, get_folder_metadata, parse_all_reports_with_report):
    render_page_header(st, "Asset Management", "Quality check laporan Word.")

    laporan_root = get_data_path("Laporan")
    if not os.path.exists(laporan_root):
        st.error(f"Folder laporan belum ada: {laporan_root}")
        st.info("Buat atau unggah laporan melalui halaman Sync Laporan Word, lalu jalankan quality check kembali.")
        return

    required_params = [
        "Load",
        "Current 1",
        "Current 2",
        "Current 3",
        "Dev Current",
        "Voltage 1",
        "Voltage 2",
        "Voltage 3",
        "Dev Voltage",
        "power factor",
        "THD Current %",
        "THD Voltage %",
        "Real Power",
        "Rotorbar Health",
        "Upper Sideband",
        "Lower Sideband",
        "Bearing",
        "Kondisi",
    ]

    if "word_qc_result" not in st.session_state:
        st.info("Belum ada hasil scan. Jalankan **Scan Quality Check** untuk melihat kelengkapan parameter, duplikasi, dan alasan file gagal.")

    if st.button("Scan Quality Check", type="primary"):
        with st.spinner("Mengecek kualitas laporan Word..."):
            meta = get_folder_metadata(laporan_root)
            df_word, rep = parse_all_reports_with_report(laporan_root, meta)
            summary = summarize_word_report_quality(df_word, rep, required_params)
        st.session_state["word_qc_result"] = {
            "df_word_empty": df_word.empty,
            "report": rep,
            "summary": summary,
        }

    result = st.session_state.get("word_qc_result")
    if result:
        rep = result["report"]
        summary = result["summary"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total File", int(rep.get("total_files", 0)))
        c2.metric("Gagal Parse", int(summary["failed_files_count"]))
        c3.metric("Missing Metadata", len(summary["missing_metadata_rows"]))
        c4.metric("Anomali Numerik", len(summary["numeric_flag_rows"]))

        if summary["failed_files"]:
            st.subheader("File dikarantina: tindakan diperlukan")
            failed = pd.DataFrame(summary["failed_files"]).rename(columns={"file": "File", "error": "Alasan karantina"})
            st.error("File berikut tidak masuk ke dashboard. Periksa alasan karantina, lalu perbaiki dokumen atau metadata equipment sebelum unggah ulang.")
            st.dataframe(failed, use_container_width=True, hide_index=True)

        if summary["missing_parameter_rows"]:
            st.subheader("Parameter Wajib Hilang")
            st.dataframe(pd.DataFrame(summary["missing_parameter_rows"]), use_container_width=True, hide_index=True)

        if summary["weird_date_rows"]:
            st.subheader("Tanggal Tidak Wajar")
            st.dataframe(pd.DataFrame(summary["weird_date_rows"]), use_container_width=True, hide_index=True)

        if summary["duplicate_rows"]:
            st.subheader("Duplikasi Equipment/Parameter/Tanggal")
            st.dataframe(pd.DataFrame(summary["duplicate_rows"]), use_container_width=True, hide_index=True)

        if summary["missing_metadata_rows"]:
            st.subheader("Metadata Unit/Voltage Belum Lengkap")
            st.dataframe(pd.DataFrame(summary["missing_metadata_rows"]), use_container_width=True, hide_index=True)

        if summary["numeric_flag_rows"]:
            st.subheader("Flag Nilai Numerik")
            st.dataframe(pd.DataFrame(summary["numeric_flag_rows"]), use_container_width=True, hide_index=True)

        export = build_word_qc_export(summary, rep)
        st.download_button(
            "Unduh ringkasan QC (CSV)",
            data=export.to_csv(index=False).encode("utf-8-sig"),
            file_name="ringkasan_qc_laporan_word.csv",
            mime="text/csv",
            use_container_width=True,
        )

        if result["df_word_empty"]:
            st.warning("Tidak ada data valid yang berhasil diparsing dari laporan. Tinjau alasan karantina, perbaiki file atau metadata equipment, lalu scan ulang.")
        else:
            st.success("Quality check selesai.")
