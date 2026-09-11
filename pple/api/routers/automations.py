"""Automation workflow delivery adapter."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.automations import (
    create_workflow, execute_run, list_runs, list_workflows,
    queue_run, retry_run, set_workflow_enabled,
)

router = APIRouter(prefix="/api/automations", tags=["automations"])


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    action: Literal["learning_cycle", "knowledge_health_check"]
    interval_minutes: int = Field(ge=5, le=10080)
    approval_required: bool = True


class WorkflowState(BaseModel):
    enabled: bool


class ApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=100)


class WorkflowEnvelope(BaseModel):
    workflow: dict[str, Any]


class WorkflowListEnvelope(BaseModel):
    workflows: list[dict[str, Any]]
    count: int


class RunEnvelope(BaseModel):
    run: dict[str, Any]


class RunListEnvelope(BaseModel):
    runs: list[dict[str, Any]]
    count: int


@router.get("/workflows", response_model=WorkflowListEnvelope)
def get_workflows():
    workflows = list_workflows()
    return {"workflows": workflows, "count": len(workflows)}


@router.post("/workflows", response_model=WorkflowEnvelope, status_code=status.HTTP_201_CREATED)
def add_workflow(body: WorkflowCreate):
    return {"workflow": create_workflow(**body.model_dump())}


@router.patch("/workflows/{workflow_id}", response_model=WorkflowEnvelope)
def update_workflow(workflow_id: str, body: WorkflowState):
    workflow = set_workflow_enabled(workflow_id, body.enabled)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan")
    return {"workflow": workflow}


@router.post("/workflows/{workflow_id}/run", response_model=RunEnvelope, status_code=status.HTTP_202_ACCEPTED)
def start_workflow(workflow_id: str):
    run = queue_run(workflow_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow tidak ditemukan")
    if run["status"] == "QUEUED":
        run = execute_run(run["id"])
    return {"run": run}


@router.get("/runs", response_model=RunListEnvelope)
def get_runs():
    runs = list_runs()
    return {"runs": runs, "count": len(runs)}


@router.post("/runs/{run_id}/approve", response_model=RunEnvelope)
def approve_run(run_id: str, body: ApprovalRequest):
    run = execute_run(run_id, approved_by=body.approved_by)
    if run is None:
        raise HTTPException(status_code=404, detail="Run tidak ditemukan")
    return {"run": run}


@router.post("/runs/{run_id}/retry", response_model=RunEnvelope, status_code=status.HTTP_202_ACCEPTED)
def retry_failed_run(run_id: str):
    run = retry_run(run_id)
    if run is None:
        raise HTTPException(status_code=409, detail="Hanya run gagal yang dapat diulang")
    return {"run": run}
