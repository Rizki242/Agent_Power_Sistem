"""Natural-language command parsing for the PPLE CLI (docs/final.md Phase 19).

Rule-based only, matching this repo's "rule-based logic is the source of
truth, LLM is an optional enhancement" principle (see CLAUDE.md) - no LLM
call is required for these intents. Each pattern maps an Indonesian or
English phrase to one of the commands `pple/cli/main.py` already exposes;
nothing here duplicates business logic, it only recognizes intent and the
caller dispatches to the exact same functions the formal `pple <command>`
subcommands call.

Asset/plant/unit CREATE (e.g. the "tambahkan Unit 4" example in
docs/final.md Phase 19) is intentionally not wired to anything yet: there
is no durable place to persist a new unit/plant record until the database
layer (Phase 2-4) exists, and pple/assets is a deliberately read-only
view (see CLAUDE.md). Recognizing that phrasing here and silently
no-op'ing it would be worse than not recognizing it at all, so it is left
unmatched - callers must treat an unmatched phrase as "not understood",
never as "safe to ignore".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from pple.cli.safety import RiskTier, classify_command


@dataclass
class Intent:
    name: str
    command: str
    params: dict = field(default_factory=dict)
    risk: RiskTier = RiskTier.READ


_PATTERNS: list[tuple[re.Pattern, Callable[[re.Match], Intent]]] = []


def _register(pattern: str, builder: Callable[[re.Match], Intent]) -> None:
    _PATTERNS.append((re.compile(pattern, re.IGNORECASE), builder))


_register(
    r"^(?:aktifkan|nyalakan|enable)\s+modul(?:e)?\s+(?P<module>[\w-]+)\s+(?:untuk|for|di)\s+(?P<equipment>.+)$",
    lambda m: Intent(
        "MODULE_ENABLE", "equipment module-add",
        {"module_id": m.group("module").strip(), "equipment": m.group("equipment").strip()},
    ),
)
_register(
    r"^(?:nonaktifkan|matikan|disable)\s+modul(?:e)?\s+(?P<module>[\w-]+)\s+(?:untuk|for|di|dari)\s+(?P<equipment>.+)$",
    lambda m: Intent(
        "MODULE_DISABLE", "equipment module-remove",
        {"module_id": m.group("module").strip(), "equipment": m.group("equipment").strip()},
    ),
)
_register(
    r"^(?:cek|check|analisa|analisis|analyze)\s+(?:kondisi\s+)?(?P<equipment>.+)$",
    lambda m: Intent("EQUIPMENT_HEALTH", "reliability health", {"equipment": m.group("equipment").strip()}),
)
_register(
    r"^(?:daftar|list)\s+(?:aset|asset|equipment|peralatan)(?:\s+(?:di|in|unit)\s+(?P<unit>.+))?$",
    lambda m: Intent("ASSET_LIST", "assets list", {"unit": (m.group("unit") or "").strip()}),
)
_register(
    r"^status$",
    lambda m: Intent("SYSTEM_STATUS", "status", {}),
)


def parse_intent(text: str) -> Optional[Intent]:
    """Match free text against known intents and tag it with its risk tier.

    Returns None when nothing matches - callers must surface that as "not
    understood" and never guess/execute an unrecognized phrase. HIGH-RISK
    plant-actuation phrasing is not handled here at all: callers must run
    `pple.cli.safety.check_high_risk` on the raw text first, before this
    function ever sees it.
    """
    stripped = text.strip()
    for pattern, builder in _PATTERNS:
        match = pattern.match(stripped)
        if match:
            intent = builder(match)
            intent.risk = classify_command(intent.command)
            return intent
    return None
