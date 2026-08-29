"""Vibration EngineeringModule - adapter over src.agents.specialist_agents.VibrationAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import VibrationAgent


class VibrationModule(LegacyAgentAdapterModule):
    id = "vibration"
    name = "Vibration Analysis"
    version = "1.0.0"
    applicable_equipment = ["MOTOR", "PUMP", "FAN", "TURBINE", "GENERATOR", "GEARBOX"]
    agent_cls = VibrationAgent
