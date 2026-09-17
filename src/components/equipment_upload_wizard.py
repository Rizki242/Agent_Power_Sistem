"""Component for the Equipment Upload & Registration wizard."""

import re

import pandas as pd
import streamlit as st

from src.asset_registry import upsert_asset
from src.domain_ingest import read_upload

# Canonical bulk-import field -> accepted header spellings (normalised to
# lowercase/underscore before matching, so "Rated Power (kW)" -> "rated_power_kw").
_BULK_COLUMN_ALIASES = {
    "asset_id": ("asset_id", "assetid", "id"),
    "name": ("equipment_name", "name", "nama", "nama_aset", "asset_name"),
    "equipment_type": ("category", "equipment_type", "tipe", "kategori"),
    "manufacturer": ("manufacturer", "pabrikan", "merk"),
    "model": ("model", "model_type", "model_type_", "type"),
    "rated_power_kw": ("rated_power_kw", "rated_power", "power_kw", "power"),
    "voltage_level": ("voltage", "voltage_v", "voltage_level", "tegangan"),
    "rpm": ("rpm", "speed"),
    "unit": ("unit", "unit_pembangkit"),
    "location": ("location", "location_area", "area", "lokasi"),
    "install_date": ("install_date", "installed_at", "tanggal_pasang"),
    "monitoring_modules": ("monitoring_modules", "pdm_tools", "modul_monitoring", "modules"),
    "kks": ("kks", "kode_kks"),
    "notes": ("notes", "catatan"),
}

# Tokens accepted inside a monitoring_modules cell -> src.asset_registry.MONITORING_MODULES value.
_MODULE_ALIASES = {
    "VIBRATION": "VIBRASI", "VIBRASI": "VIBRASI",
    "MCSA": "MCSA", "THERMAL": "THERMAL",
    "TRIBOLOGY": "TRIBOLOGY", "DGA": "DGA",
    "PD": "PD", "PD ONLINE": "PD", "PD_ONLINE": "PD", "PDONLINE": "PD",
}


def _normalise_header(col: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_")


_BULK_TEMPLATE_COLUMNS = [
    "asset_id", "name", "category", "manufacturer", "model",
    "rated_power_kw", "voltage", "rpm", "unit", "location",
    "install_date", "monitoring_modules", "kks", "notes",
]


def _bulk_template_csv() -> bytes:
    """One blank-ish example row - a starting point for the user's own data."""
    example = {
        "asset_id": "", "name": "ID Fan Motor 2A", "category": "Motor",
        "manufacturer": "ABB", "model": "M3BP 315 SMB", "rated_power_kw": "750",
        "voltage": "6600", "rpm": "1485", "unit": "UNIT 2",
        "location": "Unit 2 - ID Fan Area", "install_date": "2026-09-17",
        "monitoring_modules": "VIBRASI,MCSA,THERMAL", "kks": "-", "notes": "",
    }
    frame = pd.DataFrame([example], columns=_BULK_TEMPLATE_COLUMNS)
    return frame.to_csv(index=False).encode("utf-8-sig")


def _bulk_sample_csv() -> bytes:
    """Several filled-in rows across equipment types/units/monitoring
    modules, so a user can see a working bulk upload before building their
    own file - upload this as-is to try the feature end to end."""
    rows = [
        {
            "asset_id": "", "name": "ID Fan Motor 2A", "category": "Motor",
            "manufacturer": "ABB", "model": "M3BP 315 SMB", "rated_power_kw": "750",
            "voltage": "6600", "rpm": "1485", "unit": "UNIT 2",
            "location": "Unit 2 - ID Fan Area", "install_date": "2018-03-12",
            "monitoring_modules": "VIBRASI,MCSA,THERMAL", "kks": "-", "notes": "",
        },
        {
            "asset_id": "", "name": "Main Transformer Unit 1", "category": "Transformer",
            "manufacturer": "Siemens", "model": "TR-25MVA", "rated_power_kw": "25000",
            "voltage": "150000", "rpm": "", "unit": "UNIT 1",
            "location": "Switchyard Unit 1", "install_date": "2012-06-01",
            "monitoring_modules": "DGA,PD", "kks": "-", "notes": "Trafo utama step-up",
        },
        {
            "asset_id": "", "name": "Boiler Feed Pump 1A", "category": "Pump",
            "manufacturer": "Sulzer", "model": "HPT-4", "rated_power_kw": "1200",
            "voltage": "6600", "rpm": "2980", "unit": "UNIT 1",
            "location": "Turbine Hall Unit 1", "install_date": "2012-08-15",
            "monitoring_modules": "VIBRASI,TRIBOLOGY", "kks": "-", "notes": "",
        },
        {
            "asset_id": "", "name": "Circulating Water Pump 3B", "category": "Pump",
            "manufacturer": "KSB", "model": "CWP-V500", "rated_power_kw": "900",
            "voltage": "6600", "rpm": "990", "unit": "UNIT 3",
            "location": "Water Intake Unit 3", "install_date": "2019-11-20",
            "monitoring_modules": "VIBRASI,MCSA", "kks": "-", "notes": "",
        },
        {
            "asset_id": "", "name": "Instrument Air Compressor 2", "category": "Compressor",
            "manufacturer": "Atlas Copco", "model": "GA-90", "rated_power_kw": "90",
            "voltage": "400", "rpm": "2960", "unit": "UNIT 2",
            "location": "Compressor House", "install_date": "2018-05-02",
            "monitoring_modules": "VIBRASI,THERMAL", "kks": "-", "notes": "",
        },
    ]
    frame = pd.DataFrame(rows, columns=_BULK_TEMPLATE_COLUMNS)
    return frame.to_csv(index=False).encode("utf-8-sig")


def parse_bulk_asset_file(file_name: str, content: bytes) -> pd.DataFrame:
    """Parse an uploaded CSV/XLSX of many assets into the canonical column set.

    Reuses `src.domain_ingest.read_upload` for delimiter-tolerant CSV/XLSX
    parsing (raises ValueError with a readable message on a bad file), then
    maps flexible header spellings (English/Indonesian, several aliases per
    field) onto the columns `_row_to_asset_payload` expects. Unrecognised
    columns are dropped; missing ones come back as an empty column so the
    preview table always has a stable shape.
    """
    raw = read_upload(file_name, content)
    raw.columns = [_normalise_header(c) for c in raw.columns]

    canonical = pd.DataFrame(index=raw.index)
    for canonical_name, aliases in _BULK_COLUMN_ALIASES.items():
        found = next((alias for alias in aliases if alias in raw.columns), None)
        canonical[canonical_name] = raw[found].fillna("") if found is not None else ""
    return canonical


def _parse_monitoring_modules(raw) -> list[str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return []
    modules: list[str] = []
    for token in re.split(r"[,;|/]+", str(raw)):
        mapped = _MODULE_ALIASES.get(token.strip().upper())
        if mapped and mapped not in modules:
            modules.append(mapped)
    return modules


def _row_to_asset_payload(row: dict) -> dict:
    """Map one canonical bulk-import row onto the dict `upsert_asset` expects."""
    specs = {}
    manufacturer, model = row.get("manufacturer"), row.get("model")
    if manufacturer or model:
        specs["c1_type_mfg"] = " / ".join(str(v).strip() for v in (manufacturer, model) if v and str(v).strip())
    if row.get("rated_power_kw") not in (None, ""):
        specs["c1_power"] = str(row["rated_power_kw"]).strip()
    if row.get("rpm") not in (None, ""):
        specs["c1_speed"] = str(row["rpm"]).strip()
    if row.get("location") not in (None, ""):
        specs["location"] = str(row["location"]).strip()
    if row.get("install_date") not in (None, ""):
        specs["install_date"] = str(row["install_date"]).strip()

    return {
        "asset_id": str(row.get("asset_id") or "").strip() or None,
        "name": str(row.get("name") or "").strip(),
        "kks": str(row.get("kks") or "-").strip(),
        "unit": str(row.get("unit") or "Unknown").strip(),
        "equipment_type": str(row.get("equipment_type") or "-").strip(),
        "voltage_level": str(row.get("voltage_level") or "-").strip(),
        "monitoring_modules": _parse_monitoring_modules(row.get("monitoring_modules")),
        "specs": specs,
        "notes": str(row.get("notes") or "").strip(),
    }


def render_equipment_upload_wizard(st, edit_mode: bool) -> None:
    # 1. Stepper UI
    st.markdown("""
        <style>
        .wizard-stepper { display: flex; justify-content: space-between; margin-bottom: 2rem; position: relative; }
        .wizard-stepper::before {
            content: ''; position: absolute; top: 15px; left: 10%; right: 10%;
            height: 2px; background: #334155; z-index: 0;
        }
        .wizard-step { text-align: center; z-index: 1; flex: 1; font-size: 0.85rem; color: #94a3b8; font-weight: 500; }
        .wizard-icon {
            width: 32px; height: 32px; border-radius: 50%; background: #1e293b;
            color: #94a3b8; line-height: 32px; margin: 0 auto 8px; border: 2px solid #334155;
            font-size: 14px;
        }
        .wizard-step.completed .wizard-icon { background: #10b981; color: #fff; border-color: #10b981; }
        .wizard-step.active .wizard-icon { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }
        .wizard-step.active { color: #f8fafc; }
        .wizard-step.completed { color: #f8fafc; }
        </style>
        <div class="wizard-stepper">
            <div class="wizard-step completed"><div class="wizard-icon">✔</div>Category</div>
            <div class="wizard-step active"><div class="wizard-icon">2</div>Specifications</div>
            <div class="wizard-step"><div class="wizard-icon">3</div>PDM Assignment</div>
            <div class="wizard-step"><div class="wizard-icon">4</div>Confirmation</div>
        </div>
    """, unsafe_allow_html=True)

    # Main layout: Left for upload, Right for form
    col_upload, col_form = st.columns([1, 1.4], gap="large")

    with col_upload:
        st.markdown("##### Upload Equipment Data")
        st.caption("Drag & drop files here or click to browse. Supported: CSV, Excel, PDF, Image (.jpg, .png)")
        uploaded_files = st.file_uploader("Pilih Dokumen", accept_multiple_files=True, label_visibility="collapsed")

        # Display mock uploaded files if empty just to mimic the design slightly,
        # but in real usage we show actual uploaded files.
        if uploaded_files:
            for f in uploaded_files:
                st.info(f"📄 **{f.name}**")
        else:
            # Placeholder for visual parity with the mockup if no files uploaded yet
            st.markdown("""
                <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #0ea5e9;">
                    📄 Motor_Spec_M205.xlsx
                </div>
                <div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px; margin-bottom: 8px; border-left: 3px solid #0ea5e9;">
                    📄 Transformer_Test_TR001.csv
                </div>
            """, unsafe_allow_html=True)

    with col_form:
        st.markdown("##### Equipment Specifications")
        with st.form("wizard_spec_form"):
            r1c1, r1c2, r1c3 = st.columns(3)
            asset_id = r1c1.text_input("ASSET ID", placeholder="Kosongkan untuk dibuat otomatis")
            eq_name = r1c2.text_input("EQUIPMENT NAME", placeholder="mis. ID Fan Motor 2A")
            category = r1c3.selectbox("CATEGORY", ["Transformer", "Motor", "Pump", "Fan", "Compressor"])

            r2c1, r2c2, r2c3 = st.columns(3)
            manufacturer = r2c1.text_input("MANUFACTURER", placeholder="mis. ABB")
            model = r2c2.text_input("MODEL / TYPE", placeholder="mis. M3BP 315 SMB")
            rated_power = r2c3.text_input("RATED POWER (KW)")

            r3c1, r3c2, r3c3 = st.columns(3)
            voltage = r3c1.text_input("VOLTAGE (V)")
            rpm = r3c2.text_input("RPM")
            location = r3c3.text_input("LOCATION / AREA", placeholder="mis. Unit 2 - ID Fan Area")

            unit = st.selectbox("UNIT", ["UNIT 1", "UNIT 2", "UNIT 3", "UNIT COMMON", "Unknown"], index=4)
            install_date = st.date_input("INSTALL DATE")

            st.markdown("---")
            st.markdown("##### PDM TOOLS ASSIGNMENT (AUTO-DETECTED)")

            p1, p2, p3, p4, p5, p6 = st.columns(6)
            vibration = p1.checkbox("VIBRATION", value=True)
            mcsa = p2.checkbox("MCSA", value=True)
            thermal = p3.checkbox("THERMAL")
            tribology = p4.checkbox("TRIBOLOGY")
            dga = p5.checkbox("DGA")
            pd_online = p6.checkbox("PD ONLINE")

            st.markdown("<br>", unsafe_allow_html=True)
            b1, b2, _ = st.columns([1, 1, 3])
            submitted = b1.form_submit_button("Submit & Register", type="primary", disabled=not edit_mode)
            drafted = b2.form_submit_button("Save Draft", disabled=not edit_mode)

            if submitted:
                if not eq_name.strip():
                    st.error("Equipment Name wajib diisi.")
                else:
                    payload = _row_to_asset_payload({
                        "asset_id": asset_id, "name": eq_name, "equipment_type": category,
                        "manufacturer": manufacturer, "model": model, "rated_power_kw": rated_power,
                        "rpm": rpm, "voltage_level": voltage, "unit": unit, "location": location,
                        "install_date": install_date.isoformat() if install_date else "",
                        "monitoring_modules": ",".join(
                            m for m, checked in (
                                ("VIBRASI", vibration), ("MCSA", mcsa), ("THERMAL", thermal),
                                ("TRIBOLOGY", tribology), ("DGA", dga), ("PD", pd_online),
                            ) if checked
                        ),
                    })
                    saved = upsert_asset(payload)
                    st.success(f"Aset '{saved['name']}' ({saved['asset_id']}) berhasil didaftarkan.")
            elif drafted:
                st.info("Draft saved.")

    # 2. Bulk registration - many assets at once via CSV/XLSX, for engineers
    # who already keep an equipment list in a spreadsheet instead of typing
    # one asset at a time in the form above.
    st.divider()
    st.markdown("##### 📥 Registrasi Massal Banyak Aset (CSV / Excel)")
    st.caption(
        "Unduh templat, isi satu baris per aset, lalu unggah kembali. Kolom yang dikenali: "
        "asset_id, name, category, manufacturer, model, rated_power_kw, voltage, rpm, unit, "
        "location, install_date, monitoring_modules (pisahkan dengan koma, contoh: "
        "VIBRASI,MCSA,THERMAL), kks, notes."
    )
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "⬇️ Unduh Templat CSV",
        data=_bulk_template_csv(),
        file_name="templat_registrasi_aset.csv",
        mime="text/csv",
        disabled=not edit_mode,
        help="Satu baris contoh kosong - titik awal untuk mengisi data aset Anda sendiri.",
    )
    dl2.download_button(
        "📄 Unduh Contoh Data (Sample)",
        data=_bulk_sample_csv(),
        file_name="contoh_registrasi_aset.csv",
        mime="text/csv",
        disabled=not edit_mode,
        help="Beberapa baris contoh terisi (motor, transformator, pompa, kompresor) - unggah langsung untuk mencoba fitur ini.",
    )
    bulk_file = st.file_uploader(
        "Unggah Daftar Aset (CSV/XLSX)", type=["csv", "xlsx", "xls"],
        key="_bulk_asset_uploader", disabled=not edit_mode,
    )
    if bulk_file is not None:
        try:
            parsed = parse_bulk_asset_file(bulk_file.name, bulk_file.getvalue())
        except ValueError as exc:
            st.error(str(exc))
        else:
            if parsed.empty or parsed["name"].astype(str).str.strip().eq("").all():
                st.warning(
                    "Tidak ada baris dengan kolom 'name'/'equipment_name' yang terbaca. "
                    "Periksa header kolom pada file yang diunggah."
                )
            else:
                st.caption(f"{len(parsed)} baris terbaca. Periksa/koreksi di tabel sebelum mendaftarkan.")
                edited = st.data_editor(
                    parsed, hide_index=True, width="stretch", num_rows="dynamic",
                    key="_bulk_asset_editor", disabled=not edit_mode,
                )
                if st.button(
                    "Daftarkan Semua Aset", type="primary",
                    disabled=not edit_mode, key="_bulk_register_btn",
                ):
                    registered, skipped = 0, []
                    for _, row in edited.iterrows():
                        payload = _row_to_asset_payload(row.to_dict())
                        if not payload["name"]:
                            skipped.append(str(row.get("asset_id") or "(baris tanpa nama)"))
                            continue
                        upsert_asset(payload)
                        registered += 1
                    if registered:
                        st.success(f"{registered} aset berhasil didaftarkan.")
                    if skipped:
                        st.warning(f"{len(skipped)} baris dilewati karena tidak punya nama aset: {', '.join(skipped)}")
                    if registered:
                        st.rerun()
