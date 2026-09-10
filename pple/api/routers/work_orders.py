"""Work Orders API router."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.data_loader import get_data_path

router = APIRouter(prefix="/api", tags=["work-orders"])

_work_orders_db: List[Dict[str, Any]] = []


def _seed_work_orders() -> List[Dict[str, Any]]:
    return [
        {
            "wo_number": "WO-202608-0101",
            "equipment": "BC 10.1",
            "title": "Investigasi Bearing & Re-greasing DE/NDE",
            "priority": "P2 - High",
            "reason": "AI Multi-Modal Fusion: Indikasi keausan bearing & suhu naik",
            "required_tools": ["Vibration Analyzer", "Thermal Camera", "Grease Gun"],
            "required_parts": ["Grease Shell Gadus S2", "Bearing 6314 C3"],
            "required_manpower": "2 Technicians",
            "target_completion_date": "2026-08-30",
            "status": "Draft - Awaiting Approval",
        },
        {
            "wo_number": "WO-202608-0102",
            "equipment": "BFP 1A",
            "title": "Laser Alignment Verification & Soft Foot Check",
            "priority": "P3 - Medium",
            "reason": "AI Diagnostics: Modulasi spektrum 2X & getaran aksial",
            "required_tools": ["Laser Alignment Kit", "Dial Indicator"],
            "required_parts": ["Stainless Steel Shim Pack 0.05-1.0mm"],
            "required_manpower": "1 Alignment Specialist + 1 Mechanic",
            "target_completion_date": "2026-09-05",
            "status": "Approved - Ready for Execution",
        },
    ]


def _get_work_orders_store_path() -> str:
    configured = os.environ.get("WORK_ORDERS_FILE")
    if configured and configured.strip():
        return os.path.abspath(configured.strip())
    return get_data_path("runtime", "work_orders.json")


def _load_work_orders() -> List[Dict[str, Any]]:
    global _work_orders_db
    path = _get_work_orders_store_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            if isinstance(data, list):
                _work_orders_db = data
                return data
        except Exception:
            pass

    _work_orders_db = _seed_work_orders()
    return list(_work_orders_db)


def _save_work_orders(work_orders: List[Dict[str, Any]]) -> str:
    global _work_orders_db
    path = _get_work_orders_store_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fp:
        json.dump(work_orders, fp, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    _work_orders_db = list(work_orders)
    return path


class ApproveWORequest(BaseModel):
    wo_number: str
    approved_by: str
    action: Optional[str] = "Approve"


@router.get("/workorders")
def get_work_orders():
    work_orders = _load_work_orders()
    return {"work_orders": work_orders, "count": len(work_orders)}


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
