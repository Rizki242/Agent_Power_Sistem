"""Legacy-compatible HTTP routes for specialist condition-monitoring domains.

This router is intentionally thin: domain loading and diagnosis remain in the
shared ``src`` modules while the FastAPI layer only validates query inputs,
maps missing records to HTTP errors, and preserves the existing response
envelopes consumed by the React frontend.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from pple.api.schemas.specialist import (
    DGADetailResponse,
    DGAListResponse,
    DGASummaryResponse,
    PDAssessmentResponse,
    PDListResponse,
    PDSampleItem,
    PDSummaryResponse,
    ThermalListResponse,
    ThermalSummaryResponse,
    TribologyDetailResponse,
    TribologyListResponse,
    TribologySummaryResponse,
)
from src.dga_data import (
    get_dga_summary,
    get_dga_transformer_detail,
    search_dga_transformers,
)
from src.pd_data import get_pd_sample_detail, get_pd_summary, search_pd_samples
from src.thermal_data import (
    get_thermal_record_detail,
    get_thermal_summary,
    load_thermal_irt_tests,
)
from src.tribology_data import (
    get_tribology_sample_detail,
    get_tribology_summary,
    search_tribology_samples,
)


router = APIRouter(prefix="/api", tags=["specialist-domains"])


@router.get("/dga/summary", response_model=DGASummaryResponse)
def get_dga_summary_endpoint():
    """Return summary counts for transformers by status and unit."""
    try:
        return get_dga_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/dga/transformers", response_model=DGAListResponse)
def get_dga_transformers_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Return transformers with DGA analysis."""
    try:
        transformers = search_dga_transformers(unit=unit, status=status, search=search)
        return {"transformers": transformers, "count": len(transformers)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/dga/transformers/{transformer_id}", response_model=DGADetailResponse)
def get_dga_transformer_detail_endpoint(transformer_id: str):
    """Return full DGA details and historical trends for a transformer."""
    target = get_dga_transformer_detail(transformer_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Transformer {transformer_id} not found")
    return target


@router.get("/tribology/summary", response_model=TribologySummaryResponse)
def get_tribology_summary_endpoint():
    """Return summary counts for lubrication samples."""
    try:
        return get_tribology_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tribology/samples", response_model=TribologyListResponse)
def get_tribology_samples_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    oil_type: Optional[str] = None,
    search: Optional[str] = None,
):
    """Return oil samples with their evaluation."""
    try:
        samples = search_tribology_samples(
            unit=unit,
            status=status,
            oil_type=oil_type,
            search=search,
        )
        return {"samples": samples, "count": len(samples)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tribology/samples/{sample_id}", response_model=TribologyDetailResponse)
def get_tribology_sample_detail_endpoint(sample_id: str):
    """Return an oil-analysis sample and its historical trend."""
    target = get_tribology_sample_detail(sample_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
    return target


@router.get("/thermal/summary", response_model=ThermalSummaryResponse)
def get_thermal_summary_endpoint():
    """Return summary counts for IRT inspections."""
    try:
        return get_thermal_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/thermal/inspections", response_model=ThermalListResponse)
def get_thermal_inspections_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Return thermal IRT inspection points."""
    try:
        records = load_thermal_irt_tests()
        if unit and unit.upper() != "ALL":
            records = [record for record in records if record["unit"].upper() == unit.upper()]
        if status and status.upper() != "ALL":
            records = [record for record in records if record["status"].upper() == status.upper()]
        if search and search.strip():
            search_term = search.lower().strip()
            records = [
                record
                for record in records
                if search_term in record["equipment"].lower()
                or search_term in record["kks"].lower()
            ]
        return {"inspections": records, "count": len(records)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# PD currently uses illustrative defaults plus recorded overrides. Clients
# must retain the existing source-data disclaimer when presenting these routes.
@router.get("/pd/summary", response_model=PDSummaryResponse)
def get_pd_summary_endpoint():
    """Return summary counts for partial-discharge samples."""
    try:
        return get_pd_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/pd/samples", response_model=PDListResponse)
def get_pd_samples_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Return PD samples with evaluated status attached."""
    try:
        samples = search_pd_samples(unit=unit, status=status, search=search)
        return {"samples": samples, "count": len(samples)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/pd/samples/{sample_id}", response_model=PDSampleItem)
def get_pd_sample_detail_endpoint(sample_id: str):
    """Return one PD sample's PRPD parameters and status."""
    target = get_pd_sample_detail(sample_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
    return target


@router.get("/pd/samples/{sample_id}/assessment", response_model=PDAssessmentResponse)
def get_pd_sample_assessment(sample_id: str):
    """Run the PD specialist against one persisted or illustrative sample."""
    target = get_pd_sample_detail(sample_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")
    try:
        from src.agents.specialist_agents import PDAgent

        return PDAgent().evaluate(target["equipment"], target)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

