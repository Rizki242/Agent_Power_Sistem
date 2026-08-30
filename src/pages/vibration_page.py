"""Vibration dashboard - asset register + periodic overall-velocity readings."""

from src.agents.specialist_agents import VibrationAgent
from src.components.agent_result import render_agent_result
from src.components.status_colors import (
    STATUS_PIE_COLORS,
    canon_condition_status,
    render_status_badge,
)
from src.components.theme import render_page_header
from src.vibration_data import (
    build_vibration_agent_input,
    get_bearing_info,
    latest_cbmai_vibration_record,
    load_cbmai_vibration_dataset,
    load_vibration_assets,
    load_vibration_monthly_tests,
    match_monthly_test_by_equipment,
)


def render_vibration_page(st) -> None:
    render_page_header(st, "Vibrasi", "Monitoring kondisi vibrasi aset berputar - ISO 10816-3", badge="")

    assets_df = load_vibration_assets()
    monthly_tests = load_vibration_monthly_tests()

    if assets_df.empty:
        st.warning("Data aset vibrasi tidak tersedia.")
        return

    assets_df = assets_df.copy()
    assets_df["_status_canon"] = assets_df["status_vibrasi"].map(canon_condition_status)

    # --- KPI cards ---------------------------------------------------------
    counts = assets_df["_status_canon"].value_counts()
    cols = st.columns(5)
    cols[0].metric("Total Aset", len(assets_df))
    cols[1].metric("Normal (Hijau)", int(counts.get("Normal", 0)))
    cols[2].metric("Standby", int(counts.get("Standby", 0)))
    cols[3].metric("Alarm (Kuning)", int(counts.get("Alarm", 0)), delta_color="inverse")
    cols[4].metric("High (Merah)", int(counts.get("High", 0)), delta_color="inverse")

    # --- Pie chart -----------------------------------------------------------
    import plotly.express as px

    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = counts.reindex(plot_order, fill_value=0).reset_index()
    plot_df.columns = ["Status", "Count"]
    plot_df = plot_df[plot_df["Count"] > 0]
    if not plot_df.empty:
        fig = px.pie(
            plot_df, names="Status", values="Count", title="Status Aset Vibrasi",
            color="Status", color_discrete_map=STATUS_PIE_COLORS,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, width="stretch")

    # --- Filter + selector ---------------------------------------------------
    units = ["All"] + sorted(assets_df["unit_group"].dropna().unique().tolist())
    sel_unit = st.selectbox("Unit", units, key="vibration_unit_filter")
    scoped_df = assets_df if sel_unit == "All" else assets_df[assets_df["unit_group"] == sel_unit]

    if scoped_df.empty:
        st.info("Tidak ada aset pada unit ini.")
        return

    equipment_options = scoped_df["equipment"].tolist()
    if st.session_state.get("vibration_selected_asset") not in equipment_options:
        st.session_state["vibration_selected_asset"] = equipment_options[0]
    selected_equipment = st.selectbox("Pilih Aset:", equipment_options, key="vibration_selected_asset")

    asset_row = scoped_df[scoped_df["equipment"] == selected_equipment].iloc[0]
    status = canon_condition_status(asset_row.get("status_vibrasi"))
    render_status_badge(st, selected_equipment, status)
    st.caption(f"**Asset ID:** {asset_row.get('asset_id', '-')} | **Unit:** {asset_row.get('unit_group', '-')}")

    detail_view = st.radio("Tampilan Detail", ["Ringkasan", "Rekomendasi"], horizontal=True, key="vibration_detail_view")

    matched_record = match_monthly_test_by_equipment(selected_equipment, monthly_tests)

    if detail_view == "Ringkasan":
        bearing_info = get_bearing_info(asset_row.get("asset_id", ""))
        if bearing_info:
            st.markdown("**Informasi Bearing**")
            st.dataframe(
                [{"Parameter": k, "Nilai": v} for k, v in bearing_info.items() if v],
                hide_index=True, width="stretch",
            )
        if matched_record:
            st.markdown("**Pengujian Periodik Terakhir**")
            cols = st.columns(3)
            cols[0].metric("Velocity Max (mm/s)", matched_record.get("velocity_max", "-"))
            cols[1].metric("ISO Group", matched_record.get("iso_group", "-"))
            cols[2].metric("Tanggal Uji", matched_record.get("test_date", "-"))
            points = matched_record.get("points") or {}
            if points:
                st.dataframe(
                    [{"Titik": k, "Velocity (mm/s)": v} for k, v in points.items()],
                    hide_index=True, width="stretch",
                )
        else:
            st.info("Data pengujian periodik belum tersedia/tidak cocok untuk aset ini.")

        cbmai_df = load_cbmai_vibration_dataset()
        if not cbmai_df.empty:
            st.markdown("**Dataset Vibrasi CBMAI**")
            equipment_ids = sorted(cbmai_df["equipment_id"].astype(str).unique().tolist())
            selected_cbmai_id = st.selectbox(
                "Pilih equipment ID CBMAI:",
                equipment_ids,
                key="vibration_cbmai_equipment_id",
            )
            scoped = cbmai_df[cbmai_df["equipment_id"].astype(str) == selected_cbmai_id].copy()
            latest = latest_cbmai_vibration_record(selected_cbmai_id) or {}
            cols = st.columns(4)
            cols[0].metric("Record CBMAI", len(scoped))
            cols[1].metric("Velocity Terakhir (mm/s)", latest.get("velocity_rms_mm_s", "-"))
            cols[2].metric("Severity Terakhir", latest.get("overall_severity", "-"))
            cols[3].metric("Confidence", latest.get("diagnosis_confidence", "-"))
            trend_fig = px.line(
                scoped,
                x="timestamp",
                y=["velocity_rms_mm_s", "acceleration_rms_g", "temperature_c"],
                color_discrete_sequence=["#2563eb", "#dc2626", "#f59e0b"],
                markers=True,
                title=f"Trend Vibrasi CBMAI - {selected_cbmai_id}",
            )
            trend_fig.update_layout(height=380, margin=dict(l=10, r=10, t=45, b=10), legend_title_text="Parameter")
            st.plotly_chart(trend_fig, width="stretch")
            latest_rows = scoped.sort_values("timestamp", ascending=False).head(20)
            st.dataframe(
                latest_rows[[
                    "timestamp", "equipment_id", "equipment_type", "condition",
                    "velocity_rms_mm_s", "acceleration_rms_g", "temperature_c",
                    "1x_amp_mm_s", "2x_amp_mm_s", "bpfo_amp_g", "bpfi_amp_g",
                    "overall_severity", "diagnosis_confidence",
                ]],
                hide_index=True,
                width="stretch",
            )

    elif detail_view == "Rekomendasi":
        if matched_record:
            agent_input = build_vibration_agent_input(matched_record)
            result = VibrationAgent().evaluate(selected_equipment, agent_input)
            render_agent_result(st, result, {"overall_rms": "Overall RMS (mm/s)"})
            st.caption(
                "Skor berdasarkan Overall RMS terukur; parameter spektral (1X/2X/BPFO/BPFI) "
                "belum tersedia dari sumber data dan menggunakan asumsi standar VibrationAgent."
            )
        else:
            cbmai_df = load_cbmai_vibration_dataset()
            if cbmai_df.empty:
                st.info("Data pengujian belum tersedia untuk aset ini - rekomendasi tidak dapat dihitung.")
            else:
                equipment_ids = sorted(cbmai_df["equipment_id"].astype(str).unique().tolist())
                selected_cbmai_id = st.selectbox(
                    "Pilih equipment ID CBMAI untuk analisa:",
                    equipment_ids,
                    key="vibration_cbmai_reco_equipment_id",
                )
                latest = latest_cbmai_vibration_record(selected_cbmai_id) or {}
                agent_input = {
                    "overall_rms": latest.get("velocity_rms_mm_s", 0.0),
                    "amp_1x": latest.get("1x_amp_mm_s", 0.0),
                    "amp_2x": latest.get("2x_amp_mm_s", 0.0),
                    "bpfo_amp": latest.get("bpfo_amp_g", 0.0),
                    "bpfi_amp": latest.get("bpfi_amp_g", 0.0),
                }
                result = VibrationAgent().evaluate(selected_cbmai_id, agent_input)
                render_agent_result(st, result, {
                    "overall_rms": "Overall RMS (mm/s)",
                    "amp_1x": "1X amplitude (mm/s)",
                    "amp_2x": "2X amplitude (mm/s)",
                    "bpfo_amp": "BPFO amplitude",
                    "bpfi_amp": "BPFI amplitude",
                })
                st.caption(f"Sumber: Dataset vibrasi CBMAI, record terakhir {latest.get('timestamp', '-')}, kondisi label awal {latest.get('condition', '-')}/{latest.get('overall_severity', '-')}")
