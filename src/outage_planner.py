"""Predictive Maintenance Scheduling & Outage Planning Optimization Engine.

Aligns Remaining Useful Life (RUL) projections from the Fusion Engine
with planned plant outage cycles (Simple Inspection, Minor Overhaul, Major Overhaul)
at PLTU Jeranjang to:
- Detect assets at risk of failing before the scheduled outage window (Pre-Outage Trip Risk)
- Automatically bundle corrective maintenance work packages per unit
- Calculate downtime hours saved through consolidated turnaround scope
- Produce interactive timeline/Gantt chart data for engineering managers
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd


DEFAULT_OUTAGE_SCHEDULE: List[Dict[str, Any]] = [
    {
        "outage_id": "OUT-U1-2026-SI",
        "unit": "UNIT 1",
        "name": "Unit 1 Simple Inspection (SI)",
        "outage_type": "Simple Inspection (SI)",
        "days_until_outage": 45,
        "duration_days": 10,
        "description": "Inspeksi berkala burner, fan auxiliary, bearing lubrication, & damper check",
        "color": "#38bdf8",
    },
    {
        "outage_id": "OUT-U2-2026-MO",
        "unit": "UNIT 2",
        "name": "Unit 2 Minor Overhaul (MO)",
        "outage_type": "Minor Overhaul (MO)",
        "days_until_outage": 85,
        "duration_days": 18,
        "description": "Inspeksi bearing turbin-generator, overhaul pompa sirkulasi utama (CWP/BFP), pembersihan kondensor",
        "color": "#818cf8",
    },
    {
        "outage_id": "OUT-U3-2026-SEI",
        "unit": "UNIT 3",
        "name": "Unit 3 Serious Inspection (SEI)",
        "outage_type": "Serious Inspection / Major Overhaul",
        "days_until_outage": 140,
        "duration_days": 32,
        "description": "Major overhaul turbin generator, re-blading, stator rewinding check, boiler tube mapping",
        "color": "#a855f7",
    },
    {
        "outage_id": "OUT-BOP-2026-SI",
        "unit": "COMMON",
        "name": "Balance of Plant (BOP) Service Window",
        "outage_type": "Auxiliary Maintenance Window",
        "days_until_outage": 60,
        "duration_days": 7,
        "description": "Servis coal handling, crusher, conveyor belt motor, & water treatment plant",
        "color": "#94a3b8",
    },
]


def parse_rul_lower_bound(rul_val: Any) -> int:
    """Extracts conservative lower bound days from RUL string (e.g. '14–45 hari' -> 14)."""
    if rul_val is None:
        return 180
    if isinstance(rul_val, (int, float)):
        return max(1, int(rul_val))

    s = str(rul_val).strip()
    match = re.search(r"(\d+)", s)
    if match:
        try:
            return max(1, int(match.group(1)))
        except ValueError:
            return 180
    return 180


def plan_outage_maintenance(
    fleet_matrix: List[Dict[str, Any]],
    outage_calendar: Optional[List[Dict[str, Any]]] = None,
    base_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Correlates fleet RUL projections with planned outage calendar to create optimized turnaround scopes."""
    if outage_calendar is None:
        outage_calendar = [dict(s) for s in DEFAULT_OUTAGE_SCHEDULE]
    if base_date is None:
        base_date = datetime.now()

    # Index outages by unit
    outage_by_unit: Dict[str, Dict[str, Any]] = {}
    for out in outage_calendar:
        u_key = str(out.get("unit", "COMMON")).upper()
        # Associate dates
        days_out = int(out.get("days_until_outage", 60))
        dur_days = int(out.get("duration_days", 14))
        start_dt = base_date + timedelta(days=days_out)
        end_dt = start_dt + timedelta(days=dur_days)

        out_copy = dict(out)
        out_copy["start_date"] = start_dt.strftime("%Y-%m-%d")
        out_copy["end_date"] = end_dt.strftime("%Y-%m-%d")
        out_copy["start_dt"] = start_dt
        out_copy["end_dt"] = end_dt
        outage_by_unit[u_key] = out_copy

    categorized_assets = []
    pre_outage_critical: List[Dict[str, Any]] = []
    bundled_by_unit: Dict[str, List[Dict[str, Any]]] = {
        "UNIT 1": [],
        "UNIT 2": [],
        "UNIT 3": [],
        "COMMON": [],
    }

    for item in fleet_matrix:
        eq = item.get("equipment", "-")
        raw_unit = str(item.get("unit", "COMMON")).upper()
        if "1" in raw_unit:
            unit_key = "UNIT 1"
        elif "2" in raw_unit:
            unit_key = "UNIT 2"
        elif "3" in raw_unit:
            unit_key = "UNIT 3"
        else:
            unit_key = "COMMON"

        assigned_outage = outage_by_unit.get(unit_key, outage_by_unit.get("COMMON"))
        days_to_outage = assigned_outage.get("days_until_outage", 60) if assigned_outage else 60
        outage_name = assigned_outage.get("name", "Scheduled Outage") if assigned_outage else "Scheduled Outage"

        rul_val = parse_rul_lower_bound(item.get("rul_days"))
        h_idx = float(item.get("health_index", 100.0))
        h_stat = str(item.get("health_status", "HEALTHY")).upper()
        crit = str(item.get("criticality", "A")).upper()

        rul_expiry_dt = base_date + timedelta(days=rul_val)

        # Determine Urgency Window
        # Case 1: RUL expires BEFORE outage starts -> Risk of forced trip!
        if (rul_val < days_to_outage and h_stat in ["CRITICAL", "ALERT", "WARNING"]) or h_stat == "CRITICAL":
            urgency = "PRE_OUTAGE_CRITICAL"
            urgency_label = "🚨 Risiko Trip Pra-Outage"
            urgency_color = "#ef4444"
            recommended_action = (
                f"RUL ({rul_val} hari) < Waktu ke Outage ({days_to_outage} hari). "
                "Lakukan mitigasi online, reduksi beban, atau siapkan Opportunity Outage darurat!"
            )
        # Case 2: RUL aligns within or near the upcoming outage window (within +60 days after outage)
        elif rul_val <= (days_to_outage + 65) or h_stat in ["ALERT", "WARNING"]:
            urgency = "OPTIMAL_OUTAGE_SCOPE"
            urgency_label = "📦 Paket Ideal Outage"
            urgency_color = "#f59e0b"
            recommended_action = (
                f"Sangat ideal diservis pada {outage_name}. "
                "Bundel penggantian komponen, balancing, dan alignment bersamaan."
            )
        # Case 3: Safe for post-outage
        else:
            urgency = "POST_OUTAGE_SAFE"
            urgency_label = "🟢 Aman Pasca-Outage"
            urgency_color = "#10b981"
            recommended_action = "Kondisi sehat; lanjutkan pemantauan getaran dan arus rutin."

        asset_plan_item = {
            **item,
            "unit_normalized": unit_key,
            "rul_lower_bound_days": rul_val,
            "rul_expiry_date": rul_expiry_dt.strftime("%Y-%m-%d"),
            "target_outage_id": assigned_outage.get("outage_id", "-") if assigned_outage else "-",
            "target_outage_name": outage_name,
            "days_to_outage": days_to_outage,
            "urgency": urgency,
            "urgency_label": urgency_label,
            "urgency_color": urgency_color,
            "recommended_action": recommended_action,
        }

        categorized_assets.append(asset_plan_item)

        if urgency == "PRE_OUTAGE_CRITICAL":
            pre_outage_critical.append(asset_plan_item)

        if urgency in ["PRE_OUTAGE_CRITICAL", "OPTIMAL_OUTAGE_SCOPE"]:
            bundled_by_unit[unit_key].append(asset_plan_item)

    # Calculate Saved Downtime Hours:
    # An auxiliary forced trip/maintenance takes ~16h generation loss.
    # Bundling N assets into 1 outage saves (N - 1) * 16h per unit.
    total_bundled_count = sum(len(items) for items in bundled_by_unit.values())
    saved_downtime_hours = 0
    for u_k, items in bundled_by_unit.items():
        if len(items) > 1:
            saved_downtime_hours += (len(items) - 1) * 16

    # Build Gantt Timeline Data for Plotly
    gantt_df_rows = []
    # 1. Outage Windows
    for out in outage_calendar:
        u_k = str(out.get("unit", "COMMON")).upper()
        out_info = outage_by_unit.get(u_k, out)
        gantt_df_rows.append({
            "Task": f"📅 {out_info.get('name')}",
            "Start": out_info.get("start_date"),
            "Finish": out_info.get("end_date"),
            "Category": "Jendela Outage Unit",
            "Color": out_info.get("color", "#38bdf8"),
            "Type": "Outage",
            "Detail": f"Durasi: {out_info.get('duration_days')} hari",
        })

    # 2. Critical & Bundled Assets RUL Depletion Projection
    for a in sorted(categorized_assets, key=lambda x: (x["urgency"] != "PRE_OUTAGE_CRITICAL", x["rul_lower_bound_days"]))[:15]:
        if a["urgency"] in ["PRE_OUTAGE_CRITICAL", "OPTIMAL_OUTAGE_SCOPE"]:
            gantt_df_rows.append({
                "Task": f"⚙️ {a.get('equipment')} ({a.get('unit_normalized')})",
                "Start": base_date.strftime("%Y-%m-%d"),
                "Finish": a.get("rul_expiry_date"),
                "Category": a.get("urgency_label"),
                "Color": a.get("urgency_color"),
                "Type": "Asset_RUL",
                "Detail": f"RUL: {a.get('rul_lower_bound_days')} hari · {a.get('primary_failure_mode')}",
            })

    gantt_df = pd.DataFrame(gantt_df_rows) if gantt_df_rows else pd.DataFrame()

    return {
        "outage_schedules": list(outage_by_unit.values()),
        "categorized_assets": categorized_assets,
        "pre_outage_critical": pre_outage_critical,
        "bundled_by_unit": bundled_by_unit,
        "total_bundled_count": total_bundled_count,
        "saved_downtime_hours": saved_downtime_hours,
        "gantt_data": gantt_df,
    }


def generate_outage_turnaround_package(
    unit: str,
    bundled_assets: List[Dict[str, Any]],
    outage_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generates an executive Turnaround Outage Work Package ready for dispatch."""
    package_id = f"TOP-{unit.replace(' ', '')}-{datetime.now().strftime('%Y%m%d')}"
    outage_name = outage_info.get("name", f"Turnaround {unit}") if outage_info else f"Turnaround {unit}"

    scope_items = []
    required_parts = []
    for a in bundled_assets:
        eq = a.get("equipment", "-")
        fm = a.get("primary_failure_mode", "General Overhaul")
        crit = a.get("criticality", "A")
        rul = a.get("rul_lower_bound_days", 30)

        scope_items.append({
            "equipment": eq,
            "task": f"Overhaul & Perbaikan Defek: {fm}",
            "criticality": f"Class {crit}",
            "rul_days": rul,
            "primary_failure_mode": fm,
            "status": a.get("health_status", "WARNING"),
        })

        # Suku cadang rekomendasi
        if "Bearing" in fm:
            required_parts.append(f"Bearing set replacement untuk {eq} (DE & NDE)")
        if "Rotor" in fm or "Stator" in fm:
            required_parts.append(f"Winding insulation kit & slot wedge untuk {eq}")
        if "Looseness" in fm or "Misalignment" in fm:
            required_parts.append(f"Precision laser alignment shims & torque bolts untuk {eq}")

    if not required_parts:
        required_parts = ["Standar mechanical seal & gasket kit", "High-temperature synthetic bearing grease"]

    return {
        "package_id": package_id,
        "unit": unit,
        "outage_name": outage_name,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_equipment": len(bundled_assets),
        "scope_items": scope_items,
        "required_parts": list(set(required_parts)),
        "loto_required": True,
        "isolation_procedure": "Electrical Breaker Rack-Out, Mechanical Valve Lockout & Safety Tagging",
        "turnaround_lead": "CBM Reliability Supervisor & Maintenance Outage Lead",
    }

