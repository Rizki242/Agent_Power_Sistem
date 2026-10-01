"""Fleet-wide reliability summary over the latest MCSA snapshot.

Moved verbatim out of api_server.py's /api/reliability/fleet endpoint so
the Streamlit Agent Dashboard computes the exact same fleet matrix
(total assets, health summary, critical watchlist) instead of the HTTP
layer owning business logic.
"""

from datetime import date
from typing import Dict, Optional

import pandas as pd

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.fusion_inputs import extract_mcsa_fusion_inputs

# Both Streamlit and React must read these fields from the payload. They must
# not invent a healthy score when the snapshot is missing, stale, or partial.
FLEET_STALE_AFTER_DAYS = 90
FLEET_HEALTH_STATUSES = ("HEALTHY", "WATCH", "WARNING", "ALERT", "CRITICAL", "UNKNOWN")
FLEET_DOMAINS = ("MCSA", "VIBRASI", "THERMAL", "TRIBOLOGY", "DGA", "PD")
FLEET_PARITY_CONTRACT = {
    "id": "fleet-reliability-snapshot",
    "source": "pple.application.fleet.FleetReliabilityUseCase",
    "endpoint": "/api/reliability/fleet",
    "builder": "src.fleet_reliability.build_fleet_reliability",
    "snapshot_scope": "fleet_health_watchlist_coverage",
    "engineering_drilldown_owner": "STREAMLIT",
    "react_scope": "snapshot_and_watchlist_only",
    "ownership_note": (
        "Snapshot armada dipakai bersama lewat FleetReliabilityUseCase. "
        "Diagnosis engineering mendalam tetap di Streamlit, bukan duplikat di React."
    ),
    "render_rules": {
        "unknown": "UNKNOWN berarti data belum cukup. Jangan diganti HEALTHY atau angka 90.",
        "stale": "STALE berarti pengukuran lebih tua dari ambang. Tetap tampilkan, jangan disembunyikan sebagai normal.",
        "missing_domain": "Domain tanpa pengukuran adalah data gap, bukan kondisi normal.",
        "watchlist": "Watchlist hanya WARNING, ALERT, dan CRITICAL. UNKNOWN tidak masuk watchlist.",
    },
}


def _empty_health_counts() -> Dict[str, int]:
    return {status: 0 for status in FLEET_HEALTH_STATUSES}


def _empty_unit_summary() -> Dict[str, Dict]:
    return {
        unit: {
            "total": 0,
            "health_sum": 0.0,
            "known_health_count": 0,
            "avg_health": None,
            "health_known": False,
            **_empty_health_counts(),
        }
        for unit in ("UNIT 1", "UNIT 2", "UNIT 3", "COMMON")
    }


def _latest_measurement_date(eq_data: pd.DataFrame) -> Optional[pd.Timestamp]:
    if eq_data is None or "Date" not in getattr(eq_data, "columns", []):
        return None
    parsed = pd.to_datetime(eq_data["Date"], errors="coerce")
    if parsed.dropna().empty:
        return None
    return parsed.max().normalize()


def _freshness(latest: Optional[pd.Timestamp], today: date) -> tuple[str, Optional[int]]:
    if latest is None or pd.isna(latest):
        return "UNKNOWN", None
    age_days = (today - latest.date()).days
    if age_days > FLEET_STALE_AFTER_DAYS:
        return "STALE", age_days
    return "FRESH", age_days


def _health_label(value: Optional[float]) -> str:
    if value is None:
        return "UNKNOWN"
    return f"{float(value):.1f}"


def _coverage_status(total_assets: int, known_health: int, fresh_assets: int, stale_assets: int) -> str:
    if total_assets == 0 or known_health == 0:
        return "UNKNOWN"
    if fresh_assets == 0 and stale_assets > 0:
        return "STALE"
    if fresh_assets < total_assets:
        return "PARTIAL"
    return "FRESH"


def _coverage_headline(status: str, stale_assets: int, undated_assets: int, unknown_health: int, missing_domains: list) -> str:
    if status == "UNKNOWN":
        return "UNKNOWN — tidak ada snapshot yang cukup untuk rata-rata kesehatan. Jangan ditampilkan sebagai kondisi normal."
    parts = []
    if status == "STALE":
        parts.append(f"STALE — tidak ada pengukuran yang lebih baru dari {FLEET_STALE_AFTER_DAYS} hari")
    elif status == "PARTIAL":
        parts.append("PARTIAL — sebagian aset belum punya tanggal atau pengukuran segar")
    else:
        parts.append("FRESH — snapshot MCSA masih di dalam ambang usia")
    if stale_assets:
        parts.append(f"{stale_assets} aset STALE")
    if undated_assets:
        parts.append(f"{undated_assets} aset tanpa tanggal (UNKNOWN)")
    if unknown_health:
        parts.append(f"{unknown_health} aset tanpa health index (UNKNOWN)")
    if missing_domains:
        parts.append("Data gap: " + ", ".join(missing_domains))
    return ". ".join(parts) + "."


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


def _finalize_fleet_payload(
    asset_matrix,
    health_counts,
    health_sum,
    known_health,
    unit_summary,
    risk_matrix,
    risk_matrix_assets,
    domain_seen,
    fresh_assets,
    stale_assets,
    undated_assets,
    unknown_health,
    newest_date,
) -> Dict:
    for unit in unit_summary.values():
        known = int(unit.get("known_health_count", 0))
        if known > 0:
            unit["avg_health"] = round(unit["health_sum"] / known, 1)
            unit["health_known"] = True
        else:
            unit["avg_health"] = None
            unit["health_known"] = False

    avg_health = round(health_sum / known_health, 1) if known_health else None
    asset_matrix.sort(
        key=lambda item: (
            item["health_index"] is not None,
            item["health_index"] if item["health_index"] is not None else 0,
            -item.get("severity", 0),
        )
    )
    bad_actors = sorted(
        [item for item in asset_matrix if item.get("composite_risk_score") is not None],
        key=lambda item: -item["composite_risk_score"],
    )[:10]

    y_categories = ["CRITICAL", "ALERT", "WARNING", "HEALTHY / WATCH"]
    x_categories = ["Class C (Low)", "Class B (Medium)", "Class A (Critical)"]
    crit_keys = ["C", "B", "A"]
    z_matrix, text_matrix, hover_matrix = [], [], []
    for y_cat in y_categories:
        row_z, row_text, row_hover = [], [], []
        for c_key in crit_keys:
            bucket = risk_matrix.get(c_key, {})
            names = risk_matrix_assets.get(c_key, {})
            if y_cat == "HEALTHY / WATCH":
                count = bucket.get("HEALTHY", 0) + bucket.get("WATCH", 0)
                assets = names.get("HEALTHY", []) + names.get("WATCH", [])
            else:
                count = bucket.get(y_cat, 0)
                assets = names.get(y_cat, [])
            row_z.append(count)
            row_text.append(f"<b>{count}</b>" if count > 0 else "0")
            if assets:
                sample = "<br>• ".join(assets[:6])
                if len(assets) > 6:
                    sample += f"<br>... dan {len(assets) - 6} lainnya"
                hover = f"<b>{y_cat} | Class {c_key}</b><br>Total: {count} Aset<br><br>• {sample}"
            else:
                hover = f"<b>{y_cat} | Class {c_key}</b><br>Tidak ada aset"
            row_hover.append(hover)
        z_matrix.append(row_z)
        text_matrix.append(row_text)
        hover_matrix.append(row_hover)

    missing_domains = [domain for domain, seen in domain_seen.items() if not seen]
    status = _coverage_status(len(asset_matrix), known_health, fresh_assets, stale_assets)
    return {
        "total_assets": len(asset_matrix),
        "fleet_health_average": avg_health,
        "fleet_health_label": _health_label(avg_health),
        "health_summary": health_counts,
        "unit_summary": unit_summary,
        "risk_matrix": risk_matrix,
        "risk_matrix_assets": risk_matrix_assets,
        "risk_grid": {
            "x": x_categories,
            "y": y_categories,
            "z": z_matrix,
            "text": text_matrix,
            "hover": hover_matrix,
        },
        "bad_actors": bad_actors,
        "critical_watchlist": [
            item for item in asset_matrix if item["health_status"] in ("CRITICAL", "ALERT", "WARNING")
        ][:10],
        "asset_matrix": asset_matrix,
        "parity_contract": dict(FLEET_PARITY_CONTRACT),
        "coverage": {
            "status": status,
            "fleet_health_known": avg_health is not None,
            "measured_assets": known_health,
            "unknown_health_assets": unknown_health,
            "fresh_assets": fresh_assets,
            "stale_assets": stale_assets,
            "undated_assets": undated_assets,
            "stale_after_days": FLEET_STALE_AFTER_DAYS,
            "as_of": None if newest_date is None else newest_date.date().isoformat(),
            "missing_domains": missing_domains,
            "headline": _coverage_headline(status, stale_assets, undated_assets, unknown_health, missing_domains),
        },
    }


def build_fleet_reliability(
    df_latest: pd.DataFrame,
    fusion_agent: ReliabilityFusionAgent,
    asset_graph: AssetKnowledgeGraph,
    limit: int = 60,
    include_multi_domain: bool = True,
) -> Dict:
    empty_unit_summary = _empty_unit_summary()

    if df_latest is None or df_latest.empty:
        return _finalize_fleet_payload(
            asset_matrix=[],
            health_counts=_empty_health_counts(),
            health_sum=0.0,
            known_health=0,
            unit_summary=empty_unit_summary,
            risk_matrix={"C": _empty_health_counts(), "B": _empty_health_counts(), "A": _empty_health_counts()},
            risk_matrix_assets={
                "C": {status: [] for status in FLEET_HEALTH_STATUSES},
                "B": {status: [] for status in FLEET_HEALTH_STATUSES},
                "A": {status: [] for status in FLEET_HEALTH_STATUSES},
            },
            domain_seen={domain: False for domain in FLEET_DOMAINS},
            fresh_assets=0,
            stale_assets=0,
            undated_assets=0,
            unknown_health=0,
            newest_date=None,
        )

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
    health_counts = _empty_health_counts()
    health_sum = 0.0
    known_health = 0
    fresh_assets = 0
    stale_assets = 0
    undated_assets = 0
    unknown_health = 0
    newest_date = None
    domain_seen = {domain: False for domain in FLEET_DOMAINS}
    today = date.today()

    unit_summary = _empty_unit_summary()

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

        h_stat = fusion_res.get("health_status") or "UNKNOWN"
        if h_stat not in health_counts:
            h_stat = "UNKNOWN"
        health_counts[h_stat] += 1
        raw_index = fusion_res.get("health_index")
        health_known = raw_index is not None and h_stat != "UNKNOWN"
        h_idx = float(raw_index) if health_known else None
        if health_known:
            health_sum += h_idx
            known_health += 1
        else:
            unknown_health += 1

        measured_on = _latest_measurement_date(eq_data)
        freshness, age_days = _freshness(measured_on, today)
        if freshness == "FRESH":
            fresh_assets += 1
        elif freshness == "STALE":
            stale_assets += 1
        else:
            undated_assets += 1
        if measured_on is not None and (newest_date is None or measured_on > newest_date):
            newest_date = measured_on

        # Unit aggregation
        if norm_unit not in unit_summary:
            unit_summary[norm_unit] = {
                "total": 0,
                "health_sum": 0.0,
                "known_health_count": 0,
                "avg_health": None,
                "health_known": False,
                **_empty_health_counts(),
            }
        unit_summary[norm_unit]["total"] += 1
        if health_known:
            unit_summary[norm_unit]["health_sum"] += h_idx
            unit_summary[norm_unit]["known_health_count"] += 1
        unit_summary[norm_unit][h_stat] = unit_summary[norm_unit].get(h_stat, 0) + 1

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
        domain_coverage = {domain: "DATA_GAP" for domain in FLEET_DOMAINS}
        if not eq_data.empty:
            domain_coverage["MCSA"] = "MEASURED"
            domain_seen["MCSA"] = True

        if include_multi_domain:
            if vibration_tests:
                try:
                    from src.vibration_data import match_monthly_test_by_equipment
                    v_match = match_monthly_test_by_equipment(eq, vibration_tests)
                    if v_match:
                        domain_seen["VIBRASI"] = True
                        v_st = str(v_match.get("status", "")).upper()
                        if any(x in v_st for x in ["UNSATISFACTORY", "UNACCEPTABLE", "ALARM", "ALERT"]):
                            domain_alerts["vibration"] = True
                            domain_coverage["VIBRASI"] = "ALERT"
                        else:
                            domain_coverage["VIBRASI"] = "MEASURED"
                except Exception:
                    pass

            try:
                from src.thermal_data import search_thermal_records
                th_recs = search_thermal_records(eq)
                if th_recs:
                    domain_seen["THERMAL"] = True
                    t_st = str(th_recs[0].get("status", "")).upper()
                    if any(x in t_st for x in ["ALERT", "CRITICAL", "WARNING"]):
                        domain_alerts["thermal"] = True
                        domain_coverage["THERMAL"] = "ALERT"
                    else:
                        domain_coverage["THERMAL"] = "MEASURED"
            except Exception:
                pass

            try:
                from src.tribology_data import search_tribology_samples
                tr_samples = search_tribology_samples(eq)
                if tr_samples:
                    domain_seen["TRIBOLOGY"] = True
                    tr_st = str(tr_samples[0].get("status", "")).upper()
                    if any(x in tr_st for x in ["ALERT", "CRITICAL", "WARNING"]):
                        domain_alerts["tribology"] = True
                        domain_coverage["TRIBOLOGY"] = "ALERT"
                    else:
                        domain_coverage["TRIBOLOGY"] = "MEASURED"
            except Exception:
                pass

        # Severity & Criticality weights for composite risk
        crit_weight = {"A": 3.0, "B": 2.0, "C": 1.0}.get(crit, 1.5)
        sev_val = fusion_res["failure_mode_diagnosis"].get("severity", 1)
        multi_domain_penalty = sum(15.0 for d, active in domain_alerts.items() if active and d != "mcsa")
        composite_risk_score = None
        if health_known:
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
            "domain_coverage": domain_coverage,
            "freshness": freshness,
            "age_days": age_days,
            "measurement_date": None if measured_on is None else measured_on.date().isoformat(),
            "composite_risk_score": composite_risk_score,
        })

    return _finalize_fleet_payload(
        asset_matrix=asset_matrix,
        health_counts=health_counts,
        health_sum=health_sum,
        known_health=known_health,
        unit_summary=unit_summary,
        risk_matrix=risk_matrix,
        risk_matrix_assets=risk_matrix_assets,
        domain_seen=domain_seen,
        fresh_assets=fresh_assets,
        stale_assets=stale_assets,
        undated_assets=undated_assets,
        unknown_health=unknown_health,
        newest_date=newest_date,
    )
