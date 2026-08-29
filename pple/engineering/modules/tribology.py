"""Tribology EngineeringModule - adapter over src.agents.specialist_agents.TribologyAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import TribologyAgent


class TribologyModule(LegacyAgentAdapterModule):
    id = "tribology"
    name = "Tribology & Oil Condition"
    version = "1.0.0"
    applicable_equipment = ["MOTOR", "PUMP", "TURBINE", "GEARBOX"]
    agent_cls = TribologyAgent
