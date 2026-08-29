import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd

from src.docx_parser import parse_docx_report
from src.metadata import enrich_equipment_metadata, normalize_equipment_code


BATCH_DIR_NAME = "uploads"
MANIFEST_NAME = "manifest.json"


def _safe_filename(name: str) -> str:
    original = Path(str(name or "report.docx")).name
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(original).stem).strip(" ._") or "report"
    suffix = Path(original).suffix.lower()
    if suffix not in {".docx", ".docm"}:
        raise ValueError("Format file harus .docx atau .docm")
    return f"{stem}{suffix}"


def _unique_filename(directory: Path, name: str) -> str:
    candidate = _safe_filename(name)
    stem, suffix = Path(candidate).stem, Path(candidate).suffix
    counter = 2
    while (directory / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def _write_manifest(batch_path: Path, manifest: dict) -> None:
    temp_path = batch_path / f"{MANIFEST_NAME}.tmp"
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    os.replace(temp_path, batch_path / MANIFEST_NAME)


def _record_audit_event(manifest: dict, action: str, **details) -> None:
    event = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "action": action,
    }
    event.update(details)
    manifest.setdefault("audit_events", []).append(event)


def load_batch_manifest(batch_path) -> dict:
    path = Path(batch_path) / MANIFEST_NAME
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def create_batch(laporan_root, uploaded_files, now=None) -> tuple[Path, dict]:
    now = now or datetime.now()
    batch_id = f"batch-{now.strftime('%H%M%S')}-{uuid4().hex[:6]}"
    batch_path = Path(laporan_root) / BATCH_DIR_NAME / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / batch_id
    batch_path.mkdir(parents=True, exist_ok=False)

    entries = []
    for uploaded in uploaded_files:
        original_name = str(getattr(uploaded, "name", "report.docx"))
        stored_name = _unique_filename(batch_path, original_name)
        payload = bytes(uploaded.getbuffer())
        (batch_path / stored_name).write_bytes(payload)
        entries.append({
            "original_name": original_name,
            "stored_name": stored_name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "parse_status": "pending",
            "error": "",
        })

    manifest = {
        "batch_id": batch_id,
        "uploaded_at": now.isoformat(timespec="seconds"),
        "status": "pending",
        "files": entries,
    }
    _record_audit_event(manifest, "created", file_count=len(entries))
    _write_manifest(batch_path, manifest)
    return batch_path, manifest


def preview_batch(batch_path, master_df, folder_metadata=None) -> tuple[pd.DataFrame, dict]:
    batch_path = Path(batch_path)
    manifest = load_batch_manifest(batch_path)
    parsed_frames = []

    master_codes = set()
    if isinstance(master_df, pd.DataFrame) and not master_df.empty:
        master_codes = set(master_df.get("Equipment", pd.Series(dtype=str)).map(normalize_equipment_code))

    for entry in manifest.get("files", []):
        entry.update({"equipment": "", "report_date": "", "metadata": {}, "row_count": 0, "error": ""})
        path = batch_path / entry["stored_name"]
        code = normalize_equipment_code(entry["stored_name"].split("_")[0].split(".")[0])
        try:
            rows = parse_docx_report(str(path), full_name=code)
            frame = pd.DataFrame(rows)
            frame = enrich_equipment_metadata(frame, master_df=master_df, folder_metadata=folder_metadata)
            if frame.empty:
                raise ValueError("Tidak ada parameter MCSA yang berhasil diekstrak")
            equipment = normalize_equipment_code(frame["Equipment"].iloc[0])
            report_date = pd.to_datetime(frame["Date"].iloc[0], errors="coerce")
            known = equipment in master_codes
            unit = str(frame.get("Unit_Name", pd.Series(["Unknown"])).iloc[0])
            voltage = str(frame.get("Voltage_Level", pd.Series(["Unknown"])).iloc[0])
            if not known or unit == "Unknown" or voltage == "Unknown":
                raise ValueError(f"Equipment {equipment or code} tidak ditemukan di equipment_master.json")
            entry.update({
                "parse_status": "valid",
                "equipment": equipment,
                "report_date": "" if pd.isna(report_date) else report_date.date().isoformat(),
                "metadata": {"unit": unit, "voltage": voltage, "full_name": str(frame["Full_Name"].iloc[0])},
                "row_count": int(len(frame)),
            })
            frame["_batch_id"] = manifest["batch_id"]
            frame["_source_file"] = entry["stored_name"]
            parsed_frames.append(frame)
        except Exception as exc:
            entry["parse_status"] = "quarantined"
            entry["error"] = str(exc)[:300]

    manifest["status"] = "previewed"
    preview = pd.concat(parsed_frames, ignore_index=True) if parsed_frames else pd.DataFrame()
    _record_audit_event(
        manifest,
        "previewed",
        valid_files=sum(item.get("parse_status") == "valid" for item in manifest["files"]),
        quarantined_files=sum(item.get("parse_status") == "quarantined" for item in manifest["files"]),
        parsed_rows=int(len(preview)),
    )
    _write_manifest(batch_path, manifest)
    return preview, manifest


def commit_batch(batch_path, preview_df, current_df, save_mcsa_data, original_file_path) -> tuple[pd.DataFrame, dict]:
    batch_path = Path(batch_path)
    manifest = load_batch_manifest(batch_path)
    valid_files = {item["stored_name"] for item in manifest.get("files", []) if item.get("parse_status") == "valid"}
    valid = preview_df[preview_df.get("_source_file", pd.Series(dtype=str)).isin(valid_files)].copy()
    if valid.empty:
        raise ValueError("Batch tidak memiliki file valid untuk disimpan")

    valid = valid.drop(columns=["_batch_id", "_source_file"], errors="ignore")
    merged = pd.concat([current_df, valid], ignore_index=True)
    merged["Date"] = pd.to_datetime(merged.get("Date", pd.NaT), errors="coerce")
    rows_before_dedup = int(len(merged))
    merged = merged.drop_duplicates(subset=["Equipment", "Parameter", "Date"], keep="last")
    save_mcsa_data(merged, original_file_path)

    manifest["status"] = "committed"
    manifest["committed_at"] = datetime.now().isoformat(timespec="seconds")
    manifest["committed_rows"] = int(len(valid))
    _record_audit_event(
        manifest,
        "committed",
        source_rows=int(len(current_df)),
        imported_rows=int(len(valid)),
        rows_after_commit=int(len(merged)),
        replaced_or_duplicate_rows=rows_before_dedup - int(len(merged)),
    )
    _write_manifest(batch_path, manifest)
    return merged, manifest


def list_recent_batches(laporan_root, limit=10) -> list[dict]:
    root = Path(laporan_root) / BATCH_DIR_NAME
    if not root.exists():
        return []
    manifests = []
    for path in root.rglob(MANIFEST_NAME):
        try:
            item = load_batch_manifest(path.parent)
            item["batch_path"] = str(path.parent)
            manifests.append(item)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    manifests.sort(key=lambda item: item.get("uploaded_at", ""), reverse=True)
    return manifests[:limit]
