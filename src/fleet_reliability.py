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


def _normalize_unit(unit_str: str) -> str:
    if not unit_str:
        return "COMMON"
    u = str(unit_str).upper()
    if "UNIT 1" in u or "UNIT_1" in u or u.endswith(" 1"):
        return "UNIT 1"
    if "UNIT 2" in u or "UNIT_2" in u or u.endswith(" 2"):
        return "UNIT 2"
    if "UNIT 3" in u or "UNIT_3" in u or u.endswith(" 3"):
        return "UNIT 3"
    if "COMMON" in u:
        return "COMMON"
    return u


def build_fleet_reliability(
    df_latest: pd.DataFrame,
    fusion_agent: ReliabilityFusionAgent,
    asset_graph: AssetKnowledgeGraph,
    limit: int = 60,
    include_multi_domain: bool = True,
) -> Dict:
    empty_unit_summary = {
        "UNIT 1": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "UNIT 2": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "UNIT 3": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "COMMON": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
    }

    if df_latest is None or df_latest.empty:
        return {
            "total_assets": 0,
            "health_summary": {},
            "fleet_health_average": 90.0,
            "unit_summary": empty_unit_summary,
            "risk_matrix": {"C": {}, "B": {}, "A": {}},
            "risk_matrix_assets": {"C": {}, "B": {}, "A": {}},
            "risk_grid": {},
            "bad_actors": [],
            "critical_watchlist": [],
            "asset_matrix": [],
        }

    eq_names = [str(e) for e in df_latest["Equipment"].dropna().unique()]

    # Preload multi-domain tests if requested
    vibration_tests = []
    if include_multi_domain:
        try:
            from src.vibration_data import load_vibration_monthly_tests
            vibration_tests = load_vibration_monthly_tests()
        except Exception:
            vibration_tests = []

    asset_matrix = []
    health_counts = {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0}
    health_sum = 0.0

    unit_summary = {
        "UNIT 1": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "UNIT 2": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "UNIT 3": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "COMMON": {"total": 0, "health_sum": 0.0, "avg_health": 0.0, "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
    }

    # 3x4 risk matrix counts & asset names
    risk_matrix = {
        "C": {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "B": {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
        "A": {"HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0},
    }
    risk_matrix_assets = {
        "C": {"HEALTHY": [], "WATCH": [], "WARNING": [], "ALERT": [], "CRITICAL": []},
        "B": {"HEALTHY": [], "WATCH": [], "WARNING": [], "ALERT": [], "CRITICAL": []},
        "A": {"HEALTHY": [], "WATCH": [], "WARNING": [], "ALERT": [], "CRITICAL": []},
    }

    for eq in eq_names[:limit]:
        eq_data = df_latest[df_latest["Equipment"] == eq]
        node = asset_graph.get_equipment_node(eq)

        raw_unit = node.get("unit", "UNIT COMMON")
        norm_unit = _normalize_unit(raw_unit)
        crit = str(node.get("criticality", "A")).upper()
        if crit not in ["A", "B", "C"]:
            crit = "A"

        fusion_inputs = extract_mcsa_fusion_inputs(eq_data)

        fusion_res = fusion_agent.run_full_fusion(
            equipment=eq,
            asset_type=node.get("asset_type", "Electric Motor-Pump"),
            criticality=crit,
            **fusion_inputs,
        )

        h_stat = fusion_res["health_status"]
        if h_stat in health_counts:
            health_counts[h_stat] += 1
        h_idx = fusion_res["health_index"]
        health_sum += h_idx

        # Unit aggregation
        if norm_unit not in unit_summary:
            unit_summary[norm_unit] = {
                "total": 0, "health_sum": 0.0, "avg_health": 0.0,
                "HEALTHY": 0, "WATCH": 0, "WARNING": 0, "ALERT": 0, "CRITICAL": 0,
            }
        unit_summary[norm_unit]["total"] += 1
        unit_summary[norm_unit]["health_sum"] += h_idx
        if h_stat in unit_summary[norm_unit]:
            unit_summary[norm_unit][h_stat] += 1

        # Risk matrix
        if crit in risk_matrix and h_stat in risk_matrix[crit]:
            risk_matrix[crit][h_stat] += 1
            risk_matrix_assets[crit][h_stat].append(eq)

        # Multi-domain alerts check
        domain_alerts = {
            "mcsa": h_stat in ["WARNING", "ALERT", "CRITICAL"],
            "vibration": False,
            "thermal": False,
            "tribology": False,
        }

        if include_multi_domain:
            if vibration_tests:
                try:
                    from src.vibration_data import match_monthly_test_by_equipment
                    v_match = match_monthly_test_by_equipment(eq, vibration_tests)
                    if v_match:
                        v_st = str(v_match.get("status", "")).upper()
                        if any(x in v_st for x in ["UNSATISFACTORY", "UNACCEPTABLE", "ALARM", "ALERT"]):
                            domain_alerts["vibration"] = True
                except Exception:
                    pass

            try:
                from src.thermal_data import search_thermal_records
                th_recs = search_thermal_records(eq)
                if th_recs:
                    t_st = str(th_recs[0].get("status", "")).upper()
                    if any(x in t_st for x in ["ALERT", "CRITICAL", "WARNING"]):
                        domain_alerts["thermal"] = True
            except Exception:
                pass

            try:
                from src.tribology_data import search_tribology_samples
                tr_samples = search_tribology_samples(eq)
                if tr_samples:
                    tr_st = str(tr_samples[0].get("status", "")).upper()
                    if any(x in tr_st for x in ["ALERT", "CRITICAL", "WARNING"]):
                        domain_alerts["tribology"] = True
            except Exception:
                pass

        # Severity & Criticality weights for composite risk
        crit_weight = {"A": 3.0, "B": 2.0, "C": 1.0}.get(crit, 1.5)
        sev_val = fusion_res["failure_mode_diagnosis"].get("severity", 1)
        multi_domain_penalty = sum(15.0 for d, active in domain_alerts.items() if active and d != "mcsa")
        composite_risk_score = round(
            ((100.0 - h_idx) * crit_weight) + (sev_val * 12.0) + multi_domain_penalty,
            1,
        )

        asset_matrix.append({
            "equipment": eq,
            "unit": norm_unit,
            "raw_unit": raw_unit,
            "system": node.get("system", "Auxiliary"),
            "criticality": crit,
            "health_index": h_idx,
            "health_status": h_stat,
            "health_color": fusion_res["health_color"],
            "primary_failure_mode": fusion_res["failure_mode_diagnosis"]["primary_failure_mode"],
            "severity": sev_val,
            "confidence": fusion_res["failure_mode_diagnosis"]["confidence"],
            "rul_days": fusion_res["predictive_rul"]["estimated_rul_days"],
            "risk_level": fusion_res["risk_assessment"]["risk_level"],
            "domain_alerts": domain_alerts,
            "composite_risk_score": composite_risk_score,
        })

    # Finalize unit averages
    for u_k, u_v in unit_summary.items():
        if u_v["total"] > 0:
            u_v["avg_health"] = round(u_v["health_sum"] / u_v["total"], 1)

    avg_health = round(health_sum / len(asset_matrix), 1) if asset_matrix else 90.0

    # Sort asset_matrix ascending by health index
    asset_matrix.sort(key=lambda x: (x["health_index"], -x["severity"]))

    # Bad actors: Top 10 sorted descending by composite risk score
    bad_actors = sorted(asset_matrix, key=lambda x: -x["composite_risk_score"])[:10]

    # Pre-calculated 2D Risk Grid for Plotly Heatmap
    # Y-axis (Top to Bottom): CRITICAL, ALERT, WARNING, HEALTHY/WATCH
    # X-axis (Left to Right): Class C, Class B, Class A
    y_categories = ["CRITICAL", "ALERT", "WARNING", "HEALTHY / WATCH"]
    x_categories = ["Class C (Low)", "Class B (Medium)", "Class A (Critical)"]
    crit_keys = ["C", "B", "A"]

    z_matrix = []
    text_matrix = []
    hover_matrix = []

    for y_cat in y_categories:
        row_z = []
        row_text = []
        row_hover = []
        for c_key in crit_keys:
            if y_cat == "HEALTHY / WATCH":
                count = risk_matrix[c_key]["HEALTHY"] + risk_matrix[c_key]["WATCH"]
                assets = risk_matrix_assets[c_key]["HEALTHY"] + risk_matrix_assets[c_key]["WATCH"]
            else:
                count = risk_matrix[c_key].get(y_cat, 0)
                assets = risk_matrix_assets[c_key].get(y_cat, [])

            row_z.append(count)
            row_text.append(f"<b>{count}</b>" if count > 0 else "0")

            if assets:
                sample_str = "<br>• ".join(assets[:6])
                if len(assets) > 6:
                    sample_str += f"<br>... dan {len(assets)-6} lainnya"
                hover_info = f"<b>{y_cat} | Class {c_key}</b><br>Total: {count} Aset<br><br>• {sample_str}"
            else:
                hover_info = f"<b>{y_cat} | Class {c_key}</b><br>Tidak ada aset"
            row_hover.append(hover_info)

        z_matrix.append(row_z)
        text_matrix.append(row_text)
        hover_matrix.append(row_hover)

    risk_grid = {
        "x": x_categories,
        "y": y_categories,
        "z": z_matrix,
        "text": text_matrix,
        "hover": hover_matrix,
    }

    return {
        "total_assets": len(asset_matrix),
        "fleet_health_average": avg_health,
        "health_summary": health_counts,
        "unit_summary": unit_summary,
        "risk_matrix": risk_matrix,
        "risk_matrix_assets": risk_matrix_assets,
        "risk_grid": risk_grid,
        "bad_actors": bad_actors,
        "critical_watchlist": [a for a in asset_matrix if a["health_status"] in ["CRITICAL", "ALERT", "WARNING"]][:10],
        "asset_matrix": asset_matrix,
    }
