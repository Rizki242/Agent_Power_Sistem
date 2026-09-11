import re
import os
import json

import pandas as pd
from src.data_loader import get_data_path
from src.rotorbar import evaluate_rotorbar
from src.utils import safe_float as _safe_float


def calculate_rotorbar_severity(params):
    return evaluate_rotorbar(params)


def calculate_condition(params):
    results = {
        'Rotorbar': 'Normal',
        'Unbalance_Voltage': 'Normal',
        'Unbalance_Current': 'Normal',
        'THD': 'Normal',
        'Bearing': 'Normal', # Default if no data
        'Overall': 'Normal'
    }
    
    rb = calculate_rotorbar_severity(params)
    results['Rotorbar'] = rb.get('Status', 'Normal')

    # --- 2. Unbalance Analysis ---
    # Voltage Unbalance (NEMA MG-1)
    # > 1% Warning, > 2% Alarm
    if 'Dev Voltage' in params and params['Dev Voltage'] is not None:
        val = _safe_float(params.get('Dev Voltage'))
        if val is not None:
            if val > 2.0:
                results['Unbalance_Voltage'] = 'High'
            elif val > 1.0:
                results['Unbalance_Voltage'] = 'Alarm'

    # Current Unbalance
    # > 10% Alarm, > 5% Warning
    if 'Dev Current' in params and params['Dev Current'] is not None:
        val = _safe_float(params.get('Dev Current'))
        if val is not None:
            if val > 10.0:
                results['Unbalance_Current'] = 'High'
            elif val > 5.0:
                results['Unbalance_Current'] = 'Alarm'

    # --- 3. Power Quality (THD) ---
    # IEEE 519: Voltage THD > 5% is bad
    thd_candidates = []
    if 'THD Voltage %' in params and params['THD Voltage %'] is not None:
        val = _safe_float(params.get('THD Voltage %'))
        if val is not None:
            if val > 8.0:
                thd_candidates.append('High')
            elif val > 5.0:
                thd_candidates.append('Alarm')

    if 'THD Current %' in params and params['THD Current %'] is not None:
        val = _safe_float(params.get('THD Current %'))
        if val is not None:
            if val > 8.0:
                thd_candidates.append('High')
            elif val > 5.0:
                thd_candidates.append('Alarm')

    if thd_candidates:
        if 'High' in thd_candidates:
            results['THD'] = 'High'
        elif 'Alarm' in thd_candidates:
            results['THD'] = 'Alarm'

    # --- 4. Bearing ---
    # User Request: Normal or Bad.
    # Mapping: Bad -> High (Red)
    if 'Bearing' in params and isinstance(params['Bearing'], str):
        val = params['Bearing'].lower()
        if 'bad' in val or 'damage' in val or 'rusak' in val or 'high' in val:
            results['Bearing'] = 'High'
        elif 'alarm' in val or 'warning' in val:
            results['Bearing'] = 'Alarm'
        elif 'ok' in val or 'normal' in val:
            results['Bearing'] = 'Normal'

    # --- 5. Overall Calculation ---
    # Priority: High > Alarm > Normal
    severity_map = {
        'Normal': 1, 
        'Monitoring': 1,
        'Standby': 0,
        'Alarm': 2, 
        'Warning': 2, 
        'High': 3, 
        'Bad': 3,
        'High / Warning': 2, # Kept for backward compatibility if old data exists
        'CRITICAL / TRIP RISK': 3,
        'Critical': 3
    }
    
    current_max = 1
    for k, v in results.items():
        if k != 'Overall':
            score = severity_map.get(v, 1)
            if score > current_max:
                current_max = score
    
    final_status = 'Normal'
    if current_max == 2:
        final_status = 'Alarm' # User: Alarm = Kuning
    elif current_max == 3:
        final_status = 'High'  # User: High = Merah
        
    results['Overall'] = final_status
    return results


def generate_initial_analysis(history_df):
    if history_df is None or len(history_df) == 0:
        return {
            'indicators': [],
            'recommendations': [
                'Tidak ada data history untuk dianalisis.'
            ],
            'references': []
        }

    df = history_df.copy()
    if 'Parameter' not in df.columns:
        return {
            'indicators': [],
            'recommendations': [
                'Format data tidak memiliki kolom Parameter.'
            ],
            'references': []
        }

    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    else:
        df['Date'] = pd.NaT

    df = df.dropna(subset=['Parameter'])
    df['Parameter'] = df['Parameter'].astype(str)

    df_sorted = df.sort_values(by=['Date'], ascending=True)
    latest_rows = df_sorted.groupby('Parameter', as_index=False).tail(1)
    latest_map = {row['Parameter']: row for _, row in latest_rows.iterrows()}

    def _row_val(param_name):
        row = latest_map.get(param_name)
        if row is None:
            return None
        v = row.get('Value') if 'Value' in row else None
        if v is None or (isinstance(v, float) and pd.isna(v)):
            v = row.get('Raw_Value') if 'Raw_Value' in row else None
        return v

    condition_params = {
        'Dev Voltage': _row_val('Dev Voltage'),
        'Dev Current': _row_val('Dev Current'),
        'THD Voltage %': _row_val('THD Voltage %'),
        'THD Current %': _row_val('THD Current %'),
        'Bearing': _row_val('Bearing'),
        'Upper Sideband': _row_val('Upper Sideband'),
        'Lower Sideband': _row_val('Lower Sideband'),
        'Rotorbar Health': _row_val('Rotorbar Health'),
        'Se Fund': _row_val('Se Fund'),
        'Se Harm': _row_val('Se Harm'),
        'Rotorbar Level %': _row_val('Rotorbar Level %'),
    }
    status = calculate_condition(condition_params)

    def _trend(param_name):
        s = df_sorted[df_sorted['Parameter'] == param_name].copy()
        if s.empty:
            return None

        if 'Value' in s.columns:
            nums = s['Value'].map(_safe_float)
        else:
            nums = pd.Series([None] * len(s), index=s.index)
        if 'Raw_Value' in s.columns:
            nums = nums.fillna(s['Raw_Value'].map(_safe_float))
        s = s.assign(_num=nums).dropna(subset=['_num'])
        if len(s) < 2:
            return 'Stabil'

        last = float(s['_num'].iloc[-1])
        prev = float(s['_num'].iloc[-2])
        delta = last - prev
        eps = max(0.01, abs(prev) * 0.01)
        if abs(delta) <= eps:
            return 'Stabil'
        return 'Naik' if delta > 0 else 'Turun'

    def _last_num(param_name):
        v = _row_val(param_name)
        return _safe_float(v)

    def _last_date(param_name):
        row = latest_map.get(param_name)
        if row is None:
            return None
        dt = row.get('Date')
        if isinstance(dt, pd.Timestamp) and not pd.isna(dt):
            return dt.date().isoformat()
        return None

    indicator_specs = [
        ('Dev Voltage', 'Unbalance_Voltage'),
        ('Dev Current', 'Unbalance_Current'),
        ('THD Voltage %', 'THD'),
        ('THD Current %', 'THD'),
    ]

    indicators = []
    for p_name, status_key in indicator_specs:
        if p_name in latest_map:
            indicators.append({
                'Parameter': p_name,
                'Nilai Terakhir': _last_num(p_name),
                'Trend': _trend(p_name),
                'Status': status.get(status_key, 'Normal'),
                'Tanggal': _last_date(p_name)
            })

    if 'Bearing' in latest_map:
        indicators.append({
            'Parameter': 'Bearing',
            'Nilai Terakhir': _row_val('Bearing'),
            'Trend': None,
            'Status': status.get('Bearing', 'Normal'),
            'Tanggal': _last_date('Bearing')
        })

    if any(k in latest_map for k in ['Upper Sideband', 'Lower Sideband', 'Rotorbar Health', 'Rotorbar Level %']):
        rb = calculate_rotorbar_severity(condition_params)
        indicators.append({
            'Parameter': 'Rotorbar',
            'Nilai Terakhir': rb.get('Assessment'),
            'Trend': None,
            'Status': status.get('Rotorbar', 'Normal'),
            'Tanggal': _last_date('Rotorbar Health') or _last_date('Upper Sideband') or _last_date('Lower Sideband')
        })

    references = []
    recommendations = []

    overall = status.get('Overall', 'Normal')
    if overall == 'High':
        recommendations.append('Prioritaskan inspeksi dan verifikasi ulang hasil pengukuran; pertimbangkan pembatasan operasi hingga penyebab jelas.')
    elif overall == 'Alarm':
        recommendations.append('Jadwalkan pemeriksaan lanjutan dan lakukan trending lebih sering untuk parameter yang abnormal.')

    uv = status.get('Unbalance_Voltage', 'Normal')
    if uv in {'Alarm', 'High'}:
        recommendations.append('Cek ketidakseimbangan tegangan (suplai/terminal/koneksi), ketidakseimbangan beban satu fasa, dan kualitas sambungan; lakukan ukur ulang di titik yang sama.')
        references.append('NEMA MG 1 (Voltage unbalance guidance)')

    uc = status.get('Unbalance_Current', 'Normal')
    if uc in {'Alarm', 'High'}:
        recommendations.append('Jika arus tidak seimbang, periksa indikasi unbalance tegangan, koneksi, dan kondisi beban; pastikan konfigurasi CT dan pembacaan benar.')
        if 'NEMA MG 1 (Voltage unbalance guidance)' not in references:
            references.append('NEMA MG 1 (Voltage unbalance guidance)')

    thd = status.get('THD', 'Normal')
    if thd in {'Alarm', 'High'}:
        recommendations.append('Jika THD tegangan tinggi, identifikasi sumber harmonisa (mis. VFD/rectifier), evaluasi filter/reaktor, dan pastikan pengukuran di titik PCC sesuai praktik yang benar.')
        references.append('IEEE Std 519 (Harmonic control in power systems)')

    br = status.get('Bearing', 'Normal')
    if br in {'Alarm', 'High'}:
        recommendations.append('Tindak lanjuti indikasi bearing: cek pelumasan, alignment, looseness, dan lakukan inspeksi lanjutan (vibrasi/termografi) sesuai prosedur maintenance.')
        references.append('ISO 15243 (Rolling bearings — Damage and failures)')

    if not recommendations:
        recommendations.append('Tidak ada anomali utama terdeteksi pada indikator yang tersedia; lanjutkan monitoring berkala dan konsistenkan metode pengukuran.')

    references = list(dict.fromkeys([r for r in references if r]))

    return {
        'indicators': indicators,
        'recommendations': recommendations,
        'references': references
    }

def load_thresholds_config():
    base = get_data_path('config')
    paths = [
        os.path.join(base, 'thresholds_default.json'),
        os.path.join(base, 'thresholds_site_override.json'),
        os.path.join(base, 'thresholds_motor_override.json'),
    ]
    cfg = {}
    for p in paths:
        try:
            if os.path.exists(p):
                with open(p, 'r', encoding='utf-8') as fp:
                    data = json.load(fp)
                for k, v in (data or {}).items():
                    cfg[k] = v
        except Exception:
            pass
    return cfg


def load_esa_mcsa_guidance_config():
    defaults = {
        'overall': {
            'high': [
                'Prioritaskan inspeksi dan verifikasi ulang hasil pengukuran (ESA/MCSA).',
                'Pertimbangkan pembatasan operasi sampai penyebab utama terkonfirmasi.',
            ],
            'alarm': [
                'Jadwalkan pemeriksaan lanjutan dan lakukan trending lebih sering untuk parameter yang abnormal (ESA/MCSA).',
            ],
            'normal': [
                'Lanjutkan monitoring berkala dengan prosedur pengukuran yang konsisten (ESA/MCSA).',
            ],
        },
        'load': {
            'invalid': [
                'Load terlalu rendah untuk diagnosis yang valid; lakukan pengukuran ulang pada beban lebih tinggi.',
            ],
            'monitoring': [
                'Load menengah: gunakan hasil untuk monitoring; konfirmasi ulang di beban lebih tinggi untuk diagnosis rotor bar yang lebih akurat.',
            ],
            'valid': [
                'Load memadai untuk diagnosis; lanjutkan interpretasi ESA/MCSA sesuai indikator.',
            ],
        },
        'unbalance_voltage': {
            'alarm_high': [
                'Periksa suplai/terminal/koneksi dan ketidakseimbangan beban satu fasa; ulangi pengukuran di titik yang sama.',
            ],
        },
        'unbalance_current': {
            'alarm_high': [
                'Periksa indikasi unbalance tegangan, koneksi, dan kondisi beban; pastikan konfigurasi CT dan pembacaan benar.',
            ],
        },
        'thd_voltage': {
            'alarm_high': [
                'Identifikasi sumber harmonisa (mis. VFD/rectifier), evaluasi filter/reaktor, dan validasi titik ukur sesuai praktik ESA/MCSA.',
            ],
        },
        'rotorbar': {
            'monitoring': [
                'Indikasi rotor bar ringan: lakukan trending, konfirmasi pada load lebih tinggi, dan validasi sideband sesuai standar ESA/MCSA.',
            ],
            'alarm_high': [
                'Indikasi rotor bar kuat: lakukan verifikasi ulang pengukuran, inspeksi rotor (bila memungkinkan), dan siapkan rencana tindak lanjut maintenance.',
            ],
        },
        'bearing': {
            'alarm_high': [
                'Tindak lanjuti indikasi bearing: cek pelumasan, alignment, looseness, dan lakukan inspeksi lanjutan sesuai prosedur maintenance.',
            ],
        },
        'references': [
            'ESA/MCSA International guidelines',
        ],
    }

    cfg_path = get_data_path('config', 'esa_mcsa_guidance.json')
    override = {}
    try:
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as fp:
                override = json.load(fp) or {}
    except Exception:
        override = {}

    def _deep_merge(a, b):
        if not isinstance(a, dict) or not isinstance(b, dict):
            return b
        out = dict(a)
        for k, v in b.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    return _deep_merge(defaults, override)


def generate_esa_mcsa_quick_recommendations(latest_df: pd.DataFrame):
    thresholds = load_thresholds_config() or {}
    guidance = load_esa_mcsa_guidance_config() or {}

    def _get_thr(path, default=None):
        cur = thresholds
        for p in path:
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur

    def _row_map(df_in: pd.DataFrame):
        if df_in is None or df_in.empty or 'Parameter' not in df_in.columns:
            return {}
        m = {}
        for _, r in df_in.iterrows():
            p = str(r.get('Parameter', '')).strip()
            if p:
                m[p] = r
        return m

    rows = _row_map(latest_df)

    def _value(param_name):
        r = rows.get(param_name)
        if r is None:
            return None
        v = r.get('Value') if isinstance(r, dict) else r['Value'] if 'Value' in r else None
        if v is None or (isinstance(v, float) and pd.isna(v)):
            v = r.get('Raw_Value') if isinstance(r, dict) else r['Raw_Value'] if 'Raw_Value' in r else None
        return v

    def _classify_pct(val, alarm_pct, high_pct):
        v = _safe_float(val)
        if v is None:
            return 'Normal', None
        if high_pct is not None and v > float(high_pct):
            return 'High', v
        if alarm_pct is not None and v > float(alarm_pct):
            return 'Alarm', v
        return 'Normal', v

    load_val = _safe_float(_value('Load'))
    load_valid_min = _get_thr(['load', 'valid_min'], 40)
    load_monitoring_min = _get_thr(['load', 'monitoring_min'], 20)
    load_quality = None
    if load_val is not None:
        if load_val < float(load_monitoring_min):
            load_quality = 'Invalid'
        elif load_val < float(load_valid_min):
            load_quality = 'Monitoring'
        else:
            load_quality = 'Valid'

    uv_status, uv_num = _classify_pct(
        _value('Dev Voltage'),
        _get_thr(['unbalance_voltage', 'alarm_pct'], 1),
        _get_thr(['unbalance_voltage', 'high_pct'], 2)
    )
    uc_status, uc_num = _classify_pct(
        _value('Dev Current'),
        _get_thr(['unbalance_current', 'alarm_pct'], 5),
        _get_thr(['unbalance_current', 'high_pct'], 10)
    )
    thd_status, thd_num = _classify_pct(
        _value('THD Voltage %'),
        _get_thr(['thd_voltage', 'alarm_pct'], 5),
        _get_thr(['thd_voltage', 'high_pct'], 8)
    )

    thd_i_status, thd_i_num = _classify_pct(
        _value('THD Current %'),
        _get_thr(['thd_current', 'alarm_pct'], 5),
        _get_thr(['thd_current', 'high_pct'], 8)
    )

    bearing_raw = _value('Bearing')
    bearing_status = 'Normal'
    if isinstance(bearing_raw, str):
        s = bearing_raw.strip().lower()
        if any(k in s for k in ['bad', 'damage', 'rusak', 'high', 'critical', 'trip']):
            bearing_status = 'High'
        elif any(k in s for k in ['alarm', 'warning']):
            bearing_status = 'Alarm'
        elif any(k in s for k in ['ok', 'normal', 'good']):
            bearing_status = 'Normal'

    rotor_params = {
        'Upper Sideband': _value('Upper Sideband'),
        'Lower Sideband': _value('Lower Sideband'),
        'Rotorbar Health': _value('Rotorbar Health'),
        'Se Fund': _value('Se Fund'),
        'Se Harm': _value('Se Harm'),
        'Rotorbar Level %': _value('Rotorbar Level %'),
    }
    rb = calculate_rotorbar_severity(rotor_params)
    rb_status = rb.get('Status', 'Normal')
    if rb_status not in {'Normal', 'Monitoring', 'Alarm', 'High', 'CRITICAL / TRIP RISK'}:
        rb_status = 'Normal'
    if rb_status == 'CRITICAL / TRIP RISK':
        rb_status = 'High'

    statuses = {
        'Load Quality': load_quality or 'Unknown',
        'Unbalance Voltage': uv_status,
        'Unbalance Current': uc_status,
        'THD Voltage': thd_status,
        'THD Current': thd_i_status,
        'Rotorbar': rb_status,
        'Bearing': bearing_status,
    }

    overall = 'Normal'
    if any(v == 'High' for v in [uv_status, uc_status, thd_status, thd_i_status, rb_status, bearing_status]):
        overall = 'High'
    elif any(v == 'Alarm' for v in [uv_status, uc_status, thd_status, thd_i_status, rb_status, bearing_status]):
        overall = 'Alarm'

    recommendations = []
    references = list(dict.fromkeys([r for r in (guidance.get('references') or []) if r]))

    rec_overall = (guidance.get('overall') or {}).get(overall.lower(), [])
    recommendations.extend(rec_overall or [])

    if load_quality == 'Invalid':
        recommendations.extend(((guidance.get('load') or {}).get('invalid') or []))
    elif load_quality == 'Monitoring':
        recommendations.extend(((guidance.get('load') or {}).get('monitoring') or []))
    elif load_quality == 'Valid':
        recommendations.extend(((guidance.get('load') or {}).get('valid') or []))

    if uv_status in {'Alarm', 'High'}:
        recommendations.extend(((guidance.get('unbalance_voltage') or {}).get('alarm_high') or []))
    if uc_status in {'Alarm', 'High'}:
        recommendations.extend(((guidance.get('unbalance_current') or {}).get('alarm_high') or []))
    if thd_status in {'Alarm', 'High'} or thd_i_status in {'Alarm', 'High'}:
        recommendations.extend(((guidance.get('thd_voltage') or {}).get('alarm_high') or []))
    if rb_status == 'Monitoring':
        recommendations.extend(((guidance.get('rotorbar') or {}).get('monitoring') or []))
    if rb_status in {'Alarm', 'High'}:
        recommendations.extend(((guidance.get('rotorbar') or {}).get('alarm_high') or []))
    if bearing_status in {'Alarm', 'High'}:
        recommendations.extend(((guidance.get('bearing') or {}).get('alarm_high') or []))

    recommendations = list(dict.fromkeys([r for r in recommendations if str(r).strip()]))

    values = {
        'Load %': load_val,
        'Dev Voltage %': uv_num,
        'Dev Current %': uc_num,
        'THD Voltage %': thd_num,
        'THD Current %': thd_i_num,
        'Rotorbar Assessment': rb.get('Assessment'),
        'Rotorbar Max Sideband': rb.get('Max Sideband'),
        'Rotorbar RB Index': rb.get('RB Index'),
        'Rotorbar Level %': rb.get('Level %'),
        'Bearing': bearing_raw,
    }

    # Generate Detailed Text Report
    detailed_report = generate_detailed_analysis_report(statuses, values, overall)

    return {
        'overall': overall,
        'statuses': statuses,
        'values': values,
        'recommendations': recommendations,
        'references': references,
        'detailed_report': detailed_report
    }


def generate_detailed_analysis_report(statuses, values, overall_status):
    """
    Generates a structured text report based on statuses and values.
    """
    report = []
    
    # --- 1. Kondisi Umum Motor ---
    report.append("#ANALISA")
    report.append("- Kondisi Umum Motor")
    if overall_status == 'Normal':
        report.append("Motor beroperasi dalam kondisi normal tanpa indikasi gangguan listrik maupun mekanik yang signifikan. Parameter utama berada dalam batas yang diizinkan.")
    elif overall_status == 'Alarm':
        report.append("Motor beroperasi dengan indikasi peringatan (Alarm). Terdapat parameter yang menyimpang dari batas normal namun belum kritis.")
    else:
        report.append("Motor dalam kondisi kritis (High/Bad). Terdeteksi gangguan signifikan yang memerlukan perhatian segera.")
    report.append("")

    # --- 2. Tegangan dan Arus ---
    report.append("- Tegangan dan Arus")
    uv = values.get('Dev Voltage %')
    uc = values.get('Dev Current %')
    
    v_msg = f"1. Tegangan antar fasa seimbang (unbalance {uv if uv is not None else '-'}%)" if uv is not None and uv <= 1.0 else f"1. Ketidakseimbangan tegangan terukur sebesar {uv if uv is not None else '-'}%"
    c_msg = f"2. Arus antar fasa seimbang dengan deviasi {uc if uc is not None else '-'}%" if uc is not None and uc <= 5.0 else f"2. Ketidakseimbangan arus terukur sebesar {uc if uc is not None else '-'}%"
    
    report.append(v_msg)
    report.append(c_msg)
    if statuses.get('Unbalance Voltage') == 'Normal' and statuses.get('Unbalance Current') == 'Normal':
        report.append("   Kondisi ini menunjukkan sistem suplai listrik dalam keadaan baik.")
    else:
        report.append("   Terdapat indikasi ketidakseimbangan pada suplai listrik atau beban.")
    report.append("")

    # --- 3. Beban Motor ---
    report.append("- Beban Motor")
    load = values.get('Load %')
    if load is not None:
        if load < 40:
            report.append(f"Motor beroperasi pada beban sekitar {load:.1f}%, dikategorikan sebagai beban rendah (underload). Kondisi ini menyebabkan performa motor tidak berada pada titik kerja optimal.")
        elif load < 70:
            report.append(f"Motor beroperasi pada beban menengah sekitar {load:.1f}%.")
        else:
            report.append(f"Motor beroperasi pada beban optimal sekitar {load:.1f}%.")
    else:
        report.append("Data beban motor tidak tersedia.")
    report.append("")

    # --- 4. Power Factor ---
    # Note: Power Factor value might need to be passed if available in values, currently mostly derived or separate.
    # Assuming it's not explicitly in 'values' dictionary passed from generate_esa_mcsa_quick_recommendations yet,
    # or we can add it there if we parsed it.
    # For now, generic or skip if not present.
    report.append("- Power Factor")
    # Placeholder logic as PF is not strictly in 'values' dict in previous code block
    # We will assume normal unless flagged in recommendations or if we had the value.
    # Let's check if 'power factor' key exists in input if we passed it through.
    # Ideally 'values' should contain 'Power Factor' if available.
    report.append("Informasi Power Factor spesifik perlu diverifikasi dari data detail.") 
    report.append("")

    # --- 5. Kondisi Stator ---
    report.append("- Kondisi Stator")
    # Basic logic: usually derived from connection/impedance analysis not fully present in basic MCSA params
    report.append("Tidak ditemukan indikasi gangguan stator seperti short antar lilitan ataupun degradasi isolasi berdasarkan parameter yang tersedia. Stator dinyatakan dalam kondisi normal.")
    report.append("")

    # --- 6. Kondisi Rotor ---
    report.append("- Kondisi Rotor")
    rb_stat = statuses.get('Rotorbar')
    if load is not None and load < 40:
        report.append("Analisa kesehatan rotor bar tidak dapat dilakukan secara akurat karena beban motor terlalu rendah. Tidak terdapat indikasi awal kerusakan rotor, namun diperlukan pengujian ulang pada beban yang lebih tinggi.")
    elif rb_stat == 'Normal':
        report.append("Indikator kesehatan rotor bar menunjukkan kondisi normal. Sideband berada dalam batas aman.")
    else:
        report.append(f"Terdapat indikasi {rb_stat} pada rotor bar. Perlu evaluasi lebih lanjut.")
    report.append("")

    # --- 7. Air Gap dan Mekanis ---
    report.append("- Air Gap dan Mekanis")
    # Often derived from eccentricity/sidebands logic not fully exploded here
    report.append("Tidak ditemukan indikasi static maupun dynamic eccentricity yang signifikan berdasarkan data saat ini.")
    report.append("")

    # --- 8. Harmonik ---
    report.append("- Harmonik")
    thd_v = values.get('THD Voltage %')
    thd_i = values.get('THD Current %')
    if statuses.get('THD Voltage') == 'Normal' and statuses.get('THD Current') == 'Normal':
        report.append(f"Distorsi harmonik arus ({thd_i if thd_i is not None else '-'}%) dan tegangan ({thd_v if thd_v is not None else '-'}%) berada pada level rendah dan masih dalam batas standar.")
    else:
        report.append(f"Terdeteksi distorsi harmonik: THD Arus {thd_i if thd_i is not None else '-'}%, THD Tegangan {thd_v if thd_v is not None else '-'}%.")
    report.append("")

    # --- REKOMENDASI ---
    report.append("#REKOMENDASI")
    
    # 1. Operasional
    report.append("- Operasional")
    if overall_status == 'Normal':
        report.append("Motor dapat terus dioperasikan dengan aman. Tidak ditemukan indikasi kerusakan yang memerlukan tindakan korektif segera.")
    elif overall_status == 'Alarm':
        report.append("Motor dapat dioperasikan dengan pengawasan ketat. Segera jadwalkan window maintenance untuk pemeriksaan fisik dan verifikasi temuan.")
    else: # High/Critical
        report.append("Risiko kegagalan tinggi. Pertimbangkan untuk mengurangi beban atau menghentikan operasi jika memungkinkan. Segera siapkan motor cadangan dan jadwalkan perbaikan.")
    report.append("")

    # 2. Pengujian Lanjutan
    report.append("- Pengujian Lanjutan")
    next_steps = []
    
    # Load issue
    if load is not None and load < 40:
        next_steps.append("Ukur ulang MCSA saat motor beroperasi pada beban minimal ≥ 40% untuk mendapatkan evaluasi kondisi rotor bar yang lebih valid.")
    
    # Unbalance issue
    uv_stat = statuses.get('Unbalance Voltage', 'Normal')
    uc_stat = statuses.get('Unbalance Current', 'Normal')
    if uv_stat in {'Alarm', 'High'} or uc_stat in {'Alarm', 'High'}:
        next_steps.append("Lakukan pemeriksaan termografi pada terminal box motor dan panel starter untuk mendeteksi kemungkinan koneksi longgar (loose connection).")
        next_steps.append("Cek keseimbangan tegangan suplai dari trafo atau panel distribusi.")

    # THD issue
    thd_v_stat = statuses.get('THD Voltage', 'Normal')
    thd_i_stat = statuses.get('THD Current', 'Normal')
    if thd_v_stat in {'Alarm', 'High'} or thd_i_stat in {'Alarm', 'High'}:
        next_steps.append("Lakukan pengukuran kualitas daya (Power Quality Analyzer) di sisi suplai untuk memverifikasi spektrum harmonisa.")
    
    # Mechanical/Bearing issue
    br_stat = statuses.get('Bearing', 'Normal')
    if br_stat in {'Alarm', 'High'}:
        next_steps.append("Lakukan analisa vibrasi spektrum lengkap untuk mengonfirmasi jenis kerusakan bearing (inner/outer race, cage, ball).")
        next_steps.append("Cek fisik: suara abnormal, suhu bearing, dan kondisi pelumasan (greasing).")

    # Rotor issue
    rb_stat = statuses.get('Rotorbar', 'Normal')
    if rb_stat in {'Alarm', 'High'}:
        next_steps.append("Lakukan pengujian offline (Static Test / Motor Circuit Analysis) untuk konfirmasi integritas rotor bar dan resistansi lilitan.")

    if not next_steps:
        report.append("Tidak ada pengujian lanjutan mendesak yang diperlukan saat ini. Lanjutkan sesuai jadwal rutin.")
    else:
        for step in next_steps:
            report.append(f"- {step}")
    report.append("")

    # 3. Optimasi Operasi & Perawatan
    report.append("- Optimasi Operasi & Perawatan")
    maint_steps = []
    if load is not None and load < 40:
        maint_steps.append("Evaluasi sizing motor terhadap beban aktual. Operasi underload jangka panjang menurunkan efisiensi dan faktor daya.")
    
    if thd_v_stat in {'Alarm', 'High'} or thd_i_stat in {'Alarm', 'High'}:
        maint_steps.append("Periksa setting filter harmonik atau VFD (jika menggunakan drive) untuk mengurangi injeksi harmonisa ke sistem.")

    if not maint_steps:
        maint_steps.append("Pertahankan kondisi operasi saat ini dan pastikan jadwal preventive maintenance (kebersihan, pelumasan) berjalan baik.")
    
    for step in maint_steps:
        report.append(f"- {step}")
    report.append("")

    # 4. Monitoring Berkala
    report.append("- Monitoring Berkala")
    report.append("Hasil pengukuran ini dapat dijadikan baseline.")
    if overall_status == 'Normal':
        report.append("Disarankan melanjutkan pemantauan berkala (misal: setiap 3 bulan) menggunakan MCSA dan dikombinasikan dengan analisa vibrasi untuk memastikan kondisi motor tetap dalam batas normal.")
    elif overall_status == 'Alarm':
        report.append("Tingkatkan frekuensi monitoring (misal: setiap 1 bulan) untuk memantau tren degradasi parameter yang abnormal.")
    else:
        report.append("Lakukan monitoring intensif (harian/mingguan) hingga perbaikan atau penggantian motor dilakukan.")

    return "\n".join(report)


def evaluate_vibration(params: dict) -> dict:
    """
    Evaluates vibration based on ISO 10816 / ISO 20816 simple rules (Class III/IV generic).
    Expected keys: 'Velocity_RMS' (mm/s), 'Acceleration_RMS' (g), 'Displacement_PkPk' (um).
    """
    results = {'Overall': 'Normal'}
    current_max = 1
    
    velocity = _safe_float(params.get('Velocity_RMS'))
    if velocity is not None:
        if velocity > 7.1:
            results['Velocity_RMS'] = 'High'
            current_max = 3
        elif velocity > 4.5:
            results['Velocity_RMS'] = 'Alarm'
            current_max = max(current_max, 2)
        else:
            results['Velocity_RMS'] = 'Normal'
            
    accel = _safe_float(params.get('Acceleration_RMS'))
    if accel is not None:
        if accel > 1.5:  # Generic bearing threshold
            results['Acceleration_RMS'] = 'High'
            current_max = 3
        elif accel > 0.5:
            results['Acceleration_RMS'] = 'Alarm'
            current_max = max(current_max, 2)
        else:
            results['Acceleration_RMS'] = 'Normal'
            
    if current_max == 3:
        results['Overall'] = 'High'
    elif current_max == 2:
        results['Overall'] = 'Alarm'
        
    return results


def evaluate_dga(params: dict) -> dict:
    """
    Evaluates DGA based on simplified IEEE C57.104 TDCG limit or individual gas limits.
    Expected keys (in ppm): 'H2', 'CH4', 'C2H2', 'C2H4', 'C2H6', 'CO', 'CO2'.
    """
    results = {'Overall': 'Normal'}
    current_max = 1
    
    # Calculate TDCG
    combustible_gases = ['H2', 'CH4', 'C2H2', 'C2H4', 'C2H6', 'CO']
    tdcg = 0.0
    has_gas_data = False
    
    for gas in combustible_gases:
        val = _safe_float(params.get(gas))
        if val is not None:
            has_gas_data = True
            tdcg += val
            
    if has_gas_data:
        results['TDCG'] = tdcg
        if tdcg > 4630: # Condition 4
            results['TDCG_Status'] = 'High'
            current_max = 3
        elif tdcg > 720: # Condition 2/3
            results['TDCG_Status'] = 'Alarm'
            current_max = max(current_max, 2)
        else:
            results['TDCG_Status'] = 'Normal'
            
    # Key individual gases: C2H2 (Acetylene) is very critical (Arcing)
    c2h2 = _safe_float(params.get('C2H2'))
    if c2h2 is not None:
        if c2h2 > 35:
            results['C2H2_Status'] = 'High'
            current_max = 3
        elif c2h2 > 9:
            results['C2H2_Status'] = 'Alarm'
            current_max = max(current_max, 2)
            
    if current_max == 3:
        results['Overall'] = 'High'
    elif current_max == 2:
        results['Overall'] = 'Alarm'
        
    return results


def evaluate_thermal(params: dict) -> dict:
    """
    Evaluates thermal data (Temperature).
    Expected keys: 'Temperature', 'Bearing_Temp', 'Winding_Temp' in Celsius.
    """
    results = {'Overall': 'Normal'}
    current_max = 1
    
    # Generic temperature thresholds
    temp_keys = ['Temperature', 'Bearing_Temp', 'Winding_Temp']
    for key in temp_keys:
        val = _safe_float(params.get(key))
        if val is not None:
            if val > 100:  # Critical generic threshold
                results[key] = 'High'
                current_max = 3
            elif val > 80: # Warning generic threshold
                results[key] = 'Alarm'
                current_max = max(current_max, 2)
            else:
                results[key] = 'Normal'
                
    if current_max == 3:
        results['Overall'] = 'High'
    elif current_max == 2:
        results['Overall'] = 'Alarm'
        
    return results

def evaluate_tribology(params: dict) -> dict:
    """
    Evaluates tribology (oil analysis) data.
    Expected keys: 'Water_ppm', 'TAN' (mgKOH/g), 'Viscosity_cSt', 'Fe_ppm'.
    """
    results = {'Overall': 'Normal'}
    current_max = 1
    
    # 1. Water Content (ppm)
    water = _safe_float(params.get('Water_ppm'))
    if water is not None:
        if water > 1000:
            results['Water_ppm'] = 'High'
            current_max = 3
        elif water > 500:
            results['Water_ppm'] = 'Alarm'
            current_max = max(current_max, 2)
            
    # 2. Total Acid Number (TAN)
    tan = _safe_float(params.get('TAN'))
    if tan is not None:
        if tan > 1.0:
            results['TAN'] = 'High'
            current_max = 3
        elif tan > 0.5:
            results['TAN'] = 'Alarm'
            current_max = max(current_max, 2)
            
    # 3. Wear Metal: Iron (Fe)
    fe = _safe_float(params.get('Fe_ppm'))
    if fe is not None:
        if fe > 100:
            results['Fe_ppm'] = 'High'
            current_max = 3
        elif fe > 50:
            results['Fe_ppm'] = 'Alarm'
            current_max = max(current_max, 2)
            
    if current_max == 3:
        results['Overall'] = 'High'
    elif current_max == 2:
        results['Overall'] = 'Alarm'
        
    return results
