"""Fleet-wide reliability summary over the latest MCSA snapshot.

Moved verbatim out of api_server.py's /api/reliability/fleet endpoint so
the Streamlit Agent Dashboard computes the exact same fleet matrix
(total assets, health summary, critical watchlist) instead of the HTTP
layer owning business logic.
"""

from typing import Dict

import pandas as pd

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs


def build_fleet_reliability(
    df_latest: pd.DataFrame,
    fusion_agent: ReliabilityFusionAgent,
    asset_graph: AssetKnowledgeGraph,
    limit: int = 60,
) -> Dict:
    if df_latest is None or df_latest.empty:
        return {"total_assets": 0, "health_summary": {}, "fleet_health_average": 90.0, "asset_matrix": []}

    eq_names = [str(e) for e in df_latest["Equipment"].dropna().unique()]

    asset_matrix = []
    health_counts = {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0}
    health_sum = 0.0

    for eq in eq_names[:limit]:
        eq_data = df_latest[df_latest["Equipment"] == eq]
        node = asset_graph.get_equipment_node(eq)

        fusion_inputs = extract_mcsa_fusion_inputs(eq_data)

        fusion_res = fusion_agent.run_full_fusion(
            equipment=eq,
            asset_type=node.get("asset_type", "Electric Motor-Pump"),
            criticality=node.get("criticality", "A"),
            **fusion_inputs,
        )

        h_stat = fusion_res["health_status"]
        if h_stat in health_counts:
            health_counts[h_stat] += 1
        health_sum += fusion_res["health_index"]

        asset_matrix.append({
            "equipment": eq,
            "unit": node.get("unit", "UNIT COMMON"),
            "system": node.get("system", "Auxiliary"),
            "criticality": node.get("criticality", "A"),
            "health_index": fusion_res["health_index"],
            "health_status": h_stat,
            "health_color": fusion_res["health_color"],
            "primary_failure_mode": fusion_res["failure_mode_diagnosis"]["primary_failure_mode"],
            "severity": fusion_res["failure_mode_diagnosis"]["severity"],
            "confidence": fusion_res["failure_mode_diagnosis"]["confidence"],
            "rul_days": fusion_res["predictive_rul"]["estimated_rul_days"],
            "risk_level": fusion_res["risk_assessment"]["risk_level"]
        })

    avg_health = round(health_sum / len(asset_matrix), 1) if asset_matrix else 90.0

    asset_matrix.sort(key=lambda x: (x["health_index"], -x["severity"]))

    return {
        "total_assets": len(asset_matrix),
        "fleet_health_average": avg_health,
        "health_summary": health_counts,
        "critical_watchlist": [a for a in asset_matrix if a["health_status"] in ["CRITICAL", "ALERT", "WARNING"]][:10],
        "asset_matrix": asset_matrix
    }
