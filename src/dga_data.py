"""
DGA (Dissolved Gas Analysis) data loader and Transformer asset database.
Loads transformer health and gas data from Excel reports and structured records.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd

from src.data_loader import get_data_path
from src.domain_overrides import DomainOverrideStore

# Standard list of power transformers across the plant
DEFAULT_TRANSFORMERS = [
    {
        "transformer_id": "TRF-001",
        "name": "Generator Step-Up Transformer 1 (GT 1)",
        "unit": "UNIT 1",
        "voltage_ratio": "10.5 / 150 kV",
        "rated_capacity": "31.25 MVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "14,500 L",
        "sampling_date": "2026-07-15",
        "gases": {"H2": 12.0, "CH4": 18.0, "C2H6": 8.0, "C2H4": 15.0, "C2H2": 0.2, "CO": 180.0, "CO2": 1450.0, "H2O": 18.0},
        "status": "NORMAL"
    },
    {
        "transformer_id": "TRF-002",
        "name": "Generator Step-Up Transformer 2 (GT 2)",
        "unit": "UNIT 2",
        "voltage_ratio": "10.5 / 150 kV",
        "rated_capacity": "31.25 MVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "14,500 L",
        "sampling_date": "2026-07-18",
        "gases": {"H2": 5.0, "CH4": 6.0, "C2H6": 9.0, "C2H4": 9.0, "C2H2": 0.5, "CO": 32.0, "CO2": 754.0, "H2O": 25.0},
        "status": "NORMAL"
    },
    {
        "transformer_id": "TRF-003",
        "name": "Generator Step-Up Transformer 3 (GT 3)",
        "unit": "UNIT 3",
        "voltage_ratio": "10.5 / 150 kV",
        "rated_capacity": "31.25 MVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "15,000 L",
        "sampling_date": "2026-07-20",
        "gases": {"H2": 28.0, "CH4": 45.0, "C2H6": 14.0, "C2H4": 85.0, "C2H2": 2.1, "CO": 340.0, "CO2": 2100.0, "H2O": 28.0},
        "status": "PREWARNING"
    },
    {
        "transformer_id": "TRF-004",
        "name": "Unit Auxiliary Transformer 3 (UAT 3)",
        "unit": "UNIT 3",
        "voltage_ratio": "6.3 / 6.3 kV",
        "rated_capacity": "6,300 kVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "12,000 L",
        "sampling_date": "2019-11-14",
        "gases": {"H2": 5.0, "CH4": 16.0, "C2H6": 28.0, "C2H4": 2.0, "C2H2": 0.0, "CO": 59.0, "CO2": 338.0, "H2O": 6.0},
        "status": "NORMAL"
    },
    {
        "transformer_id": "TRF-005",
        "name": "ESP Transformer Rectifier Unit 2",
        "unit": "UNIT 2",
        "voltage_ratio": "0.4 / 72 kV",
        "rated_capacity": "1.2 MVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "1,800 L",
        "sampling_date": "2026-06-30",
        "gases": {"H2": 5.0, "CH4": 2.0, "C2H6": 11.0, "C2H4": 14.0, "C2H2": 0.5, "CO": 663.0, "CO2": 4194.0, "H2O": 15.0},
        "status": "PREWARNING"
    },
    {
        "transformer_id": "TRF-006",
        "name": "Station Service Transformer (SST)",
        "unit": "COMMON",
        "voltage_ratio": "150 / 6.3 kV",
        "rated_capacity": "10.0 MVA",
        "oil_type": "Mineral Oil (IEC 60296)",
        "oil_volume": "8,500 L",
        "sampling_date": "2026-05-14",
        "gases": {"H2": 8.0, "CH4": 9.0, "C2H6": 4.0, "C2H4": 7.0, "C2H2": 0.0, "CO": 95.0, "CO2": 920.0, "H2O": 12.0},
        "status": "NORMAL"
    }
]

def _override_store() -> DomainOverrideStore:
    return DomainOverrideStore(get_data_path('config', 'dga_overrides.json'))


def _dga_history_path() -> Path:
    return Path(get_data_path('DGA', 'dga_history_cbmai.csv'))


def _clean_unit(value: Any) -> str:
    text = str(value or '').strip().replace('_', ' ')
    return text.upper() if text else 'UNKNOWN'


def load_dga_history(csv_path: Optional[str] = None) -> pd.DataFrame:
    """Load CBMAI DGA history CSV copied into data/DGA.

    Expected source columns follow CBMAI's template: Date, Unit, Equipment,
    H2, CH4, C2H6, C2H4, C2H2, CO, CO2, WaterContent, BDV, temperatures, etc.
    Missing file/columns returns an empty DataFrame so the built-in demo assets
    and manual overrides remain usable.
    """
    path = Path(csv_path) if csv_path else _dga_history_path()
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame()
    required = {'Date', 'Unit', 'Equipment', 'H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO', 'CO2'}
    if not required.issubset(df.columns):
        return pd.DataFrame()
    df = df.copy()
    df['Date'] = pd.to_datetime(df['Date'], format='mixed', errors='coerce')
    for col in ('H2', 'CH4', 'C2H6', 'C2H4', 'C2H2', 'CO', 'CO2', 'WaterContent', 'BDV'):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
    df = df.dropna(subset=['Date', 'Equipment'])
    return df.sort_values(['Equipment', 'Date'])


def _csv_transformer_id(equipment: str, index: int) -> str:
    slug = ''.join(ch for ch in equipment.upper() if ch.isalnum())[-10:] or str(index + 1)
    return f'DGA-CBMAI-{index + 1:03d}-{slug}'


def _transformers_from_history() -> List[Dict[str, Any]]:
    history = load_dga_history()
    if history.empty:
        return []

    asset_lookup: Dict[str, Dict[str, Any]] = {}
    try:
        from src.asset_registry import list_assets
        for a in list_assets():
            asset_lookup[a.get('name', '').strip().upper()] = a
            for alias in a.get('aliases', []):
                asset_lookup[str(alias).strip().upper()] = a
    except Exception:
        asset_lookup = {}

    records: List[Dict[str, Any]] = []
    for idx, (equipment, group) in enumerate(history.groupby('Equipment', sort=True)):
        latest = group.sort_values('Date').iloc[-1]
        gases = {
            'H2': float(latest.get('H2', 0.0)),
            'CH4': float(latest.get('CH4', 0.0)),
            'C2H6': float(latest.get('C2H6', 0.0)),
            'C2H4': float(latest.get('C2H4', 0.0)),
            'C2H2': float(latest.get('C2H2', 0.0)),
            'CO': float(latest.get('CO', 0.0)),
            'CO2': float(latest.get('CO2', 0.0)),
            'H2O': float(latest.get('WaterContent', 0.0)),
        }
        diag = calculate_dga_diagnosis(gases)

        eq_key = str(equipment).strip().upper()
        asset = asset_lookup.get(eq_key)

        trf_id = asset.get('asset_id') if asset else _csv_transformer_id(str(equipment), idx)
        unit_val = asset.get('unit') if (asset and asset.get('unit')) else _clean_unit(latest.get('Unit'))
        v_ratio = asset.get('voltage_level', '-') if asset else '-'

        specs = asset.get('specs', {}) if asset else {}
        cap_val = specs.get('rated_capacity_kva', '-')
        if cap_val and cap_val != '-':
            rated_capacity = f"{cap_val} kVA" if "VA" not in str(cap_val).upper() else str(cap_val)
        else:
            rated_capacity = '-'

        oil_vol_val = specs.get('oil_litres', '-')
        oil_vol = f"{oil_vol_val} L" if (oil_vol_val and oil_vol_val != '-') else '-'
        oil_type = specs.get('oil_type', 'Mineral Oil')
        mfg = specs.get('manufacturer', '-')
        sn = specs.get('serial_number', '-')

        records.append({
            'transformer_id': trf_id,
            'asset_id': asset.get('asset_id', '') if asset else '',
            'name': str(equipment).strip(),
            'unit': _clean_unit(unit_val),
            'voltage_ratio': v_ratio,
            'rated_capacity': rated_capacity,
            'oil_type': oil_type,
            'oil_volume': oil_vol,
            'manufacturer': mfg,
            'serial_number': sn,
            'sampling_date': latest['Date'].strftime('%Y-%m-%d'),
            'gases': gases,
            'water_content': float(latest.get('WaterContent', 0.0)),
            'bdv': float(latest.get('BDV', 0.0)),
            'status': diag['status'],
            'source': 'CBMAI DGA CSV',
        })
    return records


def _history_for_equipment(equipment: str) -> List[Dict[str, Any]]:
    history = load_dga_history()
    if history.empty or not equipment:
        return []
    group = history[history['Equipment'].astype(str).str.upper() == str(equipment).upper()]
    records: List[Dict[str, Any]] = []
    for _, row in group.sort_values('Date').iterrows():
        gases = {
            'H2': float(row.get('H2', 0.0)),
            'CH4': float(row.get('CH4', 0.0)),
            'C2H6': float(row.get('C2H6', 0.0)),
            'C2H4': float(row.get('C2H4', 0.0)),
            'C2H2': float(row.get('C2H2', 0.0)),
            'CO': float(row.get('CO', 0.0)),
            'CO2': float(row.get('CO2', 0.0)),
        }
        diag = calculate_dga_diagnosis(gases)
        records.append({
            'date': row['Date'].strftime('%Y-%m-%d'),
            'tdcg': diag['tdcg'],
            'H2': gases['H2'],
            'CH4': gases['CH4'],
            'C2H6': gases['C2H6'],
            'C2H4': gases['C2H4'],
            'C2H2': gases['C2H2'],
            'CO': gases['CO'],
            'CO2': gases['CO2'],
            'water_content': float(row.get('WaterContent', 0.0)),
            'bdv': float(row.get('BDV', 0.0)),
            'status': diag['status'],
        })
    return records


def _merged_transformers() -> List[Dict[str, Any]]:
    """Transformers from CBMAI CSV history + DEFAULT_TRANSFORMERS (deduplicated) + overrides.

    Real history records take precedence over default mock assets.
    Manual override wins by transformer_id.
    """
    overrides = _override_store().all()
    history_records = _transformers_from_history()
    history_names = {t['name'].strip().upper() for t in history_records}
    history_ids = {t['transformer_id'].strip().upper() for t in history_records}

    filtered_defaults = [
        t for t in DEFAULT_TRANSFORMERS
        if t['name'].strip().upper() not in history_names
        and t['transformer_id'].strip().upper() not in history_ids
    ]
    base = history_records + filtered_defaults
    merged = [dict(overrides.get(t['transformer_id'], t)) for t in base]
    known_ids = {t['transformer_id'] for t in base}
    merged.extend(dict(record) for tid, record in overrides.items() if tid not in known_ids)
    return merged


def save_dga_transformer(transformer_id: str, fields: Dict[str, Any]) -> None:
    """Add a new transformer or edit an existing one (base or previously-overridden)."""
    record = dict(fields)
    record['transformer_id'] = transformer_id
    _override_store().set(transformer_id, record)


def calculate_dga_diagnosis(gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates TDCG, IEEE C57.104 condition, Duval Triangle 1, and Rogers Ratios."""
    h2 = float(gases.get("H2") or 0)
    ch4 = float(gases.get("CH4") or 0)
    c2h6 = float(gases.get("C2H6") or 0)
    c2h4 = float(gases.get("C2H4") or 0)
    c2h2 = float(gases.get("C2H2") or 0)
    co = float(gases.get("CO") or 0)
    co2 = float(gases.get("CO2") or 0)
    
    tdcg = h2 + ch4 + c2h6 + c2h4 + c2h2 + co
    
    # IEEE C57.104
    ieee_cond = "Condition 1 (Normal)"
    status = "NORMAL"
    if tdcg > 4630:
        ieee_cond = "Condition 4 (Critical)"
        status = "HIGH"
    elif tdcg > 1920:
        ieee_cond = "Condition 3 (High Warning)"
        status = "WARNING"
    elif tdcg > 720:
        ieee_cond = "Condition 2 (Warning)"
        status = "PREWARNING"
        
    # Duval Triangle 1
    sum_duval = ch4 + c2h4 + c2h2
    p_ch4 = (ch4 / sum_duval * 100) if sum_duval > 0 else 0
    p_c2h4 = (c2h4 / sum_duval * 100) if sum_duval > 0 else 0
    p_c2h2 = (c2h2 / sum_duval * 100) if sum_duval > 0 else 0
    
    duval_diag = "Normal Operation"
    if sum_duval > 10:
        if p_ch4 >= 98:
            duval_diag = "PD (Partial Discharge)"
        elif p_c2h2 < 4 and p_c2h4 < 20 and p_ch4 >= 76:
            duval_diag = "T1 (Thermal Fault T < 300°C)"
        elif p_c2h4 >= 20 and p_c2h4 < 50 and p_c2h2 < 4:
            duval_diag = "T2 (Thermal Fault 300°C < T < 700°C)"
        elif p_c2h4 >= 50 and p_c2h2 < 15:
            duval_diag = "T3 (Thermal Fault T > 700°C)"
        elif p_c2h2 >= 4 and p_c2h2 < 13 and p_c2h4 <= 50:
            duval_diag = "D1 (Low Energy Discharge / Sparking)"
        elif p_c2h2 >= 13 and p_c2h2 <= 29:
            duval_diag = "D1 (Low Energy Discharge / Sparking)"
        elif p_c2h2 >= 29:
            duval_diag = "D2 (High Energy Discharge / Arcing)"
        elif p_c2h2 >= 15 and p_c2h4 >= 50:
            duval_diag = "DT (Mixed Thermal & Electrical Fault)"
        else:
            duval_diag = "T1 (Thermal Fault T < 300°C)"

    # Rogers Ratios
    r1 = ch4 / h2 if h2 > 0 else 0
    r2 = c2h6 / ch4 if ch4 > 0 else 0
    r3 = c2h4 / c2h6 if c2h6 > 0 else 0
    
    rogers_diag = "Normal Deterioration"
    if r2 < 0.1 and 0.1 <= r1 < 1.0 and r3 < 0.1:
        rogers_diag = "Normal Deterioration"
    elif r2 < 0.1 and r1 < 0.1 and r3 < 0.1:
        rogers_diag = "Partial Discharge"
    elif 0.1 <= r2 < 1.0 and 0.1 <= r1 < 1.0 and 0.1 <= r3 < 3.0:
        rogers_diag = "Thermal Fault < 150°C"
    elif r2 < 0.1 and 0.1 <= r1 < 1.0 and 0.1 <= r3 < 3.0:
        rogers_diag = "Thermal Fault 150°C - 200°C"
    elif r2 < 0.1 and r1 >= 1.0 and 0.1 <= r3 < 3.0:
        rogers_diag = "Thermal Fault 200°C - 300°C"
    elif r2 < 0.1 and r1 >= 1.0 and r3 >= 3.0:
        rogers_diag = "Thermal Fault 300°C - 700°C"
    elif r2 < 0.1 and 0.1 <= r1 < 1.0 and r3 >= 3.0:
        rogers_diag = "Thermal Fault > 700°C"

    # CO2/CO ratio for paper insulation aging
    co2_co_ratio = round(co2 / co, 1) if co > 0 else 0.0
    paper_status = "Normal (< 7 ratio)" if 3 <= co2_co_ratio <= 10 else ("Severe Paper Degradation" if co2_co_ratio < 3 else "Normal")

    return {
        "tdcg": round(tdcg, 1),
        "ieee_condition": ieee_cond,
        "status": status,
        "duval_diagnosis": duval_diag,
        "rogers_diagnosis": rogers_diag,
        "co2_co_ratio": co2_co_ratio,
        "paper_status": paper_status,
        "duval_coords": {
            "pct_CH4": round(p_ch4, 1),
            "pct_C2H4": round(p_c2h4, 1),
            "pct_C2H2": round(p_c2h2, 1)
        }
    }

def get_dga_summary() -> Dict[str, Any]:
    """Returns summary stats for transformer DGA fleet."""
    transformers = _merged_transformers()
    by_unit = {}
    by_status = {"NORMAL": 0, "PREWARNING": 0, "WARNING": 0, "HIGH": 0}
    
    for t in transformers:
        u = t["unit"]
        by_unit[u] = by_unit.get(u, 0) + 1
        
        diag = calculate_dga_diagnosis(t["gases"])
        st = diag["status"]
        by_status[st] = by_status.get(st, 0) + 1
        
    return {
        "total_transformers": len(transformers),
        "by_unit": by_unit,
        "by_status": by_status
    }

def search_dga_transformers(unit: Optional[str] = None, status: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns filtered transformer list with diagnosis."""
    results = []
    for t in _merged_transformers():
        if unit and unit.upper() != "ALL" and t["unit"].upper() != unit.upper():
            continue
        if search and search.strip():
            st = search.lower().strip()
            if st not in t["name"].lower() and st not in t["transformer_id"].lower():
                continue
                
        diag = calculate_dga_diagnosis(t["gases"])
        if status and status.upper() != "ALL" and diag["status"].upper() != status.upper():
            continue
            
        t_copy = dict(t)
        t_copy["diagnosis"] = diag
        t_copy["status"] = diag["status"]
        t_copy["tdcg"] = diag["tdcg"]
        t_copy["duval_diag"] = diag["duval_diagnosis"]
        results.append(t_copy)
        
    return results

def get_dga_transformer_detail(transformer_id: str) -> Optional[Dict[str, Any]]:
    """Returns detailed transformer record including gas parameters and historical trend."""
    target = None
    query = transformer_id.strip().upper()
    merged = _merged_transformers()
    for t in merged:
        if (
            t["transformer_id"].upper() == query
            or t.get("asset_id", "").upper() == query
            or t["name"].upper() == query
        ):
            target = dict(t)
            break
            
    if not target:
        try:
            from src.asset_registry import list_assets
            for a in list_assets():
                aliases = [a.get("name", "").upper()] + [str(al).upper() for al in a.get("aliases", [])]
                if query == a.get("asset_id", "").upper() or query in aliases:
                    for t in merged:
                        if (
                            t.get("asset_id", "").upper() == a.get("asset_id", "").upper()
                            or t["name"].upper() == a.get("name", "").upper()
                        ):
                            target = dict(t)
                            break
                    if target:
                        break
        except Exception:
            pass

    if not target:
        for t in merged:
            t_name = t["name"].upper()
            t_id = t["transformer_id"].upper()
            if query in t_name or t_name in query or query in t_id:
                target = dict(t)
                break

    if not target:
        import re
        q_tokens = set(re.findall(r'[A-Za-z0-9]+', query))
        if q_tokens:
            best_match = None
            best_score = 0.0
            for t in merged:
                t_tokens = set(re.findall(r'[A-Za-z0-9]+', t["name"].upper()))
                if not t_tokens:
                    continue
                if t_tokens == q_tokens:
                    target = dict(t)
                    break
                if q_tokens.issubset(t_tokens) or t_tokens.issubset(q_tokens):
                    score = len(q_tokens & t_tokens) / max(len(q_tokens), len(t_tokens))
                    if score > best_score:
                        best_score = score
                        best_match = t
            if not target and best_match and best_score >= 0.5:
                target = dict(best_match)

    if not target:
        return None
        
    diag = calculate_dga_diagnosis(target["gases"])
    target["diagnosis"] = diag
    target["status"] = diag["status"]
    
    real_history = _history_for_equipment(target.get("name", ""))
    if real_history:
        target["history"] = real_history
    else:
        # Mock history records for built-in demo assets when no source CSV exists
        target["history"] = [
            {"date": "2025-11-10", "tdcg": max(10, diag["tdcg"] * 0.75), "H2": target["gases"]["H2"] * 0.8, "C2H4": target["gases"]["C2H4"] * 0.7, "CO": target["gases"]["CO"] * 0.9, "status": "NORMAL"},
            {"date": "2026-03-15", "tdcg": max(15, diag["tdcg"] * 0.88), "H2": target["gases"]["H2"] * 0.9, "C2H4": target["gases"]["C2H4"] * 0.85, "CO": target["gases"]["CO"] * 0.95, "status": "NORMAL"},
            {"date": target["sampling_date"], "tdcg": diag["tdcg"], "H2": target["gases"]["H2"], "C2H4": target["gases"]["C2H4"], "CO": target["gases"]["CO"], "status": diag["status"]}
        ]
    
    # Recommendations based on status
    if diag["status"] == "HIGH":
        rec = "Kondisi DGA Kritis. Lakukan re-sampling dalam 48 jam, verifikasi pembebanan trafo, dan persiapkan offline testing (Insulation Resistance & Tan Delta)."
    elif diag["status"] == "WARNING":
        rec = "Kandungan gas mudah terbakar (TDCG) tinggi. Tingkatkan frekuensi sampling menjadi 1 bulan sekali dan pantau kenaikan suhu minyak trafo."
    elif diag["status"] == "PREWARNING":
        rec = "Laju pembentukan gas terdeteksi termonitor. Lanjutkan pemantauan berkala 3 bulan sekali dan catat riwayat pembebanan puncak."
    else:
        rec = "Kondisi minyak trafo normal. Lanjutkan pengujian DGA rutin 6 bulan sekali sesuai IEEE C57.104."
    
    target["recommendation"] = rec
    return target
