"""Shared Streamlit workspace shell for the five non-MCSA domains.

Vibrasi, DGA, Partial Discharge, Tribology, and Thermal each had a read-only
page: a KPI row, a status pie, an equipment picker, and an agent verdict.
None of them could ingest data, none could filter by period, none could
produce a report - the three things MCSA has had all along.

Rather than growing five copies of those three features, every domain page
renders the same workspace here and supplies a DomainWorkspaceConfig
describing only what is domain-specific (its id, its labels, its agent, and
optionally its existing summary view). Upload, manual entry, period
filtering, trends, diagnosis, and report export are one implementation.

Tabs
----
    Ringkasan      the domain's own existing summary view (callback)
    Data & Upload  CSV/XLSX upload, manual entry, template, batch history
    Tren & Riwayat period filter + per-parameter trend + record table
    Diagnosa       specialist agent fed by ingested measurements
    Laporan        Word / PowerPoint / CSV export for the chosen period

Nothing here computes an engineering verdict: status and severity always
come from the domain's specialist agent, keeping the rule-based layer the
single source of truth (CLAUDE.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Callable, Optional

import pandas as pd

from src import domain_ingest as ingest
from src import domain_measurements as dm
from src.components.theme import render_page_header
from src.time_filters import clamp_period, preset_period

# "Mingguan" is handled here rather than in src.time_filters because it is a
# rolling 7-day window anchored on the data, not one of that module's
# calendar-month presets.
PERIOD_PRESETS = (
    "Semua",
    "Kondisi saat Ini",
    "Pengujian Terakhir",
    "Mingguan",
    "3 Bulan",
    "6 Bulan",
    "12 Bulan",
    "Kustom",
)


@dataclass
class DomainWorkspaceConfig:
    """What one domain must declare to get the shared workspace."""

    domain: str                       # VIBRASI | DGA | PD | TRIBOLOGY | THERMAL
    title: str
    subtitle: str = ""
    agent_factory: Optional[Callable[[], Any]] = None
    metric_labels: dict[str, str] = field(default_factory=dict)
    summary_renderer: Optional[Callable[[Any], None]] = None
    disclaimer: str = ""


def render_domain_workspace(st, config: DomainWorkspaceConfig) -> None:
    """Render the five-tab workspace for one domain."""
    if config.disclaimer:
        st.warning(config.disclaimer, icon=":material/info:")
    render_page_header(st, config.title, config.subtitle)

    tab_summary, tab_data, tab_trend, tab_diag, tab_report = st.tabs(
        ["Ringkasan", "Data & Upload", "Tren & Riwayat", "Diagnosa", "Laporan"]
    )

    with tab_summary:
        if config.summary_renderer is not None:
            config.summary_renderer(st)
        else:
            render_store_summary(st, config)

    with tab_data:
        render_data_tab(st, config)

    with tab_trend:
        render_trend_tab(st, config)

    with tab_diag:
        render_diagnosis_tab(st, config)

    with tab_report:
        render_report_tab(st, config)


# ---------------------------------------------------------------------------
# Ringkasan fallback (for a domain with no legacy summary view of its own)
# ---------------------------------------------------------------------------

def render_store_summary(st, config: DomainWorkspaceConfig) -> None:
    summary = dm.summarise(config.domain)
    cols = st.columns(4)
    cols[0].metric("Record tersimpan", summary["records"])
    cols[1].metric("Equipment", summary["equipment_count"])
    cols[2].metric("Parameter", len(summary["parameters"]))

    period_label = "-"
    if summary["earliest"] is not None:
        period_label = f"{summary['earliest']:%d %b %Y} - {summary['latest']:%d %b %Y}"
    cols[3].metric("Rentang data", period_label)

    if summary["records"] == 0:
        st.info(
            "Belum ada data tersimpan untuk domain ini. Gunakan tab "
            "**Data & Upload** untuk mengunggah CSV/XLSX atau input manual."
        )


# ---------------------------------------------------------------------------
# Data & Upload
# ---------------------------------------------------------------------------

def render_data_tab(st, config: DomainWorkspaceConfig) -> None:
    domain = config.domain
    specs = ingest.parameter_specs(domain)

    st.markdown("#### Unggah data (CSV / Excel)")
    st.caption(
        "Format kolom lebar: satu baris per pengujian, satu kolom per parameter. "
        "Nama kolom Indonesia maupun Inggris dikenali otomatis."
    )
    st.download_button(
        "Unduh template CSV",
        data=ingest.template_csv(domain),
        file_name=f"template_{domain.lower()}.csv",
        mime="text/csv",
        icon=":material/download:",
        key=f"{domain}_template",
    )

    uploaded = st.file_uploader(
        "Pilih file",
        type=["csv", "xlsx", "xls"],
        key=f"{domain}_uploader",
        help="Setiap unggahan diarsipkan sebagai satu batch dengan manifest audit.",
    )

    preview_key = f"{domain}_preview"
    content_key = f"{domain}_preview_bytes"
    if uploaded is not None:
        try:
            content = uploaded.getvalue()
            st.session_state[preview_key] = ingest.preview_upload(domain, uploaded.name, content)
            st.session_state[content_key] = content
        except ValueError as exc:
            st.error(str(exc))
            st.session_state.pop(preview_key, None)
            st.session_state.pop(content_key, None)

    preview = st.session_state.get(preview_key)
    if preview:
        cols = st.columns(4)
        cols[0].metric("Baris sumber", preview["source_rows"])
        cols[1].metric("Pengukuran valid", len(preview["valid"]))
        cols[2].metric("Ditolak", len(preview["rejected"]), delta_color="inverse")
        cols[3].metric("Parameter dikenali", len(preview["parameters_found"]))

        if preview["unmapped_columns"]:
            st.warning(
                "Kolom tidak dikenali dan akan diabaikan: " + ", ".join(preview["unmapped_columns"]),
                icon=":material/warning:",
            )
        if preview["rejected"]:
            with st.expander(f"Lihat {len(preview['rejected'])} baris yang ditolak", expanded=False):
                st.dataframe(pd.DataFrame(preview["rejected"]), hide_index=True, width="stretch")

        if preview["valid"]:
            st.dataframe(pd.DataFrame(preview["valid"]).head(50), hide_index=True, width="stretch")
            if st.button(
                "Simpan ke database domain", type="primary",
                key=f"{domain}_commit", icon=":material/save:",
            ):
                batch_path, _ = ingest.create_batch(
                    domain, preview["file_name"], st.session_state.get(content_key, b""), preview,
                )
                result = ingest.commit_batch(domain, batch_path, preview)
                st.success(f"{result['written']} pengukuran tersimpan (batch {result['batch_id']}).")
                st.session_state.pop(preview_key, None)
                st.session_state.pop(content_key, None)
                st.rerun()
        else:
            st.error("Tidak ada baris valid untuk disimpan.")

    st.divider()
    st.markdown("#### Input manual")
    st.caption("Input manual dan unggahan file melewati validasi dan tersimpan di store yang sama.")

    with st.form(f"{domain}_manual_form", border=True):
        cols = st.columns(4)
        equipment = cols[0].text_input("Equipment *", key=f"{domain}_m_eq")
        unit_name = cols[1].text_input("Unit", key=f"{domain}_m_unit")
        test_date = cols[2].date_input("Tanggal uji *", value=date.today(), key=f"{domain}_m_date")
        condition = cols[3].text_input("Kondisi", key=f"{domain}_m_cond")

        values: dict[str, Any] = {}
        value_cols = st.columns(3)
        for index, spec in enumerate(specs):
            label = f"{spec.label} ({spec.uom})" if spec.uom else spec.label
            values[spec.key] = value_cols[index % 3].text_input(label, key=f"{domain}_m_{spec.key}")

        notes = st.text_area("Catatan", key=f"{domain}_m_notes")
        submitted = st.form_submit_button("Simpan pengukuran", type="primary", icon=":material/add:")

    if submitted:
        rows = ingest.manual_entry_rows(
            domain,
            {
                "equipment": equipment,
                "unit_name": unit_name,
                "test_date": test_date,
                "condition": condition,
                "notes": notes,
            },
            values,
        )
        if not rows:
            st.warning("Tidak ada nilai parameter yang diisi.")
        else:
            result = dm.append_measurements(domain, rows, batch_id="manual")
            if result["written"]:
                st.success(f"{result['written']} pengukuran tersimpan.")
            for rejected in result["rejected"]:
                st.error(rejected.get("_reason", "Baris ditolak."))

    st.divider()
    st.markdown("#### Riwayat batch unggahan")
    batches = ingest.list_recent_batches(domain)
    if not batches:
        st.caption("Belum ada batch unggahan.")
    else:
        st.dataframe(
            pd.DataFrame([
                {
                    "Batch": item.get("batch_id"),
                    "Waktu": item.get("uploaded_at"),
                    "File": item.get("file"),
                    "Status": item.get("status"),
                    "Valid": item.get("valid_rows"),
                    "Ditolak": item.get("rejected_rows"),
                    "Tersimpan": item.get("written_rows", 0),
                }
                for item in batches
            ]),
            hide_index=True,
            width="stretch",
        )


# ---------------------------------------------------------------------------
# Period selection (shared by Tren and Laporan)
# ---------------------------------------------------------------------------

def resolve_preset_range(preset: str, min_date: date, max_date: date) -> tuple[date, date]:
    """Resolve a preset against the data's own newest date, not today's date.

    Anchoring on the newest reading is what makes "Kondisi saat Ini"
    meaningful for a dataset whose last test was months ago - the same
    reasoning src.time_filters.preset_period already applies.
    """
    if preset == "Mingguan":
        return clamp_period(max_date - timedelta(days=6), max_date, min_date, max_date)
    return preset_period(preset, min_date, max_date)


def render_period_picker(st, config: DomainWorkspaceConfig, key_prefix: str) -> Optional[tuple[date, date]]:
    """Period picker bounded by what the store actually holds.

    Returns None when the domain has no dated data yet: offering a period the
    data cannot cover would promise a report that does not exist.
    """
    earliest, latest = dm.available_period(config.domain)
    if earliest is None or latest is None:
        st.info(
            "Belum ada data bertanggal untuk domain ini. Unggah data terlebih "
            "dahulu di tab **Data & Upload**."
        )
        return None

    min_date, max_date = earliest.date(), latest.date()
    cols = st.columns([2, 3])
    preset = cols[0].selectbox("Periode", PERIOD_PRESETS, key=f"{key_prefix}_preset")

    if preset == "Kustom":
        chosen = cols[1].date_input(
            "Rentang tanggal",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key=f"{key_prefix}_range",
        )
        if isinstance(chosen, (tuple, list)) and len(chosen) == 2:
            start, end = chosen
        elif isinstance(chosen, date):
            start = end = chosen
        else:
            start, end = min_date, max_date
    else:
        start, end = resolve_preset_range(preset, min_date, max_date)
        cols[1].caption(
            f"Rentang aktif: **{start:%d %b %Y} - {end:%d %b %Y}** "
            f"(data tersedia {min_date:%d %b %Y} - {max_date:%d %b %Y})"
        )

    return clamp_period(start, end, min_date, max_date)


# ---------------------------------------------------------------------------
# Tren & Riwayat
# ---------------------------------------------------------------------------

def render_trend_tab(st, config: DomainWorkspaceConfig) -> None:
    period = render_period_picker(st, config, key_prefix=f"{config.domain}_trend")
    if period is None:
        return
    start, end = period

    frame = dm.filter_measurements(config.domain, date_start=start, date_end=end)
    if frame.empty:
        st.info("Tidak ada pengukuran pada periode ini.")
        return

    equipment_options = ["Semua"] + sorted(frame["equipment"].dropna().unique().tolist())
    parameter_options = sorted(frame["parameter"].dropna().unique().tolist())

    cols = st.columns(2)
    selected_equipment = cols[0].selectbox("Equipment", equipment_options, key=f"{config.domain}_trend_eq")
    selected_parameters = cols[1].multiselect(
        "Parameter", parameter_options,
        default=parameter_options[:3],
        key=f"{config.domain}_trend_params",
    )

    scoped = frame if selected_equipment == "Semua" else frame[frame["equipment"] == selected_equipment]
    if selected_parameters:
        scoped = scoped[scoped["parameter"].isin(selected_parameters)]

    cols = st.columns(3)
    cols[0].metric("Pengukuran", len(scoped))
    cols[1].metric("Equipment", int(scoped["equipment"].nunique()))
    cols[2].metric("Hari pengujian", int(scoped["test_date"].dt.date.nunique()))

    numeric = scoped[scoped["value"].notna()]
    if not numeric.empty:
        import plotly.express as px

        figure = px.line(
            numeric.sort_values("test_date"),
            x="test_date", y="value", color="parameter",
            line_dash="equipment" if selected_equipment == "Semua" else None,
            markers=True, title=f"Tren {config.title}",
        )
        figure.update_layout(
            height=420, margin=dict(l=10, r=10, t=45, b=10), legend_title_text="Parameter",
        )
        st.plotly_chart(figure, width="stretch")
    else:
        st.caption("Parameter terpilih tidak memiliki nilai numerik untuk digambarkan.")

    st.dataframe(
        scoped[[
            "test_date", "equipment", "unit_name", "parameter",
            "raw_value", "uom", "condition", "source_file",
        ]].sort_values("test_date", ascending=False),
        hide_index=True,
        width="stretch",
    )


# ---------------------------------------------------------------------------
# Diagnosa
# ---------------------------------------------------------------------------

def render_diagnosis_tab(st, config: DomainWorkspaceConfig) -> None:
    if config.agent_factory is None:
        st.info("Domain ini belum memiliki specialist agent.")
        return

    frame = dm.load_measurements(config.domain)
    if frame.empty:
        st.info(
            "Belum ada pengukuran tersimpan. Diagnosa di tab ini hanya dijalankan "
            "atas data terukur, bukan nilai asumsi."
        )
        return

    equipment_options = sorted(frame["equipment"].dropna().unique().tolist())
    selected = st.selectbox("Equipment", equipment_options, key=f"{config.domain}_diag_eq")

    scoped = dm.filter_measurements(config.domain, equipment=selected)
    payload = ingest.agent_input_from_measurements(config.domain, scoped)
    if not payload:
        st.info("Tidak ada parameter terukur untuk equipment ini.")
        return

    latest_date = scoped["test_date"].max()
    if pd.notna(latest_date):
        st.caption(f"Sumber: {len(payload)} parameter terukur, pengujian terakhir {latest_date:%d %b %Y}.")
    else:
        st.caption(f"Sumber: {len(payload)} parameter terukur.")

    result = config.agent_factory().evaluate(selected, payload)

    from src.components.agent_result import render_agent_result

    render_agent_result(st, result, config.metric_labels)


# ---------------------------------------------------------------------------
# Laporan
# ---------------------------------------------------------------------------

def render_report_tab(st, config: DomainWorkspaceConfig) -> None:
    from src.domain_report import build_report_bundle

    period = render_period_picker(st, config, key_prefix=f"{config.domain}_report")
    if period is None:
        return
    start, end = period

    frame = dm.filter_measurements(config.domain, date_start=start, date_end=end)
    if frame.empty:
        st.info("Tidak ada data pada periode ini - laporan tidak dibuat agar tidak menyajikan periode kosong.")
        return

    st.caption(
        f"{len(frame)} pengukuran dari {frame['equipment'].nunique()} equipment "
        f"pada {start:%d %b %Y} - {end:%d %b %Y}."
    )

    bundle = build_report_bundle([config.domain], start, end)
    stem = f"Laporan_{config.domain}_{start:%Y%m%d}_{end:%Y%m%d}"

    cols = st.columns(3)
    cols[0].download_button(
        "Unduh Word", data=bundle["docx"], file_name=f"{stem}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        icon=":material/description:", key=f"{config.domain}_rep_docx",
    )
    cols[1].download_button(
        "Unduh PowerPoint", data=bundle["pptx"], file_name=f"{stem}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        icon=":material/slideshow:", key=f"{config.domain}_rep_pptx",
    )
    cols[2].download_button(
        "Unduh CSV", data=bundle["csv"], file_name=f"{stem}.csv",
        mime="text/csv", icon=":material/table:", key=f"{config.domain}_rep_csv",
    )
