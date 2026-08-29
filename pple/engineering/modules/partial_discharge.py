"""Partial Discharge EngineeringModule - adapter over src.agents.specialist_agents.PDAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import PDAgent


class PartialDischargeModule(LegacyAgentAdapterModule):
    id = "partial_discharge"
    name = "Partial Discharge"
    version = "1.0.0"
    applicable_equipment = ["GENERATOR", "TRANSFORMER", "MOTOR", "SWITCHGEAR"]
    agent_cls = PDAgent
