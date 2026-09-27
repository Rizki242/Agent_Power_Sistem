"""One CSV/XLSX ingest pipeline shared by the five non-MCSA domains.

MCSA already has a batch ingest with preview, quarantine, commit, and a
`manifest.json` audit trail (src.report_batches, for Word reports). The other
five domains had no write path at all - their data could only be changed by
editing the source Excel/CSV by hand. This module gives them the same audit
shape, over CSV/XLSX instead of .docx, writing into the canonical store in
src.domain_measurements.

Wide input, long storage
------------------------
Engineers export condition-monitoring data one row per test with one column
per parameter ("wide"), which is how the existing EXSUM/EKSUM Excel files are
already laid out. The canonical store is long (one row per reading). This
module is where that conversion happens, driven by a declarative PROFILES
table rather than five bespoke parsers.

Each profile's parameter keys are deliberately the exact keys that domain's
specialist agent reads in src.agents.specialist_agents - so anything ingested
here can be fed straight to the agent for a real diagnosis, instead of the
agent falling back to its built-in example values.

Batch layout (mirrors data/Laporan/uploads/ for MCSA Word batches):

    data/domain/<DOMAIN>/uploads/YYYY/MM/DD/batch-HHMMSS-xxxxxx/
        <original upload file>
        manifest.json      counts, per-row rejects, audit events
"""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

from pple.core.events import Events, publish
from src.domain_measurements import (
    append_measurements,
    canon_domain,
    domain_dir,
    normalise_rows,
)


class ParameterSpec:
    """One measurable parameter: its canonical key, label, unit, and the
    source-column aliases seen in real exports."""

    def __init__(self, key: str, label: str, uom: str = "", aliases: Iterable[str] = (), numeric: bool = True):
        self.key = key
        self.label = label
        self.uom = uom
        self.aliases = tuple(aliases)
        self.numeric = numeric

    def matches(self, column: str) -> bool:
        candidate = _norm_column(column)
        return candidate in {_norm_column(name) for name in (self.key, self.label, *self.aliases)}


def _norm_column(value: Any) -> str:
    return "".join(ch for ch in str(value or "").strip().lower() if ch.isalnum())


# Identity columns every domain shares. `equipment` and `test_date` are
# mandatory (src.domain_measurements.REQUIRED_FIELDS); the rest are optional.
IDENTITY_ALIASES = {
    "equipment": ("equipment", "peralatan", "asset", "aset", "nama aset", "asset_name", "tag", "equipment_id"),
    "asset_id": ("asset_id", "id aset", "assetid", "kode aset"),
    "unit_name": ("unit_name", "unit", "unit group", "unit_group"),
    "test_date": ("test_date", "tanggal", "tanggal uji", "date", "timestamp", "tgl"),
    "condition": ("condition", "kondisi", "status"),
    "notes": ("notes", "note", "catatan", "keterangan", "remark"),
}


PROFILES: dict[str, dict[str, Any]] = {
    "VIBRASI": {
        "label": "Vibrasi",
        "parameters": [
            ParameterSpec("overall_rms", "Overall RMS", "mm/s", ("velocity_rms_mm_s", "velocity max", "velocity_max", "overall")),
            ParameterSpec("amp_1x", "Amplitudo 1X", "mm/s", ("1x_amp_mm_s", "1x")),
            ParameterSpec("amp_2x", "Amplitudo 2X", "mm/s", ("2x_amp_mm_s", "2x")),
            ParameterSpec("axial_1x", "Aksial 1X", "mm/s", ("axial",)),
            ParameterSpec("bpfo_amp", "BPFO", "g", ("bpfo_amp_g", "bpfo")),
            ParameterSpec("bpfi_amp", "BPFI", "g", ("bpfi_amp_g", "bpfi")),
            ParameterSpec("acceleration_rms", "Akselerasi RMS", "g", ("acceleration_rms_g",)),
            ParameterSpec("temperature", "Suhu", "degC", ("temperature_c", "suhu")),
            # Per-point readings from a real field inspection sheet: 6
            # measurement points (e.g. motor/pump DE-NDE), each read in
            # Vertical/Horizontal/Axial direction - "1V".."6A". This is a
            # different (and common) shape from the single-overall-value
            # columns above: a raw multi-point sheet rather than a
            # pre-computed 1X/2X/BPFO summary. Both are kept so either kind
            # of export maps correctly; see agent_input_from_measurements()
            # for how a missing overall_rms is derived from these when only
            # the point-based columns are present.
            *[
                ParameterSpec(f"pt{point}_{axis.lower()}", f"Titik {point} - {axis_label}", "mm/s", (f"{point}{axis}",))
                for point in range(1, 7)
                for axis, axis_label in (("V", "Vertikal"), ("H", "Horizontal"), ("A", "Axial"))
            ],
            # SPM shock pulse per bearing (1-2 motor, 3-4 driven machine), as
            # printed on page 2 of the plant's DETAIL REPORT VIBRASI form.
            # Only Max and Carpet are recorded; delta is always derived
            # (max - carpet) by src.vibration_standards rather than stored,
            # so a stored delta can never disagree with its own inputs.
            *[
                ParameterSpec(
                    f"sp_{kind}_{bearing}",
                    f"Shock Pulse {label} - Bearing {bearing}",
                    "dB",
                    (f"sp {kind} {bearing}", f"{label} {bearing}", f"{label}{bearing}"),
                )
                for bearing in range(1, 5)
                for kind, label in (("max", "Max"), ("carpet", "Carpet"))
            ],
        ],
    },
    "DGA": {
        "label": "DGA",
        "parameters": [
            ParameterSpec("h2", "H2", "ppm", ("hidrogen", "hydrogen")),
            ParameterSpec("ch4", "CH4", "ppm", ("metana", "methane")),
            ParameterSpec("c2h2", "C2H2", "ppm", ("asetilena", "acetylene")),
            ParameterSpec("c2h4", "C2H4", "ppm", ("etilena", "ethylene")),
            ParameterSpec("c2h6", "C2H6", "ppm", ("etana", "ethane")),
            ParameterSpec("co", "CO", "ppm", ("karbon monoksida",)),
            ParameterSpec("co2", "CO2", "ppm", ("karbon dioksida",)),
            # Already present in data/domain/DGA/measurements.csv from the
            # GT#1..GT#3 sampling sheets, but missing from this table - so a
            # re-upload of those same sheets silently dropped both columns.
            # TDCG is the lab sheet's own printed total, kept as reported
            # rather than recomputed, so a transcription error stays visible.
            ParameterSpec("tdcg", "TDCG", "ppm", ("total dissolved combustible gas", "total combustible")),
            ParameterSpec("h2o", "H2O", "ppm", ("moisture", "kadar air oli", "water in oil")),
            # Expanded parameters for rich form and TE integration
            ParameterSpec("bdv_kv", "Breakdown Voltage", "kV", ("bdv", "dielectric strength", "breakdown voltage")),
            ParameterSpec("water_content_ppm", "Water Content", "ppm", ("water content", "kadar air", "water ppm")),
            ParameterSpec("beban_mw", "Beban Operasi", "MW", ("load", "beban", "load mw")),
            ParameterSpec("temp_oil", "Suhu Minyak", "degC", ("oil temp", "suhu minyak", "oil temperature")),
            ParameterSpec("temp_winding", "Suhu Winding", "degC", ("winding temp", "suhu winding")),
        ],
    },
    "TRIBOLOGY": {
        "label": "Tribology",
        "parameters": [
            ParameterSpec("viscosity_40c", "Viskositas 40C", "cSt", ("viscosity", "viskositas", "viscosity_40")),
            ParameterSpec("nominal_viscosity", "Viskositas nominal", "cSt", ("iso vg", "iso_vg")),
            ParameterSpec("tan", "TAN", "mg KOH/g", ("total acid number",)),
            ParameterSpec("water_ppm", "Kandungan air", "ppm", ("water", "air", "moisture")),
            ParameterSpec("total_water_ppm", "Total Water", "ppm", ("total water", "total_water")),
            ParameterSpec("oxidation", "Oksidasi", "", ("oxidation",)),
            ParameterSpec("fe_ppm", "Wear Fe", "ppm", ("fe", "wear_fe", "besi", "iron")),
            ParameterSpec("cu_ppm", "Wear Cu", "ppm", ("cu", "wear_cu", "tembaga", "copper")),
            ParameterSpec("pb_ppm", "Wear Pb", "ppm", ("pb", "wear_pb", "timbal", "lead")),
            ParameterSpec("si_ppm", "Wear Si", "ppm", ("si", "wear_si", "silikon", "silicon")),
            ParameterSpec("flash_point", "Flash point", "degC", ("titik nyala",)),
            ParameterSpec("iso_cleanliness", "ISO cleanliness", "", ("iso 4406", "kebersihan", "iso_code"), numeric=False),
            ParameterSpec("nas_class", "NAS Class", "", ("nas", "nas_class")),
        ],
    },
    "THERMAL": {
        "label": "Thermal",
        "parameters": [
            ParameterSpec("bearing_temp", "Suhu bearing", "degC", ("bearing", "suhu bearing", "temp")),
            ParameterSpec("winding_temp", "Suhu winding", "degC", ("winding", "suhu winding", "stator")),
            ParameterSpec("ambient_temp", "Suhu ambient", "degC", ("ambient", "suhu ruang")),
            ParameterSpec("hotspot_temp", "Suhu hotspot", "degC", ("hotspot", "titik panas")),
            ParameterSpec("delta_t_phase", "Delta-T antar fasa", "K", ("delta t", "deltat", "delta_t")),
        ],
    },
    "PD": {
        "label": "Partial Discharge",
        "parameters": [
            ParameterSpec("pulse_magnitude_r", "Pulse Magnitude Fasa R", "pC", ("magnitude r", "fasa r", "phase r")),
            ParameterSpec("pulse_magnitude_s", "Pulse Magnitude Fasa S", "pC", ("magnitude s", "fasa s", "phase s")),
            ParameterSpec("pulse_magnitude_t", "Pulse Magnitude Fasa T", "pC", ("magnitude t", "fasa t", "phase t")),
            ParameterSpec("nqn_r", "NQN Fasa R", "", ("nqn r", "nqn_r")),
            ParameterSpec("nqn_s", "NQN Fasa S", "", ("nqn s", "nqn_s")),
            ParameterSpec("nqn_t", "NQN Fasa T", "", ("nqn t", "nqn_t")),
            ParameterSpec("phase_angle_r", "Phase Angle Fasa R", "deg", ("phase angle r",)),
            ParameterSpec("phase_angle_s", "Phase Angle Fasa S", "deg", ("phase angle s",)),
            ParameterSpec("phase_angle_t", "Phase Angle Fasa T", "deg", ("phase angle t",)),
            # Legacy single-phase columns kept for backward compat
            ParameterSpec("pulse_magnitude_pc", "Pulse magnitude", "pC", ("magnitude", "magnitudo", "pulse")),
            ParameterSpec("nqn", "NQN", "", ("normalized quantity number",)),
            ParameterSpec("phase_clustering_deg", "Phase clustering", "deg", ("phase clustering", "clustering")),
            ParameterSpec("pd_type", "Tipe discharge", "", ("tipe", "discharge type", "type"), numeric=False),
            ParameterSpec("prpd_severity", "PRPD Severity", "", ("prpd", "severity"), numeric=False),
        ],
    },
}


def profile(domain: str) -> dict[str, Any]:
    return PROFILES[canon_domain(domain)]


def parameter_specs(domain: str) -> list[ParameterSpec]:
    return list(profile(domain)["parameters"])


def template_frame(domain: str) -> pd.DataFrame:
    """A blank wide-format frame with exactly the columns this domain expects.

    Offered to users as a downloadable template so "upload CSV" does not mean
    "guess the format".
    """
    columns = ["equipment", "asset_id", "unit_name", "test_date"]
    columns += [spec.key for spec in parameter_specs(domain)]
    columns += ["condition", "notes"]
    return pd.DataFrame(columns=columns)


def template_csv(domain: str) -> bytes:
    """The template as CSV bytes, with one commented example row of guidance."""
    frame = template_frame(domain)
    example = {column: "" for column in frame.columns}
    example["equipment"] = "CWP 1A"
    example["unit_name"] = "UNIT 1"
    example["test_date"] = datetime.now().strftime("%Y-%m-%d")
    example["condition"] = "Normal"
    for spec in parameter_specs(domain):
        example[spec.key] = "0" if spec.numeric else ""
    frame = pd.DataFrame([example], columns=frame.columns)
    return frame.to_csv(index=False).encode("utf-8-sig")


def _read_csv_any_delimiter(buffer) -> pd.DataFrame:
    """Read a CSV whose delimiter is comma, tab, or semicolon.

    Real exports from Excel are routinely tab- or semicolon-separated while
    still carrying a .csv extension (confirmed: a real field template shared
    for this feature was tab-separated) - pandas' comma default would parse
    the whole file as one unsplit column instead of raising, which is worse
    than an error because nothing looks obviously wrong until every column
    turns out unmapped. `sep=None` with the python engine runs csv.Sniffer
    to detect the real delimiter.
    """
    return pd.read_csv(buffer, sep=None, engine="python")


def read_upload(file_name: str, content: bytes) -> pd.DataFrame:
    """Parse an uploaded CSV/XLSX into a DataFrame, raising ValueError with a
    readable message rather than a library traceback."""
    suffix = Path(file_name).suffix.lower()
    from io import BytesIO

    buffer = BytesIO(content)
    try:
        if suffix in {".xlsx", ".xls", ".xlsm"}:
            return pd.read_excel(buffer)
        if suffix == ".csv":
            try:
                return _read_csv_any_delimiter(buffer)
            except UnicodeDecodeError:
                buffer.seek(0)
                return _read_csv_any_delimiter(io.TextIOWrapper(buffer, encoding="latin-1"))
    except Exception as exc:
        raise ValueError(f"Gagal membaca '{file_name}': {exc}") from exc
    raise ValueError(f"Format '{suffix or file_name}' tidak didukung. Gunakan CSV atau XLSX.")


def map_columns(domain: str, frame: pd.DataFrame) -> dict[str, str]:
    """Map source columns onto canonical fields/parameters.

    Returns {source_column: canonical_key}. Columns that match nothing are
    left out and reported separately by `preview_upload` - never silently
    dropped without the user being told.
    """
    mapping: dict[str, str] = {}
    specs = parameter_specs(domain)

    for column in frame.columns:
        normalised = _norm_column(column)
        matched: Optional[str] = None

        for field, aliases in IDENTITY_ALIASES.items():
            if normalised in {_norm_column(alias) for alias in aliases}:
                matched = field
                break

        if matched is None:
            for spec in specs:
                if spec.matches(column):
                    matched = spec.key
                    break

        if matched is not None and matched not in mapping.values():
            mapping[str(column)] = matched

    return mapping


def _duplicate_columns(domain: str, frame: pd.DataFrame, mapping: dict[str, str]) -> list[str]:
    """Columns that matched a known field/parameter but were excluded from
    `mapping` because another column already claimed that canonical key -
    distinct from a column matching nothing at all, so preview_upload can
    tell the user the real reason instead of calling it unrecognized."""
    specs = parameter_specs(domain)
    duplicates: list[str] = []
    for column in frame.columns:
        col = str(column)
        if col in mapping:
            continue
        normalised = _norm_column(column)
        matched = any(
            normalised in {_norm_column(alias) for alias in aliases} for aliases in IDENTITY_ALIASES.values()
        ) or any(spec.matches(column) for spec in specs)
        if matched:
            duplicates.append(col)
    return duplicates


def wide_to_long(domain: str, frame: pd.DataFrame, source_file: str = "") -> list[dict[str, Any]]:
    """Explode a wide test-per-row frame into canonical long rows."""
    domain = canon_domain(domain)
    mapping = map_columns(domain, frame)
    inverse = {value: key for key, value in mapping.items()}
    uom_by_key = {spec.key: spec.uom for spec in parameter_specs(domain)}
    parameter_keys = [spec.key for spec in parameter_specs(domain) if spec.key in inverse]

    rows: list[dict[str, Any]] = []
    today_str = datetime.now().strftime("%Y-%m-%d")
    for _, record in frame.iterrows():
        raw_test_date = record.get(inverse["test_date"]) if "test_date" in inverse else ""
        if raw_test_date is None or (isinstance(raw_test_date, float) and pd.isna(raw_test_date)) or str(raw_test_date).strip() == "":
            resolved_test_date = today_str
        else:
            resolved_test_date = str(raw_test_date).strip()

        identity = {
            field: record.get(inverse[field]) if field in inverse else ""
            for field in ("equipment", "asset_id", "unit_name", "condition", "notes")
        }
        identity["test_date"] = resolved_test_date
        for key in parameter_keys:
            raw_value = record.get(inverse[key])
            if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)) or str(raw_value).strip() == "":
                continue
            rows.append({
                **identity,
                "parameter": key,
                "value": raw_value,
                "raw_value": raw_value,
                "uom": uom_by_key.get(key, ""),
                "source_file": source_file,
            })
    return rows


def preview_upload(domain: str, file_name: str, content: bytes) -> dict[str, Any]:
    """Parse + map + validate an upload without writing anything.

    Returns everything the UI needs to let a user decide whether to commit:
    the mapped/unmapped columns, the valid rows, and the rejected rows each
    with a reason.
    """
    domain = canon_domain(domain)
    frame = read_upload(file_name, content)
    mapping = map_columns(domain, frame)
    duplicate = _duplicate_columns(domain, frame, mapping)
    unmapped = [str(column) for column in frame.columns if str(column) not in mapping and str(column) not in duplicate]

    long_rows = wide_to_long(domain, frame, source_file=file_name)
    valid, rejected = normalise_rows(domain, long_rows)

    return {
        "domain": domain,
        "file_name": file_name,
        "source_rows": int(len(frame)),
        "mapping": mapping,
        "unmapped_columns": unmapped,
        "duplicate_columns": duplicate,
        "valid": valid,
        "rejected": rejected,
        "parameters_found": sorted({row["parameter"] for row in valid}),
    }


def _uploads_root(domain: str) -> Path:
    return domain_dir(domain) / "uploads"


def create_batch(domain: str, file_name: str, content: bytes, preview: dict[str, Any], now: Optional[datetime] = None) -> tuple[Path, dict[str, Any]]:
    """Archive the uploaded file plus a manifest, returning (path, manifest).

    Archiving happens before the commit so a rejected/aborted upload still
    leaves an audit trail of what was attempted - same reasoning as
    src.report_batches.create_batch.
    """
    domain = canon_domain(domain)
    now = now or datetime.now()
    batch_id = f"batch-{now.strftime('%H%M%S')}-{uuid.uuid4().hex[:6]}"
    batch_path = _uploads_root(domain) / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d") / batch_id
    batch_path.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file_name).name or "upload.csv"
    (batch_path / safe_name).write_bytes(content)

    manifest = {
        "batch_id": batch_id,
        "domain": domain,
        "uploaded_at": now.isoformat(timespec="seconds"),
        "file": safe_name,
        "status": "preview",
        "source_rows": preview.get("source_rows", 0),
        "valid_rows": len(preview.get("valid", [])),
        "rejected_rows": len(preview.get("rejected", [])),
        "mapping": preview.get("mapping", {}),
        "unmapped_columns": preview.get("unmapped_columns", []),
        "duplicate_columns": preview.get("duplicate_columns", []),
        "rejected": preview.get("rejected", [])[:200],
        "audit_events": [{"action": "preview", "at": now.isoformat(timespec="seconds")}],
    }
    _write_manifest(batch_path, manifest)
    return batch_path, manifest


def commit_batch(domain: str, batch_path, preview: dict[str, Any]) -> dict[str, Any]:
    """Append a previewed batch's valid rows to the canonical store."""
    domain = canon_domain(domain)
    batch_path = Path(batch_path)
    manifest = load_manifest(batch_path)
    batch_id = manifest.get("batch_id", batch_path.name)

    result = append_measurements(domain, preview.get("valid", []), batch_id=batch_id)

    manifest["status"] = "committed"
    manifest["written_rows"] = result["written"]
    manifest.setdefault("audit_events", []).append({
        "action": "commit",
        "at": datetime.now().isoformat(timespec="seconds"),
        "written": result["written"],
    })
    _write_manifest(batch_path, manifest)
    publish(Events.MEASUREMENT_UPLOADED, domain=domain, batch_id=batch_id, written=result["written"])
    return {**result, "batch_id": batch_id, "manifest": manifest}


def _write_manifest(batch_path: Path, manifest: dict[str, Any]) -> None:
    target = Path(batch_path) / "manifest.json"
    tmp_path = str(target) + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp_path, target)


def load_manifest(batch_path) -> dict[str, Any]:
    target = Path(batch_path) / "manifest.json"
    if not target.exists():
        return {}
    try:
        with open(target, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def list_recent_batches(domain: str, limit: int = 10) -> list[dict[str, Any]]:
    """Most recent upload batches for this domain, newest first."""
    root = _uploads_root(domain)
    if not root.exists():
        return []
    manifests = []
    for path in root.glob("*/*/*/batch-*"):
        manifest = load_manifest(path)
        if manifest:
            manifest["_path"] = str(path)
            manifests.append(manifest)
    manifests.sort(key=lambda item: str(item.get("uploaded_at", "")), reverse=True)
    return manifests[:limit]


def manual_entry_rows(domain: str, identity: dict[str, Any], values: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn one manual form submission into canonical long rows.

    The manual path and the upload path deliberately converge on the same
    validation (src.domain_measurements.normalise_rows) and the same store, so
    a hand-typed reading is indistinguishable downstream from an uploaded one.
    """
    domain = canon_domain(domain)
    uom_by_key = {spec.key: spec.uom for spec in parameter_specs(domain)}
    rows = []
    for key, value in values.items():
        if value is None or str(value).strip() == "":
            continue
        rows.append({
            "equipment": identity.get("equipment", ""),
            "asset_id": identity.get("asset_id", ""),
            "unit_name": identity.get("unit_name", ""),
            "test_date": identity.get("test_date", ""),
            "condition": identity.get("condition", ""),
            "notes": identity.get("notes", ""),
            "parameter": key,
            "value": value,
            "raw_value": value,
            "uom": uom_by_key.get(key, ""),
            "source_file": "input-manual",
        })
    return rows


_VIBRATION_POINT_KEYS = tuple(
    f"pt{point}_{axis}" for point in range(1, 7) for axis in ("v", "h", "a")
)


def agent_input_from_measurements(domain: str, frame: pd.DataFrame) -> dict[str, Any]:
    """Collapse a per-equipment measurement slice into a specialist agent's
    input dict, using the newest reading of each parameter.

    This is the payoff of aligning PROFILES' parameter keys with the agents'
    input keys: ingested data feeds the real agent instead of leaving it on
    its built-in example values.
    """
    domain = canon_domain(domain)
    if frame is None or frame.empty:
        return {}
    ordered = frame.sort_values("test_date", ascending=True, na_position="first")
    latest = ordered.drop_duplicates(subset=["parameter"], keep="last")

    payload: dict[str, Any] = {}
    for _, row in latest.iterrows():
        key = str(row.get("parameter") or "").strip()
        if not key:
            continue
        value = row.get("value")
        if pd.isna(value):
            # Qualitative reading (numeric=False parameter): use raw_value's
            # text as-is. NaN is truthy in Python, so a plain `raw_value or
            # ""` would let a missing raw_value (itself NaN, e.g. after a
            # CSV round-trip through an empty cell) through as the literal
            # string "nan" instead of being recognized as missing - omit the
            # key entirely instead, the same way wide_to_long() already
            # skips a missing value rather than storing a placeholder.
            raw_value = row.get("raw_value")
            if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)) or str(raw_value).strip() == "":
                continue
            payload[key] = str(raw_value)
        else:
            payload[key] = float(value)

    if domain == "VIBRASI" and "overall_rms" not in payload:
        # A per-point field sheet (1V/1H/1A.."6V"/"6H"/"6A") has no single
        # "overall" column at all - VibrationAgent requires overall_rms, and
        # silently leaving it unset would make it fall back to its built-in
        # 2.2 mm/s example value, i.e. a real upload producing a fabricated
        # diagnosis. ISO 10816-3 evaluates plant condition on the worst
        # reading across all measured points, so the maximum of the point
        # values that are actually present is a real, standard-consistent
        # measurement to derive from - not an invented one - as long as at
        # least one point was actually read.
        point_values = [payload[key] for key in _VIBRATION_POINT_KEYS if isinstance(payload.get(key), float)]
        if point_values:
            payload["overall_rms"] = max(point_values)

    return payload
