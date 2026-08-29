from datetime import datetime
import pandas as pd

from src.data_loader import (
    audit_mcsa_dataframe,
    fix_mcsa_dataframe,
    get_data_path,
    load_mcsa_data,
    save_mcsa_data,
)
from src.standards import calculate_condition
from src.utils import safe_float


def render_data_management_page(st, df, df_latest_all, edit_mode):
    st.header("📝 Manajemen Data MCSA")
    st.info("Update nilai parameter, info Unit, atau hapus data equipment.")

    if not edit_mode:
        st.warning("Mode Edit nonaktif. Aksi yang mengubah data dinonaktifkan.")

    with st.expander("Data Health Check", expanded=False):
        file_path = get_data_path("Report MCSA.xls")
        st.caption(f"Sumber data: {file_path}")
        audit = audit_mcsa_dataframe(df)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rows", int(audit.get("rows", 0)))
        c2.metric("Invalid Date", int(audit.get("invalid_date_count", 0)))
        c3.metric("Duplicate Key", int(audit.get("duplicate_key_count", 0)))
        c4.metric("Missing Cols", len(audit.get("missing_columns") or []))

        missing_cols = audit.get("missing_columns") or []
        if missing_cols:
            st.error("Kolom wajib hilang: " + ", ".join(missing_cols))

        bad_dates = audit.get("invalid_date_sample")
        if isinstance(bad_dates, pd.DataFrame) and not bad_dates.empty:
            st.subheader("Contoh Date tidak valid")
            st.dataframe(bad_dates, use_container_width=True, hide_index=True)

        dup = audit.get("duplicate_key_sample")
        if isinstance(dup, pd.DataFrame) and not dup.empty:
            st.subheader("Contoh duplikat (Equipment, Parameter, Date)")
            st.dataframe(dup, use_container_width=True, hide_index=True)

        if st.button("Perbaiki Otomatis (ringan)", disabled=not edit_mode):
            fixed_df, rep = fix_mcsa_dataframe(df)
            save_mcsa_data(fixed_df, file_path)
            st.success(
                f"Selesai. Rows: {rep.get('rows_before')} → {rep.get('rows_after')}. "
                f"Duplikat dihapus: {rep.get('duplicates_removed')}. "
                f"Date diperbaiki: {rep.get('repaired_dates')}."
            )
            st.rerun()

    action = st.radio("Aksi:", ["Edit/Update Data", "Hapus Data Equipment", "Reload dari Excel (Reset)"])

    all_eq_list = sorted(df_latest_all["Equipment"].unique())
    selected_eq_manage = st.selectbox("Pilih Equipment:", all_eq_list, key="manage_eq")

    if action == "Edit/Update Data":
        st.subheader(f"Edit Data: {selected_eq_manage}")

        current_data = df_latest_all[df_latest_all["Equipment"] == selected_eq_manage]

        def get_val(param):
            row = current_data[current_data["Parameter"] == param]
            if not row.empty:
                return row["Raw_Value"].values[0]
            return ""

        curr_unit = current_data["Unit_Name"].iloc[0] if not current_data.empty else "Unknown"
        curr_volt = current_data["Voltage_Level"].iloc[0] if not current_data.empty else "Unknown"

        with st.form("edit_form"):
            st.markdown("### Info Equipment")
            c1, c2 = st.columns(2)
            with c1:
                unit_options = ["UNIT 1", "UNIT 2", "UNIT 3", "UNIT COMMON", "Unknown"]
                unit_idx = unit_options.index(curr_unit) if curr_unit in unit_options else 0
                new_unit = st.selectbox("Unit Name", unit_options, index=unit_idx)
            with c2:
                volt_options = ["380/400 V", "6.3 KV", "Unknown"]
                volt_idx = 0 if curr_volt == "380/400 V" else (1 if curr_volt == "6.3 KV" else 2)
                new_volt = st.selectbox("Voltage Level", volt_options, index=volt_idx)

            upd_date = st.date_input("Tanggal Update", value=datetime.now().date())

            st.markdown("### Parameter MCSA")
            col1, col2 = st.columns(2)

            params_to_edit = [
                "Load", "Current 1", "Current 2", "Current 3", "Dev Current",
                "Voltage 1", "Voltage 2", "Voltage 3", "Dev Voltage",
                "power factor", "THD Current %", "THD Voltage %", "Real Power",
                "Rotorbar Health", "Upper Sideband", "Lower Sideband",
                "Se Fund", "Se Harm", "Rotorbar Level %",
                "Rotorbar", "Rotorbar Severity Level",
                "Bearing"
            ]

            new_values = {}
            for i, param in enumerate(params_to_edit):
                with col1 if i % 2 == 0 else col2:
                    val = st.text_input(f"{param}", value=str(get_val(param)))
                    new_values[param] = val

            st.markdown("---")
            st.markdown("**Hasil Perhitungan Otomatis akan memperbarui 'Kondisi' dan 'Bearing'**")

            submitted = st.form_submit_button("Hitung & Simpan", disabled=not edit_mode)

            if submitted:
                calc_results = calculate_condition(new_values)
                st.success(f"Hasil Perhitungan: {calc_results}")

                upd_dt = pd.to_datetime(upd_date)
                m_name = upd_dt.strftime("%b").upper()
                y_val = int(upd_dt.year)
                new_rows = []

                for p, v in new_values.items():
                    if v and v != "nan":
                        new_rows.append({
                            "Equipment": selected_eq_manage,
                            "Parameter": p,
                            "Month": m_name,
                            "Year": y_val,
                            "Month_Name": m_name,
                            "Date": str(upd_date),
                            "Raw_Value": v,
                            "Value": safe_float(v),
                            "Unit": "",
                            "Limit": "",
                            "Status": "Normal",
                            "Unit_Name": new_unit,
                            "Voltage_Level": new_volt,
                        })

                new_rows.append({
                    "Equipment": selected_eq_manage,
                    "Parameter": "Kondisi",
                    "Month": m_name,
                    "Year": y_val,
                    "Month_Name": m_name,
                    "Date": str(upd_date),
                    "Raw_Value": calc_results["Overall"],
                    "Value": None,
                    "Unit": "",
                    "Limit": "",
                    "Status": calc_results["Overall"],
                    "Unit_Name": new_unit,
                    "Voltage_Level": new_volt,
                })

                if "Bearing" in calc_results:
                    new_rows.append({
                        "Equipment": selected_eq_manage,
                        "Parameter": "Bearing",
                        "Month": m_name,
                        "Year": y_val,
                        "Month_Name": m_name,
                        "Date": str(upd_date),
                        "Raw_Value": calc_results["Bearing"],
                        "Value": None,
                        "Unit": "",
                        "Limit": "",
                        "Status": calc_results["Bearing"],
                        "Unit_Name": new_unit,
                        "Voltage_Level": new_volt,
                    })

                df.loc[df["Equipment"] == selected_eq_manage, "Unit_Name"] = new_unit
                df.loc[df["Equipment"] == selected_eq_manage, "Voltage_Level"] = new_volt

                new_df_rows = pd.DataFrame(new_rows)
                updated_df = pd.concat([df, new_df_rows], ignore_index=True)

                file_path = get_data_path("Report MCSA.xls")
                save_mcsa_data(updated_df, file_path)

                st.session_state.data_changed = True
                st.success("Data berhasil disimpan.")
                st.rerun()

    elif action == "Hapus Data Equipment":
        st.warning(f"Apakah Anda yakin ingin menghapus SEMUA data untuk {selected_eq_manage}?")
        if st.button("Ya, Hapus Permanen", disabled=not edit_mode):
            cleaned_df = df[df["Equipment"] != selected_eq_manage]
            file_path = get_data_path("Report MCSA.xls")
            save_mcsa_data(cleaned_df, file_path)

            st.session_state.data_changed = True
            st.success(f"Data {selected_eq_manage} telah dihapus.")
            st.rerun()

    elif action == "Reload dari Excel (Reset)":
        st.warning(
            "⚠️ **PERINGATAN**: Tindakan ini akan membaca ulang file Excel (`Report MCSA.xls`) "
            "dan Laporan Word, lalu menimpa database CSV saat ini. Semua perubahan manual yang "
            "Anda lakukan di aplikasi akan hilang jika belum disimpan ke file sumber."
        )

        if st.button("Ya, Reload Ulang Semua Data", type="primary", disabled=not edit_mode):
            with st.spinner("Membaca ulang data dari Excel & Word..."):
                file_path = get_data_path("Report MCSA.xls")
                df_new = load_mcsa_data(file_path, force_excel=True)
                save_mcsa_data(df_new, file_path)
                st.session_state.data_changed = True

            st.success("Database berhasil di-reset ulang dari sumber Excel & Word!")
            st.rerun()
