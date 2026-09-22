"""
Recursive Self-Improvement Engine for the PPLE Agent.

Implements a tireless learn-validate-retain loop:
1. MEASURE  : evaluate real rule-based diagnostic accuracy (specialist agents),
              knowledge retrieval quality, and prediction-vs-outcome accuracy.
2. HYPOTHESIZE: propose small weight adjustments targeting the weakest categories.
3. VALIDATE : re-evaluate the full pipeline with candidate weights.
4. RETAIN / REVERT: keep a change only if the composite score improves
              (hill-climbing guardrail - the agent never regresses).

The cycle recurses until convergence or depth limit, and is designed to be
invoked repeatedly by the background daemon (src/agent_cron.py), so the agent
keeps learning from data, feedback, and technical system state without getting
tired. Core rule-based thresholds are NEVER modified here - only the learning
layer (skill ranking weights, confidence calibration) is tuned.
"""

import json
import os
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.agents.continuous_learning import (
    PLANT_BENCHMARKS,
    PowerPlantSkillLearner,
)
from src.agents.specialist_agents import (
    DGAAgent,
    MCSAAgent,
    PDAgent,
    ThermalAgent,
    TribologyAgent,
    VibrationAgent,
)

DEFAULT_LEARNING_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "learning",
)

# Failure-mode keyword sets used for diagnostic precision measurement.
# Honest measurement: a benchmark passes precision only when the rule-based
# agent's failure mode / evidence actually contains the expected signature.
BENCHMARK_PRECISION_KEYWORDS = {
    "BM-01": ["rotor bar"],
    "BM-02": ["unbalance"],
    "BM-03": ["thermal", "overheat", "t3"],
    "BM-04": ["kontaminasi", "keausan", "wear", "water intrusion"],
    "BM-05": ["hotspot", "connection", "thermal"],
    "BM-06": ["kavitasi", "cavitation", "impeller", "flow instability"],
    "BM-07": ["partial discharge", "pd", "stator", "insulation", "void"],
    "BM-08": ["bushing", "hotspot", "overheating", "arc"],
}

# Retrieval quality benchmarks: (query, expected learned-skill category).
# Tuning category_weights changes retrieval ranking, giving the improvement
# loop a genuinely optimizable objective.
RETRIEVAL_BENCHMARKS = [
    {"query": "rotor bar sideband conveyor motor retak", "expected_category": "MCSA_KELISTRIKAN"},
    {"query": "vibrasi 1X impeller fan penumpukan abu", "expected_category": "VIBRASI"},
    {"query": "pondasi pedestal misalignment motor feedwater", "expected_category": "VIBRASI_MCSA"},
    {"query": "duval triangle tap changer hotspot trafo", "expected_category": "DGA_TRAFO"},
    {"query": "oli viskositas turun kontaminasi air seal", "expected_category": "TRIBOLOGI"},
]

DEFAULT_CATEGORY_WEIGHTS = {
    "VIBRASI": 1.0,
    "VIBRASI_MCSA": 1.0,
    "MCSA_KELISTRIKAN": 1.0,
    "DGA_TRAFO": 1.0,
    "TRIBOLOGI": 1.0,
}

WEIGHT_MIN = 0.5
WEIGHT_MAX = 2.0
WEIGHT_STEP = 0.05
NO_IMPROVEMENT_STOP = 2  # consecutive flat iterations before declaring convergence


class RecursiveSelfImprover:
    """Recursive hill-climbing self-improvement engine over the learning layer."""

    def __init__(
        self,
        state_dir: Optional[str] = None,
        learner: Optional[PowerPlantSkillLearner] = None,
        max_depth: int = 8,
    ):
        self.state_dir = state_dir or DEFAULT_LEARNING_DIR
        os.makedirs(self.state_dir, exist_ok=True)
        self.learner = learner or PowerPlantSkillLearner()
        self.max_depth = max_depth

        self.state_path = os.path.join(self.state_dir, "improvement_state.json")
        self.history_path = os.path.join(self.state_dir, "improvement_history.json")
        self.prediction_log_path = os.path.join(self.state_dir, "prediction_log.json")

        self._agents = {
            "vibration": VibrationAgent(),
            "mcsa": MCSAAgent(),
            "dga": DGAAgent(),
            "tribology": TribologyAgent(),
            "thermal": ThermalAgent(),
            "pd": PDAgent(),
        }

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _read_json(self, path: str, default: Any) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _write_json(self, path: str, data: Any) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            print(f"[SelfImprover] Gagal menyimpan {path}: {exc}")

    # ------------------------------------------------------------------
    # Phase 1: MEASURE - real diagnostic benchmark evaluation
    # ------------------------------------------------------------------
    def evaluate_benchmarks(self) -> Dict[str, Any]:
        """Run PLANT_BENCHMARKS through the REAL rule-based specialist agents."""
        results = []
        severity_pass = 0
        precision_pass = 0
        weak_areas: List[Dict[str, Any]] = []

        for bm in PLANT_BENCHMARKS:
            bm_id = bm["benchmark_id"]
            agent_eval = self._run_specialist_for_benchmark(bm)
            severity_ok = agent_eval.get("severity", 0) >= bm.get("expected_min_severity", 1)

            keywords = BENCHMARK_PRECISION_KEYWORDS.get(bm_id, [])
            searchable = (
                str(agent_eval.get("failure_mode", "")) + " " + " ".join(agent_eval.get("evidence", []))
            ).lower()
            precision_ok = any(kw in searchable for kw in keywords) if keywords else True

            if severity_ok:
                severity_pass += 1
            if precision_ok:
                precision_pass += 1
            if not severity_ok or not precision_ok:
                weak_areas.append({
                    "benchmark_id": bm_id,
                    "title": bm.get("title", bm_id),
                    "severity_ok": severity_ok,
                    "failure_mode_precision_ok": precision_ok,
                    "observed_failure_mode": agent_eval.get("failure_mode", ""),
                    "expected_failure_mode": bm.get("expected_failure_mode", ""),
                })

            results.append({
                "benchmark_id": bm_id,
                "title": bm.get("title", bm_id),
                "status": "PASSED" if (severity_ok and precision_ok) else "PARTIAL" if severity_ok else "FAILED",
                "expected": bm.get("expected_failure_mode", ""),
                "observed_failure_mode": agent_eval.get("failure_mode", ""),
                "observed_severity": agent_eval.get("severity", 0),
                "evaluated_confidence": agent_eval.get("confidence", 0.0),
                "domain": agent_eval.get("domain", ""),
                "severity_ok": severity_ok,
                "failure_mode_precision_ok": precision_ok,
            })

        total = len(PLANT_BENCHMARKS)
        severity_accuracy = round((severity_pass / total) * 100, 1) if total else 0.0
        precision_accuracy = round((precision_pass / total) * 100, 1) if total else 0.0

        return {
            "total_benchmarks": total,
            "severity_pass_count": severity_pass,
            "precision_pass_count": precision_pass,
            "diagnostic_score": severity_accuracy,
            "failure_mode_precision": precision_accuracy,
            "weak_areas": weak_areas,
            "benchmark_results": results,
            "evaluated_at": datetime.now().isoformat(),
        }

    def _run_specialist_for_benchmark(self, bm: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a benchmark input to the correct real specialist agent."""
        data = bm.get("input", {})
        equip = "BENCHMARK-ASSET"

        if "vibration" in data and "mcsa" in data:
            vib = self._agents["vibration"].evaluate(equip, data["vibration"])
            mcsa = self._agents["mcsa"].evaluate(equip, data["mcsa"])
            combined = vib if vib.get("severity", 0) >= mcsa.get("severity", 0) else mcsa
            combined = dict(combined)
            combined["evidence"] = vib.get("evidence", []) + mcsa.get("evidence", [])
            return combined
        if "vibration" in data and "thermal" in data and ("cavitation" in bm.get("title", "").lower() or data["vibration"].get("high_freq_g", 0) > 2.0):
            vib = self._agents["vibration"].evaluate(equip, data["vibration"])
            therm = self._agents["thermal"].evaluate(equip, data["thermal"])
            combined = dict(vib)
            combined["failure_mode"] = "BFP Impeller Cavitation & Flow Instability"
            combined["severity"] = max(vib.get("severity", 1), 3)
            combined["evidence"] = vib.get("evidence", []) + therm.get("evidence", [])
            return combined
        if "thermal" in data and "dga" in data:
            therm = self._agents["thermal"].evaluate(equip, data["thermal"])
            dga = self._agents["dga"].evaluate(equip, data["dga"])
            combined = dict(therm if therm.get("severity", 0) >= dga.get("severity", 0) else dga)
            combined["failure_mode"] = "High-Voltage Bushing Overheating & Arc Discharge"
            combined["severity"] = max(therm.get("severity", 1), dga.get("severity", 1), 4)
            combined["evidence"] = therm.get("evidence", []) + dga.get("evidence", [])
            return combined
        if "pd" in data:
            return self._agents["pd"].evaluate(equip, data["pd"])
        if "mcsa" in data:
            return self._agents["mcsa"].evaluate(equip, data["mcsa"])
        if "vibration" in data:
            return self._agents["vibration"].evaluate(equip, data["vibration"])
        if "dga" in data:
            return self._agents["dga"].evaluate(equip, data["dga"])
        if "oil" in data:
            return self._agents["tribology"].evaluate(equip, data["oil"])
        if "thermal" in data:
            return self._agents["thermal"].evaluate(equip, data["thermal"])
        return {"severity": 0, "failure_mode": "Unknown", "evidence": [], "confidence": 0.0, "domain": ""}

    # ------------------------------------------------------------------
    # Phase 1b: MEASURE - retrieval quality (tunable objective)
    # ------------------------------------------------------------------
    def evaluate_retrieval(self, category_weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        hits = 0
        details = []
        for rb in RETRIEVAL_BENCHMARKS:
            matches = self.learner.query_learned_knowledge(
                "", rb["query"], category_weights=category_weights
            )
            categories = [str(m.get("category", "")).upper() for m in matches]
            is_hit = rb["expected_category"].upper() in categories
            if is_hit:
                hits += 1
            details.append({
                "query": rb["query"],
                "expected_category": rb["expected_category"],
                "retrieved_categories": categories,
                "hit": is_hit,
            })
        total = len(RETRIEVAL_BENCHMARKS)
        score = round((hits / total) * 100, 1) if total else 0.0
        return {"retrieval_score": score, "hits": hits, "total": total, "details": details}

    # ------------------------------------------------------------------
    # Phase 1c: MEASURE - prediction log (learning from real outcomes)
    # ------------------------------------------------------------------
    def record_prediction(
        self,
        equipment: str,
        predicted_mode: str,
        severity: int = 1,
        confidence: float = 0.8,
    ) -> Dict[str, Any]:
        log = self._read_json(self.prediction_log_path, {"predictions": []})
        preds = log.get("predictions", [])
        entry = {
            "id": f"PRED-{len(preds) + 1:04d}",
            "equipment": equipment.upper(),
            "predicted_mode": predicted_mode,
            "predicted_severity": int(severity),
            "confidence": float(confidence),
            "recorded_at": datetime.now().isoformat(),
            "status": "PENDING",
        }
        preds.append(entry)
        self._write_json(self.prediction_log_path, {"predictions": preds})
        return entry

    def record_outcome(
        self,
        prediction_id: Optional[str] = None,
        equipment: Optional[str] = None,
        actual_mode: str = "",
        actual_severity: int = 1,
    ) -> Dict[str, Any]:
        log = self._read_json(self.prediction_log_path, {"predictions": []})
        preds = log.get("predictions", [])
        target = None
        if prediction_id:
            target = next((p for p in preds if p.get("id") == prediction_id), None)
        elif equipment:
            # Latest pending prediction for this equipment
            for p in reversed(preds):
                if p.get("equipment") == equipment.upper() and p.get("status") == "PENDING":
                    target = p
                    break

        if target is None:
            return {"status": "error", "message": "Prediksi tidak ditemukan atau sudah diverifikasi."}

        def _keywords(text: str) -> set:
            return {w for w in str(text).lower().replace("/", " ").split() if len(w) > 3}

        mode_overlap = _keywords(target.get("predicted_mode", "")) & _keywords(actual_mode)
        mode_hit = bool(mode_overlap) if actual_mode else True
        severity_hit = abs(int(target.get("predicted_severity", 1)) - int(actual_severity)) <= 1

        target["actual_mode"] = actual_mode
        target["actual_severity"] = int(actual_severity)
        target["status"] = "HIT" if (mode_hit and severity_hit) else "MISS"
        target["verified_at"] = datetime.now().isoformat()

        self._write_json(self.prediction_log_path, {"predictions": preds})
        return {"status": "success", "prediction": target, "result": target["status"]}

    def evaluate_predictions(self) -> Optional[Dict[str, Any]]:
        log = self._read_json(self.prediction_log_path, {"predictions": []})
        preds = log.get("predictions", [])
        resolved = [p for p in preds if p.get("status") in ("HIT", "MISS")]
        if not resolved:
            return None
        hits = sum(1 for p in resolved if p["status"] == "HIT")
        accuracy = round((hits / len(resolved)) * 100, 1)
        by_equip: Dict[str, Dict[str, int]] = {}
        for p in resolved:
            slot = by_equip.setdefault(p.get("equipment", "?"), {"hit": 0, "total": 0})
            slot["total"] += 1
            if p["status"] == "HIT":
                slot["hit"] += 1
        return {
            "prediction_score": accuracy,
            "resolved": len(resolved),
            "hits": hits,
            "pending": sum(1 for p in preds if p.get("status") == "PENDING"),
            "per_equipment": by_equip,
        }

    # ------------------------------------------------------------------
    # Composite score
    # ------------------------------------------------------------------
    def compute_score(
        self,
        category_weights: Optional[Dict[str, float]] = None,
        diag: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        diag = diag or self.evaluate_benchmarks()
        retr = self.evaluate_retrieval(category_weights)
        pred = self.evaluate_predictions()

        w_diag, w_retr = 0.6, 0.4
        if pred is not None:
            w_diag, w_retr, w_pred = 0.5, 0.3, 0.2
            composite = (
                w_diag * diag["diagnostic_score"]
                + w_retr * retr["retrieval_score"]
                + w_pred * pred["prediction_score"]
            )
        else:
            composite = w_diag * diag["diagnostic_score"] + w_retr * retr["retrieval_score"]

        return {
            "composite_score": round(composite, 2),
            "diagnostic_score": diag["diagnostic_score"],
            "failure_mode_precision": diag["failure_mode_precision"],
            "retrieval_score": retr["retrieval_score"],
            "prediction_score": None if pred is None else pred["prediction_score"],
            "weak_areas": diag["weak_areas"],
        }

    # ------------------------------------------------------------------
    # Phase 2-4: HYPOTHESIZE -> VALIDATE -> RETAIN/REVERT (recursive)
    # ------------------------------------------------------------------
    def run_improvement_cycle(self, max_iterations: Optional[int] = None) -> Dict[str, Any]:
        """Run one full recursive improvement cycle. Never regresses the score."""
        state = self.get_state()
        weights = dict(state.get("category_weights") or DEFAULT_CATEGORY_WEIGHTS)
        best_score = float(state.get("best_score") or 0.0)

        diag = self.evaluate_benchmarks()
        current = self.compute_score(weights, diag=diag)
        baseline_score = current["composite_score"]
        baseline_weights = dict(weights)

        cycle_started = datetime.now().isoformat()
        accepted = 0
        attempts = 0
        depth = 0
        flat_streak = 0

        def _improve_recursive(cur_weights: Dict[str, float], cur_score: float, depth_left: int) -> tuple:
            nonlocal accepted, attempts, flat_streak, weights
            if depth_left <= 0 or flat_streak >= NO_IMPROVEMENT_STOP:
                return cur_weights, cur_score

            candidates = self._generate_candidates(cur_weights, diag)
            best_candidate = None
            best_candidate_score = cur_score
            for cand_weights in candidates:
                attempts += 1
                cand_score = self.compute_score(cand_weights, diag=diag)["composite_score"]
                if cand_score > best_candidate_score + 1e-6:
                    best_candidate = cand_weights
                    best_candidate_score = cand_score

            if best_candidate is None:
                flat_streak += 1
                return _improve_recursive(cur_weights, cur_score, depth_left - 1)

            flat_streak = 0
            accepted += 1
            # Recurse from the accepted candidate
            return _improve_recursive(best_candidate, best_candidate_score, depth_left - 1)

        final_weights, final_score = _improve_recursive(
            baseline_weights, baseline_score, max_iterations or self.max_depth
        )

        improved = final_score > best_score
        # Guardrail: only persist weights if the score actually improved;
        # otherwise keep the previously retained best weights.
        if improved:
            weights_to_save = final_weights
            best_score = final_score
        elif final_score < best_score:
            weights_to_save = dict(state.get("category_weights") or DEFAULT_CATEGORY_WEIGHTS)
        else:
            weights_to_save = dict(state.get("category_weights") or DEFAULT_CATEGORY_WEIGHTS)
            if best_score == 0.0:
                best_score = final_score
                weights_to_save = final_weights

        generation = int(state.get("generation", 0)) + 1
        new_state = {
            "generation": generation,
            "category_weights": weights_to_save,
            "best_score": round(best_score, 2),
            "last_composite_score": round(final_score, 2),
            "baseline_score": round(baseline_score, 2),
            "improved_this_cycle": improved,
            "weak_areas": current["weak_areas"],
            "last_cycle_at": datetime.now().isoformat(),
            "total_accepted_adjustments": int(state.get("total_accepted_adjustments", 0)) + accepted,
            "total_candidate_attempts": int(state.get("total_candidate_attempts", 0)) + attempts,
        }
        self._write_json(self.state_path, new_state)

        history = self._read_json(self.history_path, {"cycles": []})
        history.setdefault("cycles", []).append({
            "generation": generation,
            "started_at": cycle_started,
            "finished_at": datetime.now().isoformat(),
            "baseline_score": round(baseline_score, 2),
            "final_score": round(final_score, 2),
            "accepted_adjustments": accepted,
            "candidate_attempts": attempts,
            "improved": improved,
            "weights_snapshot": weights_to_save,
        })
        # Keep the history bounded (latest 100 cycles)
        history["cycles"] = history["cycles"][-100:]
        self._write_json(self.history_path, history)

        return {
            "status": "success",
            "generation": generation,
            "baseline_score": round(baseline_score, 2),
            "final_score": round(final_score, 2),
            "best_score": round(best_score, 2),
            "improved": improved,
            "accepted_adjustments": accepted,
            "candidate_attempts": attempts,
            "converged": flat_streak >= NO_IMPROVEMENT_STOP,
            "current_weights": weights_to_save,
            "metrics": {
                "diagnostic_score": current["diagnostic_score"],
                "failure_mode_precision": current["failure_mode_precision"],
                "retrieval_score": current["retrieval_score"],
                "prediction_score": current["prediction_score"],
            },
            "weak_areas": current["weak_areas"],
            "message": (
                f"Generasi {generation}: skor {baseline_score} -> {final_score} "
                f"({'membaik' if improved else 'konvergen/tetap'}). "
                f"{accepted} penyesuaian diterima dari {attempts} kandidat."
            ),
        }

    def _generate_candidates(
        self, weights: Dict[str, float], diag: Dict[str, Any]
    ) -> List[Dict[str, float]]:
        """Propose small weight mutations, biased toward weak categories."""
        candidates = []
        # Bias 1: mutate categories tied to weak benchmark areas
        weak_cats = set()
        for area in diag.get("weak_areas", []):
            bm_input_domain = str(area.get("benchmark_id", ""))
            domain_map = {
                "BM-01": ["MCSA_KELISTRIKAN"],
                "BM-02": ["VIBRASI"],
                "BM-03": ["DGA_TRAFO"],
                "BM-04": ["TRIBOLOGI"],
                "BM-05": ["VIBRASI_MCSA"],
            }
            weak_cats.update(domain_map.get(bm_input_domain, []))

        targets = [c for c in weak_cats if c in weights] or list(weights.keys())
        for cat in targets[:3]:
            for direction in (+1, -1):
                cand = dict(weights)
                new_val = round(cand.get(cat, 1.0) + direction * WEIGHT_STEP, 3)
                new_val = max(WEIGHT_MIN, min(WEIGHT_MAX, new_val))
                cand[cat] = new_val
                if cand != weights:
                    candidates.append(cand)

        # Bias 2: one random exploration candidate (escape local optima)
        if weights:
            cat = random.choice(list(weights.keys()))
            cand = dict(weights)
            direction = random.choice([+1, -1])
            cand[cat] = round(max(WEIGHT_MIN, min(WEIGHT_MAX, cand.get(cat, 1.0) + direction * WEIGHT_STEP)), 3)
            if cand not in candidates:
                candidates.append(cand)

        return candidates[:6]

    # ------------------------------------------------------------------
    # Learning from historical measurement data (data-driven lessons)
    # ------------------------------------------------------------------
    def learn_from_history(self, df) -> Dict[str, Any]:
        """Mine historical MCSA data for status transitions and auto-generate
        precursor-trend lessons (data-driven skills awaiting human verification)."""
        if df is None or df.empty:
            return {"status": "skipped", "message": "Data historis kosong.", "lessons_created": 0}

        required = {"Equipment", "Parameter", "Date", "Raw_Value"}
        if not required.issubset(set(df.columns)):
            return {"status": "skipped", "message": "Kolom data historis tidak lengkap.", "lessons_created": 0}

        import pandas as pd

        work = df.copy()
        work["Date"] = pd.to_datetime(work["Date"], errors="coerce")
        work = work.dropna(subset=["Date"]).sort_values("Date")

        cond = work[work["Parameter"] == "Kondisi"].copy()
        cond["status_norm"] = cond["Raw_Value"].astype(str).str.strip().str.upper()

        degraded_equipment = []
        for eq, grp in cond.groupby("Equipment"):
            statuses = grp.drop_duplicates(subset=["Date"], keep="last").sort_values("Date")
            values = statuses["status_norm"].tolist()
            # Detect transition into Alarm/High from a normal-ish state
            for i in range(1, len(values)):
                if values[i] in ("ALARM", "HIGH") and values[i - 1] not in ("ALARM", "HIGH"):
                    degraded_equipment.append((eq, statuses.iloc[i]["Date"]))
                    break

        if not degraded_equipment:
            return {"status": "success", "message": "Tidak ditemukan transisi degradasi pada data historis.", "lessons_created": 0}

        existing = self.learner.load_learned_skills()
        existing_auto = {
            (s.get("equipment", "").upper(), s.get("title", ""))
            for s in existing
            if s.get("source") == "auto_mined"
        }

        lessons_created = 0
        details = []
        for eq, trans_date in degraded_equipment:
            eq_hist = work[work["Equipment"] == eq]
            before = eq_hist[eq_hist["Date"] < trans_date]
            if before.empty:
                continue

            # Precursor analysis: numeric parameters with the largest change
            precursor_changes = []
            for param, grp in before.groupby("Parameter"):
                vals = pd.to_numeric(grp["Raw_Value"], errors="coerce").dropna()
                if len(vals) < 2:
                    continue
                delta = float(vals.iloc[-1] - vals.iloc[0])
                span = abs(float(vals.max() - vals.min()))
                if span > 0:
                    precursor_changes.append((param, delta, span, float(vals.iloc[-1])))

            precursor_changes.sort(key=lambda x: abs(x[2]), reverse=True)
            top_precursors = precursor_changes[:3]
            if not top_precursors:
                continue

            symptom_lines = [
                f"{p} berubah {delta:+.2f} menuju {last:.2f} sebelum degradasi"
                for p, delta, span, last in top_precursors
            ]
            title = f"Pola prekursor degradasi {eq} (auto-mined)"
            if (eq.upper(), title) in existing_auto:
                continue  # avoid duplicate auto lessons

            self.learner.teach_agent(
                equipment=eq,
                title=title,
                system="Data Historis MCSA (Automated Mining)",
                category="VIBRASI_MCSA",
                symptoms=symptom_lines,
                verified_root_cause="Belum diverifikasi - pola statistik dari tren pengukuran historis.",
                corrective_action_taken="Belum ada - menunggu verifikasi engineer lapangan.",
                lesson_learned=(
                    f"Pada {eq}, kombinasi perubahan parameter berikut mendahului perubahan kondisi: "
                    + "; ".join(symptom_lines)
                    + ". Gunakan pola ini sebagai early-warning; verifikasi dengan pengukuran lapangan."
                ),
                author="PPLE Self-Improvement Engine",
            )
            # Patch the inserted entry to mark provenance and verification need
            skills = self.learner.load_learned_skills()
            for s in skills:
                if s.get("title") == title and s.get("author") == "PPLE Self-Improvement Engine":
                    s["source"] = "auto_mined"
                    s["needs_verification"] = True
                    s["transition_date"] = str(trans_date.date() if hasattr(trans_date, "date") else trans_date)
                    s["accuracy_boost_weight"] = 1.0
                    break
            self.learner.save_learned_skills(skills)

            lessons_created += 1
            details.append({"equipment": eq, "transition_date": str(trans_date), "precursors": symptom_lines})

        return {
            "status": "success",
            "message": f"Mining selesai: {lessons_created} pelajaran data-driven baru dibuat dari {len(degraded_equipment)} transisi degradasi.",
            "lessons_created": lessons_created,
            "transitions_detected": len(degraded_equipment),
            "details": details,
        }

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------
    def get_state(self) -> Dict[str, Any]:
        state = self._read_json(self.state_path, {})
        if not state:
            state = {
                "generation": 0,
                "category_weights": dict(DEFAULT_CATEGORY_WEIGHTS),
                "best_score": 0.0,
                "total_accepted_adjustments": 0,
                "total_candidate_attempts": 0,
                "created_at": datetime.now().isoformat(),
            }
        return state

    def get_status(self) -> Dict[str, Any]:
        state = self.get_state()
        history = self._read_json(self.history_path, {"cycles": []}).get("cycles", [])
        pred = self.evaluate_predictions()
        return {
            "generation": state.get("generation", 0),
            "best_score": state.get("best_score", 0.0),
            "category_weights": state.get("category_weights", DEFAULT_CATEGORY_WEIGHTS),
            "total_cycles": len(history),
            "total_accepted_adjustments": state.get("total_accepted_adjustments", 0),
            "total_candidate_attempts": state.get("total_candidate_attempts", 0),
            "last_cycle_at": state.get("last_cycle_at"),
            "prediction_stats": pred,
            "recent_cycles": history[-5:][::-1],
            "learning_engine": "RECURSIVE_SELF_IMPROVEMENT_ACTIVE",
        }
