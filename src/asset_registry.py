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


def save_evidence(asset_id: str, module: str, filename: str, content: bytes, test_date: date) -> str:
    """Store uploaded evidence in a dated, asset-scoped audit folder."""
    safe_name = Path(filename).name or "evidence.bin"
    safe_module = str(module).upper().replace("/", "-")
    folder = Path(get_data_path("asset_management", "evidence", safe_module, test_date.strftime("%Y"), test_date.strftime("%m"), str(asset_id)))
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / safe_name
    target.write_bytes(content)
    return str(target)
