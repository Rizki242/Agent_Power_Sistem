"""
Thermal Infrared Thermography (IRT) data loader.
Parses periodic thermal inspection reports from data/vibrasi/pengujian/EKSUM IRT JULI 2026.xlsx.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd
from src.data_loader import get_data_path

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

def get_thermal_summary() -> Dict[str, Any]:
    """Returns summary statistics for thermal IRT inspections."""
    records = load_thermal_irt_tests()
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
