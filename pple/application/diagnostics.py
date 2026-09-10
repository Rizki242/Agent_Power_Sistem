"""Application Use Case for multi-modal equipment diagnosis."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
import pandas as pd

from pple.core.logging import log_diagnosis
from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs


class DiagnoseEquipmentUseCase:
    """Orchestrates multi-modal diagnostic fusion across CBM domains."""

    def __init__(
        self,
        fusion_agent: Optional[ReliabilityFusionAgent] = None,
        asset_graph: Optional[AssetKnowledgeGraph] = None,
    ):
        self.fusion_agent = fusion_agent or ReliabilityFusionAgent()
        self.asset_graph = asset_graph or AssetKnowledgeGraph()

    def diagnose_from_inputs(
        self,
        equipment: str,
        asset_type: Optional[str] = "Motor-Pump",
        criticality: Optional[str] = "A",
        vibration: Optional[Dict[str, Any]] = None,
        mcsa: Optional[Dict[str, Any]] = None,
        dga: Optional[Dict[str, Any]] = None,
        pd: Optional[Dict[str, Any]] = None,
        tribology: Optional[Dict[str, Any]] = None,
        thermal: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run fusion diagnosis from explicit multi-domain telemetry inputs."""
        t0 = time.perf_counter()
        result = self.fusion_agent.run_full_fusion(
            equipment=equipment,
            asset_type=asset_type or "Motor-Pump",
            criticality=criticality or "A",
            vibration_data=vibration,
            mcsa_data=mcsa,
            dga_data=dga,
            pd_data=pd,
            oil_data=tribology,
            thermal_data=thermal,
        )
        duration_ms = (time.perf_counter() - t0) * 1000
        health_index = float(result.get("health_index", 0.0))
        health_status = str(result.get("overall_status") or result.get("health_status") or "UNKNOWN")
        log_diagnosis(
            equipment=equipment,
            health_index=health_index,
            health_status=health_status,
            duration_ms=duration_ms,
            asset_type=asset_type,
            criticality=criticality,
        )
        return result

    def diagnose_from_mcsa_dataset(
        self,
        equipment: str,
        df_latest: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Run fusion diagnosis pulling MCSA parameters from the latest measurement dataset."""
        node = self.asset_graph.get_equipment_node(equipment)
        eq_data = (
            df_latest[df_latest["Equipment"].astype(str).str.upper() == equipment.upper()]
            if not df_latest.empty
            else pd.DataFrame()
        )

        fusion_inputs = extract_mcsa_fusion_inputs(eq_data)

        t0 = time.perf_counter()
        fusion_res = self.fusion_agent.run_full_fusion(
            equipment=equipment,
            asset_type=node.get("asset_type", "Electric Motor-Pump"),
            criticality=node.get("criticality", "A"),
            **fusion_inputs,
        )
        duration_ms = (time.perf_counter() - t0) * 1000

        fusion_res["asset_node"] = node
        fusion_res["data_sources"] = sorted(fusion_inputs.keys())

        health_index = float(fusion_res.get("health_index", 0.0))
        health_status = str(fusion_res.get("overall_status") or fusion_res.get("health_status") or "UNKNOWN")
        log_diagnosis(
            equipment=equipment,
            health_index=health_index,
            health_status=health_status,
            duration_ms=duration_ms,
            data_sources=fusion_res["data_sources"],
            asset_type=node.get("asset_type"),
            criticality=node.get("criticality"),
        )
        return fusion_res
