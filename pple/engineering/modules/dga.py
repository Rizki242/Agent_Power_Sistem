"""DGA EngineeringModule - adapter over src.agents.specialist_agents.DGAAgent."""

from pple.engineering.legacy_adapter import LegacyAgentAdapterModule
from src.agents.specialist_agents import DGAAgent


class DGAModule(LegacyAgentAdapterModule):
    id = "dga"
    name = "Dissolved Gas Analysis"
    version = "1.0.0"
    applicable_equipment = ["TRANSFORMER"]
    agent_cls = DGAAgent
