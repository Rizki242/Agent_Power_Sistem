"""Generic /api/v2/domain/* REST API over the five condition-monitoring
domains' shared measurement store (docs/final.md Phase 24 - the same
"converge on one service layer" goal as pple/api/router.py).

The Streamlit dashboard (src.components.domain_workspace) already covers
upload/preview/report for Vibrasi/DGA/Tribology/Thermal/PD, but only from
inside Streamlit - the React frontend and the pple CLI had no way to reach
the same features. This router is a thin HTTP layer over the exact same
src.domain_measurements / src.domain_ingest / src.domain_report / (for
Vibrasi) src.vibration_report modules the Streamlit pages call, per
CLAUDE.md's "FastAPI ... do not duplicate business logic" rule - every
endpoint here delegates, none re-implements ingest/validation/report logic.

Additive only, exactly like pple/api/router.py: mounted alongside the
legacy /api/* and the module-registry /api/v2/* routes, never replacing
either.
"""

from __future__ import annotations

from datetime import date, datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src import domain_ingest as ingest
from src import domain_measurements as dm
from src import domain_report as report

router = APIRouter(prefix="/api/v2/domain", tags=["domain-measurements-v2"])

_REPORT_MEDIA_TYPES = {
    "csv": "text/csv",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _canon_or_404(domain: str) -> str:
    try:
        return dm.canon_domain(domain)
    except dm.UnknownDomainError:
        raise HTTPException(status_code=404, detail=f"Domain '{domain}' tidak dikenali. Pilihan: {', '.join(dm.DOMAINS)}")


def _parse_date(value: Optional[str], field: str) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=422, detail=f"'{field}' harus berformat YYYY-MM-DD, dapat '{value}'")


@router.get("/domains")
def list_domains():
    """The five domains this store serves, with their label and parameter list."""
    return {
        "domains": [
            {
                "domain": domain,
                "label": ingest.profile(domain)["label"],
                "parameters": [
                    {"key": spec.key, "label": spec.label, "uom": spec.uom, "numeric": spec.numeric}
                    for spec in ingest.parameter_specs(domain)
                ],
            }
            for domain in dm.DOMAINS
        ]
    }


@router.get("/{domain}/measurements")
def list_measurements(
    domain: str,
    equipment: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 500,
):
    """Stored readings for one domain, optionally scoped to one equipment
    and/or a date range (YYYY-MM-DD) - the same data the Streamlit Tren &
    Riwayat / Laporan tabs read via src.domain_measurements.filter_measurements."""
    domain = _canon_or_404(domain)
    frame = dm.filter_measurements(
        domain,
        equipment=equipment or None,
        date_start=_parse_date(start, "start"),
        date_end=_parse_date(end, "end"),
    )
    frame = frame.sort_values("test_date", ascending=False).head(max(1, limit))
    # astype(object) before .where(): on a float64 column, assigning None
    # in place of NaN is silently coerced right back to NaN (a float
    # column can't hold None) - json.dumps then rejects NaN as
    # non-compliant. Casting to object first lets None actually stick.
    rows = frame.astype(object).where(frame.notna(), None).to_dict(orient="records")
    for row in rows:
        if row.get("test_date") is not None:
            row["test_date"] = str(row["test_date"])[:10]
    return {"domain": domain, "count": len(rows), "measurements": rows}


@router.get("/{domain}/summary")
def domain_summary(domain: str, start: Optional[str] = None, end: Optional[str] = None):
    """Per-equipment specialist-agent verdicts for a period - the same
    computation src.domain_report.build_docx's "Ringkasan kondisi" table
    uses, without rendering a document."""
    domain = _canon_or_404(domain)
    frame = dm.load_measurements(domain)
    start_date = _parse_date(start, "start") or (frame["test_date"].min().date() if not frame.empty and frame["test_date"].notna().any() else date.today())
    end_date = _parse_date(end, "end") or date.today()
    data = report.collect_domain_data(domain, start_date, end_date)
    return {
        "domain": domain,
        "label": data["label"],
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "equipment_count": data["equipment_count"],
        "reading_count": data["reading_count"],
        "verdicts": data["verdicts"],
    }


@router.get("/{domain}/template.csv")
def download_template(domain: str):
    """A blank upload template with the identity + parameter columns this
    domain recognizes - what the Streamlit upload tab's "Unduh Template" links to."""
    domain = _canon_or_404(domain)
    return StreamingResponse(
        BytesIO(ingest.template_csv(domain)),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={domain.lower()}_template.csv"},
    )


@router.post("/{domain}/preview")
async def preview_upload(domain: str, file: UploadFile = File(...)):
    """Parse + validate an upload without writing anything - mirrors the
    Streamlit workspace's preview step so a client can show the same
    valid/rejected/unmapped breakdown before deciding to commit."""
    domain = _canon_or_404(domain)
    content = await file.read()
    try:
        preview = ingest.preview_upload(domain, file.filename or "upload.csv", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "domain": preview["domain"],
        "file_name": preview["file_name"],
        "source_rows": preview["source_rows"],
        "mapping": preview["mapping"],
        "unmapped_columns": preview["unmapped_columns"],
        "duplicate_columns": preview["duplicate_columns"],
        "valid_count": len(preview["valid"]),
        "rejected": preview["rejected"][:200],
        "parameters_found": preview["parameters_found"],
    }


@router.post("/{domain}/commit")
async def commit_upload(domain: str, file: UploadFile = File(...)):
    """Preview, archive, and write an upload in one call - the CLI/API
    equivalent of the Streamlit workspace's preview-then-commit flow
    collapsed into one request, since a script/CLI caller has no separate
    interactive preview step to review first. Re-validates server-side
    exactly like the Streamlit path does; nothing here trusts the client."""
    domain = _canon_or_404(domain)
    content = await file.read()
    file_name = file.filename or "upload.csv"
    try:
        preview = ingest.preview_upload(domain, file_name, content)
        batch_path, _ = ingest.create_batch(domain, file_name, content, preview)
        result = ingest.commit_batch(domain, batch_path, preview)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "domain": domain,
        "batch_id": result["batch_id"],
        "written": result["written"],
        "rejected": len(preview["rejected"]),
        "unmapped_columns": preview["unmapped_columns"],
        "duplicate_columns": preview["duplicate_columns"],
    }


@router.get("/{domain}/report")
def domain_report(domain: str, start: Optional[str] = None, end: Optional[str] = None, format: str = "docx"):
    """A period report (csv/docx/pptx) for one domain - the same
    src.domain_report builders the Streamlit workspace's Laporan tab
    downloads from."""
    domain = _canon_or_404(domain)
    fmt = format.lower()
    if fmt not in _REPORT_MEDIA_TYPES:
        raise HTTPException(status_code=422, detail=f"format harus salah satu dari: {', '.join(_REPORT_MEDIA_TYPES)}")

    frame = dm.load_measurements(domain)
    start_date = _parse_date(start, "start") or (frame["test_date"].min().date() if not frame.empty and frame["test_date"].notna().any() else date.today())
    end_date = _parse_date(end, "end") or date.today()

    bundle = report.build_report_bundle([domain], start_date, end_date, formats=[fmt])
    payload = bundle[fmt]
    filename = f"{domain.lower()}_report_{start_date}_{end_date}.{fmt}"
    return StreamingResponse(
        BytesIO(payload),
        media_type=_REPORT_MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/vibrasi/report/{equipment}")
def vibrasi_detail_report(equipment: str):
    """DETAIL REPORT VIBRASI (FORM.JRG.F.05.001) for one equipment, as a
    Word document - the same src.vibration_report.build_docx the Streamlit
    Vibrasi workspace's Laporan tab downloads. Not part of the generic
    {domain}/report above because this is a per-equipment plant form, not
    a period-wide multi-equipment report."""
    from src import vibration_report

    frame = dm.filter_measurements("VIBRASI", equipment=equipment)
    if frame.empty:
        raise HTTPException(status_code=404, detail=f"Tidak ada pengukuran Vibrasi untuk equipment '{equipment}'")

    payload = vibration_report.build_docx(equipment)
    return StreamingResponse(
        BytesIO(payload),
        media_type=_REPORT_MEDIA_TYPES["docx"],
        headers={"Content-Disposition": f"attachment; filename=detail_report_vibrasi_{equipment}.docx"},
    )
