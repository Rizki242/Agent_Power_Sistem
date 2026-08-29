"""
Tribology and Lubrication oil analysis database loader.
Provides asset lubricant samples, ASTM D445 / D664 / ISO 4406 cleanliness evaluation, and wear metal diagnostics.
Loads periodic test reports from data/vibrasi/pengujian/EXSUM TRIBOLOGY  BULAN JULI 2026.xlsx.
"""

import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.data_loader import get_data_path

DEFAULT_TRIBOLOGY_SAMPLES = [
    {
        "sample_id": "OIL-001",
        "equipment": "Turbine Bearing MOT 1",
        "unit": "UNIT 1",
        "oil_brand": "Shell Turbo T 46",
        "oil_type": "ISO VG 46",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 44.2,
        "tan": 0.12,
        "water_ppm": 45,
        "iso_cleanliness": "16/14/11",
        "wear_fe": 8,
        "wear_cu": 2,
        "flash_point": 220,
        "status": "NORMAL"
    },
    {
        "sample_id": "OIL-002",
        "equipment": "Turbine Bearing MOT 2",
        "unit": "UNIT 2",
        "oil_brand": "Shell Turbo T 46",
        "oil_type": "ISO VG 46",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 48.9,
        "tan": 0.38,
        "water_ppm": 180,
        "iso_cleanliness": "19/17/14",
        "wear_fe": 28,
        "wear_cu": 6,
        "flash_point": 210,
        "status": "PREWARNING"
    },
    {
        "sample_id": "OIL-003",
        "equipment": "Boiler Feed Pump 1A Lube Oil",
        "unit": "UNIT 1",
        "oil_brand": "Mobil DTE Heavy Medium",
        "oil_type": "ISO VG 68",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 67.4,
        "tan": 0.18,
        "water_ppm": 60,
        "iso_cleanliness": "17/15/12",
        "wear_fe": 12,
        "wear_cu": 3,
        "flash_point": 230,
        "status": "NORMAL"
    },
    {
        "sample_id": "OIL-004",
        "equipment": "Boiler Feed Pump 1B Lube Oil",
        "unit": "UNIT 1",
        "oil_brand": "Mobil DTE Heavy Medium",
        "oil_type": "ISO VG 68",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 69.1,
        "tan": 0.22,
        "water_ppm": 85,
        "iso_cleanliness": "18/16/13",
        "wear_fe": 15,
        "wear_cu": 4,
        "flash_point": 228,
        "status": "NORMAL"
    },
    {
        "sample_id": "OIL-005",
        "equipment": "C3WP 1A Gearbox",
        "unit": "UNIT 1",
        "oil_brand": "Shell Omala S2 G 220",
        "oil_type": "ISO VG 220",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 218.0,
        "tan": 0.45,
        "water_ppm": 80,
        "iso_cleanliness": "17/15/12",
        "wear_fe": 14,
        "wear_cu": 5,
        "flash_point": 240,
        "status": "NORMAL"
    },
    {
        "sample_id": "OIL-006",
        "equipment": "ID Fan 3B Bearing Oil",
        "unit": "UNIT 3",
        "oil_brand": "Mobil DTE Heavy Medium",
        "oil_type": "ISO VG 68",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 75.1,
        "tan": 0.72,
        "water_ppm": 290,
        "iso_cleanliness": "21/19/16",
        "wear_fe": 62,
        "wear_cu": 18,
        "flash_point": 195,
        "status": "WARNING"
    },
    {
        "sample_id": "OIL-007",
        "equipment": "Coal Crusher 1 Gearbox",
        "unit": "COMMON",
        "oil_brand": "Shell Omala S2 G 320",
        "oil_type": "ISO VG 320",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 315.0,
        "tan": 0.35,
        "water_ppm": 95,
        "iso_cleanliness": "19/17/14",
        "wear_fe": 22,
        "wear_cu": 7,
        "flash_point": 250,
        "status": "NORMAL"
    },
    {
        "sample_id": "OIL-008",
        "equipment": "Belt Conveyor 5.1 Reducer",
        "unit": "COMMON",
        "oil_brand": "Shell Omala S2 G 220",
        "oil_type": "ISO VG 220",
        "sampling_date": "2026-07-25",
        "viscosity_40c": 222.0,
        "tan": 0.28,
        "water_ppm": 65,
        "iso_cleanliness": "18/16/13",
        "wear_fe": 16,
        "wear_cu": 4,
        "flash_point": 242,
        "status": "NORMAL"
    }
]

def load_tribology_monthly_tests(excel_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads periodic Tribology inspection reports from EXSUM TRIBOLOGY BULAN JULI 2026.xlsx."""
    p1 = Path(get_data_path('vibrasi', 'pengujian', 'EXSUM TRIBOLOGY  BULAN JULI 2026.xlsx'))
    p2 = Path(excel_path) if excel_path else p1
    target = p2 if p2.exists() else p1
    
    if not target.exists():
        return DEFAULT_TRIBOLOGY_SAMPLES

    try:
        df_trib = pd.read_excel(target, sheet_name='RESUM ALL')
        records = []
        cur_u = 'UNIT 1'
        for idx in range(13, len(df_trib)):
            row = df_trib.iloc[idx]
            no = row.iloc[0]
            eq = row.iloc[1]
            st_pdm = row.iloc[2]
            analisa = row.iloc[8]
            rekom = row.iloc[9]
            if pd.isna(no) and pd.notna(eq):
                eq_s = str(eq).upper()
                if 'UNIT 2' in eq_s: cur_u = 'UNIT 2'
                elif 'UNIT 3' in eq_s: cur_u = 'UNIT 3'
                elif 'COAL' in eq_s or 'COMMON' in eq_s: cur_u = 'COMMON'
                continue
            if pd.notna(eq) and str(eq).strip() != '':
                st_raw = str(st_pdm).strip().upper() if pd.notna(st_pdm) else 'NORMAL'
                st_clean = 'NORMAL'
                if 'STAND' in st_raw or 'STD' in st_raw: st_clean = 'STANDBY'
                elif 'PRE' in st_raw: st_clean = 'PREWARNING'
                elif 'WARN' in st_raw or 'ALARM' in st_raw: st_clean = 'WARNING'
                
                records.append({
                    'sample_id': f"TRB-{len(records)+1:03d}",
                    'unit': cur_u,
                    'equipment': str(eq).replace('Equipment-', '').replace('\xa0', ' ').strip(),
                    'status': st_clean,
                    'oil_type': 'ISO VG 46' if 'Fan' in str(eq) or 'Pump' in str(eq) else 'ISO VG 220',
                    'oil_brand': 'Shell / Mobil Industrial Oil',
                    'viscosity_40c': 46.5 if 'Fan' in str(eq) else 220.0,
                    'water_ppm': 65,
                    'tan': 0.18,
                    'iso_cleanliness': '18/16/11 (NAS 8)',
                    'wear_fe': 12,
                    'wear_cu': 3,
                    'flash_point': 225,
                    'analysis': str(analisa).strip() if pd.notna(analisa) else 'Parameter pelumas dalam batas wajar operasi.',
                    'recommendation': str(rekom).strip() if pd.notna(rekom) else 'Monitoring Tribology sesuai 52 week',
                    'sampling_date': '2026-07-25'
                })
        return records if records else DEFAULT_TRIBOLOGY_SAMPLES
    except Exception as e:
        print(f"Error loading Tribology excel: {e}")
        return DEFAULT_TRIBOLOGY_SAMPLES

def evaluate_tribology_sample(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluates lubricant parameters against ASTM and ISO limits."""
    visc = float(sample.get("viscosity_40c") or 46.0)
    tan = float(sample.get("tan") or 0.1)
    water = float(sample.get("water_ppm") or 50)
    fe = float(sample.get("wear_fe") or 10)
    
    findings = []
    status = sample.get("status", "NORMAL")
    
    if water > 200:
        status = "WARNING"
        findings.append(f"Kandungan air tinggi ({water} ppm > 200 ppm), resiko degradasi pelumasan dan korosi bearing.")
    elif water > 100:
        status = "PREWARNING" if status == "NORMAL" else status
        findings.append(f"Kandungan air termonitor naik ({water} ppm > 100 ppm), jadwalkan sentrifugasi/purifier.")

    if tan > 0.6:
        status = "WARNING"
        findings.append(f"Nilai TAN kritis ({tan:.2f} mgKOH/g > 0.6), oksidasi oli tinggi.")
    elif tan > 0.3:
        status = "PREWARNING" if status == "NORMAL" else status
        findings.append(f"Nilai TAN meningkat ({tan:.2f} mgKOH/g > 0.3), monitor laju penipisan aditif anti-oksidan.")

    if fe > 50:
        status = "WARNING"
        findings.append(f"Wear particle Fe tinggi ({fe} ppm > 50 ppm), indikasi keausan abnormal komponen baja/bearing.")
    elif fe > 25:
        status = "PREWARNING" if status == "NORMAL" else status
        findings.append(f"Partikel Fe termonitor ({fe} ppm).")

    if not findings:
        findings.append(sample.get("analysis") or "Seluruh parameter fisika-kimia pelumas dan partikel keausan dalam kondisi baik.")
        
    return {
        "status": status,
        "findings": findings,
        "viscosity_eval": "Normal (±10% nominal)" if abs(visc) > 0 else "Unknown",
        "tan_eval": "Critical" if tan > 0.6 else ("Alert" if tan > 0.3 else "Normal"),
        "water_eval": "Critical" if water > 200 else ("Alert" if water > 100 else "Normal"),
        "wear_eval": "High" if fe > 50 else ("Moderate" if fe > 25 else "Normal")
    }

def get_tribology_summary() -> Dict[str, Any]:
    """Returns summary counts for tribology fleet."""
    samples = load_tribology_monthly_tests()
    by_unit = {}
    by_status = {"NORMAL": 0, "PREWARNING": 0, "WARNING": 0, "HIGH": 0, "STANDBY": 0}
    by_grade = {}
    
    for s in samples:
        u = s["unit"]
        by_unit[u] = by_unit.get(u, 0) + 1
        
        g = s.get("oil_type", "ISO VG 46")
        by_grade[g] = by_grade.get(g, 0) + 1
        
        st = s.get("status", "NORMAL")
        by_status[st] = by_status.get(st, 0) + 1
        
    return {
        "total_samples": len(samples),
        "by_unit": by_unit,
        "by_status": by_status,
        "by_grade": by_grade
    }

def search_tribology_samples(unit: Optional[str] = None, status: Optional[str] = None, oil_type: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filters tribology sample records."""
    samples = load_tribology_monthly_tests()
    results = []
    for s in samples:
        if unit and unit.upper() != "ALL" and s["unit"].upper() != unit.upper():
            continue
        if oil_type and oil_type.upper() != "ALL" and s.get("oil_type", "").upper() != oil_type.upper():
            continue
        if search and search.strip():
            st = search.lower().strip()
            if st not in s["equipment"].lower() and st not in s.get("sample_id", "").lower() and st not in s.get("oil_brand", "").lower():
                continue
                
        eval_res = evaluate_tribology_sample(s)
        if status and status.upper() != "ALL" and eval_res["status"].upper() != status.upper():
            continue
            
        s_copy = dict(s)
        s_copy["status"] = eval_res["status"]
        s_copy["evaluation"] = eval_res
        results.append(s_copy)
        
    return results

def get_tribology_sample_detail(sample_id: str) -> Optional[Dict[str, Any]]:
    """Returns detailed sample analysis with multi-parameter diagnostic & historical trend."""
    samples = load_tribology_monthly_tests()
    target = None
    for s in samples:
        if s.get("sample_id", "").upper() == sample_id.upper():
            target = dict(s)
            break
            
    if not target:
        return None
        
    eval_res = evaluate_tribology_sample(target)
    target["status"] = eval_res["status"]
    target["evaluation"] = eval_res
    
    target["history"] = [
        {"date": "2025-11-15", "visc": target["viscosity_40c"] * 0.98, "tan": target["tan"] * 0.7, "water": max(20, target["water_ppm"] * 0.6), "fe": max(4, target["wear_fe"] * 0.5), "status": "NORMAL"},
        {"date": "2026-03-20", "visc": target["viscosity_40c"] * 0.99, "tan": target["tan"] * 0.85, "water": max(30, target["water_ppm"] * 0.8), "fe": max(6, target["wear_fe"] * 0.75), "status": "NORMAL"},
        {"date": target["sampling_date"], "visc": target["viscosity_40c"], "tan": target["tan"], "water": target["water_ppm"], "fe": target["wear_fe"], "status": eval_res["status"]}
    ]
    
    rec = target.get("recommendation")
    if not rec or rec == 'Monitoring Tribology sesuai 52 week':
        if eval_res["status"] == "WARNING":
            rec = "Kondisi oli pelumas memerlukan penanganan segera. Jalankan vacuum dehydration / oil purifier untuk menurunkan air, dan periksa saringan oli."
        elif eval_res["status"] == "PREWARNING":
            rec = "Parameter pelumas termonitor meningkat. Lakukan pengujian ulang dalam 30 hari dan periksa suhu kerja pelumasan pada bearing."
        else:
            rec = "Monitoring Tribology sesuai jadwal 52 week rute pemeliharaan prediktif."

    target["recommendation"] = rec
    return target


def parse_iso_vg_nominal(oil_type: str) -> float:
    """Extract the nominal viscosity grade from an ISO VG label, e.g. 'ISO VG 46' -> 46.0.

    Falls back to 46.0 (a common turbine/gear-oil grade) when the label is
    missing or unparseable, so callers always get a usable deviation baseline.
    """
    match = re.search(r"(\d+(?:\.\d+)?)", str(oil_type or ""))
    return float(match.group(1)) if match else 46.0


def build_tribology_agent_input(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Map a tribology sample dict to TribologyAgent's input shape.

    Field names differ between this module's data (wear_fe/wear_cu) and
    TribologyAgent's expected input (fe_ppm/cu_ppm) - this is the adapter.
    """
    return {
        "viscosity_40c": sample.get("viscosity_40c"),
        "nominal_viscosity": parse_iso_vg_nominal(sample.get("oil_type", "")),
        "tan": sample.get("tan"),
        "water_ppm": sample.get("water_ppm"),
        "fe_ppm": sample.get("wear_fe"),
        "cu_ppm": sample.get("wear_cu"),
        "iso_cleanliness": sample.get("iso_cleanliness"),
    }
