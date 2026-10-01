"""Small, auditable automation registry for local PPLE workflows."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


ALLOWED_ACTIONS = {"learning_cycle", "knowledge_health_check", "fleet_health_check"}


def _storage_dir() -> str:
    override = os.environ.get("PPLE_AUTOMATION_DIR")
    if override:
        return override
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "automations")


def _path(name: str) -> str:
    return os.path.join(_storage_dir(), name)


def _read(name: str) -> list[dict[str, Any]]:
    path = _path(name)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _write(name: str, records: list[dict[str, Any]]) -> None:
    directory = _storage_dir()
    os.makedirs(directory, exist_ok=True)
    target = _path(name)
    descriptor, temporary = tempfile.mkstemp(prefix="automation-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    except Exception:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


def list_workflows() -> list[dict[str, Any]]:
    return _read("workflows.json")


def list_runs() -> list[dict[str, Any]]:
    return list(reversed(_read("runs.json")))


def create_workflow(name: str, action: str, interval_minutes: int, approval_required: bool) -> dict[str, Any]:
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"Action '{action}' tidak diizinkan")
    now = datetime.now(timezone.utc).isoformat()
    workflow = {
        "id": f"WF-{uuid4().hex[:8].upper()}",
        "name": name.strip(),
        "action": action,
        "interval_minutes": interval_minutes,
        "approval_required": approval_required,
        "enabled": True,
        "created_at": now,
        "last_run_at": None,
    }
    workflows = list_workflows()
    workflows.append(workflow)
    _write("workflows.json", workflows)
    return workflow


def set_workflow_enabled(workflow_id: str, enabled: bool) -> dict[str, Any] | None:
    workflows = list_workflows()
    found = None
    for workflow in workflows:
        if workflow["id"] == workflow_id:
            workflow["enabled"] = enabled
            found = workflow
            break
    if found:
        _write("workflows.json", workflows)
    return found


def queue_run(workflow_id: str) -> dict[str, Any] | None:
    workflows = list_workflows()
    workflow = next((item for item in workflows if item["id"] == workflow_id), None)
    if workflow is None:
        return None
    now = datetime.now(timezone.utc).isoformat()
    run = {
        "id": f"RUN-{uuid4().hex[:10].upper()}", "workflow_id": workflow_id,
        "workflow_name": workflow["name"], "action": workflow["action"],
        "status": "WAITING_APPROVAL" if workflow["approval_required"] else "QUEUED",
        "created_at": now, "started_at": None, "finished_at": None,
        "approved_by": None, "result": None, "error": None,
    }
    runs = _read("runs.json")
    runs.append(run)
    _write("runs.json", runs)
    workflow["last_run_at"] = now
    _write("workflows.json", workflows)
    return run


def run_due_workflows(now: datetime | None = None) -> list[dict[str, Any]]:
    """Queue due workflows and execute those that do not require approval."""
    current = now or datetime.now(timezone.utc)
    existing_runs = _read("runs.json")
    processed: list[dict[str, Any]] = []
    for workflow in list_workflows():
        if not workflow.get("enabled"):
            continue
        pending = any(
            run.get("workflow_id") == workflow["id"]
            and run.get("status") in {"WAITING_APPROVAL", "QUEUED", "RUNNING"}
            for run in existing_runs
        )
        if pending:
            continue
        last_run = workflow.get("last_run_at")
        if last_run:
            try:
                due_at = datetime.fromisoformat(last_run) + timedelta(minutes=workflow["interval_minutes"])
                if current < due_at:
                    continue
            except (TypeError, ValueError):
                pass
        run = queue_run(workflow["id"])
        if run is None:
            continue
        if run["status"] == "QUEUED":
            run = execute_run(run["id"]) or run
        processed.append(run)
        existing_runs.append(run)
    return processed


def dispatch_action(action: str) -> dict[str, Any]:
    if action == "learning_cycle":
        from src.agent_cron import run_learning_cycle
        return run_learning_cycle()
    if action == "knowledge_health_check":
        from src.knowledge_retriever import load_knowledge_base
        return {"status": "success", "indexed_chunks": len(load_knowledge_base(force_reload=True))}
    if action == "fleet_health_check":
        from src.data_loader import get_latest_data, load_mcsa_data, get_data_path
        from src.agents.fusion_engine import ReliabilityFusionAgent
        from src.agents.asset_graph import AssetKnowledgeGraph
        from src.fleet_reliability import build_fleet_reliability
        from pple.core.events import publish, Events
        
        df = load_mcsa_data(get_data_path("mcsa_updated.csv"))
        if df is None or df.empty:
            df = load_mcsa_data(get_data_path("Report MCSA.xls"))
        df_latest = get_latest_data(df)
        
        fusion_agent = ReliabilityFusionAgent()
        asset_graph = AssetKnowledgeGraph()
        
        res = build_fleet_reliability(df_latest, fusion_agent, asset_graph, include_multi_domain=True)
        bad_count = len(res.get("critical_watchlist", []))
        
        # Publish event
        publish(
            Events.ANALYSIS_COMPLETED,
            source="AUTOMATION_CRON",
            summary=(
                f"Fleet health checked. Avg Health: {res.get('fleet_health_label', res.get('fleet_health_average'))}. "
                f"Coverage: {(res.get('coverage') or {}).get('status', 'UNKNOWN')}. Critical assets: {bad_count}."
            )
        )
        
        return {
            "status": "success",
            "fleet_health_average": res.get("fleet_health_average"),
            "critical_assets_count": bad_count,
            "total_assets_scanned": res.get("total_assets")
        }
    raise ValueError(f"Action '{action}' tidak diizinkan")


def execute_run(run_id: str, approved_by: str | None = None) -> dict[str, Any] | None:
    runs = _read("runs.json")
    run = next((item for item in runs if item["id"] == run_id), None)
    if run is None:
        return None
    run["status"] = "RUNNING"
    run["started_at"] = datetime.now(timezone.utc).isoformat()
    run["approved_by"] = approved_by
    _write("runs.json", runs)
    try:
        run["result"] = dispatch_action(run["action"])
        run["status"] = "SUCCESS"
    except Exception as exc:
        run["status"] = "FAILED"
        run["error"] = str(exc)
    run["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write("runs.json", runs)
    return run


def retry_run(run_id: str) -> dict[str, Any] | None:
    original = next((item for item in _read("runs.json") if item["id"] == run_id), None)
    if original is None or original["status"] != "FAILED":
        return None
    workflows = list_workflows()
    workflow = next((item for item in workflows if item["id"] == original["workflow_id"]), None)
    return queue_run(workflow["id"]) if workflow else None
