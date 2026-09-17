"""Rich domain-specific input forms for DGA, Vibrasi, Tribologi, and Partial Discharge.

Each render_* function replaces the generic three-column text-input block in
domain_workspace.render_data_tab() with a structured form that mirrors the
official PLTU Jeranjang measurement sheets (FORM.JRG.*) and the UI mockups
shown in the design reference.

Functions are pure Streamlit — they receive `st` as their first argument so
they can be called from within AppTest.from_function in tests.  They write
rows to the canonical domain_measurements store on submit (same path as the
generic form), so no test needs a live Streamlit server.

Design choices:
- Equipment list pulled from asset_registry first; falls back to free-text
  so a new asset can always be added without a prior registry entry.
- Scan button is a placeholder (shows info toast); real OCR/PDF scan is a
  future feature.
- Auto-save draft: key values are persisted in st.session_state under a
  domain-scoped key so the user does not lose work on a page reload.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from src import domain_measurements as dm
from src.asset_registry import list_assets

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UNIT_OPTIONS = ["Unit 1", "Unit 2", "Unit 3", "Common", "Semua Unit"]
_UNIT_STATUS_OPTIONS = ["Unit ON", "Unit OFF", "Partial Load", "Overhaul", "Standby"]
_JENIS_MONITORING_OPTIONS = [
    "Monitoring Rutin",
    "Setelah Alarm",
    "Post-Maintenance",
    "Commissioning",
    "Investigasi Khusus",
]

# IEEE C57.104-2019 TDCG condition thresholds
_TDCG_COND = [
    (720, "Kondisi 1 Normal"),
    (1920, "Kondisi 2 - Monitor Ketat"),
    (4630, "Kondisi 3 - Tindakan Segera"),
]

# ISO 10816-3 vibration zone limits for Group 1 (rigid, >15 kW) in mm/s
_VIB_ZONES = [
    (2.3, "A", "#10b981"),
    (4.5, "B", "#84cc16"),
    (7.1, "C", "#f59e0b"),
    (float("inf"), "D", "#ef4444"),
]


def _get_equipment_list(domain: Optional[str] = None) -> list[str]:
    """Return equipment names from asset registry, filtered by domain if given."""
    try:
        assets = list_assets()
        names = [a.get("name", "") for a in assets if a.get("name")]
        if domain == "DGA":
            # Prioritise transformers for DGA
            trafo = [n for n in names if any(k in n.lower() for k in ("trafo", "transformer", "uat", "gt", "pmt"))]
            others = [n for n in names if n not in trafo]
            return trafo + others
        return sorted(set(names))
    except Exception:
        return []


def _vib_zone(value: float) -> tuple[str, str]:
    """Return (zone_label, hex_color) for an overall vibration value."""
    for limit, label, color in _VIB_ZONES:
        if value < limit:
            return label, color
    return "D", "#ef4444"


def _tdcg_status(tdcg: float) -> str:
    for limit, label in _TDCG_COND:
        if tdcg <= limit:
            return label
    return "Kondisi 4 - KRITIS"


def _save_draft(key: str, values: dict) -> None:
    """Persist draft values to session_state."""
    import streamlit as _st
    _st.session_state[f"_draft_{key}"] = values


def _load_draft(key: str) -> dict:
    """Load draft values from session_state."""
    import streamlit as _st
    return _st.session_state.get(f"_draft_{key}", {})


def _scan_button(st, key: str) -> None:
    """Placeholder scan button shown at top-right of the form header."""
    if st.button("🔍 Scan", key=f"scan_{key}", help="Scan laporan PDF (segera hadir)"):
        st.toast("Fitur Scan dari PDF akan segera tersedia.", icon="ℹ️")


# ---------------------------------------------------------------------------
# DGA Input Form
# ---------------------------------------------------------------------------

def render_dga_input_form(st, default_equipment: Optional[str] = None) -> None:
    """Rich structured form for Dissolved Gas Analysis measurement entry."""
    domain = "DGA"
    draft = _load_draft(domain)
    equipment_list = _get_equipment_list(domain)

    # ── Header bar ───────────────────────────────────────────────────────────
    h_col, scan_col = st.columns([6, 1])
    with h_col:
        st.markdown("### 📊 Input Data DGA")
        st.caption("Masukkan hasil uji gas terlarut dari laporan lab.")
    with scan_col:
        _scan_button(st, domain)

    # Realtime TDCG from draft
    draft_gases = draft.get("gases", {})
    tdcg_live = sum(draft_gases.get(g, 0) for g in ("h2", "ch4", "c2h2", "c2h4", "c2h6", "co", "co2"))
    status_live = _tdcg_status(tdcg_live)
    kpi_col1, kpi_col2, _ = st.columns([2, 3, 2])
    kpi_col1.markdown(
        f"<div style='background:#1e293b;padding:8px 12px;border-radius:6px;font-size:0.85rem;'>"
        f"<span style='color:#94a3b8;'>TDCG</span><br>"
        f"<strong style='font-size:1.1rem;color:#f8fafc;'>{tdcg_live:.0f} ppm</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )
    status_color = "#10b981" if "Normal" in status_live else ("#f59e0b" if "2" in status_live else "#ef4444")
    kpi_col2.markdown(
        f"<div style='background:{status_color}22;padding:8px 12px;border-radius:6px;font-size:0.85rem;border:1px solid {status_color}44;'>"
        f"<strong style='color:{status_color};'>{status_live}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # ── Toggle: Input Manual / Import CSV ────────────────────────────────────
    mode_col1, mode_col2 = st.columns([1, 1])
    # (tabs handled by domain_workspace; here just the manual form)

    # ── Section: Identitas Sampel ────────────────────────────────────────────
    st.markdown("**Identitas Sampel**")
    r1c1, r1c2 = st.columns(2)
    sel_unit = r1c1.selectbox("UNIT", _UNIT_OPTIONS, key=f"{domain}_unit")
    eq_options = equipment_list if equipment_list else []
    default_idx = 0
    if default_equipment and default_equipment in eq_options:
        default_idx = eq_options.index(default_equipment)
    sel_equipment = r1c2.text_input("EQUIPMENT", value=default_equipment or (eq_options[default_idx] if eq_options else ""), key=f"{domain}_equipment")
    if eq_options:
        sel_equipment = r1c2.selectbox(
            "EQUIPMENT",
            eq_options,
            index=default_idx,
            key=f"{domain}_equipment_select",
        )

    r2c1, r2c2 = st.columns(2)
    sel_date = r2c1.date_input("TANGGAL SAMPLING", value=date.today(), key=f"{domain}_date")
    sel_status = r2c2.selectbox("UNIT STATUS", _UNIT_STATUS_OPTIONS, key=f"{domain}_unit_status")

    sel_jenis = st.selectbox("JENIS MONITORING", _JENIS_MONITORING_OPTIONS, key=f"{domain}_jenis")
    sel_keterangan = st.text_area(
        "KETERANGAN",
        placeholder="Contoh: request setelah alarm, sampling rutin bulanan, unit off saat overhaul",
        key=f"{domain}_keterangan",
    )

    # ── Section: Kondisi Operasi ─────────────────────────────────────────────
    st.markdown("**Kondisi Operasi**")
    op1, op2, op3 = st.columns(3)
    beban_mw = op1.number_input("BEBAN (MW)", min_value=0.0, step=0.5, key=f"{domain}_beban")
    temp_oil = op2.number_input("TEMP OIL (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_oil")
    temp_winding = op3.number_input("TEMP WINDING (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_winding")

    # ── Section: Dissolved Gases ─────────────────────────────────────────────
    tdcg_val = sum([
        st.session_state.get(f"{domain}_h2", 0.0),
        st.session_state.get(f"{domain}_ch4", 0.0),
        st.session_state.get(f"{domain}_c2h2", 0.0),
        st.session_state.get(f"{domain}_c2h4", 0.0),
        st.session_state.get(f"{domain}_c2h6", 0.0),
        st.session_state.get(f"{domain}_co", 0.0),
        st.session_state.get(f"{domain}_co2", 0.0),
    ])
    tdcg_status = _tdcg_status(tdcg_val)
    tdcg_color = "#10b981" if "Normal" in tdcg_status else ("#f59e0b" if "2" in tdcg_status else "#ef4444")

    gas_header_col, tdcg_badge_col = st.columns([3, 2])
    gas_header_col.markdown("⚡ **Dissolved Gases (ppm)**")
    tdcg_badge_col.markdown(
        f"<div style='text-align:right;'><span style='background:{tdcg_color}22;color:{tdcg_color};"
        f"padding:3px 8px;border-radius:4px;font-size:0.8rem;font-weight:700;border:1px solid {tdcg_color}44;'>"
        f"{tdcg_status} – TDCG {tdcg_val:.0f} ppm</span></div>",
        unsafe_allow_html=True,
    )

    g1, g2, g3, g4 = st.columns(4)
    h2 = g1.number_input("H2\nHYDROGEN", min_value=0.0, step=1.0, key=f"{domain}_h2")
    ch4 = g2.number_input("CH4\nMETHANE", min_value=0.0, step=1.0, key=f"{domain}_ch4")
    c2h6 = g3.number_input("C2H6\nETHANE", min_value=0.0, step=1.0, key=f"{domain}_c2h6")
    c2h4 = g4.number_input("C2H4\nETHYLENE", min_value=0.0, step=1.0, key=f"{domain}_c2h4")

    g5, g6, g7, _ = st.columns(4)
    g5.markdown("<span style='color:#ef4444;font-size:0.8rem;font-weight:700;'>C2H2★\nACETYLENE</span>", unsafe_allow_html=True)
    c2h2 = g5.number_input("C2H2 ★ ACETYLENE", min_value=0.0, step=0.1, key=f"{domain}_c2h2", label_visibility="collapsed")
    co = g6.number_input("CO\nCARBON MONOXIDE", min_value=0.0, step=1.0, key=f"{domain}_co")
    co2 = g7.number_input("CO2\nCARBON DIOXIDE", min_value=0.0, step=1.0, key=f"{domain}_co2")

    # ── Section: Kualitas Minyak ─────────────────────────────────────────────
    st.markdown("💧 **Kualitas Minyak**")
    mq1, mq2 = st.columns(2)
    water_content = mq1.number_input("WATER CONTENT (ppm)", min_value=0.0, step=0.5, key=f"{domain}_water_content")
    bdv = mq2.number_input("BREAKDOWN VOLTAGE (kV)", min_value=0.0, step=0.5, key=f"{domain}_bdv")

    # ── Action buttons ───────────────────────────────────────────────────────
    st.divider()
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("Reset", key=f"{domain}_reset"):
            for k in [f"{domain}_{x}" for x in ("unit", "equipment_select", "date", "unit_status", "jenis",
                                                   "keterangan", "beban", "temp_oil", "temp_winding",
                                                   "h2", "ch4", "c2h6", "c2h4", "c2h2", "co", "co2",
                                                   "water_content", "bdv")]:
                st.session_state.pop(k, None)
            st.session_state.pop(f"_draft_{domain}", None)
            st.rerun()
    with btn_col2:
        save_clicked = st.button("💾 Simpan DGA", type="primary", key=f"{domain}_save")

    if save_clicked:
        equipment = sel_equipment if isinstance(sel_equipment, str) else str(sel_equipment)
        if not equipment:
            st.error("Equipment tidak boleh kosong.")
            return
        tdcg_final = h2 + ch4 + c2h2 + c2h4 + c2h6 + co + co2
        rows = [
            {"equipment": equipment, "unit_name": sel_unit, "test_date": sel_date, "condition": _tdcg_status(tdcg_final),
             "notes": sel_keterangan, "parameter": p, "value": v}
            for p, v in [
                ("h2", h2), ("ch4", ch4), ("c2h2", c2h2), ("c2h4", c2h4),
                ("c2h6", c2h6), ("co", co), ("co2", co2),
                ("bdv_kv", bdv), ("water_content_ppm", water_content),
                ("beban_mw", beban_mw), ("temp_oil", temp_oil), ("temp_winding", temp_winding),
            ] if v
        ]
        if not rows:
            st.warning("Tidak ada nilai gas yang diisi.")
            return
        result = dm.append_measurements(domain, rows, batch_id="manual")
        if result.get("written"):
            st.success(f"✅ {result['written']} parameter DGA tersimpan untuk {equipment}.")
        for rej in result.get("rejected", []):
            st.error(rej.get("_reason", "Baris ditolak."))


# ---------------------------------------------------------------------------
# Tribologi Input Form
# ---------------------------------------------------------------------------

def render_tribology_input_form(st, default_equipment: Optional[str] = None) -> None:
    """Rich oil analysis form — 'Update Nilai Pengujian' (Tribology)."""
    domain = "TRIBOLOGY"
    equipment_list = _get_equipment_list()

    # ── Header ───────────────────────────────────────────────────────────────
    h_col, scan_col = st.columns([6, 1])
    with h_col:
        st.markdown("### 🛢️ Update Nilai Pengujian")
        st.caption("Input hasil analisa pelumas per equipment.")
    with scan_col:
        _scan_button(st, domain)

    # KPI badges (live from session state)
    visc_live = st.session_state.get(f"{domain}_viscosity", 0.0)
    water_live = st.session_state.get(f"{domain}_water_ppm", 0.0)
    nas_live = st.session_state.get(f"{domain}_nas_class", 0)

    k1, k2, k3 = st.columns(3)
    k1.metric("VISCOSITY", f"{visc_live:.1f} cSt")
    k2.metric("WATER", f"{water_live:.0f} ppm")
    k3.metric("NAS", f"{nas_live:.0f}")

    st.divider()

    # ── General Information ───────────────────────────────────────────────────
    st.markdown("**General Information**")
    r1c1, r1c2 = st.columns(2)
    sel_unit = r1c1.selectbox("UNIT", _UNIT_OPTIONS, key=f"{domain}_unit")
    eq_options = equipment_list if equipment_list else []
    default_idx = 0
    if default_equipment and default_equipment in eq_options:
        default_idx = eq_options.index(default_equipment)
    if eq_options:
        sel_equipment = r1c2.selectbox("EQUIPMENT", eq_options, index=default_idx, key=f"{domain}_equipment")
    else:
        sel_equipment = r1c2.text_input("EQUIPMENT", value=default_equipment or "", key=f"{domain}_equipment")

    r2c1, r2c2 = st.columns(2)
    sel_date = r2c1.date_input("SAMPLE DATE", value=date.today(), key=f"{domain}_date")
    sel_unit_status = r2c2.selectbox("UNIT STATUS", _UNIT_STATUS_OPTIONS, key=f"{domain}_unit_status")

    sel_jenis = st.selectbox("JENIS MONITORING", _JENIS_MONITORING_OPTIONS, key=f"{domain}_jenis")
    sel_keterangan = st.text_area(
        "KETERANGAN",
        placeholder="Contoh: request setelah alarm, sampling rutin bulanan, unit off saat overhaul",
        key=f"{domain}_keterangan",
    )

    # ── Physical Properties ───────────────────────────────────────────────────
    st.markdown("⚙️ **Physical Properties**")
    pp1, pp2, pp3 = st.columns(3)
    viscosity = pp1.number_input("VISCOSITY @ 40C (CST)", min_value=0.0, step=0.1, key=f"{domain}_viscosity")
    oxidation = pp2.number_input("OXIDATION", min_value=0.0, step=0.1, key=f"{domain}_oxidation")
    tan = pp3.number_input("TAN (MG KOH/G)", min_value=0.0, step=0.01, key=f"{domain}_tan")

    st.markdown("💧 **Water Content**")
    wc1, wc2 = st.columns(2)
    water_ppm = wc1.number_input("WATER (PPM)", min_value=0.0, step=1.0, key=f"{domain}_water_ppm")
    total_water = wc2.number_input("TOTAL WATER (PPM)", min_value=0.0, step=1.0, key=f"{domain}_total_water")

    # ── Contamination & Wear Metals ───────────────────────────────────────────
    st.markdown("🧲 **Contamination & Wear Metals**")
    cm1, cm2 = st.columns(2)
    nas_class = cm1.number_input("NAS CLASS", min_value=0, step=1, key=f"{domain}_nas_class")
    iso_code = cm2.text_input("ISO CODE 4406", placeholder="e.g. 17/15/12", key=f"{domain}_iso_code")

    st.markdown("🔩 **Wear Metals (PPM)**")
    wm1, wm2, wm3, wm4 = st.columns(4)
    fe_ppm = wm1.number_input("IRON (FE)", min_value=0.0, step=0.1, key=f"{domain}_fe_ppm")
    cu_ppm = wm2.number_input("COPPER (CU)", min_value=0.0, step=0.1, key=f"{domain}_cu_ppm")
    pb_ppm = wm3.number_input("LEAD (PB)", min_value=0.0, step=0.1, key=f"{domain}_pb_ppm")
    si_ppm = wm4.number_input("SILICON (SI)", min_value=0.0, step=0.1, key=f"{domain}_si_ppm")

    # ── Actions ──────────────────────────────────────────────────────────────
    st.divider()
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("Reset", key=f"{domain}_reset"):
            for k in st.session_state:
                if k.startswith(f"{domain}_"):
                    del st.session_state[k]
            st.rerun()
    with btn_col2:
        save_clicked = st.button("💾 Simpan Oil", type="primary", key=f"{domain}_save")

    if save_clicked:
        equipment = sel_equipment if isinstance(sel_equipment, str) else str(sel_equipment)
        if not equipment:
            st.error("Equipment tidak boleh kosong.")
            return
        param_values = [
            ("viscosity_40c", viscosity), ("oxidation", oxidation), ("tan", tan),
            ("water_ppm", water_ppm), ("total_water_ppm", total_water),
            ("fe_ppm", fe_ppm), ("cu_ppm", cu_ppm), ("pb_ppm", pb_ppm), ("si_ppm", si_ppm),
            ("nas_class", nas_class), ("iso_cleanliness", iso_code),
        ]
        rows = [
            {"equipment": equipment, "unit_name": sel_unit, "test_date": sel_date,
             "condition": "", "notes": sel_keterangan, "parameter": p, "value": v}
            for p, v in param_values if v
        ]
        if not rows:
            st.warning("Tidak ada nilai yang diisi.")
            return
        result = dm.append_measurements(domain, rows, batch_id="manual")
        if result.get("written"):
            st.success(f"✅ {result['written']} parameter tersimpan untuk {equipment}.")
        for rej in result.get("rejected", []):
            st.error(rej.get("_reason", "Baris ditolak."))


# ---------------------------------------------------------------------------
# Vibrasi Input Form
# ---------------------------------------------------------------------------

def render_vibration_input_form(st, default_equipment: Optional[str] = None) -> None:
    """Rich vibration measurement form (12-point + SPM + thermal)."""
    domain = "VIBRASI"
    equipment_list = _get_equipment_list()

    h_col, scan_col = st.columns([6, 1])
    with h_col:
        st.markdown("### 📳 Input Data Vibrasi")
        st.caption("Masukkan hasil pengukuran vibrasi lapangan per titik ukur.")
    with scan_col:
        _scan_button(st, domain)

    # ── General Information ───────────────────────────────────────────────────
    st.markdown("**General Information**")
    r1c1, r1c2 = st.columns(2)
    sel_unit = r1c1.selectbox("UNIT", _UNIT_OPTIONS, key=f"{domain}_unit")
    eq_options = equipment_list or []
    default_idx = 0
    if default_equipment and default_equipment in eq_options:
        default_idx = eq_options.index(default_equipment)
    if eq_options:
        sel_equipment = r1c2.selectbox("EQUIPMENT", eq_options, index=default_idx, key=f"{domain}_equipment")
    else:
        sel_equipment = r1c2.text_input("EQUIPMENT", value=default_equipment or "", key=f"{domain}_equipment")

    r2c1, r2c2 = st.columns(2)
    sel_date = r2c1.date_input("TANGGAL PENGUKURAN", value=date.today(), key=f"{domain}_date")
    sel_unit_status = r2c2.selectbox("UNIT STATUS", _UNIT_STATUS_OPTIONS, key=f"{domain}_unit_status")

    sel_jenis = st.selectbox("JENIS MONITORING", _JENIS_MONITORING_OPTIONS, key=f"{domain}_jenis")
    sel_keterangan = st.text_area("KETERANGAN", key=f"{domain}_keterangan")

    # ── 12-Point Vibration Grid ───────────────────────────────────────────────
    st.markdown("⚡ **Data Vibrasi Overall (mm/s RMS) — ISO 10816-3**")
    st.caption("4 titik bearing × 3 arah (V=Vertikal / H=Horizontal / A=Aksial)")

    points = {}
    bearing_labels = ["Bearing 1 (Motor DE)", "Bearing 2 (Motor NDE)", "Bearing 3 (Driven DE)", "Bearing 4 (Driven NDE)"]
    for b_idx, b_label in enumerate(bearing_labels, start=1):
        st.markdown(f"**{b_label}**")
        vc, hc, ac = st.columns(3)
        v = vc.number_input(f"Titik {b_idx}V (Vertikal)", min_value=0.0, step=0.01, key=f"{domain}_pt{b_idx}v")
        h = hc.number_input(f"Titik {b_idx}H (Horizontal)", min_value=0.0, step=0.01, key=f"{domain}_pt{b_idx}h")
        a = ac.number_input(f"Titik {b_idx}A (Aksial)", min_value=0.0, step=0.01, key=f"{domain}_pt{b_idx}a")
        points[f"pt{b_idx}_v"] = v
        points[f"pt{b_idx}_h"] = h
        points[f"pt{b_idx}_a"] = a

    # Compute and display worst-case zone
    all_vals = [v for v in points.values() if v > 0]
    if all_vals:
        max_val = max(all_vals)
        zone, zone_color = _vib_zone(max_val)
        st.markdown(
            f"<div style='background:{zone_color}22;border:1px solid {zone_color}55;"
            f"padding:8px 14px;border-radius:6px;margin:8px 0;'>"
            f"<strong style='color:{zone_color};'>Zone {zone} (Max: {max_val:.2f} mm/s)</strong>"
            f" — ISO 10816-3 | A:&lt;2.3 | B:&lt;4.5 | C:&lt;7.1 | D:≥7.1</div>",
            unsafe_allow_html=True,
        )

    # ── Shock Pulse ───────────────────────────────────────────────────────────
    with st.expander("🔊 Shock Pulse Meter (dB) — Opsional"):
        spm_vals = {}
        for b_idx in range(1, 5):
            sc1, sc2 = st.columns(2)
            spm_vals[f"sp_max_{b_idx}"] = sc1.number_input(f"Bearing {b_idx} Max (dB)", min_value=0.0, step=0.5, key=f"{domain}_sp_max_{b_idx}")
            spm_vals[f"sp_carpet_{b_idx}"] = sc2.number_input(f"Bearing {b_idx} Carpet (dB)", min_value=0.0, step=0.5, key=f"{domain}_sp_carpet_{b_idx}")

    # ── Temperature ───────────────────────────────────────────────────────────
    with st.expander("🌡️ Suhu (IRT) — Opsional"):
        tc1, tc2, tc3, tc4 = st.columns(4)
        temp_de = tc1.number_input("Bearing DE (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_de")
        temp_nde = tc2.number_input("Bearing NDE (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_nde")
        temp_casing = tc3.number_input("Casing Motor (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_casing")
        temp_ambient = tc4.number_input("Ambient (°C)", min_value=0.0, step=0.5, key=f"{domain}_temp_ambient")

    # ── Actions ──────────────────────────────────────────────────────────────
    st.divider()
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("Reset", key=f"{domain}_reset"):
            for k in list(st.session_state.keys()):
                if k.startswith(f"{domain}_"):
                    del st.session_state[k]
            st.rerun()
    with btn_col2:
        save_clicked = st.button("💾 Simpan Vibrasi", type="primary", key=f"{domain}_save")

    if save_clicked:
        equipment = sel_equipment if isinstance(sel_equipment, str) else str(sel_equipment)
        if not equipment:
            st.error("Equipment tidak boleh kosong.")
            return
        all_params = {**points, **spm_vals, "temperature": temp_de}
        rows = [
            {"equipment": equipment, "unit_name": sel_unit, "test_date": sel_date,
             "condition": "", "notes": sel_keterangan, "parameter": p, "value": v}
            for p, v in all_params.items() if v
        ]
        if not rows:
            st.warning("Tidak ada nilai yang diisi.")
            return
        result = dm.append_measurements(domain, rows, batch_id="manual")
        if result.get("written"):
            st.success(f"✅ {result['written']} titik ukur vibrasi tersimpan untuk {equipment}.")
        for rej in result.get("rejected", []):
            st.error(rej.get("_reason", "Baris ditolak."))


# ---------------------------------------------------------------------------
# Partial Discharge Input Form
# ---------------------------------------------------------------------------

def render_pd_input_form(st, default_equipment: Optional[str] = None) -> None:
    """Rich PD measurement form using Iris Power BusTrac II field layout."""
    domain = "PD"
    equipment_list = _get_equipment_list()

    h_col, scan_col = st.columns([6, 1])
    with h_col:
        st.markdown("### ⚡ Input Data Partial Discharge")
        st.caption("Masukkan hasil pengujian PD per fasa dari BusTrac II / TGA-B.")
    with scan_col:
        _scan_button(st, domain)

    # KPI from session state
    nqn_r = st.session_state.get(f"{domain}_nqn_r", 0.0)
    mag_r = st.session_state.get(f"{domain}_mag_r", 0.0)
    k1, k2, _ = st.columns(3)
    k1.metric("NQN (Fasa R)", f"{nqn_r:.1f}")
    k2.metric("Pulse Magnitude", f"{mag_r:.0f} pC")

    st.divider()

    # ── General Information ───────────────────────────────────────────────────
    st.markdown("**Identitas Pengukuran**")
    r1c1, r1c2 = st.columns(2)
    sel_unit = r1c1.selectbox("UNIT", _UNIT_OPTIONS, key=f"{domain}_unit")
    eq_options = equipment_list or []
    default_idx = 0
    if default_equipment and default_equipment in eq_options:
        default_idx = eq_options.index(default_equipment)
    if eq_options:
        sel_equipment = r1c2.selectbox("EQUIPMENT (Motor/Generator)", eq_options, index=default_idx, key=f"{domain}_equipment")
    else:
        sel_equipment = r1c2.text_input("EQUIPMENT", value=default_equipment or "", key=f"{domain}_equipment")

    r2c1, r2c2 = st.columns(2)
    sel_date = r2c1.date_input("TANGGAL PENGUJIAN", value=date.today(), key=f"{domain}_date")
    sel_unit_status = r2c2.selectbox("UNIT STATUS", _UNIT_STATUS_OPTIONS, key=f"{domain}_unit_status")

    sel_jenis = st.selectbox("JENIS MONITORING", _JENIS_MONITORING_OPTIONS, key=f"{domain}_jenis")
    sel_keterangan = st.text_area("KETERANGAN", key=f"{domain}_keterangan")

    # ── Alat Ukur ────────────────────────────────────────────────────────────
    st.markdown("**Alat Ukur**")
    tool_col1, tool_col2 = st.columns(2)
    sel_tool = tool_col1.selectbox(
        "INSTRUMEN", ["Iris Power BusTrac II", "TGA-B", "PDView Handheld", "Lainnya"],
        key=f"{domain}_tool",
    )
    sel_mode = tool_col2.selectbox(
        "MODE PENGUJIAN", ["Online (Live)", "Offline (Shutdown)"],
        key=f"{domain}_mode",
    )

    # ── PD per Fasa ───────────────────────────────────────────────────────────
    st.markdown("📡 **Data PD per Fasa**")
    _PD_TYPES = ["Normal / No PD", "Corona", "Internal Void", "Surface Tracking", "Noise / Artefak"]

    ph_tabs = st.tabs(["Fasa R", "Fasa S", "Fasa T"])
    phase_data: dict[str, Any] = {}

    for fasa, tab in zip(["r", "s", "t"], ph_tabs):
        with tab:
            fc1, fc2, fc3 = st.columns(3)
            phase_data[f"pulse_magnitude_{fasa}"] = fc1.number_input(
                "Pulse Magnitude (pC)", min_value=0.0, step=1.0, key=f"{domain}_mag_{fasa}"
            )
            phase_data[f"nqn_{fasa}"] = fc2.number_input(
                "NQN", min_value=0.0, step=0.1, key=f"{domain}_nqn_{fasa}"
            )
            phase_data[f"phase_angle_{fasa}"] = fc3.number_input(
                "Phase Angle (deg)", min_value=0.0, max_value=360.0, step=1.0, key=f"{domain}_angle_{fasa}"
            )
            phase_data[f"pd_type_{fasa}"] = st.selectbox(
                "Tipe PD", _PD_TYPES, key=f"{domain}_pd_type_{fasa}"
            )

    # ── PRPD Pattern ──────────────────────────────────────────────────────────
    st.markdown("📊 **PRPD Pattern Assessment**")
    prpd_col1, prpd_col2 = st.columns(2)
    prpd_severity = prpd_col1.selectbox(
        "PRPD Severity", ["None — No Pattern", "Low", "Medium", "High — Urgent"],
        key=f"{domain}_prpd_severity",
    )
    prpd_note = prpd_col2.text_input("Catatan PRPD", key=f"{domain}_prpd_note")

    # ── Actions ──────────────────────────────────────────────────────────────
    st.divider()
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if st.button("Reset", key=f"{domain}_reset"):
            for k in list(st.session_state.keys()):
                if k.startswith(f"{domain}_"):
                    del st.session_state[k]
            st.rerun()
    with btn_col2:
        save_clicked = st.button("💾 Simpan PD", type="primary", key=f"{domain}_save")

    if save_clicked:
        equipment = sel_equipment if isinstance(sel_equipment, str) else str(sel_equipment)
        if not equipment:
            st.error("Equipment tidak boleh kosong.")
            return
        rows = [
            {"equipment": equipment, "unit_name": sel_unit, "test_date": sel_date,
             "condition": prpd_severity, "notes": sel_keterangan + (f" | PRPD: {prpd_note}" if prpd_note else ""),
             "parameter": p, "value": v}
            for p, v in phase_data.items() if v
        ]
        if not rows:
            st.warning("Tidak ada nilai yang diisi.")
            return
        result = dm.append_measurements(domain, rows, batch_id="manual")
        if result.get("written"):
            st.success(f"✅ {result['written']} parameter PD tersimpan untuk {equipment}.")
        for rej in result.get("rejected", []):
            st.error(rej.get("_reason", "Baris ditolak."))

