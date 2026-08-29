"""
Power Plant Continuous Learning & Skill Improvement Engine.
Enables CBM and O&M AI agents to continuously learn from engineer feedback,
accumulate plant disturbance case studies, calibrate diagnostic accuracy,
and evolve domain skills across Power Plant Mechanical, Electrical, and Chemical domains.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime


DEFAULT_LEARNED_SKILLS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "data",
    "learning",
    "learned_skills.json"
)


# Default initial power plant disturbance lessons learned & fault signatures
DEFAULT_SEED_CASES = [
    {
        "id": "SKILL-PLTU-001",
        "title": "BFP 1A 1X Vibration Peak & Phase Current Unbalance",
        "equipment": "BFP 1A",
        "system": "Feedwater Auxiliary System (Boiler Feed Pump)",
        "category": "VIBRASI_MCSA",
        "symptoms": [
            "1X vibration peak tinggi (5.8 mm/s ISO Zone C)",
            "Deviasi arus fasa 4.8%",
            "Suhu bearing NDE naik ke 68°C"
        ],
        "verified_root_cause": "Kendornya baut pondasi pedestal NDE dan ketidaksejajaran kopling (angular misalignment 0.15 mm), bukan unbalance rotor.",
        "corrective_action_taken": "Re-torque baut pondasi ke 140 Nm, re-alignment kopling laser tolerance <0.05 mm, dan inspeksi pelumasan grease sintetis.",
        "lesson_learned": "Pada motor 6.3kV daya besar (>500 kW), getaran 1X tinggi yang disertai deviasi arus ringan sering kali disebabkan oleh pergeseran baseframe/pedestal pondasi dinamis daripada ketidakseimbangan massa murni.",
        "author": "Chief CBM Specialist PLTU Jeranjang",
        "verified_at": "2026-01-15",
        "accuracy_boost_weight": 1.2
    },
    {
        "id": "SKILL-PLTU-002",
        "title": "ID Fan 1#1 Vibration 1X Ash Buildup on Blades",
        "equipment": "ID Fan 1#1",
        "system": "Flue Gas & Draft System",
        "category": "VIBRASI",
        "symptoms": [
            "Vibrasi horizontal 1H dan 2H naik bertahap dari 2.2 mm/s ke 6.4 mm/s dalam 3 minggu",
            "Harmonik 1X dominan pada spektrum FFT"
        ],
        "verified_root_cause": "Penumpukan abu terbang batubara (fly ash accumulation) pada sudu-sudu impeller fan akibat kelembaban gas buang saat startup.",
        "corrective_action_taken": "Pembersihan kerak abu impeller (blade water wash) saat shutdown singkat dan balancing ulang in-situ (balancing bobot koreksi 120 gram).",
        "lesson_learned": "Kenaikan tren getaran 1X bertahap pada induced draft fan biasanya merupakan indikasi kuat akumulasi kerak fly ash pada sudu impeller, bukan kelonggaran bantalan.",
        "author": "Mechanical Maintenance Engineer",
        "verified_at": "2026-02-02",
        "accuracy_boost_weight": 1.15
    },
    {
        "id": "SKILL-PLTU-003",
        "title": "Motor BC 41 Pole-Pass Sideband -43 dB Rotor Bar Crack",
        "equipment": "BC 41",
        "system": "Coal Handling Conveyor System",
        "category": "MCSA_KELISTRIKAN",
        "symptoms": [
            "Upper Sideband dB -43.2 dB (Severity Level 3)",
            "Fluktuasi arus motor berkala pada beban 85%",
            "Getaran modulated pole-pass frequency 2sf"
        ],
        "verified_root_cause": "2 batang rotor bar retak (cracked rotor bars) di dekat end-ring akibat lonjakan torsi saat conveyor sering start-stop bermuatan penuh.",
        "corrective_action_taken": "Penggantian rotor cadangan (spare rotor swap) dan re-brazing rotor bar di bengkel spesialis kelistrikan.",
        "lesson_learned": "Conveyor motor yang mengalami start-stop berat rentan mengalami thermal fatigue pada sambungan rotor bar end-ring; sideband di atas -45 dB membutuhkan penggantian sebelum terjadi patah total.",
        "author": "Electrical Predictive Maintenance Engineer",
        "verified_at": "2026-02-10",
        "accuracy_boost_weight": 1.3
    },
    {
        "id": "SKILL-PLTU-004",
        "title": "Trafo Unit 1 C2H2 & C2H4 Spike (Duval Triangle T3 Thermal Fault)",
        "equipment": "Transformer Unit 1 (GSUT)",
        "system": "Main Power Transformer 150kV",
        "category": "DGA_TRAFO",
        "symptoms": [
            "TDCG naik ke 840 ppm (Condition 3 IEEE C57.104)",
            "Etilena C2H4 185 ppm, Asetilena C2H2 12 ppm",
            "Duval Triangle 1 koordinat jatuh di zona T3 (>700°C)"
        ],
        "verified_root_cause": "Hotspot termal pada koneksi selector switch tap changer (OLTC) internal akibat kontak resistansi tinggi.",
        "corrective_action_taken": "Pemeriksaan internal tank OLTC, penggantian fixed contacts dan moving contacts, serta sirkulasi purifikasi minyak trafo vacuum degassing.",
        "lesson_learned": "Kombinasi C2H4 dominan dengan sedikit C2H2 pada minyak trafo merupakan sidik jari pasti pemanasan lokal ekstrem (>700°C) pada kontak logam berbeban tinggi.",
        "author": "Transformer Specialist CBM",
        "verified_at": "2026-02-18",
        "accuracy_boost_weight": 1.25
    },
    {
        "id": "SKILL-PLTU-005",
        "title": "CWP 1A Lube Oil Water Contamination & Viscosity Drop",
        "equipment": "CWP 1A",
        "system": "Circulating Cooling Water System",
        "category": "TRIBOLOGI",
        "symptoms": [
            "Kandungan air Karl Fischer naik ke 450 ppm (Batas baku mutu < 100 ppm)",
            "Viskositas 40°C turun dari 46 cSt ke 39.5 cSt",
            "Kekeruhan oli meningkat (warna milky/susu)"
        ],
        "verified_root_cause": "Kerusakan mechanical seal & labyrinth seal shaft pompa CWP akibat gesekan kotoran air laut, menyebabkan rembesan uap air ke oil reservoir bearing.",
        "corrective_action_taken": "Penggantian mechanical seal set, flushing oil reservoir dengan oil purifier centrifuge, dan penggantian oli baru ISO VG 46.",
        "lesson_learned": "Penurunan viskositas disertai warna susu pada pompa sirkulasi pendingin adalah tanda pasti intrusi air pendingin melalui labyrinth seal; segera lakukan oil flushing untuk mencegah pitting bearing.",
        "author": "Lubrication & Tribology Analyst",
        "verified_at": "2026-02-22",
        "accuracy_boost_weight": 1.2
    }
]


# Power plant disturbance benchmark scenarios for accuracy testing
PLANT_BENCHMARKS = [
    {
        "benchmark_id": "BM-01",
        "title": "Motor Induction Rotor Bar Breakage Signature",
        "input": {"mcsa": {"upper_sb": -41.5, "lower_sb": -42.8}, "vibration": {"overall_rms": 3.1}},
        "expected_failure_mode": "Rotor Bar Degradation / Breakage",
        "expected_min_severity": 3
    },
    {
        "benchmark_id": "BM-02",
        "title": "High-Pressure BFP Severe Unbalance & Zone D Vibration",
        "input": {"vibration": {"overall_rms": 8.9, "amp_1x": 7.2}, "mcsa": {"upper_sb": -58.0}},
        "expected_failure_mode": "Severe Unbalance (Zone D)",
        "expected_min_severity": 4
    },
    {
        "benchmark_id": "BM-03",
        "title": "Transformer High-Temperature Thermal Fault (Duval Zone T3)",
        "input": {"dga": {"c2h4": 210.0, "c2h2": 15.0, "ch4": 90.0, "tdcg": 950.0}},
        "expected_failure_mode": "Thermal Fault >700°C",
        "expected_min_severity": 3
    },
    {
        "benchmark_id": "BM-04",
        "title": "Severe Lubricant Water Intrusion & Bearing Micro-Pitting",
        "input": {"oil": {"water_ppm": 620.0, "viscosity_40c": 38.0, "fe_ppm": 75.0}},
        "expected_failure_mode": "Lubricant Contamination & Severe Wear",
        "expected_min_severity": 3
    },
    {
        "benchmark_id": "BM-05",
        "title": "Electrical Stator Terminal Contact Hotspot (IRT Delta-T)",
        "input": {"thermal": {"delta_t_phase": 18.5, "bearing_temp": 62.0}},
        "expected_failure_mode": "Electrical Connection Hotspot",
        "expected_min_severity": 3
    }
]


class PowerPlantSkillLearner:
    """
    Manages continuous learning, historical case memory, dynamic skill updates,
    and diagnostic benchmark accuracy for the Power Plant AI Agent.
    """
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path or DEFAULT_LEARNED_SKILLS_PATH
        self._ensure_storage()

    def _ensure_storage(self):
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        if not os.path.exists(self.storage_path):
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({"skills": DEFAULT_SEED_CASES, "last_calibrated": datetime.now().isoformat()}, f, indent=2, ensure_ascii=False)

    def load_learned_skills(self) -> List[Dict[str, Any]]:
        """Load all learned disturbance patterns and case studies."""
        try:
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("skills", [])
        except Exception:
            return DEFAULT_SEED_CASES

    def save_learned_skills(self, skills: List[Dict[str, Any]]) -> bool:
        """Persist learned disturbance patterns to storage."""
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump({
                    "skills": skills,
                    "last_updated": datetime.now().isoformat(),
                    "total_skills_count": len(skills)
                }, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving skills: {e}")
            return False

    def teach_agent(
        self,
        equipment: str,
        title: str,
        system: str,
        category: str,
        symptoms: List[str],
        verified_root_cause: str,
        corrective_action_taken: str,
        lesson_learned: str,
        author: str = "CBM Engineer PLTU Jeranjang"
    ) -> Dict[str, Any]:
        """
        Teaches the agent a new verified failure signature or disturbance case study.
        """
        skills = self.load_learned_skills()
        new_id = f"SKILL-PLTU-{len(skills) + 1:03d}"
        
        new_entry = {
            "id": new_id,
            "title": title or f"Kasus Gangguan {equipment}",
            "equipment": equipment.upper(),
            "system": system or "General Plant Auxiliaries",
            "category": category.upper(),
            "symptoms": symptoms if isinstance(symptoms, list) else [str(symptoms)],
            "verified_root_cause": verified_root_cause,
            "corrective_action_taken": corrective_action_taken,
            "lesson_learned": lesson_learned,
            "author": author,
            "verified_at": datetime.now().strftime("%Y-%m-%d"),
            "accuracy_boost_weight": 1.25
        }

        # Insert at top
        skills.insert(0, new_entry)
        self.save_learned_skills(skills)

        return {
            "status": "success",
            "message": f"Skill pembelajaran {new_id} berhasil didaftarkan dan diintegrasikan ke memori AI!",
            "skill": new_entry,
            "total_learned_skills": len(skills)
        }

    def query_learned_knowledge(
        self,
        equipment: str,
        query: str = "",
        category_weights: Optional[Dict[str, float]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant learned cases matching the equipment or symptoms.

        When category_weights is provided, matches are re-ranked so that
        categories the self-improvement engine considers more reliable are
        boosted (tunable retrieval objective).
        """
        skills = self.load_learned_skills()
        eq_clean = equipment.lower().strip()
        q_clean = query.lower().strip()

        scored = []
        for s in skills:
            s_eq = s.get("equipment", "").lower()
            s_text = (
                s.get("title", "") + " " +
                s.get("system", "") + " " +
                s.get("verified_root_cause", "") + " " +
                s.get("lesson_learned", "") + " " +
                " ".join(s.get("symptoms", []) if isinstance(s.get("symptoms"), list) else [])
            ).lower()

            score = 0.0
            if eq_clean and (eq_clean in s_eq or s_eq in eq_clean):
                score += 2.0
            if q_clean:
                for w in q_clean.split():
                    if len(w) > 3 and w in s_text:
                        score += 0.5

            if score > 0:
                if category_weights:
                    cat = str(s.get("category", "")).upper()
                    score *= float(category_weights.get(cat, 1.0))
                scored.append((score, s))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return [s for _, s in scored[:4]]

        return skills[:2]

    def run_benchmarks(self) -> Dict[str, Any]:
        """
        Evaluates the agent against power plant disturbance benchmark scenarios
        using the REAL rule-based specialist agents (no simulation).
        """
        # Deferred import to avoid circular dependency with the self-improvement engine
        from src.agents.self_improvement import RecursiveSelfImprover

        engine = RecursiveSelfImprover(learner=self)
        real = engine.evaluate_benchmarks()

        results = []
        for r in real["benchmark_results"]:
            results.append({
                "benchmark_id": r["benchmark_id"],
                "title": r["title"],
                "status": r["status"],
                "expected": r["expected"],
                "observed_failure_mode": r["observed_failure_mode"],
                "observed_severity": r["observed_severity"],
                "evaluated_confidence": r["evaluated_confidence"],
                "domain": r["domain"],
                "severity_ok": r["severity_ok"],
                "failure_mode_precision_ok": r["failure_mode_precision_ok"],
                "domain_alignment": f"Rule-based evaluation via {r['domain'] or 'Specialist'} Agent (ISO/IEEE/ASTM)"
            })

        accuracy_score = real["diagnostic_score"]
        if accuracy_score >= 90.0:
            rating = "GRADE A - EXPERT SYSTEM"
        elif accuracy_score >= 75.0:
            rating = "GRADE B - PROFICIENT SYSTEM"
        else:
            rating = "GRADE C - NEEDS IMPROVEMENT"

        return {
            "total_benchmarks": real["total_benchmarks"],
            "passed_benchmarks": real["severity_pass_count"],
            "diagnostic_accuracy_score": accuracy_score,
            "failure_mode_precision": real["failure_mode_precision"],
            "weak_areas": real["weak_areas"],
            "rating": rating,
            "eval_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S WITA"),
            "benchmark_results": results,
            "evaluation_mode": "REAL_RULE_BASED"
        }

    def evaluate_env_harness(self) -> Dict[str, Any]:
        """
        Evaluates the agent's diagnostic pipeline against wrapped EnvHarness environments
        (Stage mutations, Contract constraints, Chain multi-step workflows).
        Based on 'EnvHarness: Awakening Static Worlds for Agent Learning' (Google 2026).
        """
        from src.agents.env_harness import EnvRigger, DiagnosticEnvironment

        rigger = EnvRigger()
        harness = rigger.active_harness

        benchmark_evals = []
        total_score = 0.0

        for bm in PLANT_BENCHMARKS:
            env = DiagnosticEnvironment(
                equipment=bm.get("benchmark_id", "PLANT-ASSET"),
                base_telemetry=bm.get("input", {}),
                expected_failure_mode=bm.get("expected_failure_mode", ""),
                expected_min_severity=bm.get("expected_min_severity", 3)
            )
            wrapped_env = harness.apply(env)
            rollout = rigger._default_subagent_policy(wrapped_env)

            success = rollout.get("success", False)
            if success:
                total_score += 20.0  # 5 benchmarks * 20 = 100 max

            benchmark_evals.append({
                "benchmark_id": bm.get("benchmark_id"),
                "title": bm.get("title"),
                "success": success,
                "steps": rollout.get("steps", 0),
                "safety_cleared": rollout.get("safety_cleared", False),
                "work_order": rollout.get("work_order") is not None,
                "diagnosis": rollout.get("diagnosis")
            })

        return {
            "harness_score": total_score,
            "total_benchmarks": len(PLANT_BENCHMARKS),
            "harness_components": harness.list_components(),
            "results": benchmark_evals,
            "status": "EVALUATED",
            "eval_timestamp": datetime.now().isoformat()
        }

    def run_env_rigger_learning(self, equipment: str = "BFP 1A") -> Dict[str, Any]:
        """
        Executes an EnvRigger cycle: Observe -> Diagnose -> Write -> Validate,
        and translates verified candidate insights into new persistent learned skills.
        """
        from src.agents.env_harness import EnvRigger

        rigger = EnvRigger()
        # Choose a relevant benchmark or telemetry
        selected_bm = PLANT_BENCHMARKS[0]
        for bm in PLANT_BENCHMARKS:
            if equipment.lower() in bm.get("title", "").lower():
                selected_bm = bm
                break

        cycle = rigger.run_rigger_cycle(
            equipment=equipment,
            base_telemetry=selected_bm.get("input", {}),
            expected_failure_mode=selected_bm.get("expected_failure_mode", "Rotor Bar Degradation"),
            expected_min_severity=selected_bm.get("expected_min_severity", 3)
        )

        # If accepted, convert wrapper insight into a persistent learned skill
        new_skill = None
        if cycle.get("stage_4_validate", {}).get("accepted"):
            write_info = cycle.get("stage_3_write", {})
            new_skill = self.teach_agent(
                equipment=equipment,
                title=f"EnvHarness Cultivated: {write_info.get('name', 'Dynamic Disturbance')}",
                system="Adaptive Disturbance & Operational Protection",
                category="VIBRASI_MCSA",
                symptoms=[f"Synthetic disturbance: {write_info.get('description', '')}"],
                verified_root_cause=f"Terverifikasi melalui EnvRigger rollout validation pada {equipment}.",
                corrective_action_taken="Penerbitan Work Order terencana dan mitigasi getaran/arus komposit.",
                lesson_learned=f"Penerapan kontrak {write_info.get('name')} berhasil melatih agent untuk mendeteksi kopling anomali lebih awal.",
                author="EnvRigger AI Customizer"
            )

        return {
            "rigger_cycle": cycle,
            "persisted_skill": new_skill,
            "status": "COMPLETED"
        }

