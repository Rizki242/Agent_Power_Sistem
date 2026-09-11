"""System-wide diagnosis-engine / agent dashboard (default landing page).

Overview: sub-agent roster, fleet health from the latest MCSA snapshot, and
the critical watchlist. Drill-down: per-equipment multi-agent diagnosis built
from measured rows only (missing modalities are never fabricated), showing
per-domain traces, consensus health, RUL, risk, and the draft work order.
"""

from typing import Optional

import pandas as pd

from pple.application.diagnostics import DiagnoseEquipmentUseCase
from pple.application.fleet import FleetReliabilityUseCase
from src.agents.subagent_coordinator import SubAgentCoordinator
from src.components.agent_result import render_agent_result
from src.components.theme import render_page_header

HEALTH_CHIP_COLORS = {
    "HEALTHY": "#10B981",
    "WATCH": "#3B82F6",
    "WARNING": "#F59E0B",
    "ALERT": "#F97316",
    "CRITICAL": "#EF4444",
}

METRIC_LABELS = {
    "overall_rms": "Overall RMS (mm/s)",
    "amp_1x": "1X (mm/s)",
    "amp_2x": "2X (mm/s)",
    "bpfo_amp": "BPFO (mm/s pk)",
    "bpfi_amp": "BPFI (mm/s pk)",
    "axial_1x": "Aksial 1X (mm/s)",
    "max_sideband_db": "Sideband maks (dB)",
    "upper_sideband": "Upper Sideband (dB)",
    "lower_sideband": "Lower Sideband (dB)",
    "dev_current_pct": "Dev Current (%)",
    "dev_voltage_pct": "Dev Voltage (%)",
    "thd_current_pct": "THD Current (%)",
    "bearing_status": "Status bearing",
    "tdcg_ppm": "TDCG (ppm)",
    "h2_ppm": "H2 (ppm)",
    "ch4_ppm": "CH4 (ppm)",
    "c2h2_ppm": "C2H2 (ppm)",
    "c2h4_ppm": "C2H4 (ppm)",
    "c2h6_ppm": "C2H6 (ppm)",
    "co_ppm": "CO (ppm)",
    "co2_ppm": "CO2 (ppm)",
    "duval_zone": "Zona Duval",
    "pulse_magnitude_pc": "Pulse magnitude (pC)",
    "nqn": "NQN",
    "pd_type": "Tipe PD",
    "phase_clustering_deg": "Phase clustering (deg)",
    "viscosity_40c": "Viskositas 40°C (cSt)",
    "viscosity_dev_pct": "Deviasi viskositas (%)",
    "tan_mgkoh_g": "TAN (mg KOH/g)",
    "water_ppm": "Air (ppm)",
    "fe_ppm": "Fe (ppm)",
    "cu_ppm": "Cu (ppm)",
    "iso_cleanliness": "ISO cleanliness",
    "bearing_temp_c": "Suhu bearing (°C)",
    "winding_temp_c": "Suhu winding (°C)",
    "delta_t_ambient_c": "Delta-T ambient (°C)",
    "delta_t_phase_c": "Delta-T phase (°C)",
    "hotspot_temp_c": "Hotspot (°C)",
}

FLEET_COLUMNS = {
    "equipment": "Equipment",
    "unit": "Unit",
    "system": "Sistem",
    "criticality": "Kritisitas",
    "health_index": "Health Index",
    "health_status": "Status",
    "primary_failure_mode": "Failure Mode",
    "severity": "Severity",
    "rul_days": "RUL",
    "risk_level": "Risiko",
}

_coordinator: Optional[SubAgentCoordinator] = None


def _get_coordinator() -> SubAgentCoordinator:
    global _coordinator
    if _coordinator is None:
        _coordinator = SubAgentCoordinator()
    return _coordinator


def _render_health_chips(st, summary: dict) -> None:
    chips = []
    for label in ("HEALTHY", "WATCH", "WARNING", "ALERT", "CRITICAL"):
        count = int(summary.get(label, 0))
        color = HEALTH_CHIP_COLORS[label]
        chips.append(
            f'<span style="display:inline-block;margin:2px 8px 2px 0;padding:3px 10px;border-radius:999px;'
            f'background:{color}1A;color:{color};font-weight:700;border:1px solid {color}55;">'
            f"{label}: {count}</span>"
        )
    st.markdown("".join(chips), unsafe_allow_html=True)


def _render_fleet_table(st, assets: list) -> None:
    if not assets:
        st.info("Tidak ada aset pada status WARNING/ALERT/CRITICAL.")
        return
    display_df = pd.DataFrame(assets)[list(FLEET_COLUMNS.keys())].rename(columns=FLEET_COLUMNS)
    st.dataframe(
        display_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Health Index": st.column_config.ProgressColumn("Health Index", min_value=0, max_value=100, format="%.1f"),
        },
    )


def _render_roster(st, specialists: list) -> None:
    roster_rows = [
        {
            "Agen": f"{s.get('icon', '')} {s.get('name', '-')}",
            "Domain": s.get("domain", "-"),
            "Peran": s.get("role", "-"),
            "Status": s.get("status", "-"),
        }
        for s in specialists
    ]
    st.dataframe(roster_rows, hide_index=True, width="stretch")


def _run_equipment_diagnosis(coordinator: SubAgentCoordinator, df_latest_all: pd.DataFrame, equipment: str) -> dict:
    use_case = DiagnoseEquipmentUseCase(
        fusion_agent=coordinator.fusion_agent,
        asset_graph=coordinator.asset_graph,
    )
    safety = coordinator.safety_guard.check_safety(f"Diagnosa {equipment}")
    fusion_res = use_case.diagnose_from_mcsa_dataset(
        equipment=equipment,
        df_latest=df_latest_all,
    )
    return {
        "fusion": fusion_res,
        "safety": safety,
        "data_sources": fusion_res.get("data_sources", []),
    }


def render_agent_dashboard_page(st, df_latest_all: pd.DataFrame, mcsa_page=None) -> None:
    render_page_header(st, "Agent Dashboard", "Diagnosis engine multi-agen - overview sistem secara keseluruhan.")
    coordinator = _get_coordinator()
    data_key = st.session_state.get("_mcsa_data_key")

    fleet = st.session_state.get("_agent_fleet_result")
    if fleet is None or st.session_state.get("_agent_fleet_key") != data_key:
        fleet_use_case = FleetReliabilityUseCase(
            fusion_agent=coordinator.fusion_agent,
            asset_graph=coordinator.asset_graph,
        )
        fleet = fleet_use_case.get_fleet_summary(df_latest_all)
        st.session_state["_agent_fleet_key"] = data_key
        st.session_state["_agent_fleet_result"] = fleet

    specialists = coordinator.list_specialists()

    st.subheader("Overview Sistem", anchor=False)
    st.caption("Basis data: snapshot MCSA terbaru per equipment. Seluruh diagnosis bersifat rule-based.")
    metric_cols = st.columns(4)
    metric_cols[0].metric("Total Aset", fleet.get("total_assets", 0))
    metric_cols[1].metric("Fleet Health", f"{fleet.get('fleet_health_average', 0):.0f}/100")
    metric_cols[2].metric("Watchlist", len(fleet.get("critical_watchlist", [])))
    metric_cols[3].metric("Agen Online", len(specialists))
    _render_health_chips(st, fleet.get("health_summary") or {})

    st.subheader("Sub-Agent Specialist", anchor=False)
    _render_roster(st, specialists)

    st.subheader("Fleet Health Matrix", anchor=False)
    st.caption("Diurutkan dari health index terendah. Klik equipment untuk melihat diagnosis pada bagian bawah.")
    _render_fleet_table(st, fleet.get("asset_matrix", []))

    st.subheader("Critical Watchlist", anchor=False)
    _render_fleet_table(st, fleet.get("critical_watchlist", []))

    st.subheader("Diagnosis Multi-Agent per Equipment", anchor=False)
    eq_options = [a.get("equipment") for a in fleet.get("asset_matrix", []) if a.get("equipment")]
    if not eq_options:
        st.info("Tidak ada data equipment untuk diagnosis multi-agent.")
        return
    sel_eq = st.selectbox(
        "Pilih equipment",
        eq_options,
        key="agent_diag_equipment",
        help="Urutan mengikuti fleet matrix (health index terendah lebih dulu).",
    )

    diag_cache = st.session_state.get("_agent_diag_cache")
    if not isinstance(diag_cache, dict) or diag_cache.get("_key") != data_key:
        diag_cache = {"_key": data_key}
        st.session_state["_agent_diag_cache"] = diag_cache
    if sel_eq not in diag_cache:
        diag_cache[sel_eq] = _run_equipment_diagnosis(coordinator, df_latest_all, sel_eq)
    diag = diag_cache[sel_eq]

    fusion_res = diag["fusion"]
    safety = diag["safety"]

    if safety.get("safe"):
        st.success(f"Safety clearance: {safety.get('message', 'Diagnosa aman dijalankan')} - tidak ada aksi otonom terhadap peralatan.", icon=":material/verified_user:")
    else:
        st.error(f"Safety guard: {safety.get('message', '-')}")

    diagnosis = fusion_res.get("failure_mode_diagnosis", {})
    consensus_cols = st.columns(4)
    consensus_cols[0].metric("Health Index", f"{fusion_res.get('health_index', 0):.0f}/100")
    consensus_cols[1].metric("Status", fusion_res.get("health_status", "-"))
    consensus_cols[2].metric("Failure Mode", diagnosis.get("primary_failure_mode", "-"))
    consensus_cols[3].metric("Confidence", f"{diagnosis.get('confidence', 0):.0%}")

    evaluations = fusion_res.get("specialist_evaluations", {})
    st.markdown("**Hasil evaluasi sub-agent (modalitas terukur saja)**")
    st.caption("Sumber data: " + (", ".join(diag.get("data_sources", [])) or "tidak ada") + ". Domain tanpa data tidak dievaluasi dan tidak diberi skor fabrikasi.")
    if not evaluations:
        st.info("Tidak ada modalitas data terukur untuk equipment ini pada snapshot terbaru.")
    for domain, result in evaluations.items():
        st.markdown(f"**{domain}**")
        render_agent_result(st, result, METRIC_LABELS)

    rul = fusion_res.get("predictive_rul", {})
    risk = fusion_res.get("risk_assessment", {})
    decision = fusion_res.get("maintenance_decision", {})
    outcome_cols = st.columns(4)
    outcome_cols[0].metric("RUL", rul.get("estimated_rul_days", "-"))
    outcome_cols[1].metric("Prob. Gagal 30 Hari", f"{rul.get('failure_probability_30d', 0):.0%}")
    outcome_cols[2].metric("Risiko", risk.get("risk_level", "-"))
    outcome_cols[3].metric("Prioritas", decision.get("priority", "-"))

    fused_evidence = diagnosis.get("fused_evidence", [])
    if fused_evidence:
        with st.expander("Bukti gabungan (fused evidence)", expanded=False):
            for item in fused_evidence:
                st.write(f"- {item}")

    root_causes = diagnosis.get("root_causes", [])
    mitigations = diagnosis.get("mitigation_recommendations", [])
    if root_causes or mitigations:
        with st.expander("Akar penyebab & mitigasi", expanded=False):
            for item in root_causes:
                st.write(f"- {item}")
            for item in mitigations:
                st.write(f"- {item}")

    work_order = decision.get("work_order", {})
    if work_order:
        with st.expander(f"Draft Work Order - {work_order.get('wo_number', '')}", expanded=False):
            st.write(f"**Judul:** {work_order.get('title', '-')}")
            st.write(f"**Alasan:** {work_order.get('reason', '-')}")
            st.write(f"**Target penyelesaian:** {work_order.get('target_completion_date', '-')}")
            st.write(f"**Status:** {work_order.get('status', '-')}")

    st.caption("Seluruh hasil adalah diagnosis rule-based. Keputusan operasi, trip, shutdown, atau perubahan proteksi wajib melalui SOP dan otorisasi engineer (human-in-the-loop).")

    if mcsa_page is not None:
        if st.button("Buka detail MCSA", icon=":material/electric_bolt:"):
            st.switch_page(mcsa_page)
