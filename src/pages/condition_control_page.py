"""Streamlit controls for rule-based vibration, DGA, tribology, thermal, and partial discharge screening."""

from __future__ import annotations

import streamlit as st
from src.agents.specialist_agents import DGAAgent, PDAgent, ThermalAgent, TribologyAgent, VibrationAgent
from src.components.agent_result import render_agent_result
from src.components.theme import render_page_header


@st.fragment
def _render_vibration_control(st_context=st) -> None:
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
        st.session_state["condition_control_vibration_result"] = VibrationAgent().evaluate(
            equipment.strip() or "Motor/Pompa",
            {"overall_rms": overall_rms, "amp_1x": amp_1x, "amp_2x": amp_2x, "axial_1x": axial_1x, "bpfo_amp": bpfo, "bpfi_amp": bpfi}
        )
    result = st.session_state.get("condition_control_vibration_result")
    if result:
        render_agent_result(
            st, result, {"overall_rms": "Overall RMS (mm/s)", "amp_1x": "1X (mm/s)", "amp_2x": "2X (mm/s)", "bpfo_amp": "BPFO (mm/s pk)", "bpfi_amp": "BPFI (mm/s pk)", "axial_1x": "Aksial 1X (mm/s)"}
        )


@st.fragment
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
        st.session_state["condition_control_dga_result"] = DGAAgent().evaluate(
            equipment.strip() or "Main Transformer",
            {"h2": h2, "ch4": ch4, "c2h2": c2h2, "c2h4": c2h4, "c2h6": c2h6, "co": co, "co2": co2}
        )
    result = st.session_state.get("condition_control_dga_result")
    if result:
        render_agent_result(
            st, result, {"tdcg_ppm": "TDCG (ppm)", "h2_ppm": "H2 (ppm)", "ch4_ppm": "CH4 (ppm)", "c2h2_ppm": "C2H2 (ppm)", "c2h4_ppm": "C2H4 (ppm)", "c2h6_ppm": "C2H6 (ppm)", "co_ppm": "CO (ppm)", "co2_ppm": "CO2 (ppm)", "duval_zone": "Zona diagnosis"}
        )


@st.fragment
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
        st.session_state["condition_control_tribology_result"] = TribologyAgent().evaluate(
            equipment.strip() or "Pompa/gearbox",
            {"viscosity_40c": viscosity, "nominal_viscosity": nominal, "tan": tan, "water_ppm": water, "fe_ppm": fe, "cu_ppm": cu, "iso_cleanliness": iso_cleanliness.strip() or "-"}
        )
    result = st.session_state.get("condition_control_tribology_result")
    if result:
        render_agent_result(
            st, result, {"viscosity_40c": "Viskositas 40°C (cSt)", "viscosity_dev_pct": "Deviasi viskositas (%)", "tan_mgkoh_g": "TAN (mg KOH/g)", "water_ppm": "Air (ppm)", "fe_ppm": "Fe (ppm)", "cu_ppm": "Cu (ppm)", "iso_cleanliness": "ISO cleanliness"}
        )


@st.fragment
def _render_thermal_control(st) -> None:
    st.subheader("Thermal", anchor=False)
    st.caption("Screening delta-T ambient, delta-T antar fasa, dan hotspot komparatif.")
    with st.form("condition_control_thermal", border=True):
        equipment = st.text_input("Equipment", value="Motor Feeder 1A", key="control_thermal_equipment")
        cols = st.columns(3)
        bearing_temp = cols[0].number_input("Suhu Bearing (°C)", min_value=0.0, value=65.0, step=0.5, key="control_thermal_bearing")
        winding_temp = cols[1].number_input("Suhu Winding (°C)", min_value=0.0, value=75.0, step=0.5, key="control_thermal_winding")
        hotspot_temp = cols[2].number_input("Suhu Hotspot (°C)", min_value=0.0, value=82.0, step=0.5, key="control_thermal_hotspot")
        cols2 = st.columns(2)
        delta_t_amb = cols2[0].number_input("Delta-T Ambient (ΔT1 °C)", min_value=0.0, value=15.0, step=0.5, key="control_thermal_dt_amb")
        delta_t_ph = cols2[1].number_input("Delta-T Antar Fasa (ΔT2 °C)", min_value=0.0, value=4.5, step=0.5, key="control_thermal_dt_ph")
        submitted = st.form_submit_button("Analisis Thermal", type="primary", icon=":material/thermostat:", width="stretch")
    if submitted:
        st.session_state["condition_control_thermal_result"] = ThermalAgent().evaluate(
            equipment.strip() or "Motor",
            {
                "bearing_temp_c": bearing_temp,
                "winding_temp_c": winding_temp,
                "hotspot_temp_c": hotspot_temp,
                "delta_t_ambient_c": delta_t_amb,
                "delta_t_phase_c": delta_t_ph,
            },
        )
    result = st.session_state.get("condition_control_thermal_result")
    if result:
        render_agent_result(
            st,
            result,
            {
                "bearing_temp_c": "Suhu Bearing (°C)",
                "winding_temp_c": "Suhu Winding (°C)",
                "hotspot_temp_c": "Suhu Hotspot (°C)",
                "delta_t_ambient_c": "Delta-T Ambient (°C)",
                "delta_t_phase_c": "Delta-T Antar Fasa (°C)",
            },
        )


@st.fragment
def _render_pd_control(st) -> None:
    st.subheader("Partial Discharge", anchor=False)
    st.caption("Screening magnitude pulsa, NQN, dan tipe pelepasan parsial isolasi.")
    with st.form("condition_control_pd", border=True):
        equipment = st.text_input("Equipment", value="Generator 1", key="control_pd_equipment")
        cols = st.columns(2)
        pulse_mag = cols[0].number_input("Pulse Magnitude (pC)", min_value=0.0, value=350.0, step=10.0, key="control_pd_mag")
        nqn = cols[1].number_input("Normalized Quantity Number (NQN)", min_value=0.0, value=45.0, step=1.0, key="control_pd_nqn")
        cols2 = st.columns(2)
        pd_type = cols2[0].selectbox("Tipe Discharge", ["Internal Void", "Slot Discharge", "Surface Discharge", "Corona"], key="control_pd_type")
        phase_clustering = cols2[1].number_input("Phase Clustering (deg)", min_value=0.0, max_value=360.0, value=45.0, step=5.0, key="control_pd_phase")
        submitted = st.form_submit_button("Analisis Partial Discharge", type="primary", icon=":material/bolt:", width="stretch")
    if submitted:
        st.session_state["condition_control_pd_result"] = PDAgent().evaluate(
            equipment.strip() or "Generator",
            {
                "pulse_magnitude_pc": pulse_mag,
                "nqn": nqn,
                "pd_type": pd_type,
                "phase_clustering_deg": phase_clustering,
            },
        )
    result = st.session_state.get("condition_control_pd_result")
    if result:
        render_agent_result(
            st,
            result,
            {
                "pulse_magnitude_pc": "Pulse Magnitude (pC)",
                "nqn": "NQN",
                "pd_type": "Tipe Discharge",
                "phase_clustering_deg": "Phase Clustering (deg)",
            },
        )


def render_condition_control_page(st) -> None:
    """Render manual, non-actuating controls for all 5 CBM specialist domains."""
    render_page_header(st, "Engineering", "Control condition - rule-based screening multi-domain PdM.")
    st.write("Masukkan data pengukuran untuk screening rule-based pada domain yang dipilih.")
    st.info("Pastikan data berasal dari pengukuran atau sampel yang valid dan comparable. Halaman ini tidak mengirim perintah ke peralatan pembangkit.", icon=":material/verified_user:")
    vibration_tab, dga_tab, tribology_tab, thermal_tab, pd_tab = st.tabs(
        ["Vibrasi", "DGA", "Tribology", "Thermal", "Partial Discharge"]
    )
    with vibration_tab:
        _render_vibration_control(st)
    with dga_tab:
        _render_dga_control(st)
    with tribology_tab:
        _render_tribology_control(st)
    with thermal_tab:
        _render_thermal_control(st)
    with pd_tab:
        _render_pd_control(st)
