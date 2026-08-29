"""Thermal EngineeringModule - adapter over src.agents.specialist_agents.ThermalAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import ThermalAgent


class ThermalModule(LegacyAgentAdapterModule):
    id = "thermal"
    name = "Thermography & RTD Monitoring"
    version = "1.0.0"
    applicable_equipment = ["MOTOR", "PUMP", "FAN", "TURBINE", "GENERATOR", "GEARBOX", "TRANSFORMER", "SWITCHGEAR"]
    agent_cls = ThermalAgent
