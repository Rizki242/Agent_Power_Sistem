"""Audit log terpusat (docs/final.md Phase 29).

Setiap perubahan konfigurasi dicatat dengan enam kolom yang diminta spec:
WHO, WHAT, WHEN, OLD VALUE, NEW VALUE, SOURCE. "WHAT" disimpan terpisah
sebagai ``entity`` + ``field`` supaya bisa difilter, dan dirangkai jadi
kalimat oleh :func:`describe_event`.

Penyimpanan memakai JSONL (satu event per baris) di
``data/audit/audit_log.jsonl``. Append-only: berkas lama tidak pernah
ditulis ulang, jadi satu proses yang gagal di tengah jalan tidak bisa
merusak riwayat yang sudah tercatat. Database terpusat masih ditunda
(docs/final.md Phase 2-4), sama seperti manifest dan override modul.

Kegagalan menulis audit sengaja TIDAK membatalkan operasi yang sedang
berjalan - menonaktifkan modul tidak boleh gagal hanya karena folder audit
read-only. Kegagalan dicetak sebagai peringatan agar tetap terlihat.
"""

import getpass
import json
import os
import sys
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

ACTOR_ENV = "PPLE_ACTOR"

SOURCE_CLI = "CLI"
SOURCE_API = "API"
SOURCE_STREAMLIT = "STREAMLIT"
SOURCE_UNKNOWN = "python"

_WRITE_LOCK = Lock()


def default_log_path() -> str:
    from src.data_loader import get_data_path

    return get_data_path("audit", "audit_log.jsonl")


def resolve_actor(actor: Optional[str] = None) -> str:
    """Siapa yang melakukan perubahan.

    Urutan: argumen eksplisit -> PPLE_ACTOR -> user OS. Belum ada login,
    jadi ini identitas terbaik yang tersedia; catat sebagai petunjuk, bukan
    bukti otentikasi.
    """
    if actor and str(actor).strip():
        return str(actor).strip()
    env_actor = os.environ.get(ACTOR_ENV, "").strip()
    if env_actor:
        return env_actor
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _normalise(value: Any) -> Any:
    """Nilai yang tidak bisa di-JSON-kan disimpan sebagai teks."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def record_change(
    entity: str,
    field: str,
    old_value: Any,
    new_value: Any,
    actor: Optional[str] = None,
    source: str = SOURCE_UNKNOWN,
    details: Optional[Dict[str, Any]] = None,
    path: Optional[str] = None,
    when: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Catat satu perubahan dan kembalikan event yang ditulis."""
    event = {
        "when": (when or datetime.now()).isoformat(timespec="seconds"),
        "who": resolve_actor(actor),
        "entity": str(entity),
        "field": str(field),
        "old_value": _normalise(old_value),
        "new_value": _normalise(new_value),
        "source": str(source or SOURCE_UNKNOWN),
    }
    if details:
        event["details"] = {str(k): _normalise(v) for k, v in details.items()}

    target = path or default_log_path()
    try:
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False)
        with _WRITE_LOCK:
            with open(target, "a", encoding="utf-8") as fp:
                fp.write(line + "\n")
    except OSError as exc:
        # Fail-open: operasi pemanggil tetap jalan, tapi jangan sampai senyap.
        print(f"[PPLE] Gagal menulis audit log ke {target}: {exc}", file=sys.stderr)

    return event


def read_events(
    limit: int = 50,
    entity: Optional[str] = None,
    source: Optional[str] = None,
    path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Event terbaru lebih dulu. Baris rusak dilewati, bukan bikin crash."""
    target = path or default_log_path()
    if not os.path.exists(target):
        return []

    events: List[Dict[str, Any]] = []
    try:
        with open(target, "r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if entity and str(event.get("entity", "")) != str(entity):
                    continue
                if source and str(event.get("source", "")).upper() != str(source).upper():
                    continue
                events.append(event)
    except OSError as exc:
        print(f"[PPLE] Gagal membaca audit log {target}: {exc}", file=sys.stderr)
        return []

    events.reverse()
    if limit and limit > 0:
        return events[:limit]
    return events


def describe_event(event: Dict[str, Any]) -> str:
    """Ringkasan satu baris untuk CLI/UI."""
    return "{who} mengubah {field} pada {entity}: {old} -> {new} ({source})".format(
        who=event.get("who", "?"),
        field=event.get("field", "?"),
        entity=event.get("entity", "?"),
        old=event.get("old_value"),
        new=event.get("new_value"),
        source=event.get("source", SOURCE_UNKNOWN),
    )
