"""
Thermal Infrared Thermography (IRT) data loader.
Parses periodic thermal inspection reports from data/vibrasi/pengujian/EKSUM IRT JULI 2026.xlsx.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.data_loader import get_data_path
from src.domain_overrides import DomainOverrideStore

def load_thermal_irt_tests(excel_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads 110+ Thermal IRT inspection points across Unit 1, 2, 3 and Common."""
    p1 = Path(get_data_path('vibrasi', 'pengujian', 'EKSUM IRT JULI 2026.xlsx'))
    p2 = Path(excel_path) if excel_path else p1
    
    target_path = p2 if p2.exists() else p1
    if not target_path.exists():
        return []
        
    try:
        df_irt = pd.read_excel(target_path, sheet_name='SUMMARY')
        records = []
        for idx in range(1, len(df_irt)):
            row = df_irt.iloc[idx]
            u = row.get('Unit')
            kks = row.get('No KKS')
            desc = row.get('Description')
            st = row.get('Status Kondisi Terakhir')
            
            if pd.notna(desc) and str(desc).strip() != '':
                unit_str = f"UNIT {int(u)}" if pd.notna(u) and str(u).replace('.0', '').isdigit() else ("COMMON" if "COMM" in str(u).upper() else "UNIT 1")
                
                st_raw = str(st).strip() if pd.notna(st) else 'Normal'
                st_clean = 'NORMAL'
                if 'STD' in st_raw.upper() or 'STAND' in st_raw.upper():
                    st_clean = 'STANDBY'
                elif 'LOW' in st_raw.upper():
                    st_clean = 'NORMAL' # Low delta-T is good
                elif 'MED' in st_raw.upper() or 'PRE' in st_raw.upper():
                    st_clean = 'PREWARNING'
                elif 'HIGH' in st_raw.upper():
                    st_clean = 'WARNING'
                elif 'CRIT' in st_raw.upper() or 'ALARM' in st_raw.upper():
                    st_clean = 'HIGH'
                    
                records.append({
                    "id": f"IRT-{len(records)+1:03d}",
                    "unit": unit_str,
                    "kks": str(kks) if pd.notna(kks) else "",
                    "equipment": str(desc).replace('EQUIPMENT-', '').strip(),
                    "raw_status": st_raw,
                    "status": st_clean,
                    "standard": "FLIR Thermal Camera / Delta-T Matrix",
                    "test_date": "2026-07-25"
                })
        return records
    except Exception as e:
        print(f"Error loading thermal IRT tests: {e}")
        return []

def _override_store() -> DomainOverrideStore:
    return DomainOverrideStore(get_data_path('config', 'thermal_overrides.json'))


def _merged_records() -> List[Dict[str, Any]]:
    """load_thermal_irt_tests() (real IRT inspection points parsed from Excel)
    with any recorded overrides applied on top - an override whose id matches
    an existing record replaces it, a new id adds a new inspection point."""
    base = load_thermal_irt_tests()
    overrides = _override_store().all()
    known_ids = {r['id'] for r in base}
    merged = [dict(overrides.get(r['id'], r)) for r in base]
    merged.extend(dict(record) for rid, record in overrides.items() if rid not in known_ids)
    return merged


def save_thermal_record(record_id: str, fields: Dict[str, Any]) -> None:
    """Add a new inspection point or edit an existing one."""
    record = dict(fields)
    record['id'] = record_id
    _override_store().set(record_id, record)


def search_thermal_records(unit: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filters thermal IRT inspection records."""
    results = []
    for r in _merged_records():
        if unit and unit.upper() != "ALL" and r.get("unit", "").upper() != unit.upper():
            continue
        if status and status.upper() != "ALL" and r.get("status", "").upper() != status.upper():
            continue
        if search and search.strip():
            s = search.lower().strip()
            if s not in r.get("equipment", "").lower() and s not in r.get("id", "").lower() and s not in r.get("kks", "").lower():
                continue
        results.append(r)
    return results


def get_thermal_record_detail(record_id: str) -> Optional[Dict[str, Any]]:
    """Returns one inspection record plus a status-based recommendation.

    Deliberately does NOT call ThermalAgent: that agent expects numeric
    readings (bearing_temp, winding_temp, delta_t_phase, ...) that this data
    source doesn't carry - only a pre-computed status from the source Excel.
    Calling the agent with fabricated defaults would always score "healthy"
    regardless of the real status, which is worse than not scoring at all.
    """
    target = None
    for r in _merged_records():
        if str(r.get("id", "")).upper() == record_id.upper():
            target = dict(r)
            break
    if not target:
        return None

    status = str(target.get("status", "NORMAL")).upper()
    if status == "HIGH":
        rec = "Delta-T kritis. Rencanakan tindakan segera: verifikasi beban, periksa koneksi/terminal, dan jadwalkan inspeksi ulang dalam 48 jam."
    elif status == "WARNING":
        rec = "Delta-T tinggi. Tingkatkan frekuensi inspeksi thermografi dan periksa kondisi pendinginan/ventilasi terkait."
    elif status == "PREWARNING":
        rec = "Delta-T mulai meningkat. Jadwalkan inspeksi ulang dalam 30 hari dan pantau tren pada titik yang sama."
    elif status == "STANDBY":
        rec = "Equipment standby - tidak perlu tindakan thermal saat ini."
    else:
        rec = "Kondisi thermal normal. Lanjutkan inspeksi rutin sesuai jadwal IRT."
    target["recommendation"] = rec
    return target


def get_thermal_summary() -> Dict[str, Any]:
    """Returns summary statistics for thermal IRT inspections."""
    records = _merged_records()
    by_unit = {}
    by_status = {"NORMAL": 0, "PREWARNING": 0, "WARNING": 0, "HIGH": 0, "STANDBY": 0}
    
    for r in records:
        u = r["unit"]
        by_unit[u] = by_unit.get(u, 0) + 1
        st = r["status"]
        by_status[st] = by_status.get(st, 0) + 1
        
    return {
        "total_inspections": len(records),
        "by_unit": by_unit,
        "by_status": by_status
    }
