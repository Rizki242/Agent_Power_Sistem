"""MCSA EngineeringModule - adapter over src.agents.specialist_agents.MCSAAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import MCSAAgent


class MCSAModule(LegacyAgentAdapterModule):
    id = "mcsa"
    name = "Motor Current Signature Analysis"
    version = "1.0.0"
    applicable_equipment = ["MOTOR", "PUMP", "FAN", "GENERATOR"]
    agent_cls = MCSAAgent
