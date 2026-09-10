"""Application Use Case for fleet-wide reliability aggregation."""

from __future__ import annotations

from typing import Any, Dict, Optional
import pandas as pd

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.fleet_reliability import build_fleet_reliability


class FleetReliabilityUseCase:
    """Orchestrates fleet-wide reliability summary and watchlist aggregation."""

    def __init__(
        self,
        fusion_agent: Optional[ReliabilityFusionAgent] = None,
        asset_graph: Optional[AssetKnowledgeGraph] = None,
    ):
        self.fusion_agent = fusion_agent or ReliabilityFusionAgent()
        self.asset_graph = asset_graph or AssetKnowledgeGraph()

    def get_fleet_summary(self, df_latest: pd.DataFrame) -> Dict[str, Any]:
        """Aggregate health status and watchlist across all equipment in the fleet."""
        return build_fleet_reliability(
            df_latest=df_latest,
            fusion_agent=self.fusion_agent,
            asset_graph=self.asset_graph,
        )
