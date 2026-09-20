import pandas as pd
from datetime import date
from io import BytesIO

from src.components.theme import render_page_header
from src import domain_report as report


def render_ppt_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end,
                    create_ppt, history_df=None):
    render_page_header(st, "Reports", "Generate laporan presentasi PPTX.")

    tab1, tab2, tab3 = st.tabs([
        "📊 Laporan MCSA Terpilih",
        "👥 Slide Deck Meeting Keandalan CBM (16:9)",
        "📑 Laporan PPTX Per Modul CBM"
    ])

    with tab1:
        st.write("Laporan status peralatan MCSA dalam format PowerPoint (16:9).")

        unit_label = sel_unit if sel_unit != "All" else "PLTU Jeranjang"
        volt_label = sel_volt if sel_volt != "All" else "Semua Voltage"
        st.caption(f"Periode: {date_start.strftime('%d-%m-%Y')} s/d {date_end.strftime('%d-%m-%Y')}")
        st.caption(f"Filter: {unit_label} | {volt_label}")

        export_df = filtered_df.copy() if isinstance(filtered_df, pd.DataFrame) else df_latest.copy()
        eq_count = int(export_df.get("Equipment", pd.Series(dtype=str)).nunique()) if not export_df.empty else 0
        st.caption(f"Equipment terpilih: {eq_count}")

        col_opt1, col_opt2 = st.columns(2)
        with col_opt1:
            include_images = st.checkbox(
                "Sertakan gambar spektrum (Alarm/High)", value=True,
                help="Menyisipkan gambar spektrum hasil ekstraksi laporan Word pada slide equipment bermasalah. "
                     "Menambah ukuran file.",
                key="ppt_mcsa_inc_images",
            )
        with col_opt2:
            include_trend = st.checkbox(
                "Sertakan grafik tren", value=True,
                help="Menambah satu slide tren parameter (THD, Dev Current, Sideband) per equipment Alarm/High. "
                     "Butuh minimal 3 titik data historis.",
                key="ppt_mcsa_inc_trend",
            )

        hist_df = None
        if include_trend and isinstance(history_df, pd.DataFrame) and not history_df.empty:
            if not export_df.empty and "Equipment" in export_df.columns:
                keep = set(export_df["Equipment"].astype(str).unique())
                hist_df = history_df[history_df["Equipment"].astype(str).isin(keep)].copy()
            else:
                hist_df = history_df

        if st.button("Generate PPT MCSA", key="btn_gen_ppt_mcsa"):
            progress_bar = st.progress(0.0, text="Menyiapkan laporan...")

            def _on_progress(done, total, label):
                pct = 0.0 if not total else min(1.0, done / float(total))
                progress_bar.progress(pct, text=f"Menyusun slide {done}/{total} - {label}")

            with st.spinner("Sedang membuat PPT MCSA..."):
                ppt_io = create_ppt(
                    export_df,
                    context={
                        "period_start": date_start.strftime("%d-%m-%Y"),
                        "period_end": date_end.strftime("%d-%m-%Y"),
                        "unit_label": unit_label,
                        "volt_label": volt_label,
                    },
                    history_df=hist_df,
                    include_images=include_images,
                    include_trend=include_trend,
                    progress=_on_progress,
                )

            progress_bar.empty()
            st.download_button(
                label="Download Laporan MCSA (.pptx)",
                data=ppt_io,
                file_name=f"Laporan_MCSA_{date_start.strftime('%b_%Y')}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="btn_dl_ppt_mcsa",
            )
            st.success("PPT MCSA siap diunduh.")

    with tab2:
        st.subheader("Slide Deck Meeting Koordinasi Keandalan CBM (16:9)")
        st.write("Slide deck presentasi eksekutif multi-modul CBM untuk rapat evaluasi bulanan.")
        st.info(
            "💡 **Aturan Standby & Historis:** Modul dengan data pengujian aktif akan menampilkan statistik dan "
            "diagnosa detail per unit. Modul tanpa pengujian pada periode terpilih akan otomatis ditandai "
            "`⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]` dengan penjelasan operasional."
        )

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            meeting_start = st.date_input("Periode Mulai", value=date_start, key="meeting_date_start")
        with col_m2:
            meeting_end = st.date_input("Periode Selesai", value=date_end, key="meeting_date_end")

        meeting_domains = st.multiselect(
            "Pilih Modul CBM yang Diikutsertakan:",
            options=list(report.ALL_REPORT_DOMAINS),
            default=list(report.ALL_REPORT_DOMAINS),
            key="meeting_domains_select",
        )

        if st.button("Generate Slide Deck Meeting PPTX", key="btn_gen_meeting_pptx"):
            if not meeting_domains:
                st.warning("Pilih minimal satu modul CBM.")
            else:
                with st.spinner("Menyusun Slide Deck Koordinasi Keandalan CBM (16:9)..."):
                    pptx_bytes = report.build_meeting_pptx(
                        meeting_domains,
                        start=meeting_start,
                        end=meeting_end,
                        title="Meeting Koordinasi Keandalan CBM & Asset Management",
                        subtitle=f"PLTU Jeranjang (3 × 25 MW) — Evaluasi Periode {meeting_start.strftime('%d %b %Y')} s/d {meeting_end.strftime('%d %b %Y')}",
                    )

                st.download_button(
                    label="Download Slide Deck Meeting Keandalan (.pptx)",
                    data=pptx_bytes,
                    file_name=f"Meeting_CBM_PLTU_Jeranjang_{meeting_start.strftime('%b_%Y')}.pptx",
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    key="btn_dl_meeting_pptx",
                )
                st.success("Slide Deck Meeting Keandalan siap diunduh.")

    with tab3:
        st.subheader("Laporan Presentasi PPTX Per Modul CBM")
        st.write("Unduh presentasi ringkas untuk satu modul CBM spesifik.")

        col_p1, col_p2, col_p3 = st.columns([2, 1, 1])
        with col_p1:
            sel_mod = st.selectbox(
                "Pilih Modul CBM:",
                options=list(report.ALL_REPORT_DOMAINS),
                index=0,
                key="sel_single_mod_pptx",
            )
        with col_p2:
            single_start = st.date_input("Periode Mulai", value=date_start, key="single_start_pptx")
        with col_p3:
            single_end = st.date_input("Periode Selesai", value=date_end, key="single_end_pptx")

        if st.button("Generate PPTX Modul", key="btn_gen_single_mod_pptx"):
            with st.spinner(f"Menyusun presentasi PPTX modul {sel_mod}..."):
                single_pptx_bytes = report.build_pptx([sel_mod], start=single_start, end=single_end)

            st.download_button(
                label=f"Download Laporan PPTX {sel_mod}",
                data=single_pptx_bytes,
                file_name=f"Laporan_PPTX_{sel_mod}_{single_start.strftime('%b_%Y')}.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                key="btn_dl_single_pptx",
            )
            st.success(f"Laporan PPTX {sel_mod} siap diunduh.")


def render_word_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end, standby_report, create_docx):
    render_page_header(st, "Reports", "Generate laporan dokumen Word & Terpadu.")

    tab1, tab2, tab3 = st.tabs([
        "📄 Laporan MCSA Bulanan",
        "🌐 Laporan Terpadu 6 Modul CBM (Asset Management)",
        "📋 Laporan DOCX Per Modul CBM"
    ])

    with tab1:
        st.write("Laporan bulanan status peralatan MCSA dalam format Word (.docx).")

        unit_label = sel_unit if sel_unit != "All" else "PLTU Jeranjang"
        volt_label = sel_volt if sel_volt != "All" else "Semua Voltage"
        st.caption(f"Periode: {date_start.strftime('%d-%m-%Y')} s/d {date_end.strftime('%d-%m-%Y')}")
        st.caption(f"Filter: {unit_label} | {volt_label}")

        export_df = filtered_df.copy() if isinstance(filtered_df, pd.DataFrame) else df_latest.copy()
        eq_count = int(export_df.get("Equipment", pd.Series(dtype=str)).nunique()) if not export_df.empty else 0
        st.caption(f"Equipment terpilih: {eq_count}")

        if st.button("Generate Word MCSA", key="btn_gen_word_mcsa"):
            with st.spinner("Sedang membuat Dokumen Word MCSA..."):
                compliance_ctx = None
                if standby_report:
                    universe = standby_report.get("eq_universe") or []
                    present = set(standby_report.get("eq_present") or [])
                    total_expected = len(universe)
                    updated = len(present)
                    compliance_pct = 0.0 if total_expected == 0 else (updated / total_expected) * 100.0
                    compliance_ctx = {
                        "expected": total_expected,
                        "updated": updated,
                        "missing": len(universe) - len(present),
                        "pct": compliance_pct,
                    }

                docx_io = create_docx(
                    export_df,
                    context={
                        "period_start": date_start.strftime("%d-%m-%Y"),
                        "period_end": date_end.strftime("%d-%m-%Y"),
                        "unit_label": unit_label,
                        "volt_label": volt_label,
                        "compliance": compliance_ctx,
                    },
                )

                st.download_button(
                    label="Download Laporan MCSA (.docx)",
                    data=docx_io,
                    file_name=f"Laporan_MCSA_{date_start.strftime('%b_%Y')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_dl_word_mcsa",
                )
                st.success("Dokumen Word MCSA siap diunduh.")

    with tab2:
        st.subheader("Laporan Terpadu Seluruh Modul CBM / Asset Management")
        st.write("Laporan konsolidasi kondisi 6 modul CBM PLTU Jeranjang (MCSA, Vibrasi, DGA, PD, Tribologi, Thermal).")
        st.info(
            "💡 Dokumen ini merangkum seluruh pembacaan aktual yang diuji pada periode laporan. "
            "Modul yang belum melakukan uji laboratorium atau pengukuran lapangan ditandai jelas sebagai "
            "`[STANDBY]` untuk akuntabilitas operasional."
        )

        col_w1, col_w2, col_w3 = st.columns([1, 1, 1])
        with col_w1:
            all_start = st.date_input("Periode Mulai", value=date_start, key="all_start_date")
        with col_w2:
            all_end = st.date_input("Periode Selesai", value=date_end, key="all_end_date")
        with col_w3:
            report_fmt = st.selectbox("Format Berkas:", options=["Dokumen Word (.docx)", "Tabel Data (.csv)"], key="all_report_fmt")

        if st.button("Generate Laporan Terpadu CBM", key="btn_gen_all_cbm_report"):
            domains = list(report.ALL_REPORT_DOMAINS)
            month_label = all_start.strftime("%B_%Y")
            with st.spinner("Menyusun Laporan Terpadu 6 Modul CBM..."):
                if "Word" in report_fmt:
                    doc_bytes = report.build_docx(domains, start=all_start, end=all_end)
                    st.download_button(
                        label="Download Laporan Terpadu CBM (.docx)",
                        data=doc_bytes,
                        file_name=f"Laporan_CBM_Asset_Management_PLTU_Jeranjang_{month_label}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="btn_dl_all_cbm_docx",
                    )
                else:
                    csv_bytes = report.build_csv(domains, start=all_start, end=all_end)
                    st.download_button(
                        label="Download Rekap Data CBM (.csv)",
                        data=csv_bytes,
                        file_name=f"Rekap_Data_CBM_PLTU_Jeranjang_{month_label}.csv",
                        mime="text/csv",
                        key="btn_dl_all_cbm_csv",
                    )
            st.success("Laporan Terpadu CBM siap diunduh.")

    with tab3:
        st.subheader("Laporan Dokumen DOCX Per Modul CBM")
        st.write("Unduh laporan spesifik untuk satu modul CBM dalam format Microsoft Word (.docx).")

        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            sel_mod_docx = st.selectbox(
                "Pilih Modul CBM:",
                options=list(report.ALL_REPORT_DOMAINS),
                index=0,
                key="sel_mod_docx_key",
            )
        with col_s2:
            docx_start = st.date_input("Periode Mulai", value=date_start, key="docx_start_date")
        with col_s3:
            docx_end = st.date_input("Periode Selesai", value=date_end, key="docx_end_date")

        if st.button("Generate DOCX Modul", key="btn_gen_single_docx"):
            with st.spinner(f"Menyusun dokumen Word modul {sel_mod_docx}..."):
                single_docx_bytes = report.build_docx([sel_mod_docx], start=docx_start, end=docx_end)

            st.download_button(
                label=f"Download Laporan DOCX {sel_mod_docx}",
                data=single_docx_bytes,
                file_name=f"Laporan_Bulanan_{sel_mod_docx}_{docx_start.strftime('%B_%Y')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="btn_dl_single_docx",
            )
            st.success(f"Laporan DOCX {sel_mod_docx} siap diunduh.")
