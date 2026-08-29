"""Streamlit controls for rule-based vibration, DGA, and tribology screening."""

from __future__ import annotations

from typing import Any, Dict

from src.agents.specialist_agents import DGAAgent, TribologyAgent, VibrationAgent


def _render_result(st, result: Dict[str, Any], metric_labels: Dict[str, str]) -> None:
    """Render a standard specialist-agent result without unsafe actuation."""
    severity = int(result.get("severity", 1))
    condition = str(result.get("condition", "HEALTHY"))
    confidence = float(result.get("confidence", 0.0))
    health_score = float(result.get("health_score", 0.0))

    with st.container(border=True):
        metric_cols = st.columns(3)
        metric_cols[0].metric("Status", condition)
        metric_cols[1].metric("Health score", f"{health_score:.0f}/100")
        metric_cols[2].metric("Confidence", f"{confidence:.0%}")
        if severity >= 4:
            st.error(f"Severity {severity}: {result.get('failure_mode', '-')}")
        elif severity >= 3:
            st.warning(f"Severity {severity}: {result.get('failure_mode', '-')}")
        elif severity >= 2:
            st.info(f"Severity {severity}: {result.get('failure_mode', '-')}")
        else:
            st.success(f"Severity {severity}: {result.get('failure_mode', '-')}")
        evidence = result.get("evidence") or []
        if evidence:
            st.markdown("**Bukti rule-based**")
            for item in evidence:
                st.write(f"- {item}")
        recommendations = result.get("recommendation") or []
        if recommendations:
            st.markdown("**Rekomendasi tindak lanjut**")
            for item in recommendations:
                st.write(f"- {item}")
        with st.expander("Parameter yang dianalisis", expanded=False):
            rows = [{"Parameter": metric_labels.get(key, key), "Nilai": value} for key, value in (result.get("metrics") or {}).items()]
            st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Hasil adalah screening rule-based. Keputusan operasi, trip, shutdown, atau perubahan proteksi wajib melalui SOP dan otorisasi engineer.")


def _render_vibration_control(st) -> None:
    st.subheader("Vibrasi", anchor=False)
    st.caption("Screening overall RMS, 1X/2X, aksial, BPFO, dan BPFI.")
    with st.form("condition_control_vibration", border=True):
        equipment = st.text_input("Equipment", value="Motor/Pompa", key="control_vibration_equipment")
        col_a, col_b, col_c = st.columns(3)
        overall_rms = col_a.number_input("Overall RMS (mm/s)", min_value=0.0, value=2.2, step=0.1, key="control_vibration_rms")
        amp_1x = col_b.number_input("Amplitudo 1X (mm/s)", min_value=0.0, value=1.2, step=0.1, key="control_vibration_1x")
        amp_2x = col_c.number_input("Amplitudo 2X (mm/s)", min_value=0.0, value=0.6, step=0.1, key="control_vibration_2x")
        col_d, col_e, col_f = st.columns(3)
        axial_1x = col_d.number_input("Aksial 1X (mm/s)", min_value=0.0, value=0.5, step=0.1, key="control_vibration_axial")
        bpfo = col_e.number_input("BPFO (mm/s pk)", min_value=0.0, value=0.0, step=0.1, key="control_vibration_bpfo")
        bpfi = col_f.number_input("BPFI (mm/s pk)", min_value=0.0, value=0.0, step=0.1, key="control_vibration_bpfi")
        submitted = st.form_submit_button("Analisis vibrasi", type="primary", icon=":material/vibration:", width="stretch")
    if submitted:
        st.session_state["condition_control_vibration_result"] = VibrationAgent().evaluate(equipment.strip() or "Motor/Pompa", {"overall_rms": overall_rms, "amp_1x": amp_1x, "amp_2x": amp_2x, "axial_1x": axial_1x, "bpfo_amp": bpfo, "bpfi_amp": bpfi})
    result = st.session_state.get("condition_control_vibration_result")
    if result:
        _render_result(st, result, {"overall_rms": "Overall RMS (mm/s)", "amp_1x": "1X (mm/s)", "amp_2x": "2X (mm/s)", "bpfo_amp": "BPFO (mm/s pk)", "bpfi_amp": "BPFI (mm/s pk)", "axial_1x": "Aksial 1X (mm/s)"})


def _render_dga_control(st) -> None:
    st.subheader("DGA", anchor=False)
    st.caption("Screening TDCG dan pola key gas/Duval dari sampel gas terlarut yang valid.")
    with st.form("condition_control_dga", border=True):
        equipment = st.text_input("Transformer", value="Main Transformer", key="control_dga_equipment")
        cols = st.columns(4)
        h2 = cols[0].number_input("H2 (ppm)", min_value=0.0, value=15.0, step=0.1, key="control_dga_h2")
        ch4 = cols[1].number_input("CH4 (ppm)", min_value=0.0, value=25.0, step=0.1, key="control_dga_ch4")
        c2h2 = cols[2].number_input("C2H2 (ppm)", min_value=0.0, value=0.5, step=0.1, key="control_dga_c2h2")
        c2h4 = cols[3].number_input("C2H4 (ppm)", min_value=0.0, value=12.0, step=0.1, key="control_dga_c2h4")
        cols = st.columns(3)
        c2h6 = cols[0].number_input("C2H6 (ppm)", min_value=0.0, value=18.0, step=0.1, key="control_dga_c2h6")
        co = cols[1].number_input("CO (ppm)", min_value=0.0, value=250.0, step=1.0, key="control_dga_co")
        co2 = cols[2].number_input("CO2 (ppm)", min_value=0.0, value=2200.0, step=1.0, key="control_dga_co2")
        submitted = st.form_submit_button("Analisis DGA", type="primary", icon=":material/science:", width="stretch")
    if submitted:
        st.session_state["condition_control_dga_result"] = DGAAgent().evaluate(equipment.strip() or "Main Transformer", {"h2": h2, "ch4": ch4, "c2h2": c2h2, "c2h4": c2h4, "c2h6": c2h6, "co": co, "co2": co2})
    result = st.session_state.get("condition_control_dga_result")
    if result:
        _render_result(st, result, {"tdcg_ppm": "TDCG (ppm)", "h2_ppm": "H2 (ppm)", "ch4_ppm": "CH4 (ppm)", "c2h2_ppm": "C2H2 (ppm)", "c2h4_ppm": "C2H4 (ppm)", "c2h6_ppm": "C2H6 (ppm)", "co_ppm": "CO (ppm)", "co2_ppm": "CO2 (ppm)", "duval_zone": "Zona diagnosis"})


def _render_tribology_control(st) -> None:
    st.subheader("Tribology", anchor=False)
    st.caption("Screening kondisi pelumas, kontaminasi air, dan wear debris.")
    with st.form("condition_control_tribology", border=True):
        equipment = st.text_input("Equipment", value="Pompa/gearbox", key="control_tribology_equipment")
        cols = st.columns(3)
        viscosity = cols[0].number_input("Viskositas 40°C (cSt)", min_value=0.0, value=46.0, step=0.1, key="control_tribology_viscosity")
        nominal = cols[1].number_input("Viskositas nominal (cSt)", min_value=0.1, value=46.0, step=0.1, key="control_tribology_nominal")
        tan = cols[2].number_input("TAN (mg KOH/g)", min_value=0.0, value=0.15, step=0.01, format="%.2f", key="control_tribology_tan")
        cols = st.columns(4)
        water = cols[0].number_input("Air (ppm)", min_value=0.0, value=45.0, step=1.0, key="control_tribology_water")
        fe = cols[1].number_input("Fe (ppm)", min_value=0.0, value=12.0, step=1.0, key="control_tribology_fe")
        cu = cols[2].number_input("Cu (ppm)", min_value=0.0, value=3.0, step=1.0, key="control_tribology_cu")
        iso_cleanliness = cols[3].text_input("ISO cleanliness", value="16/14/11", key="control_tribology_iso")
        submitted = st.form_submit_button("Analisis tribology", type="primary", icon=":material/oil_barrel:", width="stretch")
    if submitted:
        st.session_state["condition_control_tribology_result"] = TribologyAgent().evaluate(equipment.strip() or "Pompa/gearbox", {"viscosity_40c": viscosity, "nominal_viscosity": nominal, "tan": tan, "water_ppm": water, "fe_ppm": fe, "cu_ppm": cu, "iso_cleanliness": iso_cleanliness.strip() or "-"})
    result = st.session_state.get("condition_control_tribology_result")
    if result:
        _render_result(st, result, {"viscosity_40c": "Viskositas 40°C (cSt)", "viscosity_dev_pct": "Deviasi viskositas (%)", "tan_mgkoh_g": "TAN (mg KOH/g)", "water_ppm": "Air (ppm)", "fe_ppm": "Fe (ppm)", "cu_ppm": "Cu (ppm)", "iso_cleanliness": "ISO cleanliness"})


def render_condition_control_page(st) -> None:
    """Render manual, non-actuating controls for three CBM specialist domains."""
    st.header("Control condition", anchor=False)
    st.write("Masukkan data pengukuran untuk screening rule-based pada domain yang dipilih.")
    st.info("Pastikan data berasal dari pengukuran atau sampel yang valid dan comparable. Halaman ini tidak mengirim perintah ke peralatan pembangkit.", icon=":material/verified_user:")
    vibration_tab, dga_tab, tribology_tab = st.tabs(["Vibrasi", "DGA", "Tribology"])
    with vibration_tab:
        _render_vibration_control(st)
    with dga_tab:
        _render_dga_control(st)
    with tribology_tab:
        _render_tribology_control(st)
