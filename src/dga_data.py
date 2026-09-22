"""
DGA (Dissolved Gas Analysis) data loader and Transformer asset database.
Loads transformer health and gas data from Excel reports and structured records.
"""

import math
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


def calculate_duval_pentagon(gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates Duval Pentagon 1 coordinates and fault zone per CIGRE TB 771.
    
    5 gas components: H2, C2H6, CH4, C2H4, C2H2
    Apexes on circle:
      H2: 90 deg (Top)
      C2H6: 18 deg (Top-Right)
      CH4: -54 deg (Bottom-Right)
      C2H4: -126 deg (Bottom-Left)
      C2H2: 162 deg (Top-Left)
    """
    h2 = max(0.0, float(gases.get("H2") or 0))
    c2h6 = max(0.0, float(gases.get("C2H6") or 0))
    ch4 = max(0.0, float(gases.get("CH4") or 0))
    c2h4 = max(0.0, float(gases.get("C2H4") or 0))
    c2h2 = max(0.0, float(gases.get("C2H2") or 0))
    
    total_5 = h2 + c2h6 + ch4 + c2h4 + c2h2
    if total_5 <= 0:
        return {
            "x": 0.0,
            "y": 0.0,
            "zone": "Normal",
            "zone_label": "Normal Operation (Gas Rendah)",
            "zone_desc": "Kandungan 5 gas hidrokarbon rendah, tidak ada indikasi anomali.",
            "percentages": {"H2": 0.0, "C2H6": 0.0, "CH4": 0.0, "C2H4": 0.0, "C2H2": 0.0}
        }
    
    p_h2 = (h2 / total_5) * 100.0
    p_c2h6 = (c2h6 / total_5) * 100.0
    p_ch4 = (ch4 / total_5) * 100.0
    p_c2h4 = (c2h4 / total_5) * 100.0
    p_c2h2 = (c2h2 / total_5) * 100.0
    
    # Pentagon angles in radians (90°, 18°, -54°, -126°, 162°)
    angles = [
        math.radians(90),    # H2
        math.radians(18),    # C2H6
        math.radians(-54),   # CH4
        math.radians(-126),  # C2H4
        math.radians(162)    # C2H2
    ]
    r_max = 40.0
    
    x = (
        (p_h2 / 100.0) * r_max * math.cos(angles[0]) +
        (p_c2h6 / 100.0) * r_max * math.cos(angles[1]) +
        (p_ch4 / 100.0) * r_max * math.cos(angles[2]) +
        (p_c2h4 / 100.0) * r_max * math.cos(angles[3]) +
        (p_c2h2 / 100.0) * r_max * math.cos(angles[4])
    )
    y = (
        (p_h2 / 100.0) * r_max * math.sin(angles[0]) +
        (p_c2h6 / 100.0) * r_max * math.sin(angles[1]) +
        (p_ch4 / 100.0) * r_max * math.sin(angles[2]) +
        (p_c2h4 / 100.0) * r_max * math.sin(angles[3]) +
        (p_c2h2 / 100.0) * r_max * math.sin(angles[4])
    )

    # Zone detection per Duval Pentagon 1
    if p_h2 >= 75 or (y >= 18 and -10 <= x <= 14):
        zone = "PD"
        label = "PD (Partial Discharge)"
        desc = "Pelepasan muatan parsial bertegangan tinggi di dalam rongga gas atau gelembung minyak."
    elif p_c2h2 >= 35 or (x <= -12 and -16 <= y <= 12):
        zone = "D2"
        label = "D2 (High Energy Discharge / Arcing)"
        desc = "Pelepasan busur api energi tinggi (Arcing) menembus minyak trafo, flashover antar lilitan."
    elif p_c2h2 >= 12 or (x <= -6 and y >= 0):
        zone = "D1"
        label = "D1 (Low Energy Discharge / Sparking)"
        desc = "Pelepasan percikan listrik energi rendah (Sparking), potensi elektroda mengambang atau pin isolator."
    elif p_c2h4 >= 45 or (x <= 5 and y <= -15):
        zone = "T3"
        label = "T3 (Thermal Fault T > 700°C)"
        desc = "Gangguan termal suhu tinggi (> 700°C), overheating parah pada inti besi atau belitan."
    elif p_c2h4 >= 20 or (y <= -8 and x >= -10):
        zone = "T2"
        label = "T2 (Thermal Fault 300°C < T < 700°C)"
        desc = "Gangguan termal suhu menengah (300°C - 700°C), pemanasan berlebih lokal pada sambungan konduktor."
    elif p_ch4 >= 35 or (x >= 12 and y <= 8):
        zone = "T1"
        label = "T1 (Thermal Fault T < 300°C)"
        desc = "Gangguan termal suhu rendah (< 300°C), degradasi minyak ringan pada titik panas terisolasi."
    elif p_c2h6 >= 30 or (-8 <= x <= 12 and -6 <= y <= 14):
        zone = "S"
        label = "S (Stray Gassing / Oil Overheating < 200°C)"
        desc = "Pelepasan gas alami (stray gassing) pada minyak mineral di bawah 200°C."
    else:
        zone = "T1"
        label = "T1 (Thermal Fault T < 300°C)"
        desc = "Gangguan termal suhu rendah pada minyak trafo."

    return {
        "x": round(x, 2),
        "y": round(y, 2),
        "zone": zone,
        "zone_label": label,
        "zone_desc": desc,
        "percentages": {
            "H2": round(p_h2, 1),
            "C2H6": round(p_c2h6, 1),
            "CH4": round(p_ch4, 1),
            "C2H4": round(p_c2h4, 1),
            "C2H2": round(p_c2h2, 1)
        }
    }


def calculate_rogers_ratios(gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates Rogers Ratios and IEC 60599 diagnostics.
    
    Ratios:
      R1 = C2H2 / C2H4 (Acetylene / Ethylene)
      R2 = CH4 / H2   (Methane / Hydrogen)
      R3 = C2H4 / C2H6 (Ethylene / Ethane)
    """
    h2 = max(0.0, float(gases.get("H2") or 0))
    ch4 = max(0.0, float(gases.get("CH4") or 0))
    c2h6 = max(0.0, float(gases.get("C2H6") or 0))
    c2h4 = max(0.0, float(gases.get("C2H4") or 0))
    c2h2 = max(0.0, float(gases.get("C2H2") or 0))
    co = max(0.0, float(gases.get("CO") or 0))
    co2 = max(0.0, float(gases.get("CO2") or 0))

    r1 = round(c2h2 / c2h4, 3) if c2h4 > 0 else (0.0 if c2h2 == 0 else 999.0)
    r2 = round(ch4 / h2, 3) if h2 > 0 else (0.0 if ch4 == 0 else 999.0)
    r3 = round(c2h4 / c2h6, 3) if c2h6 > 0 else (0.0 if c2h4 == 0 else 999.0)
    co2_co = round(co2 / co, 2) if co > 0 else 0.0

    # Diagnostic codes per IEC 60599
    code_r1 = 0 if r1 < 0.1 else (1 if r1 <= 3.0 else 2)
    code_r2 = 1 if r2 < 0.1 else (0 if r2 <= 1.0 else 2)
    code_r3 = 0 if r3 < 1.0 else (1 if r3 <= 3.0 else 2)
    diag_code = f"{code_r1}-{code_r2}-{code_r3}"

    if r1 < 0.1 and 0.1 <= r2 <= 1.0 and r3 < 1.0:
        diagnosis = "Normal Deterioration"
        description = "Degradasi normal isolasi minyak karena penuaan operasional normal."
        severity = "NORMAL"
    elif r1 < 0.1 and r2 < 0.1 and r3 < 1.0:
        diagnosis = "Partial Discharge (Corona)"
        description = "Pelepasan muatan listrik parsial berdaya rendah di dalam rongga isolasi atau celah gas."
        severity = "WARNING"
    elif 0.1 <= r1 <= 3.0 and 0.1 <= r2 <= 1.0 and r3 > 3.0:
        diagnosis = "Continuous Sparking / Arcing"
        description = "Pelepasan bunga api listrik terus-menerus ke elektroda mengambang atau kontak longgar."
        severity = "HIGH"
    elif r1 >= 1.0 and 0.1 <= r2 <= 1.0 and 0.1 <= r3 <= 3.0:
        diagnosis = "Arc with Power Follow-through"
        description = "Busur listrik energi tinggi menembus dielektrik minyak trafo (Arcing)."
        severity = "HIGH"
    elif r1 < 0.1 and 0.1 <= r2 <= 1.0 and 1.0 <= r3 <= 3.0:
        diagnosis = "Thermal Fault 150°C - 200°C"
        description = "Overheating ringan pada minyak trafo atau konduktor lokal."
        severity = "PREWARNING"
    elif r1 < 0.1 and r2 > 1.0 and 1.0 <= r3 <= 3.0:
        diagnosis = "Thermal Fault 200°C - 300°C"
        description = "Pemanasan setempat suhu menengah pada inti besi atau sambungan konduktor."
        severity = "WARNING"
    elif r1 < 0.1 and r2 > 1.0 and r3 >= 3.0:
        diagnosis = "Thermal Fault 300°C - 700°C"
        description = "Pemanasan konduktor serius disertai degradasi minyak dan karbonisasi awal."
        severity = "WARNING"
    elif r1 < 0.1 and 0.1 <= r2 <= 1.0 and r3 >= 3.0:
        diagnosis = "Thermal Fault > 700°C"
        description = "Suhu termal ekstrem melebihi 700°C, pembentukan jelaga dan degradasi parah."
        severity = "HIGH"
    elif r1 >= 0.1:
        diagnosis = "Electrical Discharge / Sparking"
        description = "Terdeteksi pelepasan listrik aktif yang menghasilkan gas asetilena (C2H2)."
        severity = "HIGH"
    else:
        diagnosis = "Thermal Fault Undifferentiated"
        description = "Indikasi suhu termal tidak seimbang pada belitan trafo."
        severity = "PREWARNING"

    if co2_co >= 7.0 and co2_co <= 15.0:
        paper_diag = "Normal (Penuaan wajar)"
    elif co2_co < 3.0:
        paper_diag = "Kritis (Degradasi / Pyrolysis isolasi kertas selulosa)"
    elif co2_co < 7.0:
        paper_diag = "Perhatian (Penuaan isolasi kertas dipercepat)"
    else:
        paper_diag = "Normal (Rasio tinggi menandakan oksidasi suhu rendah)"

    return {
        "r1_c2h2_c2h4": r1,
        "r2_ch4_h2": r2,
        "r3_c2h4_c2h6": r3,
        "co2_co_ratio": co2_co,
        "diag_code": diag_code,
        "diagnosis": diagnosis,
        "description": description,
        "severity": severity,
        "paper_diagnosis": paper_diag,
    }


def calculate_key_gas_profile(gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates Key Gas method proportions and fault identification per IEEE C57.104."""
    h2 = max(0.0, float(gases.get("H2") or 0))
    ch4 = max(0.0, float(gases.get("CH4") or 0))
    c2h6 = max(0.0, float(gases.get("C2H6") or 0))
    c2h4 = max(0.0, float(gases.get("C2H4") or 0))
    c2h2 = max(0.0, float(gases.get("C2H2") or 0))
    co = max(0.0, float(gases.get("CO") or 0))
    
    total_key = h2 + ch4 + c2h6 + c2h4 + c2h2 + co
    if total_key <= 0:
        return {
            "dominant_gas": "-",
            "fault_type": "Normal (Tidak Ada Gas Kunci)",
            "primary_mechanism": "Konsentrasi seluruh gas kunci berada pada tingkat latar belakang yang dapat diabaikan.",
            "proportions": {"H2": 0.0, "CH4": 0.0, "C2H6": 0.0, "C2H4": 0.0, "C2H2": 0.0, "CO": 0.0},
            "scores": {"thermal_oil": 0, "thermal_cellulose": 0, "corona_pd": 0, "arcing": 0}
        }
    
    p = {
        "H2": round((h2 / total_key) * 100.0, 1),
        "CH4": round((ch4 / total_key) * 100.0, 1),
        "C2H6": round((c2h6 / total_key) * 100.0, 1),
        "C2H4": round((c2h4 / total_key) * 100.0, 1),
        "C2H2": round((c2h2 / total_key) * 100.0, 1),
        "CO": round((co / total_key) * 100.0, 1),
    }

    s_oil = min(100.0, max(0.0, (p["C2H4"] * 1.3) + (p["CH4"] * 0.4) + (p["C2H6"] * 0.3) - (p["C2H2"] * 1.5)))
    s_cell = min(100.0, max(0.0, (p["CO"] * 1.05) - (p["C2H2"] * 1.2)))
    s_pd = min(100.0, max(0.0, (p["H2"] * 1.15) + (p["CH4"] * 0.2) - (p["C2H2"] * 1.5)))
    s_arc = min(100.0, max(0.0, (p["C2H2"] * 1.8) + (p["H2"] * 0.3)))

    scores = {
        "thermal_oil": round(s_oil, 1),
        "thermal_cellulose": round(s_cell, 1),
        "corona_pd": round(s_pd, 1),
        "arcing": round(s_arc, 1),
    }

    dominant_gas = max(p.items(), key=lambda kv: kv[1])[0]

    best_fault = max(scores.items(), key=lambda kv: kv[1])
    if best_fault[0] == "arcing" and p["C2H2"] >= 3.0:
        fault_type = "Electrical Arcing (Flashover)"
        mech = f"Gas kunci utama: Asetilena ({p['C2H2']}%), mengindikasikan loncatan busur api listrik suhu tinggi menembus minyak trafo."
    elif best_fault[0] == "thermal_oil" and p["C2H4"] >= 20.0:
        fault_type = "Thermal Oil Degradation"
        mech = f"Gas kunci utama: Etilena ({p['C2H4']}%), mengindikasikan overheating termal suhu tinggi pada minyak trafo."
    elif best_fault[0] == "thermal_cellulose" and p["CO"] >= 50.0:
        fault_type = "Thermal Cellulose / Paper Overheating"
        mech = f"Gas kunci utama: Karbon Monoksida ({p['CO']}%), mengindikasikan degradasi dan penuaan termal isolasi kertas selulosa."
    elif best_fault[0] == "corona_pd" and p["H2"] >= 40.0:
        fault_type = "Electrical Corona / Partial Discharge"
        mech = f"Gas kunci utama: Hidrogen ({p['H2']}%), mengindikasikan pelepasan muatan parsial pada rongga udara atau gelembung minyak."
    else:
        fault_type = "Normal / Undifferentiated Mix"
        mech = "Distribusi gas kunci campuran pada tingkat operasional wajar, tidak ada pola gangguan tunggal dominan."

    return {
        "dominant_gas": dominant_gas,
        "fault_type": fault_type,
        "primary_mechanism": mech,
        "proportions": p,
        "scores": scores
    }


def calculate_gas_trend_prediction(history: List[Dict[str, Any]], current_gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates rate of gas generation and 3/6/12-month projections per IEEE C57.104."""
    gas_keys = ["H2", "CH4", "C2H6", "C2H4", "C2H2", "CO", "CO2"]
    current_tdcg = sum(float(current_gases.get(k) or 0) for k in ["H2", "CH4", "C2H6", "C2H4", "C2H2", "CO"])
    
    if not history or len(history) < 2:
        rate_day = {k: 0.01 for k in gas_keys}
        rate_day["TDCG"] = 0.05
        interval_days = 90
    else:
        sorted_h = sorted(history, key=lambda r: str(r.get("date", "")))
        prev = sorted_h[-2]
        curr = sorted_h[-1]
        
        try:
            d_curr = pd.to_datetime(curr.get("date"))
            d_prev = pd.to_datetime(prev.get("date"))
            interval_days = max(1, (d_curr - d_prev).days)
        except Exception:
            interval_days = 90

        rate_day = {}
        for k in gas_keys:
            v_curr = float(curr.get(k, current_gases.get(k, 0)))
            v_prev = float(prev.get(k, 0))
            delta = v_curr - v_prev
            rate_day[k] = round(delta / interval_days, 3)
            
        tdcg_curr = float(curr.get("tdcg", current_tdcg))
        tdcg_prev = float(prev.get("tdcg", tdcg_curr))
        rate_day["TDCG"] = round((tdcg_curr - tdcg_prev) / interval_days, 3)

    rate_month = {k: round(rate_day[k] * 30.0, 2) for k in rate_day}

    forecast_3m = {}
    forecast_6m = {}
    forecast_12m = {}

    for k in gas_keys:
        curr_val = float(current_gases.get(k, 0))
        r = rate_day.get(k, 0.0)
        forecast_3m[k] = round(max(0.0, curr_val + (r * 90)), 1)
        forecast_6m[k] = round(max(0.0, curr_val + (r * 180)), 1)
        forecast_12m[k] = round(max(0.0, curr_val + (r * 365)), 1)

    r_tdcg = rate_day.get("TDCG", 0.0)
    forecast_3m["TDCG"] = round(max(0.0, current_tdcg + (r_tdcg * 90)), 1)
    forecast_6m["TDCG"] = round(max(0.0, current_tdcg + (r_tdcg * 180)), 1)
    forecast_12m["TDCG"] = round(max(0.0, current_tdcg + (r_tdcg * 365)), 1)

    tdcg_rate = rate_day.get("TDCG", 0.0)
    c2h2_rate = rate_day.get("C2H2", 0.0)
    h2_rate = rate_day.get("H2", 0.0)

    if tdcg_rate > 30.0 or c2h2_rate > 0.5:
        rate_status = "CRITICAL"
        rate_desc = "Laju pembentukan gas sangat cepat (kritis). Risiko gangguan aktif berenergi tinggi."
        action_advice = "Lakukan re-sampling dalam kurun waktu 48 jam dan evaluasi pengurangan pembebanan trafo."
    elif tdcg_rate > 10.0 or c2h2_rate > 0.1 or h2_rate > 5.0:
        rate_status = "ALERT"
        rate_desc = "Laju pembentukan gas meningkat di atas batas toleransi IEEE C57.104."
        action_advice = "Tingkatkan frekuensi sampling menjadi 1 bulan sekali dan pantau tren secara ketat."
    elif tdcg_rate > 3.0:
        rate_status = "PREWARNING"
        rate_desc = "Kenaikan gas terdeteksi moderat seiring peningkatan beban trafo."
        action_advice = "Lanjutkan pemantauan berkala 3 bulan sekali dan periksa riwayat pembebanan puncak."
    else:
        rate_status = "STABLE"
        rate_desc = "Laju pembentukan gas stabil dalam batas operasional aman (< 10 ppm/hari)."
        action_advice = "Lanjutkan siklus pemeliharaan rutin 6 bulan sekali."

    days_to_warn = None
    if current_tdcg < 720 and r_tdcg > 0.05:
        days_to_warn = int((720 - current_tdcg) / r_tdcg)
    elif current_tdcg >= 720:
        days_to_warn = 0

    return {
        "interval_days": interval_days,
        "rate_ppm_day": rate_day,
        "rate_ppm_month": rate_month,
        "rate_status": rate_status,
        "rate_desc": rate_desc,
        "action_advice": action_advice,
        "days_to_warning": days_to_warn,
        "forecast_3m": forecast_3m,
        "forecast_6m": forecast_6m,
        "forecast_12m": forecast_12m,
    }


def calculate_dga_diagnosis(gases: Dict[str, float]) -> Dict[str, Any]:
    """Calculates TDCG, IEEE C57.104 condition, Duval Triangle 1, Duval Pentagon 1, Rogers Ratios, and Key Gas."""
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
        elif p_c2h2 < 4 and p_c2h4 < 20:
            duval_diag = "T1 (Thermal Fault T < 300°C)"
        elif p_c2h2 < 4 and 20 <= p_c2h4 < 50:
            duval_diag = "T2 (Thermal Fault 300°C < T < 700°C)"
        elif p_c2h2 < 15 and p_c2h4 >= 50:
            duval_diag = "T3 (Thermal Fault T > 700°C)"
        elif (4 <= p_c2h2 < 29) and p_c2h4 >= 50:
            duval_diag = "DT (Mixed Thermal & Electrical Fault)"
        elif p_c2h2 >= 29:
            duval_diag = "D2 (High Energy Discharge / Arcing)"
        elif 4 <= p_c2h2 < 29:
            duval_diag = "D1 (Low Energy Discharge / Sparking)"
        else:
            duval_diag = "T1 (Thermal Fault T < 300°C)"

    # Rogers Ratios & Pentagon & Key Gas
    rogers_info = calculate_rogers_ratios(gases)
    pentagon_info = calculate_duval_pentagon(gases)
    key_gas_info = calculate_key_gas_profile(gases)

    return {
        "tdcg": round(tdcg, 1),
        "ieee_condition": ieee_cond,
        "status": status,
        "duval_diagnosis": duval_diag,
        "rogers_diagnosis": rogers_info["diagnosis"],
        "co2_co_ratio": rogers_info["co2_co_ratio"],
        "paper_status": rogers_info["paper_diagnosis"],
        "duval_coords": {
            "pct_CH4": round(p_ch4, 1),
            "pct_C2H4": round(p_c2h4, 1),
            "pct_C2H2": round(p_c2h2, 1)
        },
        "pentagon": pentagon_info,
        "rogers": rogers_info,
        "key_gas": key_gas_info,
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
        target["history"] = [
            {
                "date": "2025-11-10",
                "tdcg": max(10, diag["tdcg"] * 0.75),
                "H2": round(float(target["gases"].get("H2", 0)) * 0.8, 1),
                "CH4": round(float(target["gases"].get("CH4", 0)) * 0.75, 1),
                "C2H6": round(float(target["gases"].get("C2H6", 0)) * 0.8, 1),
                "C2H4": round(float(target["gases"].get("C2H4", 0)) * 0.7, 1),
                "C2H2": round(float(target["gases"].get("C2H2", 0)) * 0.5, 1),
                "CO": round(float(target["gases"].get("CO", 0)) * 0.9, 1),
                "CO2": round(float(target["gases"].get("CO2", 0)) * 0.95, 1),
                "status": "NORMAL"
            },
            {
                "date": "2026-03-15",
                "tdcg": max(15, diag["tdcg"] * 0.88),
                "H2": round(float(target["gases"].get("H2", 0)) * 0.9, 1),
                "CH4": round(float(target["gases"].get("CH4", 0)) * 0.88, 1),
                "C2H6": round(float(target["gases"].get("C2H6", 0)) * 0.9, 1),
                "C2H4": round(float(target["gases"].get("C2H4", 0)) * 0.85, 1),
                "C2H2": round(float(target["gases"].get("C2H2", 0)) * 0.8, 1),
                "CO": round(float(target["gases"].get("CO", 0)) * 0.95, 1),
                "CO2": round(float(target["gases"].get("CO2", 0)) * 0.98, 1),
                "status": "NORMAL"
            },
            {
                "date": target.get("sampling_date", "2026-09-01"),
                "tdcg": diag["tdcg"],
                "H2": round(float(target["gases"].get("H2", 0)), 1),
                "CH4": round(float(target["gases"].get("CH4", 0)), 1),
                "C2H6": round(float(target["gases"].get("C2H6", 0)), 1),
                "C2H4": round(float(target["gases"].get("C2H4", 0)), 1),
                "C2H2": round(float(target["gases"].get("C2H2", 0)), 1),
                "CO": round(float(target["gases"].get("CO", 0)), 1),
                "CO2": round(float(target["gases"].get("CO2", 0)), 1),
                "status": diag["status"]
            }
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
    target["prediction"] = calculate_gas_trend_prediction(target["history"], target["gases"])
    return target
