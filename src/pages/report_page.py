import pandas as pd


def render_ppt_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end,
                    create_ppt, history_df=None):
    st.header("Generate Laporan PPT")
    st.write("Klik tombol di bawah untuk mengunduh laporan status equipment dalam format PowerPoint (16:9).")

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
        )
    with col_opt2:
        include_trend = st.checkbox(
            "Sertakan grafik tren", value=True,
            help="Menambah satu slide tren parameter (THD, Dev Current, Sideband) per equipment Alarm/High. "
                 "Butuh minimal 3 titik data historis.",
        )

    # Riwayat dibatasi ke equipment yang lolos filter, agar filter Unit/Voltage
    # tidak perlu diduplikasi di sini.
    hist_df = None
    if include_trend and isinstance(history_df, pd.DataFrame) and not history_df.empty:
        if not export_df.empty and "Equipment" in export_df.columns:
            keep = set(export_df["Equipment"].astype(str).unique())
            hist_df = history_df[history_df["Equipment"].astype(str).isin(keep)].copy()
        else:
            hist_df = history_df

    if st.button("Generate PPT"):
        progress_bar = st.progress(0.0, text="Menyiapkan laporan...")

        def _on_progress(done, total, label):
            pct = 0.0 if not total else min(1.0, done / float(total))
            progress_bar.progress(pct, text=f"Menyusun slide {done}/{total} - {label}")

        with st.spinner("Sedang membuat PPT..."):
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
        )
        st.success("PPT siap diunduh.")


def render_word_page(st, filtered_df, df_latest, sel_unit, sel_volt, date_start, date_end, standby_report, create_docx):
    st.header("Generate Laporan Bulanan (Word)")
    st.write("Klik tombol di bawah untuk mengunduh laporan bulanan status equipment dalam format Word (.docx).")

    unit_label = sel_unit if sel_unit != "All" else "PLTU Jeranjang"
    volt_label = sel_volt if sel_volt != "All" else "Semua Voltage"
    st.caption(f"Periode: {date_start.strftime('%d-%m-%Y')} s/d {date_end.strftime('%d-%m-%Y')}")
    st.caption(f"Filter: {unit_label} | {volt_label}")

    export_df = filtered_df.copy() if isinstance(filtered_df, pd.DataFrame) else df_latest.copy()
    eq_count = int(export_df.get("Equipment", pd.Series(dtype=str)).nunique()) if not export_df.empty else 0
    st.caption(f"Equipment terpilih: {eq_count}")

    if st.button("Generate Word"):
        with st.spinner("Sedang membuat Dokumen Word..."):
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
            )
            st.success("Dokumen Word siap diunduh.")
