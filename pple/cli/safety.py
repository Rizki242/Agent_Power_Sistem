"""Command safety classification (docs/final.md Phase 20).

Every command the CLI can run - typed directly as `pple <command>` or
recognized from natural language by `pple.cli.nl` - falls into one of
three tiers before it is allowed to execute:

READ       Inspects state only (status, doctor, module/assets/reliability/
           agents listings, analyze). Always allowed, no confirmation.
WRITE      Mutates PPLE's own configuration (currently: per-equipment
           engineering-module overrides, Phase 8). Allowed, but
           `pple ask`/`pple shell` require an explicit y/N confirmation
           before running one recognized from natural language.
HIGH-RISK  Plant actuation - trip/shutdown/start/stop/breaker open-close
           and similar. PPLE never executes these itself. The existing,
           mandatory `SafetyGuardrailAgent` (src/agents/safety_guard.py)
           blocks them outright and requires human-in-the-loop
           authorization through the normal SOP/CCR channel - this module
           does not reimplement that list, it just calls the same guard.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from src.agents.safety_guard import SafetyGuardrailAgent

_safety_guard = SafetyGuardrailAgent()


class RiskTier(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    HIGH_RISK = "HIGH-RISK"


# Command paths already exposed by pple/cli/main.py, grouped by tier.
# Keep this in sync with the @app.command()/@xxx_app.command() names there.
READ_COMMANDS = {
    "status",
    "doctor",
    "module list",
    "module show",
    "equipment modules",
    "assets tree",
    "assets list",
    "assets show",
    "reliability health",
    "agents list",
    "analyze",
}
WRITE_COMMANDS = {
    "equipment module-add",
    "equipment module-remove",
}


def classify_command(command_name: str) -> RiskTier:
    """Classify one of the known command paths above (e.g. 'equipment
    module-add'). Anything not explicitly listed as WRITE defaults to
    READ - this function is only ever fed command names this CLI already
    exposes, never raw HIGH-RISK plant-actuation text (that is caught
    earlier, on the raw text, by check_high_risk)."""
    if command_name in WRITE_COMMANDS:
        return RiskTier.WRITE
    return RiskTier.READ


def check_high_risk(text: str) -> dict[str, Any]:
    """Run free-form text (a natural-language command, before it is even
    parsed into an intent) through the mandatory Safety Guardrail. Returns
    the guard's own result dict; callers must block execution whenever
    `result["violation_detected"]` is true, regardless of what intent
    parsing would otherwise have produced."""
    return _safety_guard.check_safety(text)
