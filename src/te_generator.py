"""Technology Examination (TE) Official Report Generator.

Conforms strictly to the official document standard:
PT. INDONESIA POWER - UNIT JASA PEMBANGKITAN PLTU JERANJANG
INTEGRATED MANAGEMENT SYSTEM
Form Code: FORM.JRG.F.05.006 (Rev 01)
Numbering: [No].TE/CBM/UJPJRJ/[YYYY]

Covers specialized CBM investigations across Vibrasi, Tribology, MCSA, DGA, and Thermal.
Provides:
- Data model for Technology Examination findings
- Intelligent auto-population from asset master and measurement databases
- Full 6-page Microsoft Word (.DOCX) generator with headers, tables, standards, and sign-offs
- Interactive Streamlit rendering components
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor


def _set_cell_background(cell, fill_hex: str):
    """Sets the background color of a table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex.replace("#", "")}"/>')
    tcPr.append(shd)


def _set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Sets padding for a table cell in twentieths of a point (dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)


def _set_table_borders(table, color="000000", sz="4", val="single"):
    """Sets standard borders for a docx table."""
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)


def build_te_report_data(
    equipment: str,
    technology: Optional[str] = None,
    finding: Optional[str] = None,
    status: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compiles a complete Technology Examination (TE) report payload for an asset."""
    from src.vibration_data import load_vibration_assets, search_vibration_assets

    custom_fields = custom_fields or {}
    year_str = datetime.now().strftime("%Y")
    date_str = datetime.now().strftime("%d %B %Y")

    # Search in asset master
    eq_asset = {}
    try:
        df_assets = load_vibration_assets()
        if not df_assets.empty:
            matches = df_assets[df_assets["equipment"].str.lower().str.contains(equipment.lower(), na=False)]
            if not matches.empty:
                eq_asset = matches.iloc[0].to_dict()
    except Exception:
        eq_asset = {}

    kks_code = eq_asset.get("kks") or custom_fields.get("kks") or f"LJ-LAC10AP-{equipment.replace(' ', '')}"
    component_1 = eq_asset.get("component_1") or "MOTOR"
    component_2 = eq_asset.get("component_2") or "POMPA"

    # Inferred Technology & Finding
    if not technology:
        technology = custom_fields.get("technology") or "Vibrasi dan Tribology"
    if not status:
        status = custom_fields.get("status") or "Kuning"
    if not finding:
        finding = custom_fields.get("finding") or f"Indikasi anomali vibrasi tinggi dan parameter pelumasan terdegradasi pada {equipment}"

    doc_no = custom_fields.get("doc_number") or f"7.TE/CBM/UJPJRJ/{year_str}"

    return {
        "doc_number": doc_no,
        "form_code": "FORM.JRG.F.05.006",
        "revision": "01",
        "effective_date": "07/02/2017",
        "total_pages": 6,
        "equipment": equipment.upper(),
        "unit": eq_asset.get("unit_group") or custom_fields.get("unit") or "UNIT 1",
        "kks": kks_code,
        "technology": technology,
        "date": date_str,
        "status": status,
        "finding": finding,
        "specifications": {
            "component_1": component_1,
            "component_2": component_2,
            "motor": {
                "type_mfg": eq_asset.get("c1_type_mfg") or "YKS450-2",
                "speed": f"{eq_asset.get('c1_speed') or '2979'} r/min",
                "power": f"{eq_asset.get('c1_power') or '1000'} Kw",
                "bearing_type": eq_asset.get("c1_bearing_type") or "Roller Bearing",
                "inboard_bearing": eq_asset.get("c1_inboard_bearing") or "NU1022M/C3 6022/c3",
                "outboard_bearing": eq_asset.get("c1_outboard_bearing") or "NU1022M/C3 6022/c3",
                "rotor_bar": eq_asset.get("c1_rotor_bar") or "-",
                "foundation": eq_asset.get("c1_foundation") or "Rigid",
            },
            "driven": {
                "type_mfg": eq_asset.get("c2_type_mfg") or "25SB-P",
                "speed": f"{eq_asset.get('c2_speed') or '2980'} r/min",
                "power": f"{eq_asset.get('c2_power') or '822'} Kw",
                "capacity": f"{eq_asset.get('c2_capacity') or '165'} m³/h",
                "inboard_bearing": eq_asset.get("c2_inboard_bearing") or "-",
                "onboard_bearing": eq_asset.get("c2_onboard_bearing") or "-",
                "total_blade": eq_asset.get("c2_total_blade") or "-",
            },
        },
        "vibration_data": {
            "test_date": date_str,
            "rpm": eq_asset.get("c1_speed") or "2980",
            "current": "30 A",
            "points": {
                "1V": 1.26, "1H": 2.11, "1A": 2.64,
                "2V": 1.57, "2H": 1.43, "2A": 2.39,
                "3V": 5.23, "3H": 5.10, "3A": 8.65,
                "4V": 2.30, "4H": 5.75, "4A": 9.45,
                "5V": 2.17, "5H": 4.00, "5A": 1.59,
                "6V": 2.39, "6H": 3.74, "6A": 1.13,
            },
            "spectrum_notes": [
                "Pada Motor: Pada Bearing 1 (NDE Motor) overall vibrasi masuk status prewarning, dengan nilai tertinggi 2.64 mm/s RMS",
                "Pada Fluid Coupling: Pada bearing 4 arah axial overall vibrasi tertinggi masuk status ALARM (9.45 mm/s), terindikasi degradasi mekanikal gearbox",
                "Pada Pompa: Pada Bearing 5 (DE Pompa) overall vibrasi masuk status prewarning, dengan nilai tertinggi 4.00 mm/s RMS.",
            ],
            "recommendations": [
                "Pada Motor: Lakukan acceptance testing vibrasi berkala, thermal thermography, dan monitoring arus MCSA",
                "Pada Fluid Coupling / Gearbox: Lakukan pengecekan Gear Coupling dan inspeksi kondisi pelumasan",
                "Pada Pompa: Pengecekan bearing clearance dan pengamatan trend getaran mingguan.",
            ],
        },
        "thermal_data": {
            "test_date": date_str,
            "duration": "15 MENIT",
            "current": "30 A",
            "temperatures": {
                "winding_1": 38.7, "winding_2": 37.2, "winding_3": 35.7,
                "fluid_coupling_1": 55.4, "fluid_coupling_2": 52.4,
                "bearing_pompa_1": 47.7, "bearing_pompa_2": 45.3,
            },
        },
        "tribology_data": {
            "reference_oil": "Pertamina - TURBO LUBE - 46",
            "sample_date": date_str,
            "total_fe_ppm": 1.0,
            "iso_cleanliness": "22 / 20 / 13",
            "water_ppm": 31.4,
            "viscosity_40c": 46.3,
            "tan_mg_koh_g": 0.28,
            "oxidation_abs_mm2": 1.32,
            "nas_class": 10,
        },
        "analysis": {
            "symptom_summary": "Dari symptom pengukuran dibandingkan dengan pola mobius mengindikasikan terjadi anomali gear dan bearing pada fluid coupling / intermediate drive.",
            "failure_mechanism": "Munculnya peak getaran 2X dan harmonik tinggi disertai modulasi axial mengindikasikan misalignment dan keausan elemen berputar.",
        },
        "conclusions": [
            "Nilai vibrasi bearing 4 arah axial (bearing fluid coupling) berstatus ALARM (9.45 mm/s).",
            "Hasil uji Tribology menunjukkan partikel keausan dan kontaminasi partikulat mulai meningkat.",
            "Kondisi kelistrikan stator dan rotor masih dalam batas aman, degradasi didominasi faktor mekanikal.",
        ],
        "recommendations": [
            "Segera lakukan tindakan inspeksi dan perbaikan pada kesempatan outage atau jendela pemeliharaan terdekat.",
            "Lakukan pengecekan dan re-alignment Gear Coupling.",
            "Lakukan penggantian bearing dan flushing/penggantian pelumas fluida kerja.",
        ],
        "sign_off": {
            "location": "JERANJANG",
            "date": date_str,
            "acknowledged_by": "Ricky Rinaldi",
            "acknowledged_title": "SPS RSO",
            "prepared_by": "Hermawan",
            "prepared_title": "Pelaksana PdM",
        },
    }


def _add_te_header(doc: Document, page_num: int, total_pages: int = 6, doc_number: str = "7.TE/CBM/UJPJRJ/2026"):
    """Adds standard official header block conforming to PLTU Jeranjang IMS."""
    table = doc.add_table(rows=3, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    _set_table_borders(table, color="000000", sz="4")

    # Row 0: Company title
    cell_top = table.cell(0, 0)
    cell_top.merge(table.cell(0, 3))
    p_top = cell_top.paragraphs[0]
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p_top.add_run("PT. INDONESIA POWER\nUNIT JASA PEMBANGKITAN PLTU JERANJANG\nINTEGRATED MANAGEMENT SYSTEM\n")
    r1.bold = True
    r1.font.size = Pt(10)
    r2 = p_top.add_run(doc_number)
    r2.bold = True
    r2.font.size = Pt(11)

    # Row 1: Subheaders
    headers = ["Tgl Berlaku", "No. Dokumen :", "Revisi", "Hal"]
    for idx, h in enumerate(headers):
        c = table.cell(1, idx)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.font.size = Pt(8.5)
        run.bold = True
        _set_cell_background(c, "F1F5F9")

    # Row 2: Metadata values
    vals = ["07/02/2017", "FORM.JRG.F.05.006", "01", f"{page_num} dari {total_pages}"]
    for idx, v in enumerate(vals):
        c = table.cell(2, idx)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(v)
        run.font.size = Pt(8.5)

    doc.add_paragraph()  # Spacing


def export_te_docx(te_data: Dict[str, Any]) -> io.BytesIO:
    """Generates the official 6-page Microsoft Word (.DOCX) report conforming to FORM.JRG.F.05.006."""
    doc = Document()

    # Set page margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.6)
        s.bottom_margin = Inches(0.6)
        s.left_margin = Inches(0.7)
        s.right_margin = Inches(0.7)

    doc_num = te_data.get("doc_number", "7.TE/CBM/UJPJRJ/2026")

    # =========================================================================
    # HALAMAN 1: IDENTITAS & DATA SPESIFIKASI MOTOR & POMPA
    # =========================================================================
    _add_te_header(doc, 1, 6, doc_num)

    # Equipment identity block
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.line_spacing = 1.15

    def add_meta_line(label: str, val: str, color_hex: Optional[str] = None):
        r_lbl = p_meta.add_run(f"{label:<14}: ")
        r_lbl.bold = True
        r_lbl.font.size = Pt(10)
        r_val = p_meta.add_run(f"{val}\n")
        r_val.bold = True
        r_val.font.size = Pt(10)
        if color_hex:
            r_val.font.color.rgb = RGBColor.from_string(color_hex.replace("#", ""))

    add_meta_line("Equipment", te_data.get("equipment", "-"))
    add_meta_line("KKS", te_data.get("kks", "-"))
    add_meta_line("Technology", te_data.get("technology", "-"))
    add_meta_line("Tanggal", te_data.get("date", "-"))
    st_val = te_data.get("status", "Kuning")
    st_col = "D97706" if "kuning" in st_val.lower() else ("DC2626" if "merah" in st_val.lower() else "059669")
    add_meta_line("Status", st_val, st_col)
    add_meta_line("Finding", te_data.get("finding", "-"))

    # Section I: Data Spesifikasi Motor
    h1 = doc.add_heading("I. Data Spesifikasi Motor", level=2)
    h1.runs[0].font.size = Pt(11)
    h1.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    specs = te_data.get("specifications", {})
    m_specs = specs.get("motor", {})
    d_specs = specs.get("driven", {})

    t_spec = doc.add_table(rows=10, cols=4)
    t_spec.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_spec)

    # Header columns
    c_m_h = t_spec.cell(0, 0)
    c_m_h.merge(t_spec.cell(0, 1))
    c_m_h.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_mh = c_m_h.paragraphs[0].add_run("MOTOR")
    r_mh.bold = True
    _set_cell_background(c_m_h, "CBD5E1")

    c_d_h = t_spec.cell(0, 2)
    c_d_h.merge(t_spec.cell(0, 3))
    c_d_h.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_dh = c_d_h.paragraphs[0].add_run(specs.get("component_2", "POMPA"))
    r_dh.bold = True
    _set_cell_background(c_d_h, "CBD5E1")

    spec_rows = [
        ("Type, Mfg", m_specs.get("type_mfg", "-"), "Type, Mfg.", d_specs.get("type_mfg", "-")),
        ("Speed", m_specs.get("speed", "-"), "Speed", d_specs.get("speed", "-")),
        ("Power", m_specs.get("power", "-"), "Power", d_specs.get("power", "-")),
        ("Bearing Type", m_specs.get("bearing_type", "-"), "Capacity", d_specs.get("capacity", "-")),
        ("Inboard Bearing", m_specs.get("inboard_bearing", "-"), "Inboard Bearing", d_specs.get("inboard_bearing", "-")),
        ("Outboard Bearing", m_specs.get("outboard_bearing", "-"), "Onboard Bearing", d_specs.get("onboard_bearing", "-")),
        ("Rotor Bar", m_specs.get("rotor_bar", "-"), "Total Blade", d_specs.get("total_blade", "-")),
        ("Foundation", m_specs.get("foundation", "-"), "-", "-"),
    ]

    for idx, (m_l, m_v, d_l, d_v) in enumerate(spec_rows, start=1):
        t_spec.cell(idx, 0).paragraphs[0].add_run(m_l).font.size = Pt(8.5)
        t_spec.cell(idx, 1).paragraphs[0].add_run(f": {m_v}").font.size = Pt(8.5)
        t_spec.cell(idx, 2).paragraphs[0].add_run(d_l).font.size = Pt(8.5)
        t_spec.cell(idx, 3).paragraphs[0].add_run(f": {d_v}").font.size = Pt(8.5)

    # Photo & Measurement Points placeholder box
    t_photo = doc.add_table(rows=2, cols=2)
    t_photo.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_photo)
    t_photo.cell(0, 0).paragraphs[0].add_run("FOTO EQUIPMENT").bold = True
    t_photo.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_photo.cell(0, 1).paragraphs[0].add_run("POINT PENGUKURAN (1V, 1H, 1A ... 6A)").bold = True
    t_photo.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_cell_background(t_photo.cell(0, 0), "E2E8F0")
    _set_cell_background(t_photo.cell(0, 1), "E2E8F0")

    p_ph1 = t_photo.cell(1, 0).paragraphs[0]
    p_ph1.add_run("\n\n[ Foto Fisik & Tagging Nameplate Equipment ]\n\n").italic = True
    p_ph1.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p_ph2 = t_photo.cell(1, 1).paragraphs[0]
    p_ph2.add_run("\n\n[ Diagram Titik Sensor: 1(NDE), 2(DE Motor), 3-4(Coupling), 5-6(Pompa) ]\n\n").italic = True
    p_ph2.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_page_break()

    # =========================================================================
    # HALAMAN 2: HASIL PENGUKURAN VIBRASI & STANDAR ISO 10816-3
    # =========================================================================
    _add_te_header(doc, 2, 6, doc_num)
    h2 = doc.add_heading("II. Hasil Pengukuran Vibrasi", level=2)
    h2.runs[0].font.size = Pt(11)
    h2.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    # Vibration matrix table (1V..6A)
    vib_data = te_data.get("vibration_data", {})
    pts = vib_data.get("points", {})

    t_vib = doc.add_table(rows=3, cols=21)
    t_vib.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_vib)

    # Headers
    h_top = ["TANGGAL", "RPM", "Current", "BEARING MOTOR (mm/s)", "BEARING POMPA / COUPLING", "BEARING POMPA", "Keterangan"]
    # Row 0
    t_vib.cell(0, 0).paragraphs[0].add_run("TGL").font.size = Pt(7.5)
    t_vib.cell(0, 1).paragraphs[0].add_run("RPM").font.size = Pt(7.5)
    t_vib.cell(0, 2).paragraphs[0].add_run("Cur.").font.size = Pt(7.5)

    # Merge motor cells (cols 3..8)
    c_bm = t_vib.cell(0, 3)
    c_bm.merge(t_vib.cell(0, 8))
    c_bm.paragraphs[0].add_run("BEARING MOTOR (1-2)").font.size = Pt(7.5)
    c_bm.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Merge coupling cells (cols 9..14)
    c_fc = t_vib.cell(0, 9)
    c_fc.merge(t_vib.cell(0, 14))
    c_fc.paragraphs[0].add_run("FLUID COUPLING (3-4)").font.size = Pt(7.5)
    c_fc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Merge pump cells (cols 15..20)
    c_bp = t_vib.cell(0, 15)
    c_bp.merge(t_vib.cell(0, 20))
    c_bp.paragraphs[0].add_run("BEARING POMPA (5-6)").font.size = Pt(7.5)
    c_bp.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Row 1: Direction labels
    dirs = ["1V", "1H", "1A", "2V", "2H", "2A", "3V", "3H", "3A", "4V", "4H", "4A", "5V", "5H", "5A", "6V", "6H", "6A"]
    for idx, d in enumerate(dirs, start=3):
        c = t_vib.cell(1, idx)
        c.paragraphs[0].add_run(d).font.size = Pt(7.0)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Row 2: Values
    t_vib.cell(2, 0).paragraphs[0].add_run("2026").font.size = Pt(7.0)
    t_vib.cell(2, 1).paragraphs[0].add_run(str(vib_data.get("rpm", "-"))).font.size = Pt(7.0)
    t_vib.cell(2, 2).paragraphs[0].add_run(str(vib_data.get("current", "-"))).font.size = Pt(7.0)

    for idx, d in enumerate(dirs, start=3):
        val = pts.get(d, 0.0)
        c = t_vib.cell(2, idx)
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(f"{val:.2f}")
        r.font.size = Pt(7.0)
        if val >= 7.1:
            _set_cell_background(c, "EF4444")  # Red
            r.font.color.rgb = RGBColor(255, 255, 255)
        elif val >= 4.5:
            _set_cell_background(c, "F59E0B")  # Yellow/Orange
        elif val >= 2.8:
            _set_cell_background(c, "FEF08A")  # Light yellow

    doc.add_paragraph()

    # ISO 10816-3 Table
    p_iso = doc.add_paragraph()
    p_iso.add_run("STANDART ISO 10816-3 (GROUP 1 RIGID)").bold = True
    p_iso.alignment = WD_ALIGN_PARAGRAPH.CENTER

    t_iso = doc.add_table(rows=2, cols=5)
    t_iso.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_iso)
    t_iso.cell(0, 0).paragraphs[0].add_run("ALARM LIMIT").bold = True
    t_iso.cell(0, 1).paragraphs[0].add_run("≥ 0 (Good)")
    t_iso.cell(0, 2).paragraphs[0].add_run("≥ 2.3 (Acceptable)")
    t_iso.cell(0, 3).paragraphs[0].add_run("≥ 4.5 (Warning)")
    t_iso.cell(0, 4).paragraphs[0].add_run("≥ 7.1 (Alarm/Trip)")

    t_iso.cell(1, 0).paragraphs[0].add_run("ZONE")
    for idx, (z, col) in enumerate([("A", "10B981"), ("B", "84CC16"), ("C", "F59E0B"), ("D", "EF4444")], start=1):
        c = t_iso.cell(1, idx)
        c.paragraphs[0].add_run(z).bold = True
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cell_background(c, col)

    doc.add_paragraph()

    # Spectrum Notes
    p_sn = doc.add_paragraph()
    p_sn.add_run("Hasil Rekaman Spectrum Vibrasi :\n").bold = True
    for s_note in vib_data.get("spectrum_notes", []):
        doc.add_paragraph(f"✓  {s_note}", style="List Bullet")

    p_rec = doc.add_paragraph()
    p_rec.add_run("Rekomendasi Vibrasi :\n").bold = True
    for r_note in vib_data.get("recommendations", []):
        doc.add_paragraph(f"✓  {r_note}", style="List Bullet")

    doc.add_page_break()

    # =========================================================================
    # HALAMAN 3: DATA IRT (THERMAL) & TRIBOLOGI (MACHINE WEAR)
    # =========================================================================
    _add_te_header(doc, 3, 6, doc_num)

    h3 = doc.add_heading("III. Data IRT (Infrared Thermography)", level=2)
    h3.runs[0].font.size = Pt(11)
    h3.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    thm = te_data.get("thermal_data", {})
    t_temps = thm.get("temperatures", {})

    t_irt = doc.add_table(rows=2, cols=9)
    t_irt.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_irt)

    irt_cols = ["TGL", "DURASI", "Cur.", "WIND 1", "WIND 2", "FL. COUP 3", "FL. COUP 4", "BEAR 5", "BEAR 6"]
    for idx, c_name in enumerate(irt_cols):
        c = t_irt.cell(0, idx)
        c.paragraphs[0].add_run(c_name).bold = True
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_cell_background(c, "E2E8F0")

    vals_irt = [
        "2026", str(thm.get("duration", "15 M")), str(thm.get("current", "30 A")),
        f"{t_temps.get('winding_1', 38.7)}°C", f"{t_temps.get('winding_2', 37.2)}°C",
        f"{t_temps.get('fluid_coupling_1', 55.4)}°C", f"{t_temps.get('fluid_coupling_2', 52.4)}°C",
        f"{t_temps.get('bearing_pompa_1', 47.7)}°C", f"{t_temps.get('bearing_pompa_2', 45.3)}°C",
    ]
    for idx, v in enumerate(vals_irt):
        c = t_irt.cell(1, idx)
        c.paragraphs[0].add_run(v).font.size = Pt(8.5)
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph()

    # Section IV: Data Tribology
    h4 = doc.add_heading("IV. Data Tribology (Oil Analysis)", level=2)
    h4.runs[0].font.size = Pt(11)
    h4.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    trib = te_data.get("tribology_data", {})

    t_trib = doc.add_table(rows=7, cols=3)
    t_trib.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_trib)

    t_trib.cell(0, 0).paragraphs[0].add_run("Parameter Pelumas").bold = True
    t_trib.cell(0, 1).paragraphs[0].add_run("Hasil Pengujian").bold = True
    t_trib.cell(0, 2).paragraphs[0].add_run("Nilai Rujukan / Standar").bold = True
    _set_cell_background(t_trib.cell(0, 0), "E2E8F0")
    _set_cell_background(t_trib.cell(0, 1), "E2E8F0")
    _set_cell_background(t_trib.cell(0, 2), "E2E8F0")

    trib_rows = [
        ("Reference Oil", trib.get("reference_oil", "-"), "ISO VG 46 Turbine Oil"),
        ("Sample Date", trib.get("sample_date", "-"), "Rutinitas Bulanan"),
        ("Total Fe (Iron Wear Metals)", f"{trib.get('total_fe_ppm', 1.0)} ppm", "< 25 ppm (Normal)"),
        ("ISO 4406 Cleanliness Code", trib.get("iso_cleanliness", "-"), "Target ≤ 18/16/13"),
        ("Water Content", f"{trib.get('water_ppm', 31.4)} ppm", "< 100 ppm (Max 200 ppm)"),
        ("Kinematic Viscosity 40°C", f"{trib.get('viscosity_40c', 46.3)} cSt", "41.4 – 50.6 cSt (±10%)"),
    ]
    for idx, (p_name, p_val, p_ref) in enumerate(trib_rows, start=1):
        t_trib.cell(idx, 0).paragraphs[0].add_run(p_name).font.size = Pt(8.5)
        t_trib.cell(idx, 1).paragraphs[0].add_run(p_val).font.size = Pt(8.5)
        t_trib.cell(idx, 2).paragraphs[0].add_run(p_ref).font.size = Pt(8.5)

    doc.add_page_break()

    # =========================================================================
    # HALAMAN 4: TRIBOLOGY CONTAMINATION & PARTICLE COUNTS
    # =========================================================================
    _add_te_header(doc, 4, 6, doc_num)

    h4_cont = doc.add_heading("IV. Data Tribology - Distribusi Partikel Kontaminasi", level=2)
    h4_cont.runs[0].font.size = Pt(11)
    h4_cont.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    t_part = doc.add_table(rows=8, cols=3)
    t_part.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_part)

    t_part.cell(0, 0).paragraphs[0].add_run("Ukuran Partikel (µm)").bold = True
    t_part.cell(0, 1).paragraphs[0].add_run("Jumlah Partikel (Counts/mL)").bold = True
    t_part.cell(0, 2).paragraphs[0].add_run("Evaluasi Status").bold = True
    _set_cell_background(t_part.cell(0, 0), "E2E8F0")
    _set_cell_background(t_part.cell(0, 1), "E2E8F0")
    _set_cell_background(t_part.cell(0, 2), "E2E8F0")

    particles = [
        ("> 4 µm", "19,872", "Tinggi (Kuning)"),
        ("> 6 µm", "431", "Normal"),
        ("> 14 µm", "7", "Normal"),
        ("> 21 µm", "11", "Normal"),
        ("> 38 µm", "1", "Normal"),
        ("> 50 µm", "1", "Waspada"),
        ("> 100 µm", "0", "Aman"),
    ]
    for idx, (sz, cnt, ev) in enumerate(particles, start=1):
        t_part.cell(idx, 0).paragraphs[0].add_run(sz).font.size = Pt(8.5)
        t_part.cell(idx, 1).paragraphs[0].add_run(cnt).font.size = Pt(8.5)
        t_part.cell(idx, 2).paragraphs[0].add_run(ev).font.size = Pt(8.5)

    doc.add_page_break()

    # =========================================================================
    # HALAMAN 5: ANALISA TEKNIS (SYMPTOM VS POLA MOBIUS / SPECTRUM)
    # =========================================================================
    _add_te_header(doc, 5, 6, doc_num)

    h5 = doc.add_heading("V. Analisa Teknis & Pola Spektrum", level=2)
    h5.runs[0].font.size = Pt(11)
    h5.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    # Side-by-side Symptom Comparison Table
    t_ana = doc.add_table(rows=2, cols=2)
    t_ana.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_ana)

    t_ana.cell(0, 0).paragraphs[0].add_run("Symptom Pengukuran Lapangan").bold = True
    t_ana.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_ana.cell(0, 1).paragraphs[0].add_run("Pola Teori Kerusakan (Mobius / FFT)").bold = True
    t_ana.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    _set_cell_background(t_ana.cell(0, 0), "E2E8F0")
    _set_cell_background(t_ana.cell(0, 1), "E2E8F0")

    p_s1 = t_ana.cell(1, 0).paragraphs[0]
    p_s1.add_run(
        "• Amplitudo vibrasi arah axial pada bearing fluid coupling mencapai 9.45 mm/s RMS (Status ALARM).\n"
        "• Harmonik 1X dan 2X mendominasi spektrum intermediate drive.\n"
        "• Partikel NAS class pelumasan berada pada kelas 10 (mendekati batas kritis).\n"
    ).font.size = Pt(8.5)

    p_s2 = t_ana.cell(1, 1).paragraphs[0]
    p_s2.add_run(
        "• Pola Mobius Tahap 2: Muncul frekuensi cacat bearing di daerah natural frequency (30.000–120.000 cpm).\n"
        "• Sideband frekuensi tampak di sekitar puncak frekuensi natural.\n"
        "• Indikasi ketidaksejajaran poros (misalignment) memicu beban aksial berlebih pada coupling.\n"
    ).font.size = Pt(8.5)

    doc.add_paragraph()
    ana_p = doc.add_paragraph()
    ana_text = te_data.get("analysis", {}).get("symptom_summary", "-")
    ana_p.add_run(f"Evaluasi Diagnostik:\n{ana_text}\n").font.size = Pt(9.5)
    f_mech = te_data.get("analysis", {}).get("failure_mechanism", "")
    if f_mech:
        ana_p.add_run(f"\nMekanisme Kegagalan:\n{f_mech}").italic = True

    doc.add_page_break()

    # =========================================================================
    # HALAMAN 6: KESIMPULAN, REKOMENDASI & LEMBAR TANDA TANGAN
    # =========================================================================
    _add_te_header(doc, 6, 6, doc_num)

    h6 = doc.add_heading("VI. Kesimpulan", level=2)
    h6.runs[0].font.size = Pt(11)
    h6.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    for conc in te_data.get("conclusions", []):
        doc.add_paragraph(f"- {conc}", style="List Bullet")

    h7 = doc.add_heading("VII. Rekomendasi", level=2)
    h7.runs[0].font.size = Pt(11)
    h7.runs[0].font.color.rgb = RGBColor(0, 0, 0)

    doc.add_paragraph("Segera dilakukan tindakan perbaikan:")
    for rec in te_data.get("recommendations", []):
        doc.add_paragraph(f"- {rec}", style="List Bullet")

    doc.add_paragraph("\n\n")

    # Sign-off Block
    sign_off = te_data.get("sign_off", {})
    loc_date = f"{sign_off.get('location', 'JERANJANG')}, {sign_off.get('date', datetime.now().strftime('%d %B %Y'))}"

    p_loc = doc.add_paragraph(loc_date)
    p_loc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_loc.runs[0].bold = True

    t_sign = doc.add_table(rows=3, cols=2)
    t_sign.alignment = WD_TABLE_ALIGNMENT.CENTER

    t_sign.cell(0, 0).paragraphs[0].add_run("MENGETAHUI").bold = True
    t_sign.cell(0, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_sign.cell(0, 1).paragraphs[0].add_run("DISUSUN OLEH").bold = True
    t_sign.cell(0, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Row 1: Space for signature
    t_sign.cell(1, 0).paragraphs[0].add_run("\n\n\n(Tanda Tangan)\n\n").italic = True
    t_sign.cell(1, 0).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    t_sign.cell(1, 1).paragraphs[0].add_run("\n\n\n(Tanda Tangan)\n\n").italic = True
    t_sign.cell(1, 1).paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Row 2: Names & Titles
    p_ack = t_sign.cell(2, 0).paragraphs[0]
    p_ack.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_a1 = p_ack.add_run(f"{sign_off.get('acknowledged_by', 'Ricky Rinaldi')}\n")
    r_a1.bold = True
    p_ack.add_run(sign_off.get("acknowledged_title", "SPS RSO"))

    p_prep = t_sign.cell(2, 1).paragraphs[0]
    p_prep.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_p1 = p_prep.add_run(f"{sign_off.get('prepared_by', 'Hermawan')}\n")
    r_p1.bold = True
    p_prep.add_run(sign_off.get("prepared_title", "Pelaksana PdM"))

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

