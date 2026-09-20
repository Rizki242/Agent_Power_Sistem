"""Automated CBM Reports & Multi-Module Meeting PPTX Router.

Exposes scheduled & on-demand automated sample reports:
- Weekly reports per module (MCSA, VIBRASI, DGA)
- Monthly comprehensive multi-module reports (Asset Management / CBM PLTU Jeranjang September 2026)
- Multi-Module Meeting Presentation PPTX deck with prominent visual badges for standby modules.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from src import domain_report as report

router = APIRouter(prefix="/api/reports/automated", tags=["automated-reports"])

_MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "csv": "text/csv",
}


def _resolve_period(period_type: str, year: int = 2026, month: int = 9, week: int = 3) -> tuple[date, date]:
    """Helper to generate realistic sample date boundaries."""
    if period_type == "weekly":
        # Sample week in September 2026 (e.g. Week 3: 15-21 Sept 2026)
        if week == 1:
            return date(year, month, 1), date(year, month, 7)
        elif week == 2:
            return date(year, month, 8), date(year, month, 14)
        elif week == 3:
            return date(year, month, 15), date(year, month, 21)
        else:
            return date(year, month, 22), date(year, month, 28)
    # Default: Full Month September 2026
    return date(year, month, 1), date(year, month, 30)


@router.get("/summary")
def get_automated_reports_summary():
    """
    Katalog jadwal dan contoh otomatisasi laporan CBM PLTU Jeranjang:
    - Mingguan per modul (MCSA, VIBRASI, DGA)
    - Bulanan seluruh modul (Asset Management September 2026)
    - Meeting PPTX Keandalan Multi-Modul
    """
    # Sample period: September 2026
    start_m, end_m = _resolve_period("monthly", year=2026, month=9)
    start_w, end_w = _resolve_period("weekly", year=2026, month=9, week=3)

    # Collect preview data for 6 modules in September 2026
    all_domains = ["MCSA", "VIBRASI", "DGA", "PD", "TRIBOLOGY", "THERMAL"]
    module_statuses = []
    for d in all_domains:
        d_data = report.collect_domain_data(d, start_m, end_m)
        has_data = d_data["reading_count"] > 0
        module_statuses.append({
            "domain": d,
            "label": d_data["label"],
            "has_data": has_data,
            "reading_count": d_data["reading_count"],
            "equipment_count": d_data["equipment_count"],
            "status_label": "AKTIF DIUJI" if has_data else "STANDBY / BELUM ADA DATA PENGUJIAN",
            "standby_badge": "⚠️ [BELUM ADA DATA PENGUJIAN / STANDBY]" if not has_data else None,
        })

    sample_reports = [
        # --- 1. Laporan Mingguan Per Modul (6 Domain) ---
        {
            "id": "weekly-mcsa",
            "title": "Laporan Mingguan MCSA (Motor Current Signature)",
            "frequency": "Mingguan (Setiap Senin)",
            "module": "MCSA",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Analisis kondisi rotor bar, deviasi arus/tegangan, THD motor 6.3 kV dan 380V.",
            "download_docx": "/api/reports/automated/download/weekly/MCSA?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/MCSA?format=pptx",
        },
        {
            "id": "weekly-vibrasi",
            "title": "Laporan Mingguan Vibrasi Mekanikal",
            "frequency": "Mingguan (Setiap Selasa)",
            "module": "VIBRASI",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Evaluasi spektrum 1X, 2X, unbalance, misalignment, bearing fault, dan ISO 10816-3.",
            "download_docx": "/api/reports/automated/download/weekly/VIBRASI?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/VIBRASI?format=pptx",
        },
        {
            "id": "weekly-dga",
            "title": "Laporan Mingguan DGA (Gas Terlarut Trafo)",
            "frequency": "Mingguan (Setiap Rabu)",
            "module": "DGA",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Diagnosa gas terlarut trafo daya & bantu (Duval Triangle 1, Rogers Ratios, IEEE C57.104).",
            "download_docx": "/api/reports/automated/download/weekly/DGA?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/DGA?format=pptx",
        },
        {
            "id": "weekly-pd",
            "title": "Laporan Mingguan Partial Discharge (PD)",
            "frequency": "Mingguan (Setiap Kamis)",
            "module": "PD",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Inspeksi peluahan sebagian isolasi stator generator & switchgear 6.3 kV (IEC 60270).",
            "download_docx": "/api/reports/automated/download/weekly/PD?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/PD?format=pptx",
        },
        {
            "id": "weekly-tribology",
            "title": "Laporan Mingguan Tribologi & Pelumas",
            "frequency": "Mingguan (Setiap Jumat)",
            "module": "TRIBOLOGY",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Kualitas pelumas mesin turbin & pompa, viskositas ASTM D445, TAN, kadar air, dan ISO 4406.",
            "download_docx": "/api/reports/automated/download/weekly/TRIBOLOGY?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/TRIBOLOGY?format=pptx",
        },
        {
            "id": "weekly-thermal",
            "title": "Laporan Mingguan Thermal IRT",
            "frequency": "Mingguan (Setiap Sabtu)",
            "module": "THERMAL",
            "period": f"{start_w.strftime('%d %b %Y')} - {end_w.strftime('%d %b %Y')}",
            "description": "Pemetaan distribusi suhu inframerah, delta-T koneksi busbar dan bearing (ISO 18434-1).",
            "download_docx": "/api/reports/automated/download/weekly/THERMAL?format=docx",
            "download_pptx": "/api/reports/automated/download/weekly/THERMAL?format=pptx",
        },
        # --- 2. Laporan Bulanan Terpadu & Asset Management ---
        {
            "id": "monthly-all",
            "title": "Laporan Terpadu Seluruh Modul / Asset Management CBM PLTU Jeranjang",
            "frequency": "Bulanan (Akhir Bulan September 2026)",
            "module": "ALL",
            "period": f"01 September 2026 - 30 September 2026",
            "description": "Konsolidasi 6 domain CBM: Modul dengan pengujian menampilkan diagnosa detail; modul tanpa pengujian ditandai tegas [BELUM ADA DATA PENGUJIAN / STANDBY].",
            "download_docx": "/api/reports/automated/download/monthly?format=docx",
            "download_pptx": "/api/reports/automated/download/monthly?format=pptx",
            "download_csv": "/api/reports/automated/download/monthly?format=csv",
        },
        # --- 3. Slide Deck Meeting PPTX ---
        {
            "id": "meeting-pptx",
            "title": "Slide Deck Meeting Koordinasi Keandalan CBM (Multi-Modul)",
            "frequency": "Rapat Rutin Keandalan Bulanan",
            "module": "ALL",
            "period": "September 2026",
            "description": "Presentasi eksekutif 16:9 mencakup Matriks Kesiapan 6 Modul, temuan pengujian aktif, penanda modul standby, dan rekomendasi tindak lanjut.",
            "download_pptx": "/api/reports/automated/download/meeting-pptx",
        },
    ]

    return {
        "plant": "PLTU Jeranjang (3 × 25 MW)",
        "current_sample_month": "September 2026",
        "monthly_period": {"start": str(start_m), "end": str(end_m)},
        "weekly_period": {"start": str(start_w), "end": str(end_w)},
        "modules_status_september_2026": module_statuses,
        "sample_automated_reports": sample_reports,
    }


@router.get("/download/weekly/{module}")
def download_weekly_report(
    module: str,
    format: str = Query("docx", enum=["docx", "pptx"]),
    week: int = Query(3, ge=1, le=4),
):
    """Download contoh laporan mingguan untuk modul tertentu."""
    start_w, end_w = _resolve_period("weekly", year=2026, month=9, week=week)
    domain_upper = report.canon_report_domain(module)

    if format == "pptx":
        payload = report.build_pptx([domain_upper], start_w, end_w)
    else:
        payload = report.build_docx([domain_upper], start_w, end_w)

    filename = f"Laporan_Mingguan_{domain_upper}_Week{week}_Sept2026.{format}"
    return StreamingResponse(
        BytesIO(payload),
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/download/monthly/{module}")
def download_monthly_module_report(
    module: str,
    format: str = Query("docx", enum=["docx", "pptx"]),
    year: int = Query(2026),
    month: int = Query(9),
):
    """Download contoh laporan bulanan per modul tunggal (MCSA, VIBRASI, DGA, PD, TRIBOLOGY, THERMAL)."""
    return download_monthly_report(format=format, domains=module, year=year, month=month)


@router.get("/download/monthly")
def download_monthly_report(
    format: str = Query("docx", enum=["docx", "pptx", "csv"]),
    domains: Optional[str] = Query(None, description="Comma-separated domains, default all 6"),
    year: int = Query(2026),
    month: int = Query(9),
):
    """Download laporan bulanan terpadu seluruh modul atau per modul CBM PLTU Jeranjang."""
    start_m, end_m = _resolve_period("monthly", year=year, month=month)
    if domains:
        domain_list = [report.canon_report_domain(d.strip()) for d in domains.split(",") if d.strip()]
    else:
        domain_list = list(report.ALL_REPORT_DOMAINS)

    if format == "csv":
        payload = report.build_csv(domain_list, start_m, end_m)
    elif format == "pptx":
        payload = report.build_pptx(domain_list, start_m, end_m)
    else:
        payload = report.build_docx(domain_list, start_m, end_m)

    month_name = date(year, month, 1).strftime("%B_%Y")
    if len(domain_list) == 1:
        filename = f"Laporan_Bulanan_{domain_list[0]}_{month_name}.{format}"
    else:
        filename = f"Laporan_CBM_Asset_Management_PLTU_Jeranjang_{month_name}.{format}"

    return StreamingResponse(
        BytesIO(payload),
        media_type=_MEDIA_TYPES[format],
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/download/meeting-pptx")
def download_meeting_pptx(
    year: int = Query(2026),
    month: int = Query(9),
):
    """Download Slide Deck PPTX Meeting Keandalan CBM Multi-Modul."""
    start_m, end_m = _resolve_period("monthly", year=year, month=month)
    domain_list = list(report.ALL_REPORT_DOMAINS)

    payload = report.build_meeting_pptx(
        domain_list,
        start=start_m,
        end=end_m,
        title="Meeting Koordinasi Keandalan CBM & Asset Management",
        subtitle=f"PLTU Jeranjang (3 × 25 MW) — Evaluasi Periode {date(year, month, 1).strftime('%B %Y')}",
    )

    filename = f"Meeting_CBM_PLTU_Jeranjang_{date(year, month, 1).strftime('%B_%Y')}.pptx"
    return StreamingResponse(
        BytesIO(payload),
        media_type=_MEDIA_TYPES["pptx"],
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

