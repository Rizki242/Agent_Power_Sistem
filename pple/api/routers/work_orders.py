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
    update_work_order_status,
)



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
