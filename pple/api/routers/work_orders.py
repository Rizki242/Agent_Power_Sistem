"""Work Orders API router."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.data_loader import get_data_path

router = APIRouter(prefix="/api", tags=["work-orders"])

from src.work_orders import (
    get_work_orders_store_path as _get_work_orders_store_path,
    load_work_orders as _load_work_orders,
    save_work_orders as _save_work_orders,
    seed_work_orders as _seed_work_orders,
    create_work_order,
    generate_cbm_work_order,
    update_work_order_status,
)


class ApproveWORequest(BaseModel):
    wo_number: str
    approved_by: str
    action: Optional[str] = "Approve"


class CreateWORequest(BaseModel):
    equipment: str
    title: str
    priority: Optional[str] = "P3 - Medium"
    domain: Optional[str] = "General"
    reason: Optional[str] = ""
    required_tools: Optional[List[str]] = None
    required_parts: Optional[List[str]] = None
    required_manpower: Optional[str] = "1 Technician"
    target_completion_date: Optional[str] = ""
    created_by: Optional[str] = "API Client"


class GenerateCBMWORequest(BaseModel):
    equipment: str
    domain: Optional[str] = "Multi-Domain CBM"
    severity: Optional[str] = "WARNING"
    anomaly_desc: Optional[str] = ""
    recommendations: Optional[List[str]] = None
    created_by: Optional[str] = "CBM Diagnostic Engine"


@router.get("/workorders")
def get_work_orders(
    equipment: Optional[str] = None,
    domain: Optional[str] = None,
    status: Optional[str] = None,
):
    work_orders = _load_work_orders()
    results = []
    for wo in work_orders:
        if equipment and equipment.upper() not in str(wo.get("equipment", "")).upper():
            continue
        if domain and domain.upper() not in str(wo.get("domain", "")).upper():
            continue
        if status and status.lower() not in str(wo.get("status", "")).lower():
            continue
        results.append(wo)
    return {"work_orders": results, "count": len(results)}


@router.post("/workorders")
def create_new_work_order(req: CreateWORequest):
    new_wo = create_work_order(
        equipment=req.equipment,
        title=req.title,
        priority=req.priority or "P3 - Medium",
        domain=req.domain or "General",
        reason=req.reason or "",
        required_tools=req.required_tools,
        required_parts=req.required_parts,
        required_manpower=req.required_manpower or "1 Technician",
        target_completion_date=req.target_completion_date or "",
        created_by=req.created_by or "API Client",
    )
    return {"status": "success", "work_order": new_wo}


@router.post("/workorders/generate-cbm")
def generate_from_cbm(req: GenerateCBMWORequest):
    new_wo = generate_cbm_work_order(
        equipment=req.equipment,
        domain=req.domain or "Multi-Domain CBM",
        severity=req.severity or "WARNING",
        anomaly_desc=req.anomaly_desc or "",
        recommendations=req.recommendations,
        created_by=req.created_by or "CBM Diagnostic Engine",
    )
    return {"status": "success", "work_order": new_wo}


@router.post("/workorders/approve")
def approve_work_order(req: ApproveWORequest):
    work_orders = _load_work_orders()
    for wo in work_orders:
        if wo["wo_number"] == req.wo_number:
            if req.action == "Approve":
                wo["status"] = f"Approved by {req.approved_by} - In Progress"
            elif req.action == "Complete":
                wo["status"] = f"Completed & Closed by {req.approved_by}"
            elif req.action == "Reject":
                wo["status"] = f"Rejected by {req.approved_by}"
            _save_work_orders(work_orders)
            return {"status": "success", "work_order": wo}

    raise HTTPException(status_code=404, detail="Work Order not found")
