"""Central asset register and condition-history persistence.

This registry complements, rather than replaces, the existing MCSA and
domain-specific sources.  It gives engineering one stable asset ID that can
be associated with one or more monitoring disciplines.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterable

import pandas as pd

from src.data_loader import get_data_path


MONITORING_MODULES = ("MCSA", "DGA", "VIBRASI", "PD", "TRIBOLOGY", "THERMAL")
LIFECYCLE_STATUSES = ("Aktif", "Upgrade", "Diganti", "Nonaktif")
_LOCK = Lock()


def _registry_path() -> Path:
    return Path(get_data_path("config", "asset_registry.json"))


def _condition_path() -> Path:
    return Path(get_data_path("asset_management", "condition_history.csv"))


def _read_registry() -> dict[str, dict[str, Any]]:
    path = _registry_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_registry(records: dict[str, dict[str, Any]]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(temporary, path)


def _normalise_modules(modules: Iterable[str] | None) -> list[str]:
    known = {item.upper() for item in MONITORING_MODULES}
    return sorted({str(item).strip().upper() for item in (modules or []) if str(item).strip().upper() in known})


def make_asset_id(name: str) -> str:
    """Return a readable unique ID suitable for a new engineering asset."""
    slug = re.sub(r"[^A-Z0-9]+", "-", str(name).upper()).strip("-")[:24] or "ASSET"
    return f"AST-{slug}-{uuid.uuid4().hex[:6].upper()}"


def list_assets(include_inactive: bool = True) -> list[dict[str, Any]]:
    records = list(_read_registry().values())
    if not include_inactive:
        records = [record for record in records if record.get("lifecycle_status") == "Aktif"]
    return sorted(records, key=lambda record: (str(record.get("unit", "")), str(record.get("name", ""))))


def get_asset(asset_id: str) -> dict[str, Any] | None:
    return _read_registry().get(str(asset_id))


def count_condition_records(asset_id: str) -> int:
    """How many condition-history rows reference this asset (shown to the
    user before they confirm deletion, since delete_asset() cascades)."""
    history = load_condition_history()
    if history.empty:
        return 0
    return int((history["asset_id"] == str(asset_id)).sum())


def delete_asset(asset_id: str) -> bool:
    """Remove an asset from the central register. Cascades to its condition
    history rows so no orphaned records point at a nonexistent asset_id;
    evidence files already written to disk are left in place (only the
    pointer rows are removed) since they may still matter as an audit trail."""
    asset_id = str(asset_id)
    with _LOCK:
        records = _read_registry()
        if asset_id not in records:
            return False
        del records[asset_id]
        _write_registry(records)

        history = load_condition_history()
        if not history.empty and (history["asset_id"] == asset_id).any():
            history = history[history["asset_id"] != asset_id]
            path = _condition_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            history.to_csv(path, index=False)
    return True


def upsert_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Create or update a centrally managed asset record."""
    name = str(asset.get("name", "")).strip()
    if not name:
        raise ValueError("Nama aset wajib diisi.")
    asset_id = str(asset.get("asset_id") or make_asset_id(name)).strip().upper()
    lifecycle = str(asset.get("lifecycle_status") or "Aktif")
    if lifecycle not in LIFECYCLE_STATUSES:
        lifecycle = "Aktif"
    now = datetime.now().isoformat(timespec="seconds")
    with _LOCK:
        records = _read_registry()
        prior = records.get(asset_id, {})
        record = {
            **prior,
            "asset_id": asset_id,
            "name": name,
            "unit": str(asset.get("unit") or "Unknown").strip(),
            "equipment_type": str(asset.get("equipment_type") or "-").strip(),
            "voltage_level": str(asset.get("voltage_level") or "-").strip(),
            "lifecycle_status": lifecycle,
            "monitoring_modules": _normalise_modules(asset.get("monitoring_modules")),
            "replacement_of": str(asset.get("replacement_of") or "").strip().upper(),
            "kks": str(asset.get("kks") or prior.get("kks", "-")).strip(),
            "specs": asset.get("specs") if asset.get("specs") is not None else prior.get("specs", {}),
            "aliases": asset.get("aliases") if asset.get("aliases") is not None else prior.get("aliases", []),
            "status": str(asset.get("status") or prior.get("status", "Normal")).strip(),
            "notes": str(asset.get("notes") or "").strip(),
            "updated_at": now,
            "created_at": prior.get("created_at", now),
        }
        records[asset_id] = record
        _write_registry(records)
    return record


def load_condition_history() -> pd.DataFrame:
    columns = ["record_id", "asset_id", "asset_name", "module", "test_date", "condition", "summary", "source_file", "created_at"]
    path = _condition_path()
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        history = pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame(columns=columns)
    for column in columns:
        if column not in history.columns:
            history[column] = ""
    history["test_date"] = pd.to_datetime(history["test_date"], errors="coerce")
    return history[columns].sort_values("test_date", ascending=False, na_position="last")


def add_condition_record(record: dict[str, Any]) -> dict[str, Any]:
    asset = get_asset(str(record.get("asset_id") or ""))
    if not asset:
        raise ValueError("Asset ID tidak ditemukan pada register pusat.")
    module = str(record.get("module") or "").upper().strip()
    if module not in MONITORING_MODULES:
        raise ValueError("Modul monitoring tidak valid.")
    test_date = pd.to_datetime(record.get("test_date") or date.today(), errors="coerce")
    if pd.isna(test_date):
        raise ValueError("Tanggal pengujian tidak valid.")
    row = {
        "record_id": f"COND-{uuid.uuid4().hex[:10].upper()}",
        "asset_id": asset["asset_id"],
        "asset_name": asset["name"],
        "module": module,
        "test_date": test_date.strftime("%Y-%m-%d"),
        "condition": str(record.get("condition") or "Unknown").strip(),
        "summary": str(record.get("summary") or "").strip(),
        "source_file": str(record.get("source_file") or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    with _LOCK:
        history = load_condition_history()
        history = pd.concat([history, pd.DataFrame([row])], ignore_index=True)
        path = _condition_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        history.to_csv(path, index=False)
    return row


def get_condition_record(record_id: str) -> dict[str, Any] | None:
    history = load_condition_history()
    if history.empty:
        return None
    match = history[history["record_id"] == str(record_id)]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    if pd.notna(row.get("test_date")):
        row["test_date"] = pd.Timestamp(row["test_date"]).strftime("%Y-%m-%d")
    return row


def update_condition_record(record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """Edit an existing condition-history row in place (module/test_date/
    condition/summary). asset_id and record_id are immutable - re-record a
    new entry instead of reassigning a record to a different asset."""
    module = str(fields.get("module") or "").upper().strip()
    if module not in MONITORING_MODULES:
        raise ValueError("Modul monitoring tidak valid.")
    test_date = pd.to_datetime(fields.get("test_date") or date.today(), errors="coerce")
    if pd.isna(test_date):
        raise ValueError("Tanggal pengujian tidak valid.")

    with _LOCK:
        history = load_condition_history()
        if history.empty or record_id not in set(history["record_id"]):
            raise ValueError("Record riwayat kondisi tidak ditemukan.")
        idx = history.index[history["record_id"] == record_id][0]
        history.loc[idx, "module"] = module
        history.loc[idx, "test_date"] = test_date.strftime("%Y-%m-%d")
        history.loc[idx, "condition"] = str(fields.get("condition") or "Unknown").strip()
        history.loc[idx, "summary"] = str(fields.get("summary") or "").strip()
        path = _condition_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        history.to_csv(path, index=False)
        return history.loc[idx].to_dict()


def delete_condition_record(record_id: str) -> bool:
    with _LOCK:
        history = load_condition_history()
        if history.empty or record_id not in set(history["record_id"]):
            return False
        history = history[history["record_id"] != record_id]
        path = _condition_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        history.to_csv(path, index=False)
    return True


def save_evidence(asset_id: str, module: str, filename: str, content: bytes, test_date: date) -> str:
    """Store uploaded evidence in a dated, asset-scoped audit folder."""
    safe_name = Path(filename).name or "evidence.bin"
    safe_module = str(module).upper().replace("/", "-")
    folder = Path(get_data_path("asset_management", "evidence", safe_module, test_date.strftime("%Y"), test_date.strftime("%m"), str(asset_id)))
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / safe_name
    target.write_bytes(content)
    return str(target)


def sync_assets_from_database_aset(excel_path: str | None = None) -> int:
    """Sync equipment from database_aset.xlsx into central Asset Registry.
    Extracts plant assets from PLTU Jeranjang with KKS, specifications,
    bearings, speeds, and powers.
    Returns the count of newly added or updated assets.
    """
    if excel_path:
        target = Path(excel_path)
    else:
        candidates = [
            Path(get_data_path("vibrasi", "asset", "database_aset.xlsx")),
            Path("data/vibrasi/asset/database_aset.xlsx"),
            Path(get_data_path("vibrasi", "asset", "database_aset_vibrasi_PLTU_Jeranjang_dengan_unit.xlsx")),
        ]
        target = None
        for c in candidates:
            if c.exists():
                target = c
                break

    if not target or not target.exists():
        return 0

    try:
        xls = pd.ExcelFile(str(target))
        if "Asset_Master" in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name="Asset_Master")
        else:
            return 0
    except Exception:
        return 0

    if df.empty:
        return 0

    def clean_val(v):
        if pd.isna(v):
            return None
        s = str(v).strip()
        return None if s in ("", "-", "nan", "NaN") else s

    def infer_eq_type(eq_name: str, cat: Any, comp2: Any) -> str:
        nu = str(eq_name).upper()
        cl = str(cat).lower() if cat else ""
        c2l = str(comp2).lower() if comp2 else ""
        if nu.startswith("BC ") or "conveyor" in cl:
            return "Belt Conveyor Drive"
        if "fan" in cl or any(k in nu for k in ["FAN", "IDF", "PAF", "SAF", "RAF"]):
            return "Motor Fan / Blower"
        if "turbine" in cl or "turbin" in nu or "generator" in cl:
            return "Turbine-Generator"
        if "screen" in cl or "screen" in nu:
            return "Mechanical Screen"
        if "crusher" in cl or "crusser" in nu or "crusher" in nu:
            return "Coal Crusher"
        if "pump" in cl or "pompa" in c2l or "pump" in nu:
            return "Motor Pump"
        return "Electric Drive"

    added_or_updated = 0
    for _, row in df.iterrows():
        aid = clean_val(row.get("Asset ID"))
        eq_name = clean_val(row.get("Equipment"))
        if not eq_name:
            continue
        if not aid:
            aid = make_asset_id(eq_name)

        kks = clean_val(row.get("KKS")) or "-"
        raw_unit = clean_val(row.get("Unit Group (Derived)") or row.get("unit_group")) or "Unknown"
        unit = "UNIT COMMON" if raw_unit.upper() == "COMMON" else raw_unit

        eq_type = infer_eq_type(
            eq_name,
            row.get("Asset Category (Derived)"),
            row.get("Component 2"),
        )

        c1_power = clean_val(row.get("C1 Power")) or ""
        volt = clean_val(row.get("C1 Rated Stator Voltage"))
        if not volt:
            if any(w in c1_power.upper() for w in ["355", "280", "185"]) or eq_type in ("Motor Fan / Blower", "Turbine-Generator"):
                volt = "6.6 kV"
            else:
                volt = "380 V"

        if eq_type == "Turbine-Generator":
            modules = ["VIBRASI", "TRIBOLOGY", "THERMAL", "PD"]
        else:
            modules = ["MCSA", "VIBRASI", "TRIBOLOGY", "THERMAL"]

        specs = {
            "c1_type_mfg": clean_val(row.get("C1 Type/Mfg")),
            "c1_speed": clean_val(row.get("C1 Speed")),
            "c1_power": clean_val(row.get("C1 Power")),
            "c1_bearing_type": clean_val(row.get("C1 Bearing Type")),
            "c1_inboard_bearing": clean_val(row.get("C1 Inboard Bearing")),
            "c1_outboard_bearing": clean_val(row.get("C1 Outboard Bearing")),
            "c1_rotor_bar": clean_val(row.get("C1 Rotor Bar")),
            "c1_foundation": clean_val(row.get("C1 Foundation")),
            "c2_type_mfg": clean_val(row.get("C2 Type/Mfg")),
            "c2_speed": clean_val(row.get("C2 Speed")),
            "c2_power": clean_val(row.get("C2 Power")),
            "c2_capacity": clean_val(row.get("C2 Capacity")),
            "c2_pressure": clean_val(row.get("C2 Pressure")),
            "c2_flow_rate": clean_val(row.get("C2 Flow Rate")),
            "c2_total_blade": clean_val(row.get("C2 Total Blade")),
        }
        specs = {k: v for k, v in specs.items() if v is not None}

        aliases = []
        name_clean = eq_name.upper()
        if "MOTOR " in name_clean:
            aliases.append(name_clean.replace("MOTOR ", "").strip())
        if "#" in name_clean:
            aliases.append(name_clean.replace("#", " #"))
            aliases.append(name_clean.replace("#", " Unit "))

        upsert_asset({
            "asset_id": aid,
            "name": eq_name,
            "kks": kks,
            "unit": unit,
            "equipment_type": eq_type,
            "voltage_level": volt,
            "lifecycle_status": "Aktif",
            "monitoring_modules": modules,
            "specs": specs,
            "aliases": aliases,
            "notes": f"Diimpor dari database_aset PLTU Jeranjang (KKS: {kks})",
        })
        added_or_updated += 1

    return added_or_updated


def sync_assets_from_equipment_master() -> int:
    """Sync equipment from database_aset.xlsx and equipment_master.json into the central Asset Registry.
    Ensures all plant equipment tracked across MCSA and CBM disciplines is available.
    Returns the count of newly added assets.
    """
    db_added = sync_assets_from_database_aset()

    master_path = Path(get_data_path("config", "equipment_master.json"))
    if not master_path.exists():
        return db_added

    try:
        with master_path.open("r", encoding="utf-8") as handle:
            master_items = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return db_added

    if not isinstance(master_items, list):
        return db_added

    records = _read_registry()
    existing_names = {
        str(r.get("name", "")).strip().upper() for r in records.values()
    }
    existing_eq_codes = {
        re.sub(r"[^A-Z0-9]", "", str(r.get("name", "")).upper()) for r in records.values()
    }
    for r in records.values():
        for al in r.get("aliases", []):
            existing_names.add(str(al).strip().upper())
            existing_eq_codes.add(re.sub(r"[^A-Z0-9]", "", str(al).upper()))

    added_count = 0
    for item in master_items:
        full_name = str(item.get("Full_Name") or item.get("Equipment") or "").strip()
        eq_code = str(item.get("Equipment") or "").strip()
        if not full_name:
            continue

        norm_code = re.sub(r"[^A-Z0-9]", "", full_name.upper())
        norm_eq_code = re.sub(r"[^A-Z0-9]", "", eq_code.upper())
        if (
            full_name.upper() in existing_names
            or norm_code in existing_eq_codes
            or norm_eq_code in existing_eq_codes
        ):
            continue

        unit = str(item.get("Unit_Name") or "Unknown").strip()
        volt = str(item.get("Voltage_Level") or "-").strip()

        # Infer basic equipment type
        name_upper = full_name.upper()
        if any(k in name_upper for k in ["PUMP", "WP", "BFP", "CWP", "CEP", "VCP"]):
            eq_type = "Motor Pump"
        elif any(k in name_upper for k in ["FAN", "IDF", "PAF", "SAF", "CTF"]):
            eq_type = "Motor Fan / Blower"
        elif any(k in name_upper for k in ["CRUSHER", "SCREEN", "RS"]):
            eq_type = "Mechanical Screen / Crusher"
        elif any(k in name_upper for k in ["BC", "CONVEYOR"]):
            eq_type = "Belt Conveyor Drive"
        elif any(k in name_upper for k in ["TRAFO", "TRANSFORMER"]):
            eq_type = "Power Transformer"
        else:
            eq_type = "Electric Drive"

        modules = ["MCSA", "VIBRASI", "TRIBOLOGY", "THERMAL"]
        if "TRAFO" in name_upper:
            modules = ["DGA", "PD", "THERMAL"]

        slug = re.sub(r"[^A-Z0-9]+", "-", eq_code.upper() or full_name.upper()).strip("-")[:16]
        asset_id = f"AST-{slug}"
        if asset_id in records:
            asset_id = make_asset_id(full_name)

        upsert_asset({
            "asset_id": asset_id,
            "name": full_name,
            "unit": unit,
            "equipment_type": eq_type,
            "voltage_level": volt,
            "lifecycle_status": "Aktif",
            "monitoring_modules": modules,
            "aliases": [eq_code] if eq_code and eq_code != full_name else [],
            "notes": f"Sinkronisasi otomatis dari Master Equipment Pembangkit ({eq_code})",
        })
        existing_names.add(full_name.upper())
        existing_eq_codes.add(norm_code)
        if norm_eq_code:
            existing_eq_codes.add(norm_eq_code)
        added_count += 1

    return db_added + added_count
