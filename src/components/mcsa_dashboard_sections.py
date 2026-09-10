"""Independent presenter sections for the Streamlit MCSA dashboard."""

import json
import os
from typing import Optional

import pandas as pd
import plotly.express as px

from src.components.status_colors import STATUS_PIE_COLORS
from src.data_loader import get_data_path, load_nameplate_csv
from src.equipment_canon import compute_overall_status_from_rows, norm_equipment


def render_sampling_compliance(
    st,
    standby_report: Optional[dict],
    df_month: Optional[pd.DataFrame],
) -> None:
    """Render the optional monthly sampling-compliance workspace."""
    if standby_report is None:
        return

    show_sampling = st.checkbox("Sampling Compliance", value=False)
    if not show_sampling:
        return

    with st.expander("Sampling Compliance", expanded=True):
        month_label = standby_report["month_start"].strftime("%Y-%m")
        required_label = ", ".join(standby_report.get("required_params") or [])
        st.caption(f"Bulan: {month_label} | Parameter wajib: {required_label}")

        universe = standby_report.get("eq_universe") or []
        present = set(standby_report.get("eq_present") or [])
        missing = standby_report.get("eq_missing") or []
        reasons_for_month = standby_report.get("standby_reasons") or {}
        excluded = [
            equipment
            for equipment in missing
            if equipment in reasons_for_month
            and str(reasons_for_month[equipment].get("reason", "")).strip() != ""
        ]
        missing_visible = [equipment for equipment in missing if equipment not in excluded]

        total_expected = len(universe)
        updated = len(present)
        missing_count = len(missing_visible)
        compliance_pct = 0.0 if total_expected == 0 else (updated / total_expected) * 100.0

        col_expected, col_updated, col_missing, col_compliance = st.columns(4)
        col_expected.metric("Expected", total_expected)
        col_updated.metric("Updated", updated)
        col_missing.metric("Belum Update", missing_count)
        col_compliance.metric("Compliance %", round(compliance_pct, 1))

        if present and df_month is not None:
            monthly = df_month.copy()
            monthly["Parameter"] = monthly["Parameter"].astype(str)
            load_rows = monthly[monthly["Parameter"] == "Load"]
            load_values = pd.to_numeric(load_rows.get("Value", pd.NA), errors="coerce")
            if "Raw_Value" in load_rows.columns:
                load_values = load_values.fillna(
                    pd.to_numeric(load_rows["Raw_Value"], errors="coerce")
                )
            load_rows = load_rows.assign(_load=load_values)
            equipment_load = (
                load_rows.sort_values("Date")
                .dropna(subset=["_load"])
                .drop_duplicates(subset=["Equipment"], keep="last")
            )
            class_map = {}
            for _, row in equipment_load.iterrows():
                load = float(row["_load"])
                if load < 20.0:
                    class_map[row["Equipment"]] = "Invalid (<20%)"
                elif load < 40.0:
                    class_map[row["Equipment"]] = "Monitoring Only (20–40%)"
                else:
                    class_map[row["Equipment"]] = "Valid Diagnosis (≥40%)"

            nameplate = load_nameplate_csv()
            if not nameplate.empty:
                fla_map = (
                    nameplate.set_index("Equipment")["FLA"].to_dict()
                    if "FLA" in nameplate.columns
                    else {}
                )
                for equipment in present:
                    if (
                        equipment in class_map
                        or equipment not in fla_map
                        or fla_map[equipment] in {None, "", "nan"}
                    ):
                        continue
                    current_rows = monthly[
                        (monthly["Equipment"] == equipment)
                        & (monthly["Parameter"].isin(["Current 1", "Current 2", "Current 3"]))
                    ]
                    current_values = pd.to_numeric(
                        current_rows.get("Value", pd.NA), errors="coerce"
                    )
                    if "Raw_Value" in current_rows.columns:
                        current_values = current_values.fillna(
                            pd.to_numeric(current_rows["Raw_Value"], errors="coerce")
                        )
                    if not current_values.notna().any():
                        continue
                    try:
                        fla = float(fla_map[equipment])
                        if fla <= 0:
                            continue
                        load = (float(current_values.dropna().mean()) / fla) * 100.0
                        if load < 20.0:
                            class_map[equipment] = "Invalid (<20%)"
                        elif load < 40.0:
                            class_map[equipment] = "Monitoring Only (20–40%)"
                        else:
                            class_map[equipment] = "Valid Diagnosis (≥40%)"
                    except Exception:
                        continue

            valid_count = sum(
                1 for equipment in present if class_map.get(equipment) == "Valid Diagnosis (≥40%)"
            )
            monitoring_count = sum(
                1
                for equipment in present
                if class_map.get(equipment) == "Monitoring Only (20–40%)"
            )
            invalid_count = sum(
                1 for equipment in present if class_map.get(equipment) == "Invalid (<20%)"
            )
            col_valid, col_monitoring, col_invalid = st.columns(3)
            col_valid.metric("Valid Diagnosis", valid_count)
            col_monitoring.metric("Monitoring Only", monitoring_count)
            col_invalid.metric("Invalid (Load<20%)", invalid_count)

        if missing_count:
            missing_df = pd.DataFrame({"Equipment": missing_visible})
            st.dataframe(missing_df, width="stretch", hide_index=True)
            st.download_button(
                "Download CSV (Belum Update)",
                data=missing_df.to_csv(index=False).encode("utf-8"),
                file_name=f"belum_update_{month_label}.csv",
                mime="text/csv",
            )

        st.markdown("---")
        st.subheader("Alasan Standby (pengecualian kepatuhan)")
        reason_options = [
            "PLANNED_SHUTDOWN",
            "UNPLANNED_OUTAGE",
            "MAINTENANCE",
            "UNIT_OFF",
            "VFD_BYPASS",
            "STARTUP_TEST",
            "OTHER",
        ]
        new_reasons = {}
        for equipment in missing:
            col_reason, col_note = st.columns([2, 3])
            with col_reason:
                default_reason_index = (
                    reason_options.index(reasons_for_month.get(equipment, {}).get("reason", "OTHER"))
                    if reasons_for_month.get(equipment)
                    else reason_options.index("OTHER")
                )
                selected_reason = st.selectbox(
                    f"{equipment}", reason_options, index=default_reason_index
                )
            with col_note:
                note = st.text_input(
                    f"Catatan ({equipment})",
                    value=reasons_for_month.get(equipment, {}).get("note", ""),
                )
            new_reasons[equipment] = {"reason": selected_reason, "note": note}

        if st.button("Simpan Alasan Standby"):
            reasons_path = get_data_path("config", "standby_reasons.json")
            reasons_data = {}
            try:
                if os.path.exists(reasons_path):
                    with open(reasons_path, "r", encoding="utf-8") as handle:
                        reasons_data = json.load(handle)
            except Exception:
                reasons_data = {}

            month_key = standby_report["month_start"].strftime("%Y-%m")
            reasons_data[month_key] = new_reasons
            try:
                os.makedirs(os.path.dirname(reasons_path), exist_ok=True)
                with open(reasons_path, "w", encoding="utf-8") as handle:
                    json.dump(reasons_data, handle, ensure_ascii=False, indent=2)
                st.success("Alasan standby disimpan.")
            except Exception as exc:
                st.error(f"Gagal menyimpan: {exc}")


def render_condition_summary(
    st,
    filtered_df: pd.DataFrame,
    unit_label: str,
    standby_enabled: bool,
    standby_report: Optional[dict],
) -> dict[str, str]:
    """Render fleet status metrics and the condition distribution chart."""
    if (
        standby_enabled
        and standby_report
        and isinstance(standby_report.get("eq_universe"), list)
        and standby_report.get("eq_universe")
    ):
        universe_equipment = [str(value) for value in standby_report["eq_universe"]]
    else:
        universe_equipment = [
            str(value)
            for value in filtered_df.get("Equipment", pd.Series(dtype=str))
            .dropna()
            .astype(str)
            .unique()
        ]
    universe_norm = [
        value
        for value in pd.Series(universe_equipment).map(norm_equipment).tolist()
        if value and value.lower() not in {"nan", "none"}
    ]

    missing_norm = set()
    if (
        standby_enabled
        and standby_report
        and isinstance(standby_report.get("eq_missing"), list)
    ):
        missing_norm = set(
            pd.Series([str(value) for value in standby_report["eq_missing"]])
            .map(norm_equipment)
            .tolist()
        )

    latest = filtered_df.copy()
    if "Equipment" in latest.columns:
        latest["_norm"] = latest["Equipment"].astype(str).map(norm_equipment)
    else:
        latest["_norm"] = ""
    status_by_norm = {}
    if not latest.empty:
        for equipment_norm, rows in latest.groupby("_norm"):
            if not equipment_norm or str(equipment_norm).lower() in {"nan", "none"}:
                continue
            status_by_norm[equipment_norm] = compute_overall_status_from_rows(rows)

    status_by_universe = {
        equipment_norm: (
            "Standby"
            if equipment_norm in missing_norm
            else status_by_norm.get(equipment_norm, "Unknown")
        )
        for equipment_norm in universe_norm
    }
    status_counts = pd.Series(list(status_by_universe.values())).value_counts()

    col_total, col_normal, col_standby, col_alarm, col_high = st.columns(5)
    col_total.metric("Total Equipment", len(universe_norm))
    col_normal.metric("Normal (Hijau)", int(status_counts.get("Normal", 0)))
    col_standby.metric("Standby", int(status_counts.get("Standby", 0)))
    col_alarm.metric("Alarm (Kuning)", int(status_counts.get("Alarm", 0)), delta_color="inverse")
    col_high.metric("High (Merah)", int(status_counts.get("High", 0)), delta_color="inverse")

    st.subheader(f"Distribusi Kondisi — {unit_label}")
    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = pd.DataFrame({"Status": plot_order})
    plot_df["Count"] = plot_df["Status"].map(
        lambda status: int(status_counts.get(status, 0))
    )
    plot_df = plot_df[plot_df["Count"] > 0]
    if plot_df.empty:
        st.info("Tidak ada data untuk filter ini.")
        return status_by_norm

    figure = px.pie(
        plot_df,
        names="Status",
        values="Count",
        title=f"Status Equipment — {unit_label}",
        color="Status",
        color_discrete_map=STATUS_PIE_COLORS,
        category_orders={"Status": plot_order},
    )
    figure.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
    figure.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(figure, width="stretch")
    return status_by_norm
