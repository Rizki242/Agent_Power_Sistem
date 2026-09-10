"""Vibration API router for assets, periodic tests, and ISO classes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException

from src.vibration_data import (
    get_bearing_info,
    get_equipment_class_list,
    get_vibration_asset,
    get_vibration_summary,
    load_vibration_monthly_tests,
    search_vibration_assets,
)

router = APIRouter(prefix="/api/vibration", tags=["vibration"])


@router.get("/summary")
def get_vib_summary():
    """Quick counts by unit, status, and category."""
    try:
        return get_vibration_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment")
def get_vib_equipment_list(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
):
    """List vibration assets with optional filters."""
    kwargs = {}
    if unit and unit.upper() != "ALL":
        kwargs["unit_group"] = unit
    if status and status.upper() != "ALL":
        kwargs["status"] = status
    if category and category.upper() != "ALL":
        kwargs["equipment_class"] = category
    if search and search.strip():
        kwargs["keyword"] = search.strip()

    assets = search_vibration_assets(**kwargs)

    equipment = []
    for a in assets:
        equipment.append({
            "asset_id": a.get("asset_id", ""),
            "equipment": a.get("equipment", ""),
            "kks": a.get("kks", ""),
            "unit": a.get("unit_group", ""),
            "category": a.get("asset_category_derived", ""),
            "equipment_class": a.get("equipment_class_normalized", ""),
            "status": a.get("status_vibrasi", "NORMAL"),
            "pm_week": a.get("pm_week", ""),
            "measurement_date": a.get("measurement_date", ""),
            "component_1": a.get("component_1", ""),
            "component_2": a.get("component_2", ""),
            "c1_speed": a.get("c1_speed", ""),
            "c1_power": a.get("c1_power", ""),
            "c1_foundation": a.get("c1_foundation", ""),
        })

    return {"equipment": equipment, "count": len(equipment)}


@router.get("/equipment/{asset_id}")
def get_vib_equipment_detail(asset_id: str):
    """Full detail for a single vibration asset."""
    asset = get_vibration_asset(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Vibration asset {asset_id} not found")

    bearing = get_bearing_info(asset_id) or {}

    motor_specs = {}
    for key, label in [
        ("c1_type_mfg", "Type / Mfg"),
        ("c1_speed", "Speed"),
        ("c1_power", "Power"),
        ("c1_bearing_type", "Bearing Type"),
        ("c1_inboard_bearing", "Inboard Bearing"),
        ("c1_outboard_bearing", "Outboard Bearing"),
        ("c1_rotor_bar", "Rotor Bar"),
        ("c1_foundation", "Foundation"),
        ("c1_house_power", "House Power"),
        ("c1_rated_speed", "Rated Speed"),
        ("c1_rated_active_power", "Rated Active Power"),
        ("c1_rated_stator_voltage", "Rated Stator Voltage"),
        ("c1_rated_stator_current", "Rated Stator Current"),
    ]:
        val = asset.get(key)
        if val is not None and str(val).strip() and str(val).strip() not in ("None", "nan", "-"):
            motor_specs[label] = str(val)

    driven_specs = {}
    for key, label in [
        ("c2_type_mfg", "Type / Mfg"),
        ("c2_manufacturer", "Manufacturer"),
        ("c2_speed", "Speed"),
        ("c2_power", "Power"),
        ("c2_capacity", "Capacity"),
        ("c2_pressure", "Pressure"),
        ("c2_flow_rate", "Flow Rate"),
        ("c2_bearing_type", "Bearing Type"),
        ("c2_inboard_bearing", "Inboard Bearing"),
        ("c2_onboard_bearing", "Outboard Bearing"),
        ("c2_total_blade", "Total Blade"),
        ("c2_stages", "Stages"),
    ]:
        val = asset.get(key)
        if val is not None and str(val).strip() and str(val).strip() not in ("None", "nan", "-"):
            driven_specs[label] = str(val)

    status = str(asset.get("status_vibrasi", "NORMAL")).upper()
    recommendation = "Kondisi getaran normal; lanjutkan monitoring berkala sesuai jadwal PM."
    if status == "WARNING":
        recommendation = "Getaran dalam zona waspada. Lakukan survei vibrasi terarah dan periksa alignment/pondasi dalam 1 minggu."
    elif status == "ALARM":
        recommendation = "Getaran melewati batas alarm. Periksa spektrum FFT untuk identifikasi sumber kerusakan, jadwalkan tindakan korektif."
    elif status == "PREWARNING":
        recommendation = "Tren vibrasi naik mendekati batas. Monitor lebih intensif dan periksa pelumasan bearing."

    eq_name = str(asset.get("equipment", "")).strip()
    test_points = {}
    velocity_max = 0.0
    test_date = asset.get("measurement_date", "")
    try:
        all_tests = load_vibration_monthly_tests()
        for t in all_tests:
            t_eq = str(t.get("equipment", "")).strip()
            if t_eq.lower() in eq_name.lower() or eq_name.lower() in t_eq.lower():
                test_points = t.get("points", {})
                velocity_max = t.get("velocity_max", 0.0)
                test_date = t.get("test_date", test_date)
                break
    except Exception:
        pass

    return {
        "asset_id": asset.get("asset_id", ""),
        "equipment": asset.get("equipment", ""),
        "kks": asset.get("kks", ""),
        "unit": asset.get("unit_group", ""),
        "category": asset.get("asset_category_derived", ""),
        "equipment_class": asset.get("equipment_class_normalized", ""),
        "status": status,
        "pm_week": asset.get("pm_week", ""),
        "measurement_date": test_date or asset.get("measurement_date", ""),
        "velocity_max": velocity_max,
        "points": test_points,
        "component_1": asset.get("component_1", ""),
        "component_2": asset.get("component_2", ""),
        "motor_specs": motor_specs,
        "driven_specs": driven_specs,
        "bearing": bearing,
        "recommendation": recommendation,
    }


@router.get("/classes")
def get_vib_classes():
    """Distinct ISO equipment classes."""
    return {"classes": get_equipment_class_list()}


@router.get("/tests")
def get_vib_monthly_tests(
    unit: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns monthly periodic vibration test records with individual measurement points (1V, 1H, 1A, etc.)."""
    try:
        tests = load_vibration_monthly_tests()
        if unit and unit.upper() != "ALL":
            tests = [t for t in tests if t["unit"].upper() == unit.upper()]
        if status and status.upper() != "ALL":
            tests = [t for t in tests if t["status"].upper() == status.upper()]
        if search and search.strip():
            st = search.lower().strip()
            tests = [t for t in tests if st in t["equipment"].lower()]
        return {"tests": tests, "count": len(tests)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
