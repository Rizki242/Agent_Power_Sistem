"""Agent Registry (docs/final.md Phase 18).

Reuses src.agents.subagent_coordinator.SubAgentCoordinator.list_specialists()'s
existing descriptor metadata (8 agents: the 6 specialists + Fusion + Safety)
rather than re-declaring it - that would be a second, driftable source of
truth for the exact same roster. What this module adds is a status that
isn't fabricated: the coordinator always reports "ONLINE" for every agent,
but the 6 specialist agents are each backed by a manifest-driven
pple.engineering module (see pple/engineering/manifests/*.yaml), so their
real load status (ACTIVE/DISABLED/ERROR) is available and should be used
instead. Fusion and Safety aren't manifest-driven modules - they're always
part of the pipeline - so they stay "ONLINE".
"""

from typing import Any

# SubAgentDescriptor's "domain" text doesn't match pple.engineering module
# ids by a fixed naming convention (e.g. "Partial Discharge" ->
# "partial_discharge") reliably enough to derive automatically - explicit
# map instead of string-mangling that could silently drift apart.
_DOMAIN_TO_MODULE_ID = {
    "Vibration": "vibration",
    "MCSA": "mcsa",
    "DGA": "dga",
    "Partial Discharge": "partial_discharge",
    "Tribology": "tribology",
    "Thermal": "thermal",
}


class AgentRegistry:
    def __init__(self):
        from src.agents.subagent_coordinator import SubAgentCoordinator

        self._coordinator = SubAgentCoordinator()

    @staticmethod
    def _module_status_by_id() -> dict[str, str]:
        from pple.engineering.loader import load_modules_from_manifests

        _, results = load_modules_from_manifests()
        return {r.module_id: r.status.value for r in results}

    def list_agents(self) -> list[dict[str, Any]]:
        """Every agent's descriptor, with `status` reflecting the real
        manifest load result for the 6 specialists (ACTIVE/DISABLED/ERROR)
        instead of the coordinator's hardcoded "ONLINE"."""
        module_status = self._module_status_by_id()
        agents = []
        for agent in self._coordinator.list_specialists():
            module_id = _DOMAIN_TO_MODULE_ID.get(agent["domain"])
            if module_id is not None:
                agent["status"] = module_status.get(module_id, "UNKNOWN")
            agents.append(agent)
        return agents

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        return next((a for a in self.list_agents() if a["agent_id"] == agent_id), None)
