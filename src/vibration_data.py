"""
Vibration asset database loader.

Reads the SQLite database in data/vibrasi/asset/ and exposes query helpers
that the rest of the application can use.  If the SQLite file is missing but
the source Excel workbook is present, the module rebuilds the database
automatically from the Excel sheets (UNIT_1, UNIT_2, UNIT_3, COMMON plus
the normalised Asset_Master sheet).

The public API mirrors the style already used by data_loader.py and
agent_memory.py so existing code can adopt it with minimal friction.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd

from src.data_loader import get_data_path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_VIBRASI_DIR = Path(get_data_path('vibrasi', 'asset'))
_SQLITE_PATH = _VIBRASI_DIR / 'database_aset_vibrasi_PLTU_Jeranjang_dengan_unit.sqlite'
_EXCEL_PATH = _VIBRASI_DIR / 'database_aset_vibrasi_PLTU_Jeranjang_dengan_unit.xlsx'

# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _get_connection(readonly: bool = True) -> sqlite3.Connection:
    """Return a connection to the vibration asset database.

    If the SQLite file does not exist, attempt to rebuild it from the Excel
    workbook first.
    """
    if not _SQLITE_PATH.exists() and _EXCEL_PATH.exists():
        rebuild_database_from_excel()
    uri = _SQLITE_PATH.as_uri() + ('?mode=ro' if readonly else '')
    return sqlite3.connect(uri, uri=True)


def _rows_to_dicts(cursor: sqlite3.Cursor) -> List[Dict[str, Any]]:
    cols = [desc[0] for desc in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Database rebuild from Excel
# ---------------------------------------------------------------------------


def rebuild_database_from_excel(
    excel_path: Optional[str] = None,
    sqlite_path: Optional[str] = None,
) -> str:
    """(Re-)create the SQLite database from the source Excel workbook.

    This is the only write operation in this module.  Everything else is
    read-only.  The function is safe to call repeatedly -- it drops existing
    tables before recreating them.

    Returns the path to the created SQLite file.
    """
    src = Path(excel_path) if excel_path else _EXCEL_PATH
    dst = Path(sqlite_path) if sqlite_path else _SQLITE_PATH

    if not src.exists():
        raise FileNotFoundError(f'Excel workbook not found: {src}')

    dst.parent.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(str(src))

    # --- Asset_Master (normalised, deduplicated) --------------------------
    if 'Asset_Master' in xls.sheet_names:
        df_master = pd.read_excel(xls, sheet_name='Asset_Master')
    else:
        # Fallback: combine per-unit sheets
        frames = []
        for sheet in ('UNIT_1', 'UNIT_2', 'UNIT_3', 'COMMON'):
            if sheet in xls.sheet_names:
                tmp = pd.read_excel(xls, sheet_name=sheet)
                tmp['unit_group'] = sheet.replace('_', ' ')
                frames.append(tmp)
        df_master = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # --- Report_Records ---------------------------------------------------
    df_records = (
        pd.read_excel(xls, sheet_name='Report_Records')
        if 'Report_Records' in xls.sheet_names
        else pd.DataFrame()
    )

    # --- Data_Quality -----------------------------------------------------
    df_quality = (
        pd.read_excel(xls, sheet_name='Data_Quality')
        if 'Data_Quality' in xls.sheet_names
        else pd.DataFrame()
    )

    # --- Field_Dictionary -------------------------------------------------
    df_fields = (
        pd.read_excel(xls, sheet_name='Field_Dictionary')
        if 'Field_Dictionary' in xls.sheet_names
        else pd.DataFrame()
    )

    # --- Per-unit raw sheets (UNIT_1 etc.) --------------------------------
    unit_frames = []
    for sheet in ('UNIT_1', 'UNIT_2', 'UNIT_3', 'COMMON'):
        if sheet in xls.sheet_names:
            tmp = pd.read_excel(xls, sheet_name=sheet)
            tmp['unit_group'] = sheet.replace('_', ' ')
            unit_frames.append(tmp)
    df_units = pd.concat(unit_frames, ignore_index=True) if unit_frames else pd.DataFrame()

    # --- Write to SQLite --------------------------------------------------
    conn = sqlite3.connect(str(dst))
    try:
        # Drop old tables so rebuild is idempotent
        for table in ('assets', 'report_records', 'data_quality',
                       'field_dictionary', 'unit_assets', 'source_metadata'):
            conn.execute(f'DROP TABLE IF EXISTS [{table}]')

        if not df_master.empty:
            # Normalise column names to snake_case for SQL friendliness
            df_master.columns = [
                c.strip().replace(' ', '_').replace('/', '_').lower()
                for c in df_master.columns
            ]
            df_master.to_sql('assets', conn, index=False, if_exists='replace')

        if not df_records.empty:
            df_records.columns = [
                c.strip().replace(' ', '_').replace('/', '_').lower()
                for c in df_records.columns
            ]
            df_records.to_sql('report_records', conn, index=False, if_exists='replace')

        if not df_quality.empty:
            df_quality.columns = [
                c.strip().replace(' ', '_').replace('/', '_').lower()
                for c in df_quality.columns
            ]
            df_quality.to_sql('data_quality', conn, index=False, if_exists='replace')

        if not df_fields.empty:
            df_fields.columns = [
                c.strip().replace(' ', '_').replace('/', '_').lower()
                for c in df_fields.columns
            ]
            df_fields.to_sql('field_dictionary', conn, index=False, if_exists='replace')

        if not df_units.empty:
            df_units.columns = [
                c.strip().replace(' ', '_').replace('/', '_').lower()
                for c in df_units.columns
            ]
            df_units.to_sql('unit_assets', conn, index=False, if_exists='replace')

        # Source metadata
        conn.execute('''
            CREATE TABLE IF NOT EXISTS source_metadata (
                source_file TEXT,
                page_count INTEGER,
                detail_report_records INTEGER,
                logical_assets INTEGER,
                created_from TEXT
            )
        ''')
        conn.execute(
            'INSERT INTO source_metadata VALUES (?, ?, ?, ?, ?)',
            (
                src.name,
                None,
                len(df_records) if not df_records.empty else 0,
                len(df_master) if not df_master.empty else 0,
                'rebuild_database_from_excel()',
            ),
        )

        conn.commit()
    finally:
        conn.close()

    return str(dst)


# ---------------------------------------------------------------------------
# Public query API
# ---------------------------------------------------------------------------


def load_vibration_assets() -> pd.DataFrame:
    """Load the full asset master table as a DataFrame."""
    conn = _get_connection()
    try:
        df = pd.read_sql_query('SELECT * FROM assets', conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def load_vibration_report_records() -> pd.DataFrame:
    """Load the report records table as a DataFrame."""
    conn = _get_connection()
    try:
        df = pd.read_sql_query('SELECT * FROM report_records', conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def get_vibration_asset(asset_id: str) -> Optional[Dict[str, Any]]:
    """Return a single asset dict by its Asset ID (e.g. 'AST-001')."""
    conn = _get_connection()
    try:
        cur = conn.execute('SELECT * FROM assets WHERE asset_id = ?', (asset_id,))
        rows = _rows_to_dicts(cur)
    finally:
        conn.close()
    return rows[0] if rows else None


def search_vibration_assets(
    *,
    unit_group: Optional[str] = None,
    equipment_class: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search assets with optional filters.

    Parameters
    ----------
    unit_group : str, optional
        Filter by unit group (e.g. 'UNIT 1', 'COMMON').
    equipment_class : str, optional
        Substring match on the normalised equipment class.
    status : str, optional
        Filter by status_vibrasi (NORMAL, PREWARNING, WARNING).
    keyword : str, optional
        Free-text substring search on equipment name.
    """
    clauses: List[str] = []
    params: List[Any] = []

    if unit_group:
        clauses.append('unit_group = ?')
        params.append(unit_group.upper())
    if equipment_class:
        clauses.append('equipment_class_normalized LIKE ?')
        params.append(f'%{equipment_class}%')
    if status:
        clauses.append('status_vibrasi = ?')
        params.append(status.upper())
    if keyword:
        clauses.append('equipment LIKE ?')
        params.append(f'%{keyword}%')

    where = ' AND '.join(clauses) if clauses else '1=1'
    sql = f'SELECT * FROM assets WHERE {where} ORDER BY asset_id'

    conn = _get_connection()
    try:
        cur = conn.execute(sql, params)
        rows = _rows_to_dicts(cur)
    finally:
        conn.close()
    return rows


def get_vibration_summary() -> Dict[str, Any]:
    """Return a quick summary dict (counts by unit, status, category)."""
    conn = _get_connection()
    try:
        total = conn.execute('SELECT count(*) FROM assets').fetchone()[0]

        by_unit = dict(
            conn.execute(
                'SELECT unit_group, count(*) FROM assets GROUP BY unit_group ORDER BY unit_group'
            ).fetchall()
        )

        by_status = dict(
            conn.execute(
                'SELECT status_vibrasi, count(*) FROM assets GROUP BY status_vibrasi ORDER BY status_vibrasi'
            ).fetchall()
        )

        by_category = dict(
            conn.execute(
                'SELECT asset_category_derived, count(*) '
                'FROM assets GROUP BY asset_category_derived ORDER BY asset_category_derived'
            ).fetchall()
        )
    finally:
        conn.close()

    return {
        'total_assets': total,
        'by_unit': by_unit,
        'by_status': by_status,
        'by_category': by_category,
    }


def get_equipment_class_list() -> List[str]:
    """Return distinct normalised equipment class values."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            'SELECT DISTINCT equipment_class_normalized FROM assets '
            'WHERE equipment_class_normalized IS NOT NULL '
            'ORDER BY equipment_class_normalized'
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def get_asset_ids_for_unit(unit_group: str) -> List[str]:
    """Return sorted asset IDs belonging to a unit group."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            'SELECT asset_id FROM assets WHERE unit_group = ? ORDER BY asset_id',
            (unit_group.upper(),),
        ).fetchall()
    finally:
        conn.close()
    return [r[0] for r in rows]


def get_bearing_info(asset_id: str) -> Optional[Dict[str, str]]:
    """Return bearing details for a given asset (inboard/outboard, type)."""
    asset = get_vibration_asset(asset_id)
    if not asset:
        return None
    return {
        'c1_bearing_type': asset.get('c1_bearing_type', ''),
        'c1_inboard_bearing': asset.get('c1_inboard_bearing', ''),
        'c1_outboard_bearing': asset.get('c1_outboard_bearing', ''),
        'c2_bearing_type': asset.get('c2_bearing_type', ''),
        'c2_inboard_bearing': asset.get('c2_inboard_bearing', ''),
        'c2_onboard_bearing': asset.get('c2_onboard_bearing', ''),
    }


def load_vibration_monthly_tests(excel_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Loads periodic overall vibration test measurements (1V, 1H, 1A, 2V, 2H, 2A, Vmax, Status)."""
    file_path = Path(excel_path) if excel_path else Path(get_data_path('vibrasi', 'Exsume Vibrasi Januari 2026.xlsx'))
    if not file_path.exists():
        return []
        
    try:
        df = pd.read_excel(file_path, sheet_name='SUMMARY')
        pos_names = ['1V', '1H', '1A', '2V', '2H', '2A', '3V', '3H', '3A', '4V', '4H', '4A', '5V', '5H', '5A', '6V', '6H', '6A']
        
        current_unit = "UNIT 1"
        records = []
        
        for idx in range(6, len(df)):
            row = df.iloc[idx]
            no = row.iloc[1]
            eq_name = row.iloc[2]
            group = row.iloc[3]
            v_max = row.iloc[22]
            status = row.iloc[23]
            
            # Check unit section breaks
            if pd.isna(no) and isinstance(eq_name, str) and ("UNIT" in eq_name.upper() or "COAL" in eq_name.upper()):
                if "UNIT 2" in eq_name.upper():
                    current_unit = "UNIT 2"
                elif "UNIT 3" in eq_name.upper():
                    current_unit = "UNIT 3"
                elif "COAL" in eq_name.upper() or "COMMON" in eq_name.upper():
                    current_unit = "COMMON"
                continue
                
            if pd.isna(eq_name) or str(eq_name).strip() in ('', 'nan'):
                continue
                
            # Extract point measurements
            points = {}
            for col_i, pos in enumerate(pos_names):
                val = row.iloc[4 + col_i]
                if pd.notna(val) and val != '':
                    try:
                        points[pos] = float(val)
                    except (ValueError, TypeError):
                        pass
                        
            v_max_float = 0.0
            try:
                v_max_float = float(v_max) if pd.notna(v_max) else 0.0
            except (ValueError, TypeError):
                pass
                
            st_clean = str(status).strip().upper() if pd.notna(status) else 'NORMAL'
            if 'STAND' in st_clean:
                st_clean = 'STANDBY'
            elif 'PRE' in st_clean:
                st_clean = 'PREWARNING'
            elif 'WARN' in st_clean:
                st_clean = 'WARNING'
            elif 'ALARM' in st_clean:
                st_clean = 'ALARM'
            else:
                st_clean = 'NORMAL'
                
            records.append({
                "no": int(no) if pd.notna(no) and str(no).isdigit() else len(records) + 1,
                "equipment": str(eq_name).strip(),
                "unit": current_unit,
                "iso_group": str(group).strip() if pd.notna(group) else "GROUP 1",
                "velocity_max": v_max_float,
                "status": st_clean,
                "points": points,
                "test_date": "2026-01-20"
            })
            
        return records
    except Exception as e:
        print(f"Error loading monthly vibration tests: {e}")
        return []


def match_monthly_test_by_equipment(
    equipment_name: str,
    monthly_tests: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Best-effort match of an asset's equipment name to a monthly test record.

    The asset register and the periodic-test Excel export share no common ID,
    only equipment-name text - so this tries an exact case-insensitive match
    first, then falls back to a substring match in either direction.
    """
    if not equipment_name or not monthly_tests:
        return None
    target = equipment_name.strip().upper()
    for record in monthly_tests:
        if str(record.get("equipment", "")).strip().upper() == target:
            return record
    for record in monthly_tests:
        candidate = str(record.get("equipment", "")).strip().upper()
        if candidate and (candidate in target or target in candidate):
            return record
    return None


def build_vibration_agent_input(record: Dict[str, Any]) -> Dict[str, float]:
    """Map a monthly-test record to VibrationAgent's input shape.

    Only overall_rms (velocity_max) is available from this data source today;
    spectral parameters (1X/2X/BPFO/BPFI) are left for VibrationAgent's own
    defaults since the periodic-test export doesn't carry them.
    """
    return {"overall_rms": float(record.get("velocity_max", 0.0))}

