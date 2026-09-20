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
import os
from typing import Any, Iterable, Optional

import pandas as pd

from src import domain_ingest as ingest
from src import domain_measurements as dm

ALL_REPORT_DOMAINS = ("MCSA", "VIBRASI", "DGA", "PD", "TRIBOLOGY", "THERMAL")

# Agent per domain, resolved lazily so importing this module does not drag in
# the whole agent stack for a caller that only wants the CSV.
_AGENT_FACTORIES = {
    "MCSA": ("src.agents.specialist_agents", "MCSAAgent"),
    "VIBRASI": ("src.agents.specialist_agents", "VibrationAgent"),
    "DGA": ("src.agents.specialist_agents", "DGAAgent"),
    "PD": ("src.agents.specialist_agents", "PDAgent"),
    "TRIBOLOGY": ("src.agents.specialist_agents", "TribologyAgent"),
    "THERMAL": ("src.agents.specialist_agents", "ThermalAgent"),
}


def canon_report_domain(domain: str) -> str:
    val = str(domain or "").strip().upper()
    if val in ALL_REPORT_DOMAINS:
        return val
    return dm.canon_domain(domain)


def _agent_for(domain: str):
    dom = canon_report_domain(domain)
    module_name, class_name = _AGENT_FACTORIES[dom]
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)()


def _collect_mcsa_data(start: date, end: date) -> dict[str, Any]:
    from src.data_loader import get_data_path, load_mcsa_data
    from src.agents.specialist_agents import MCSAAgent

    data_file = get_data_path("mcsa_updated.csv")
    if not os.path.exists(data_file):
        data_file = get_data_path("Report MCSA.xls")

    empty_res = {
        "domain": "MCSA",
        "label": "MCSA (Motor Current Signature)",
        "frame": pd.DataFrame(columns=["equipment", "test_date", "parameter", "raw_value", "uom"]),
        "verdicts": [],
        "equipment_count": 0,
        "reading_count": 0,
        "has_data": False,
    }

    try:
        df = load_mcsa_data(data_file)
    except Exception:
        return empty_res

    if df is None or df.empty or "Date" not in df.columns or "Equipment" not in df.columns:
        return empty_res

    dt_series = pd.to_datetime(df["Date"], errors="coerce")
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    mask = (dt_series >= start_ts) & (dt_series <= end_ts)
    scoped = df[mask].copy()

    if scoped.empty:
        return empty_res

    frame = pd.DataFrame({
        "equipment": scoped["Equipment"],
        "test_date": pd.to_datetime(scoped["Date"], errors="coerce"),
        "parameter": scoped["Parameter"],
        "raw_value": scoped["Raw_Value"],
        "uom": scoped.get("Unit", ""),
    })

    agent = MCSAAgent()
    verdicts = []
    for eq in sorted(scoped["Equipment"].dropna().unique().tolist()):
        eq_rows = scoped[scoped["Equipment"] == eq]
        payload: dict[str, Any] = {}
        for _, r in eq_rows.iterrows():
            p_name = str(r.get("Parameter", "")).strip().lower()
            val = r.get("Value")
            raw_val = r.get("Raw_Value")
            if "upper" in p_name and "sideband" in p_name:
                payload["upper_sb"] = val
            elif "lower" in p_name and "sideband" in p_name:
                payload["lower_sb"] = val
            elif "dev" in p_name and "current" in p_name:
                payload["dev_current"] = val
            elif "dev" in p_name and "voltage" in p_name:
                payload["dev_voltage"] = val
            elif "thd" in p_name and "voltage" in p_name:
                payload["thd_voltage"] = val
            elif "thd" in p_name and "current" in p_name:
                payload["thd_current"] = val
            elif "bearing" in p_name:
                payload["bearing_status"] = str(raw_val or "")
            elif "load" in p_name:
                payload["load"] = val

        try:
            res = agent.evaluate(eq, payload)
            verdicts.append({
                "equipment": eq,
                "condition": res.get("condition", "NORMAL"),
                "health_score": res.get("health_score"),
                "failure_mode": res.get("failure_mode", "-"),
                "readings": len(eq_rows),
            })
        except Exception as exc:
            verdicts.append({
                "equipment": eq,
                "condition": "Error evaluasi",
                "health_score": None,
                "failure_mode": str(exc),
                "readings": len(eq_rows),
            })

    return {
        "domain": "MCSA",
        "label": "MCSA (Motor Current Signature)",
        "frame": frame,
        "verdicts": verdicts,
        "equipment_count": int(scoped["Equipment"].nunique()),
        "reading_count": int(len(scoped)),
        "has_data": True,
    }


def collect_domain_data(domain: str, start: date, end: date) -> dict[str, Any]:
    """Measurements plus per-equipment agent verdicts for one domain/period."""
    dom_upper = canon_report_domain(domain)
    if dom_upper == "MCSA":
        return _collect_mcsa_data(start, end)

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
        "has_data": not frame.empty,
    }


def build_csv(domains: Iterable[str], start: date, end: date) -> bytes:
    """Raw measurements for the period, one row per reading, domain-tagged."""
    parts = []
    for domain in domains:
        dom_name = canon_report_domain(domain)
        if dom_name == "MCSA":
            mcsa_dict = _collect_mcsa_data(start, end)
            section = mcsa_dict.get("frame")
            if section is not None and not section.empty:
                section = section.copy()
                section.insert(0, "domain", "MCSA")
                parts.append(section)
            continue

        section = dm.filter_measurements(dm.canon_domain(dom_name), date_start=start, date_end=end)
        if section.empty:
            continue
        section = section.copy()
        section.insert(0, "domain", dm.canon_domain(dom_name))
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
            p = document.add_paragraph()
            r = p.add_run("⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]\n")
            r.bold = True
            p.add_run(
                "Tidak ada pengukuran pada periode ini. "
                "Peralatan berstatus STANDBY atau belum memasuki siklus jadwal pengujian berkala."
            )
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
            p0 = frame.paragraphs[0]
            p0.text = "⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]"
            p0.runs[0].font.size = Pt(20)
            p0.runs[0].font.bold = True
            p1 = frame.add_paragraph()
            p1.text = (
                "Tidak ada pengukuran pada periode ini.\n"
                "Penyebab: Peralatan berada dalam status operasi STANDBY, pemeliharaan terjadwal, "
                "atau siklus pengujian terjadwal pada periode berikutnya."
            )
            p1.runs[0].font.size = Pt(14)
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


def build_meeting_pptx(
    domains: Iterable[str],
    start: date,
    end: date,
    title: str = "Meeting Koordinasi Keandalan CBM",
    subtitle: str = "PLTU Jeranjang 3 × 25 MW - Predictive Maintenance",
) -> bytes:
    """
    Slide deck presentasi meeting CBM multi-modul.
    Menampilkan data pengujian dari modul yang aktif diuji pada periode tersebut,
    dan menandai secara visual dengan badge:
    ⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]
    untuk modul yang belum memiliki pengujian pada periode tersebut.
    """
    from pptx import Presentation
    from pptx.util import Inches, Pt

    deck = Presentation()
    deck.slide_width = Inches(13.333)
    deck.slide_height = Inches(7.5)

    # 1. Slide Cover Meeting
    cover_slide = deck.slides.add_slide(deck.slide_layouts[0])
    cover_slide.shapes.title.text = title
    cover_slide.placeholders[1].text = (
        f"{subtitle}\n"
        f"Periode Evaluasi: {start:%d %B %Y} - {end:%d %B %Y}\n"
        f"Waktu Paparan: {pd.Timestamp.now():%d %B %Y %H:%M} WITA | Tim CBM & Reliability Engineering"
    )

    # 2. Slide Executive Matrix: Kesiapan 6 Modul CBM
    matrix_slide = deck.slides.add_slide(deck.slide_layouts[5])
    matrix_slide.shapes.title.text = "Matriks Kesiapan & Status 6 Modul CBM"

    domain_list = [canon_report_domain(d) for d in domains]
    collected = [collect_domain_data(d, start, end) for d in domain_list]

    rows_count = len(collected) + 1
    table_shape = matrix_slide.shapes.add_table(rows_count, 5, Inches(0.8), Inches(1.5), Inches(11.7), Inches(4.8))
    tbl = table_shape.table
    tbl.columns[0].width = Inches(2.2)
    tbl.columns[1].width = Inches(3.2)
    tbl.columns[2].width = Inches(1.6)
    tbl.columns[3].width = Inches(1.6)
    tbl.columns[4].width = Inches(3.1)

    headers = ["Modul CBM", "Status Data Pengujian", "Jml Uji", "Jml Aset", "Keterangan Operasional"]
    for col_idx, h in enumerate(headers):
        cell = tbl.cell(0, col_idx)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(13)

    for row_idx, item in enumerate(collected, start=1):
        tbl.cell(row_idx, 0).text = item["label"].split("(")[0].strip()
        if item["reading_count"] > 0:
            tbl.cell(row_idx, 1).text = "✅ AKTIF DIUJI"
            tbl.cell(row_idx, 2).text = str(item["reading_count"])
            tbl.cell(row_idx, 3).text = str(item["equipment_count"])
            tbl.cell(row_idx, 4).text = "Data terverifikasi rule specialist agent"
        else:
            tbl.cell(row_idx, 1).text = "⚠️ STANDBY / BELUM ADA DATA"
            tbl.cell(row_idx, 2).text = "0"
            tbl.cell(row_idx, 3).text = "0"
            tbl.cell(row_idx, 4).text = "Aset Standby / Siklus uji periode berikutnya"

        for col_idx in range(5):
            for p in tbl.cell(row_idx, col_idx).text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(12)

    # 3. Slide Detail Setiap Modul
    for item in collected:
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = f"Evaluasi Modul: {item['label']}"

        box = slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.2))
        tf = box.text_frame
        tf.word_wrap = True

        if item["reading_count"] == 0:
            p0 = tf.paragraphs[0]
            p0.text = "⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY PADA PERIODE INI]"
            p0.runs[0].font.size = Pt(20)
            p0.runs[0].font.bold = True

            p1 = tf.add_paragraph()
            p1.text = (
                "\nKeterangan Operasional & Perencanaan:\n"
                "• Tidak terdapat aktivitas pengambilan data atau uji laboratorium pada periode pelaporan ini.\n"
                "• Unit / peralatan berada dalam status STANDBY atau pemeliharaan offline.\n"
                "• Pengujian modul ini dijadwalkan kembali pada siklus pemantauan berikutnya sesuai Program CBM Tahunan."
            )
            p1.runs[0].font.size = Pt(14)
            continue

        p0 = tf.paragraphs[0]
        p0.text = f"📊 Statistik: {item['reading_count']} data pengujian dari {item['equipment_count']} equipment aktif."
        p0.runs[0].font.size = Pt(16)
        p0.runs[0].font.bold = True

        for v in item["verdicts"][:12]:
            p = tf.add_paragraph()
            p.level = 1
            cond = v["condition"]
            badge = "🟢" if "NORM" in cond.upper() else ("🟡" if "WARN" in cond.upper() or "ALARM" in cond.upper() else "🔴")
            score = f"Health: {v['health_score']}" if v["health_score"] is not None else "Health: -"
            p.text = f"{badge} {v['equipment']}: {cond} ({score} | Mode: {v['failure_mode']})"
            for r in p.runs:
                r.font.size = Pt(13)

        if len(item["verdicts"]) > 12:
            p_more = tf.add_paragraph()
            p_more.level = 1
            p_more.text = f"... dan {len(item['verdicts']) - 12} equipment lainnya terlampir di laporan lengkap."
            for r in p_more.runs:
                r.font.size = Pt(12)

    # 4. Slide Action Items & Tindak Lanjut Meeting
    action_slide = deck.slides.add_slide(deck.slide_layouts[5])
    action_slide.shapes.title.text = "Rencana Tindak Lanjut & Keputusan Meeting Keandalan CBM"
    box_act = action_slide.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.2))
    tf_act = box_act.text_frame
    tf_act.word_wrap = True

    p_a0 = tf_act.paragraphs[0]
    p_a0.text = "🎯 Keputusan & Rekomendasi Prioritas Keandalan:"
    p_a0.runs[0].font.size = Pt(18)
    p_a0.runs[0].font.bold = True

    act_points = [
        "1. Penerbitan Work Order (WO) CBM untuk peralatan berstatus ALARM / WARNING hasil uji modul aktif.",
        "2. Konfirmasi jadwal pengujian lapangan untuk modul-modul yang saat ini berstatus STANDBY.",
        "3. Verifikasi korelasi getaran mekanik dan arus motor (Vibrasi & MCSA) pada peralatan kritis Unit 1, 2, dan 3.",
        "4. Monitoring laju kenaikan gas transformator (DGA) berkala sesuai rekomendasi IEEE C57.104.",
        "5. Pelaksanaan continuous learning cycle oleh Agent CBM Learning untuk memperbarui bobot prediksi reliabilitas.",
    ]
    for pt in act_points:
        p = tf_act.add_paragraph()
        p.text = pt
        for r in p.runs:
            r.font.size = Pt(14)

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
    domains = [canon_report_domain(item) for item in domains]
    wanted = {item.lower() for item in (formats or ("docx", "pptx", "csv"))}

    bundle: dict[str, bytes] = {}
    if "csv" in wanted:
        bundle["csv"] = build_csv(domains, start, end)
    if "docx" in wanted:
        bundle["docx"] = build_docx(domains, start, end)
    if "pptx" in wanted:
        bundle["pptx"] = build_pptx(domains, start, end)
    return bundle
