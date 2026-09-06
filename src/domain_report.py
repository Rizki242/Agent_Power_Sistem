"""Period-scoped reports over the canonical domain measurement store.

Builds Word, PowerPoint, and CSV for one domain or several combined, over
any period the stored data actually covers. One engine rather than five, for
the same reason src.domain_measurements is one store rather than five: the
report differs between domains only in which parameters appear, and that is
data, not code.

Every number in the output is read from stored measurements or computed by
the domain's own specialist agent - nothing is estimated or filled in to
make a period look complete. A domain with no rows in the period is listed
as such rather than omitted, so a reader can tell "nothing was measured"
apart from "this domain was left out of the report".
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Any, Iterable, Optional

import pandas as pd

from src import domain_ingest as ingest
from src import domain_measurements as dm

# Agent per domain, resolved lazily so importing this module does not drag in
# the whole agent stack for a caller that only wants the CSV.
_AGENT_FACTORIES = {
    "VIBRASI": ("src.agents.specialist_agents", "VibrationAgent"),
    "DGA": ("src.agents.specialist_agents", "DGAAgent"),
    "PD": ("src.agents.specialist_agents", "PDAgent"),
    "TRIBOLOGY": ("src.agents.specialist_agents", "TribologyAgent"),
    "THERMAL": ("src.agents.specialist_agents", "ThermalAgent"),
}


def _agent_for(domain: str):
    module_name, class_name = _AGENT_FACTORIES[dm.canon_domain(domain)]
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)()


def collect_domain_data(domain: str, start: date, end: date) -> dict[str, Any]:
    """Measurements plus per-equipment agent verdicts for one domain/period."""
    domain = dm.canon_domain(domain)
    frame = dm.filter_measurements(domain, date_start=start, date_end=end)

    verdicts: list[dict[str, Any]] = []
    if not frame.empty:
        for equipment in sorted(frame["equipment"].dropna().unique().tolist()):
            scoped = frame[frame["equipment"] == equipment]
            payload = ingest.agent_input_from_measurements(domain, scoped)
            if not payload:
                continue
            try:
                result = _agent_for(domain).evaluate(equipment, payload)
            except Exception as exc:  # a bad reading must not kill the report
                verdicts.append({
                    "equipment": equipment,
                    "condition": "Tidak dapat dievaluasi",
                    "health_score": None,
                    "failure_mode": str(exc),
                    "readings": len(scoped),
                })
                continue
            verdicts.append({
                "equipment": equipment,
                "condition": result.get("condition", "-"),
                "health_score": result.get("health_score"),
                "failure_mode": result.get("failure_mode", "-"),
                "readings": int(len(scoped)),
            })

    return {
        "domain": domain,
        "label": ingest.profile(domain)["label"],
        "frame": frame,
        "verdicts": verdicts,
        "equipment_count": int(frame["equipment"].nunique()) if not frame.empty else 0,
        "reading_count": int(len(frame)),
    }


def build_csv(domains: Iterable[str], start: date, end: date) -> bytes:
    """Raw measurements for the period, one row per reading, domain-tagged."""
    parts = []
    for domain in domains:
        section = dm.filter_measurements(dm.canon_domain(domain), date_start=start, date_end=end)
        if section.empty:
            continue
        section = section.copy()
        section.insert(0, "domain", dm.canon_domain(domain))
        parts.append(section)

    if not parts:
        return pd.DataFrame(columns=["domain", *dm.COLUMNS]).to_csv(index=False).encode("utf-8-sig")
    return pd.concat(parts, ignore_index=True).to_csv(index=False).encode("utf-8-sig")


def build_docx(domains: Iterable[str], start: date, end: date) -> bytes:
    """Engineering-style Word report: one section per domain."""
    from docx import Document
    from docx.shared import Pt

    document = Document()
    document.add_heading("Laporan Condition Monitoring", level=0)
    document.add_paragraph(f"Periode: {start:%d %B %Y} - {end:%d %B %Y}")
    document.add_paragraph(f"Dibuat: {pd.Timestamp.now():%d %B %Y %H:%M}")
    document.add_paragraph(
        "Seluruh angka pada laporan ini berasal dari pengukuran tersimpan dan "
        "evaluasi rule-based specialist agent. Periode tanpa data dinyatakan "
        "apa adanya, tidak diisi dengan estimasi."
    )

    for domain in domains:
        data = collect_domain_data(domain, start, end)
        document.add_heading(data["label"], level=1)

        if data["reading_count"] == 0:
            document.add_paragraph("Tidak ada pengukuran pada periode ini.")
            continue

        document.add_paragraph(
            f"{data['reading_count']} pengukuran dari {data['equipment_count']} equipment."
        )

        if data["verdicts"]:
            document.add_heading("Ringkasan kondisi", level=2)
            table = document.add_table(rows=1, cols=5)
            table.style = "Light Grid Accent 1"
            headers = ("Equipment", "Kondisi", "Health Score", "Failure Mode", "Jml. Baca")
            for cell, text in zip(table.rows[0].cells, headers):
                cell.text = text
            for verdict in data["verdicts"]:
                cells = table.add_row().cells
                cells[0].text = str(verdict["equipment"])
                cells[1].text = str(verdict["condition"])
                cells[2].text = "-" if verdict["health_score"] is None else str(verdict["health_score"])
                cells[3].text = str(verdict["failure_mode"])
                cells[4].text = str(verdict["readings"])

        document.add_heading("Detail pengukuran", level=2)
        detail = document.add_table(rows=1, cols=5)
        detail.style = "Light Grid Accent 1"
        for cell, text in zip(detail.rows[0].cells, ("Tanggal", "Equipment", "Parameter", "Nilai", "Satuan")):
            cell.text = text
        for _, row in data["frame"].sort_values("test_date").iterrows():
            cells = detail.add_row().cells
            cells[0].text = "" if pd.isna(row["test_date"]) else f"{row['test_date']:%d-%m-%Y}"
            cells[1].text = str(row["equipment"])
            cells[2].text = str(row["parameter"])
            cells[3].text = str(row["raw_value"])
            cells[4].text = str(row["uom"])

    for paragraph in document.paragraphs:
        for run in paragraph.runs:
            if run.font.size is None:
                run.font.size = Pt(10)

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def build_pptx(domains: Iterable[str], start: date, end: date) -> bytes:
    """Slide deck: a title slide plus one condition-summary slide per domain."""
    from pptx import Presentation
    from pptx.util import Inches, Pt

    deck = Presentation()
    deck.slide_width = Inches(13.333)
    deck.slide_height = Inches(7.5)

    title_slide = deck.slides.add_slide(deck.slide_layouts[0])
    title_slide.shapes.title.text = "Laporan Condition Monitoring"
    title_slide.placeholders[1].text = (
        f"Periode {start:%d %b %Y} - {end:%d %b %Y}\n"
        f"Dibuat {pd.Timestamp.now():%d %b %Y %H:%M}"
    )

    for domain in domains:
        data = collect_domain_data(domain, start, end)
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = data["label"]

        box = slide.shapes.add_textbox(Inches(0.6), Inches(1.5), Inches(12.1), Inches(5.4))
        frame = box.text_frame
        frame.word_wrap = True

        if data["reading_count"] == 0:
            frame.text = "Tidak ada pengukuran pada periode ini."
            frame.paragraphs[0].runs[0].font.size = Pt(16)
            continue

        frame.text = f"{data['reading_count']} pengukuran - {data['equipment_count']} equipment"
        frame.paragraphs[0].runs[0].font.size = Pt(16)

        for verdict in data["verdicts"][:14]:
            paragraph = frame.add_paragraph()
            score = "-" if verdict["health_score"] is None else verdict["health_score"]
            paragraph.text = (
                f"{verdict['equipment']}  -  {verdict['condition']}  "
                f"(health {score}; {verdict['failure_mode']})"
            )
            paragraph.level = 1
            for run in paragraph.runs:
                run.font.size = Pt(13)

        if len(data["verdicts"]) > 14:
            more = frame.add_paragraph()
            more.text = f"... dan {len(data['verdicts']) - 14} equipment lainnya (lihat lampiran CSV/Word)."
            more.level = 1
            for run in more.runs:
                run.font.size = Pt(12)

    buffer = BytesIO()
    deck.save(buffer)
    return buffer.getvalue()


def build_report_bundle(
    domains: Iterable[str],
    start: date,
    end: date,
    formats: Optional[Iterable[str]] = None,
) -> dict[str, bytes]:
    """All three report formats for the given domains and period."""
    domains = [dm.canon_domain(item) for item in domains]
    wanted = {item.lower() for item in (formats or ("docx", "pptx", "csv"))}

    bundle: dict[str, bytes] = {}
    if "csv" in wanted:
        bundle["csv"] = build_csv(domains, start, end)
    if "docx" in wanted:
        bundle["docx"] = build_docx(domains, start, end)
    if "pptx" in wanted:
        bundle["pptx"] = build_pptx(domains, start, end)
    return bundle
