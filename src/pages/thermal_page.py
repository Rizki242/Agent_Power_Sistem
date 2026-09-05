"""Thermal (IRT thermography) dashboard - hotspot / delta-T inspection points.

No render_data_disclaimer_banner here, unlike DGA/Tribology: the underlying
110+ inspection points are real, parsed from an actual Excel export - not
fabricated. What IS missing from that source is the numeric bearing/winding
temperature readings ThermalAgent expects, so the Rekomendasi tab below is
deliberately status-based rather than a ThermalAgent call - see
src.thermal_data.get_thermal_record_detail's docstring for why.
"""

import plotly.express as px

from src.components.status_colors import (
    STATUS_PIE_COLORS,
    canon_condition_status,
    render_status_badge,
)
from src.components.theme import render_detail_view_toggle, render_page_header
from src.thermal_data import get_thermal_record_detail, search_thermal_records


def _render_recommendation(st, detail) -> None:
    status = str(detail.get("status", "NORMAL")).upper()
    with st.container(border=True):
        if status == "HIGH":
            st.error(f"Status: {status}")
        elif status == "WARNING":
            st.warning(f"Status: {status}")
        elif status == "PREWARNING":
            st.info(f"Status: {status}")
        else:
            st.success(f"Status: {status}")
        st.markdown("**Rekomendasi tindak lanjut**")
        st.write(f"- {detail.get('recommendation', '-')}")
    st.caption(
        "Rekomendasi berbasis status hasil inspeksi IRT, bukan skor kuantitatif ThermalAgent - "
        "pembacaan suhu bearing/winding detail belum tersedia dari sumber data ini."
    )


def render_thermal_page(st) -> None:
    render_page_header(st, "Thermal", "Monitoring Thermography (IRT) & RTD - Delta-T Matrix")

    records = search_thermal_records()
    if not records:
        st.warning("Data inspeksi thermal tidak tersedia.")
        return

    for r in records:
        r["_status_canon"] = canon_condition_status(r.get("status"))

    status_counts = {}
    for r in records:
        status_counts[r["_status_canon"]] = status_counts.get(r["_status_canon"], 0) + 1

    # --- KPI cards -----------------------------------------------------------
    cols = st.columns(5)
    cols[0].metric("Total Titik Inspeksi", len(records))
    cols[1].metric("Normal (Hijau)", status_counts.get("Normal", 0))
    cols[2].metric("Standby", status_counts.get("Standby", 0))
    cols[3].metric("Alarm (Kuning)", status_counts.get("Alarm", 0), delta_color="inverse")
    cols[4].metric("High (Merah)", status_counts.get("High", 0), delta_color="inverse")

    # --- Pie chart -------------------------------------------------------------
    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = [{"Status": s, "Count": status_counts.get(s, 0)} for s in plot_order if status_counts.get(s, 0) > 0]
    if plot_df:
        fig = px.pie(
            plot_df, names="Status", values="Count", title="Status Titik Inspeksi Thermal",
            color="Status", color_discrete_map=STATUS_PIE_COLORS,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5))
        st.plotly_chart(fig, width="stretch")

    # --- Filter + selector -------------------------------------------------
    units = ["All"] + sorted({r["unit"] for r in records})
    sel_unit = st.selectbox("Unit", units, key="thermal_unit_filter")
    scoped = records if sel_unit == "All" else [r for r in records if r["unit"] == sel_unit]

    if not scoped:
        st.info("Tidak ada titik inspeksi pada unit ini.")
        return

    label_by_id = {r["id"]: f"{r['equipment']} ({r['id']})" for r in scoped}
    ids = list(label_by_id.keys())
    if st.session_state.get("thermal_selected_record") not in ids:
        st.session_state["thermal_selected_record"] = ids[0]
    selected_id = st.selectbox(
        "Pilih Titik Inspeksi:", ids, key="thermal_selected_record",
        format_func=lambda rid: label_by_id.get(rid, rid),
    )

    detail = get_thermal_record_detail(selected_id)
    if not detail:
        st.warning("Detail titik inspeksi tidak ditemukan.")
        return

    status = canon_condition_status(detail.get("status"))
    render_status_badge(st, detail["equipment"], status)
    st.caption(f"**ID:** {selected_id} | **Unit:** {detail.get('unit', '-')} | **KKS:** {detail.get('kks', '-')}")

    detail_view = render_detail_view_toggle(st, key="thermal_detail_view")

    if detail_view == "Ringkasan":
        st.markdown("**Hasil Inspeksi**")
        st.dataframe(
            [
                {"Parameter": "Status Kondisi", "Nilai": detail.get("raw_status")},
                {"Parameter": "Standard/Metode", "Nilai": detail.get("standard")},
                {"Parameter": "Tanggal Uji", "Nilai": detail.get("test_date")},
                {"Parameter": "No KKS", "Nilai": detail.get("kks")},
            ],
            hide_index=True, width="stretch",
        )

    elif detail_view == "Rekomendasi":
        _render_recommendation(st, detail)
