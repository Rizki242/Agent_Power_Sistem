"""Canonical measurement store shared by the non-MCSA condition-monitoring
domains (Vibrasi, DGA, Partial Discharge, Tribology, Thermal).

Why this exists
---------------
MCSA can offer a period filter, trend charts, and period-scoped reports for
one reason: its data lives in a single tidy long-format table with a real
`Date` column (data/MCSA/mcsa_updated.csv). Every other domain stores its
data in a different shape - Vibrasi across a SQLite register plus a monthly
Excel export plus a CBMAI CSV, Tribology and Thermal as a single-month Excel
export each, DGA as a history CSV, PD as hardcoded samples - so none of them
could offer those features without five bespoke implementations of the same
three features.

This module gives all of them one shared long-format store, deliberately
mirroring the MCSA schema that already works (one row per
equipment/date/parameter, never one column per parameter) so that adding a
new measured parameter never requires a schema migration.

Storage layout
--------------
    data/domain/<DOMAIN>/measurements.csv       canonical measurements
    data/domain/<DOMAIN>/backup/                timestamped backups on write

The data root is resolved from MCSA_DATA_DIR on every call rather than
through src.data_loader.get_data_path(). That helper carries a fallback
heuristic which redirects any not-yet-existing path into the data/MCSA/
subfolder - correct for MCSA's own files, but it would file these five
domains' data under data/MCSA/domain/, which is simply the wrong place.
Resolving per call also means MCSA_DATA_DIR can be pointed elsewhere at
runtime (deployments, tests) instead of being frozen at import time.

Writes are atomic (write .tmp then os.replace) and take a timestamped backup
first, with rotation controlled by MCSA_MAX_BACKUPS - the exact same
convention src.data_loader.save_mcsa_data already uses, so operators have one
backup/retention behavior to learn, not two.

This complements rather than replaces the existing domain readers: a domain's
current Excel/SQLite/CSV source stays the seed of record until measurements
are ingested here (see src.domain_ingest), and src.asset_registry's
condition_history.csv keeps its separate role of coarse cross-domain
condition records with evidence files.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional

import pandas as pd

_LOCK = Lock()
_PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The five domains this store serves. MCSA is intentionally absent: it already
# has its own equivalent store (mcsa_updated.csv) and moving it here would be a
# migration of working, load-bearing code for no user-visible gain.
DOMAINS = ("VIBRASI", "DGA", "PD", "TRIBOLOGY", "THERMAL")

# One row per equipment/date/parameter reading - the same long shape as
# mcsa_updated.csv. `value` is the numeric reading (NaN when the reading is
# qualitative), `raw_value` always keeps the original text as recorded.
COLUMNS = [
    "record_id",
    "asset_id",
    "equipment",
    "unit_name",
    "test_date",
    "parameter",
    "value",
    "raw_value",
    "uom",
    "condition",
    "notes",
    "source_file",
    "batch_id",
    "created_at",
]

# Fields an ingested/manually entered row must carry for the row to be usable.
REQUIRED_FIELDS = ("equipment", "test_date", "parameter")


class UnknownDomainError(ValueError):
    """Raised when a domain id outside DOMAINS is passed in."""


def _text(value: Any) -> str:
    """Trimmed text for a cell, treating pandas' missing markers as empty.

    Needed because an empty CSV cell arrives as float('nan'), and str(nan) is
    the non-empty string 'nan' - without this, a blank Equipment column would
    pass the required-field check and be stored as equipment literally named
    "nan".
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        # Non-scalar (list/dict/etc.) - not missing, fall through to str().
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "nat", "none", "<na>"} else text


def canon_domain(domain: str) -> str:
    """Normalise a domain id and validate it against DOMAINS."""
    value = str(domain or "").strip().upper()
    if value not in DOMAINS:
        raise UnknownDomainError(f"Domain '{domain}' tidak dikenal. Pilihan: {', '.join(DOMAINS)}")
    return value


def _data_root() -> Path:
    """Data root, read fresh on every call (see the module docstring)."""
    configured = os.environ.get("MCSA_DATA_DIR")
    root = Path(configured).expanduser() if configured else _PROJECT_ROOT / "data"
    return root.resolve()


def domain_dir(domain: str) -> Path:
    return _data_root() / "domain" / canon_domain(domain)


def measurements_path(domain: str) -> Path:
    return domain_dir(domain) / "measurements.csv"


def _backup_limit(default: int = 5) -> int:
    raw_value = os.environ.get("MCSA_MAX_BACKUPS", default)
    try:
        return max(1, int(raw_value))
    except (TypeError, ValueError):
        return default


def _empty_frame() -> pd.DataFrame:
    frame = pd.DataFrame(columns=COLUMNS)
    frame["test_date"] = pd.to_datetime(frame["test_date"], errors="coerce")
    return frame


def load_measurements(domain: str) -> pd.DataFrame:
    """Every stored measurement for `domain`, newest test_date first.

    Returns an empty frame with the canonical columns when nothing has been
    stored yet - callers never have to special-case a missing file.
    """
    path = measurements_path(domain)
    if not path.exists():
        return _empty_frame()
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return _empty_frame()

    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    frame = frame[COLUMNS]
    frame["test_date"] = pd.to_datetime(frame["test_date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    return frame.sort_values("test_date", ascending=False, na_position="last").reset_index(drop=True)


def _next_record_id(domain: str, existing: pd.DataFrame, offset: int) -> str:
    prefix = canon_domain(domain)[:4]
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{len(existing) + offset:04d}"


def normalise_rows(domain: str, rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split incoming rows into (valid, rejected).

    A rejected row is returned with a human-readable `_reason` rather than
    raising, so an ingest batch can quarantine the bad rows and still commit
    the good ones - the same preview/quarantine/commit behavior
    src.report_batches already gives MCSA Word uploads.
    """
    valid: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in rows:
        row = {key: raw.get(key) for key in COLUMNS if key in raw}
        row.update({key: raw.get(key) for key in raw if key in COLUMNS})

        missing = [field for field in REQUIRED_FIELDS if not _text(raw.get(field))]
        if missing:
            rejected.append({**raw, "_reason": f"Kolom wajib kosong: {', '.join(missing)}"})
            continue

        test_date = pd.to_datetime(_text(raw.get("test_date")), errors="coerce")
        if pd.isna(test_date):
            rejected.append({**raw, "_reason": "Tanggal pengujian tidak dapat dibaca."})
            continue

        numeric = pd.to_numeric(raw.get("value"), errors="coerce")
        raw_value = _text(raw.get("raw_value")) or _text(raw.get("value"))

        valid.append({
            "asset_id": _text(raw.get("asset_id")),
            "equipment": _text(raw.get("equipment")),
            "unit_name": _text(raw.get("unit_name")),
            "test_date": test_date.strftime("%Y-%m-%d"),
            "parameter": _text(raw.get("parameter")),
            "value": None if pd.isna(numeric) else float(numeric),
            "raw_value": raw_value,
            "uom": _text(raw.get("uom")),
            "condition": _text(raw.get("condition")),
            "notes": _text(raw.get("notes")),
            "source_file": _text(raw.get("source_file")),
        })

    return valid, rejected


def append_measurements(domain: str, rows: Iterable[dict[str, Any]], batch_id: str = "") -> dict[str, Any]:
    """Validate and append rows, returning {'written', 'rejected', 'total'}.

    Rows that fail validation are reported back, never silently dropped and
    never written - a partially bad upload still lands its good rows.
    """
    domain = canon_domain(domain)
    valid, rejected = normalise_rows(domain, rows)

    if not valid:
        return {"written": 0, "rejected": rejected, "total": len(load_measurements(domain))}

    with _LOCK:
        existing = load_measurements(domain)
        stamped = []
        for offset, row in enumerate(valid):
            stamped.append({
                **row,
                "record_id": _next_record_id(domain, existing, offset),
                "batch_id": str(batch_id or "").strip(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            })

        # Concatenating onto a wholly empty frame makes pandas warn about
        # dtype inference, so seed straight from the new rows in that case.
        fresh = pd.DataFrame(stamped, columns=COLUMNS)
        combined = fresh if existing.empty else pd.concat([existing, fresh], ignore_index=True)
        combined = combined[COLUMNS]
        _write_frame(domain, combined)

    return {"written": len(stamped), "rejected": rejected, "total": len(combined)}


def delete_measurements(domain: str, record_ids: Iterable[str]) -> int:
    """Remove rows by record_id. Returns how many rows were actually removed."""
    domain = canon_domain(domain)
    targets = {str(value).strip() for value in record_ids if str(value).strip()}
    if not targets:
        return 0

    with _LOCK:
        existing = load_measurements(domain)
        if existing.empty:
            return 0
        keep = existing[~existing["record_id"].astype(str).isin(targets)]
        removed = len(existing) - len(keep)
        if removed:
            _write_frame(domain, keep)
    return removed


def _write_frame(domain: str, frame: pd.DataFrame) -> None:
    """Backup-then-atomic-write, mirroring src.data_loader.save_mcsa_data."""
    path = measurements_path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            backup_dir = path.parent / "backup"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(path, backup_dir / f"measurements_{stamp}.csv")
            backups = sorted(
                name for name in os.listdir(backup_dir)
                if name.startswith("measurements_") and name.endswith(".csv")
            )
            for old in backups[:-_backup_limit()]:
                try:
                    os.remove(backup_dir / old)
                except OSError:
                    pass
        except Exception:
            # A failed backup must never block the primary save - same
            # trade-off save_mcsa_data already makes.
            pass

    output = frame.copy()
    output["test_date"] = pd.to_datetime(output["test_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    tmp_path = str(path) + ".tmp"
    output.to_csv(tmp_path, index=False)
    os.replace(tmp_path, path)


def filter_measurements(
    domain: str,
    date_start=None,
    date_end=None,
    equipment: Optional[str] = None,
    unit_name: Optional[str] = None,
    parameters: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Period/equipment/unit/parameter slice of a domain's measurements.

    Every filter is optional; passing none returns everything. Rows with an
    unparseable test_date are excluded whenever a period filter is applied,
    since they cannot be honestly placed inside or outside that period.
    """
    frame = load_measurements(domain)
    if frame.empty:
        return frame

    if date_start is not None:
        start = pd.to_datetime(date_start, errors="coerce")
        if not pd.isna(start):
            frame = frame[frame["test_date"].notna() & (frame["test_date"] >= start.normalize())]
    if date_end is not None:
        end = pd.to_datetime(date_end, errors="coerce")
        if not pd.isna(end):
            # Compare date-to-date so a reading stored at any time on the end
            # day still falls inside the period.
            frame = frame[frame["test_date"].notna() & (frame["test_date"].dt.normalize() <= end.normalize())]
    if equipment:
        frame = frame[frame["equipment"].astype(str).str.strip().str.casefold() == str(equipment).strip().casefold()]
    if unit_name:
        frame = frame[frame["unit_name"].astype(str).str.strip().str.casefold() == str(unit_name).strip().casefold()]
    if parameters:
        wanted = {str(item).strip().casefold() for item in parameters if str(item).strip()}
        if wanted:
            frame = frame[frame["parameter"].astype(str).str.strip().str.casefold().isin(wanted)]

    return frame.reset_index(drop=True)


def latest_per_equipment(domain: str, parameters: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """The newest reading of each equipment/parameter pair.

    The domain equivalent of src.data_loader.get_latest_data - what the
    Ringkasan/KPI views need, so they never average across periods.
    """
    frame = filter_measurements(domain, parameters=parameters)
    if frame.empty:
        return frame
    ordered = frame.sort_values("test_date", ascending=True, na_position="first")
    return (
        ordered.drop_duplicates(subset=["equipment", "parameter"], keep="last")
        .sort_values(["equipment", "parameter"])
        .reset_index(drop=True)
    )


def available_period(domain: str) -> tuple[Optional[pd.Timestamp], Optional[pd.Timestamp]]:
    """(earliest, latest) test_date actually present, or (None, None).

    Period pickers must be bounded by this rather than by today's date - the
    user's requirement is reports "selama itu ada datanya", so offering a
    period the store cannot cover would promise data that does not exist.
    """
    frame = load_measurements(domain)
    if frame.empty or frame["test_date"].isna().all():
        return None, None
    return frame["test_date"].min(), frame["test_date"].max()


def summarise(domain: str) -> dict[str, Any]:
    """Counts a page header/KPI row needs, computed from stored rows only."""
    frame = load_measurements(domain)
    earliest, latest = available_period(domain)
    return {
        "domain": canon_domain(domain),
        "records": int(len(frame)),
        "equipment_count": int(frame["equipment"].nunique()) if not frame.empty else 0,
        "parameters": sorted(frame["parameter"].dropna().astype(str).unique().tolist()) if not frame.empty else [],
        "earliest": earliest,
        "latest": latest,
    }
