"""Central, cross-domain asset register.

Complements data_management_page.py (which only edits raw MCSA parameters)
with the one place engineering can register an asset once and track its
condition across all six monitoring disciplines - the write side that
src.pages.asset_reports_page's "Laporan kondisi" view reads back from.
"""

from datetime import date

from src.asset_registry import (
    LIFECYCLE_STATUSES,
    MONITORING_MODULES,
    add_condition_record,
    list_assets,
    load_condition_history,
    save_evidence,
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
        if not assets:
            st.info("Belum ada aset terdaftar. Gunakan tab 'Tambah / Ubah Aset' untuk mulai.")
        else:
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
                    for a in assets
                ],
                hide_index=True, width="stretch",
            )

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

            with st.form("asset_condition_form"):
                module = st.selectbox("Modul Pengujian", module_options)
                c1, c2 = st.columns(2)
                with c1:
                    test_date = st.date_input("Tanggal Pengujian", value=date.today())
                with c2:
                    condition = st.selectbox("Kondisi", _CONDITION_OPTIONS)
                summary = st.text_area("Ringkasan Temuan")
                evidence_file = st.file_uploader("Bukti Pengujian (opsional)", type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "csv"])
                submitted = st.form_submit_button("Catat Kondisi", disabled=not edit_mode)

                if submitted:
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

        st.markdown("### Riwayat Kondisi Terbaru")
        history = load_condition_history()
        if history.empty:
            st.info("Belum ada riwayat kondisi tercatat.")
        else:
            st.dataframe(
                history.head(20).drop(columns=["record_id", "created_at"]),
                hide_index=True, width="stretch",
            )
