"""Central, cross-domain asset register.

Complements data_management_page.py (which only edits raw MCSA parameters)
with the one place engineering can register an asset once and track its
condition across all six monitoring disciplines - the write side that
src.pages.asset_reports_page's "Laporan kondisi" view reads back from.
"""

from datetime import date

import pandas as pd

from src.asset_registry import (
    LIFECYCLE_STATUSES,
    MONITORING_MODULES,
    add_condition_record,
    count_condition_records,
    delete_asset,
    delete_condition_record,
    get_condition_record,
    list_assets,
    load_condition_history,
    save_evidence,
    sync_assets_from_equipment_master,
    update_condition_record,
    upsert_asset,
)
from src.components.theme import render_page_header

_UNIT_OPTIONS = ["UNIT 1", "UNIT 2", "UNIT 3", "UNIT COMMON", "Unknown"]
_CONDITION_OPTIONS = ["Normal", "Alarm", "High", "Standby", "Unknown"]


def _asset_label(asset: dict) -> str:
    return f"{asset['name']} ({asset['asset_id']}) - {asset.get('unit', 'Unknown')}"


def render_asset_registry_page(st, edit_mode: bool) -> None:
    render_page_header(
        st, "Register Aset",
        "Daftarkan aset lintas-domain dan catat riwayat kondisinya (MCSA, DGA, Vibrasi, PD, Tribology, Thermal).",
    )
    if not edit_mode:
        st.warning("Mode Edit nonaktif. Aktifkan toggle 'Mode Edit' di sidebar untuk mendaftarkan aset atau mencatat kondisi.")

    assets = list_assets()

    tab_list, tab_new, tab_condition = st.tabs(["Daftar Aset", "Tambah / Ubah Aset", "Catat Riwayat Kondisi"])

    with tab_list:
        c_act1, c_act2 = st.columns([3, 1])
        with c_act2:
            if st.button("🔄 Sinkronisasi Master", help="Impor otomatis seluruh aset dari Master Equipment Pembangkit", disabled=not edit_mode):
                added = sync_assets_from_equipment_master()
                if added > 0:
                    st.success(f"Berhasil menambahkan {added} aset baru dari Master Equipment.")
                else:
                    st.info("Semua aset dari Master Equipment sudah terdaftar.")
                st.rerun()

        if not assets:
            st.info("Belum ada aset terdaftar. Gunakan tombol 'Sinkronisasi Master' atau tab 'Tambah / Ubah Aset' untuk mulai.")
        else:
            with c_act1:
                units_avail = ["Semua Unit"] + sorted(list({str(a.get("unit", "Unknown")) for a in assets}))
                selected_unit = st.selectbox("Filter Unit", units_avail, index=0, key="_reg_unit_filter")

            filtered_assets = assets if selected_unit == "Semua Unit" else [a for a in assets if str(a.get("unit")) == selected_unit]

            st.dataframe(
                [
                    {
                        "Asset ID": a["asset_id"],
                        "Nama": a["name"],
                        "Unit": a.get("unit", "-"),
                        "Tipe": a.get("equipment_type", "-"),
                        "Tegangan": a.get("voltage_level", "-"),
                        "Status": a.get("lifecycle_status", "-"),
                        "Modul Monitoring": ", ".join(a.get("monitoring_modules", [])) or "-",
                    }
                    for a in filtered_assets
                ],
                hide_index=True, width="stretch",
            )
            st.caption(f"Menampilkan {len(filtered_assets)} dari total {len(assets)} aset terdaftar.")

    with tab_new:
        existing_ids = ["(Aset Baru)"] + [a["asset_id"] for a in assets]
        selected = st.selectbox(
            "Aset yang diedit", existing_ids,
            format_func=lambda aid: aid if aid == "(Aset Baru)" else _asset_label(next(a for a in assets if a["asset_id"] == aid)),
            key="asset_registry_select",
        )
        prior = next((a for a in assets if a["asset_id"] == selected), {}) if selected != "(Aset Baru)" else {}

        with st.form("asset_registry_form"):
            name = st.text_input("Nama Aset", value=prior.get("name", ""))
            c1, c2 = st.columns(2)
            with c1:
                unit_idx = _UNIT_OPTIONS.index(prior["unit"]) if prior.get("unit") in _UNIT_OPTIONS else len(_UNIT_OPTIONS) - 1
                unit = st.selectbox("Unit", _UNIT_OPTIONS, index=unit_idx)
                equipment_type = st.text_input("Tipe Equipment", value=prior.get("equipment_type", ""))
            with c2:
                voltage_level = st.text_input("Voltage Level", value=prior.get("voltage_level", ""))
                lifecycle_idx = LIFECYCLE_STATUSES.index(prior["lifecycle_status"]) if prior.get("lifecycle_status") in LIFECYCLE_STATUSES else 0
                lifecycle_status = st.selectbox("Status Lifecycle", LIFECYCLE_STATUSES, index=lifecycle_idx)
            monitoring_modules = st.multiselect(
                "Modul Monitoring yang Berlaku", MONITORING_MODULES,
                default=[m for m in prior.get("monitoring_modules", []) if m in MONITORING_MODULES],
            )
            notes = st.text_area("Catatan", value=prior.get("notes", ""))
            submitted = st.form_submit_button("Simpan Aset", disabled=not edit_mode)

            if submitted:
                if not name.strip():
                    st.error("Nama aset wajib diisi.")
                else:
                    saved = upsert_asset({
                        "asset_id": prior.get("asset_id"),
                        "name": name,
                        "unit": unit,
                        "equipment_type": equipment_type,
                        "voltage_level": voltage_level,
                        "lifecycle_status": lifecycle_status,
                        "monitoring_modules": monitoring_modules,
                        "notes": notes,
                    })
                    st.success(f"Aset '{saved['name']}' ({saved['asset_id']}) tersimpan.")
                    st.rerun()

        if selected != "(Aset Baru)":
            with st.expander(":material/delete_forever: Hapus Aset Ini", expanded=False):
                related = count_condition_records(selected)
                if related:
                    st.warning(
                        f"Aset ini punya {related} catatan riwayat kondisi. Menghapus aset akan "
                        f"ikut menghapus semua catatan tersebut secara permanen."
                    )
                else:
                    st.info("Aset ini belum punya catatan riwayat kondisi.")
                confirm = st.checkbox(f"Saya yakin ingin menghapus '{prior.get('name', selected)}' ({selected})", key="_confirm_delete_asset")
                if st.button("Hapus Permanen", type="secondary", disabled=not edit_mode or not confirm, key="_delete_asset_btn"):
                    delete_asset(selected)
                    st.success(f"Aset {selected} dan riwayat kondisinya telah dihapus.")
                    st.session_state.pop("_confirm_delete_asset", None)
                    st.rerun()

    with tab_condition:
        if not assets:
            st.info("Daftarkan aset terlebih dahulu di tab 'Tambah / Ubah Aset'.")
        else:
            asset_id = st.selectbox(
                "Aset", [a["asset_id"] for a in assets],
                format_func=lambda aid: _asset_label(next(a for a in assets if a["asset_id"] == aid)),
                key="asset_condition_select",
            )
            asset = next(a for a in assets if a["asset_id"] == asset_id)
            module_options = asset.get("monitoring_modules") or list(MONITORING_MODULES)

            asset_history = load_condition_history()
            asset_records = (
                asset_history[asset_history["asset_id"] == asset_id].to_dict("records")
                if not asset_history.empty else []
            )
            record_options = ["(Catatan Baru)"] + [r["record_id"] for r in asset_records]
            record_labels = {
                r["record_id"]: f"{r['test_date'].strftime('%Y-%m-%d') if pd.notna(r['test_date']) else '-'} - {r['module']} - {r['condition']}"
                for r in asset_records
            }
            selected_record_id = st.selectbox(
                "Catatan yang diedit",
                record_options,
                format_func=lambda rid: rid if rid == "(Catatan Baru)" else record_labels.get(rid, rid),
                key="asset_condition_record_select",
            )
            editing = selected_record_id != "(Catatan Baru)"
            prior_record = get_condition_record(selected_record_id) if editing else {}

            with st.form("asset_condition_form"):
                module_default = prior_record.get("module") if editing and prior_record.get("module") in module_options else (module_options[0] if module_options else MONITORING_MODULES[0])
                module = st.selectbox("Modul Pengujian", module_options, index=module_options.index(module_default) if module_default in module_options else 0)
                c1, c2 = st.columns(2)
                with c1:
                    date_default = date.today()
                    if editing and prior_record.get("test_date"):
                        try:
                            date_default = date.fromisoformat(str(prior_record["test_date"]))
                        except ValueError:
                            pass
                    test_date = st.date_input("Tanggal Pengujian", value=date_default)
                with c2:
                    condition_default = prior_record.get("condition") if editing and prior_record.get("condition") in _CONDITION_OPTIONS else _CONDITION_OPTIONS[0]
                    condition = st.selectbox("Kondisi", _CONDITION_OPTIONS, index=_CONDITION_OPTIONS.index(condition_default))
                summary = st.text_area("Ringkasan Temuan", value=prior_record.get("summary", "") if editing else "")
                evidence_file = None
                if not editing:
                    evidence_file = st.file_uploader("Bukti Pengujian (opsional)", type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "csv"])
                submitted = st.form_submit_button("Simpan Perubahan" if editing else "Catat Kondisi", disabled=not edit_mode)

                if submitted:
                    if editing:
                        updated = update_condition_record(selected_record_id, {
                            "module": module, "test_date": test_date,
                            "condition": condition, "summary": summary,
                        })
                        st.success(f"Riwayat kondisi {updated['asset_name']} ({updated['module']}, {updated['test_date']}) diperbarui.")
                    else:
                        source_file = ""
                        if evidence_file is not None:
                            source_file = save_evidence(asset_id, module, evidence_file.name, evidence_file.getvalue(), test_date)
                        row = add_condition_record({
                            "asset_id": asset_id,
                            "module": module,
                            "test_date": test_date,
                            "condition": condition,
                            "summary": summary,
                            "source_file": source_file,
                        })
                        st.success(f"Riwayat kondisi tercatat untuk {row['asset_name']} ({row['module']}, {row['test_date']}).")
                    st.rerun()

            if editing:
                if st.button("Hapus Catatan Ini", type="secondary", disabled=not edit_mode, key="_delete_condition_btn"):
                    delete_condition_record(selected_record_id)
                    st.success("Catatan riwayat kondisi telah dihapus.")
                    st.session_state.pop("asset_condition_record_select", None)
                    st.rerun()

        st.markdown("### Riwayat Kondisi Terbaru")
        history = load_condition_history()
        if history.empty:
            st.info("Belum ada riwayat kondisi tercatat.")
        else:
            st.dataframe(
                history.head(20).drop(columns=["record_id", "created_at"]),
                hide_index=True, width="stretch",
            )
            st.caption("Untuk mengubah atau menghapus satu catatan, pilih aset dan catatannya di form di atas.")
