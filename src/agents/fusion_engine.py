"""
Multi-Modal Reliability Fusion Engine, Failure Mode Diagnoser, RUL Predictor,
Risk Engine, and Maintenance Decision Generator.
"""

from typing import Dict, Any, List, Optional
import math
from datetime import datetime, timedelta

from pple.engineering.registry import ModuleRegistry
from pple.engineering.modules.vibration import VibrationModule
from pple.engineering.modules.mcsa import MCSAModule
from pple.engineering.modules.dga import DGAModule
from pple.engineering.modules.partial_discharge import PartialDischargeModule
from pple.engineering.modules.tribology import TribologyModule
from pple.engineering.modules.thermal import ThermalModule


class FailureModeDiagnosisAgent:
    """
    Correlates multi-modal evidence across Vibration, MCSA, Tribology, Thermal, PD, and DGA
    to determine cross-validated root cause failure modes and high-confidence diagnostics.
    """
    def diagnose(self, specialist_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        vib = specialist_results.get("Vibration", {})
        mcsa = specialist_results.get("MCSA", {})
        oil = specialist_results.get("Tribology", {})
        thermal = specialist_results.get("Thermal", {})
        dga = specialist_results.get("DGA", {})
        pd = specialist_results.get("Partial Discharge", {})

        vib_mode = vib.get("failure_mode", "")
        mcsa_mode = mcsa.get("failure_mode", "")
        oil_mode = oil.get("failure_mode", "")
        thermal_mode = thermal.get("failure_mode", "")
        dga_mode = dga.get("failure_mode", "")
        pd_mode = pd.get("failure_mode", "")

        fused_evidence = []
        root_causes = []
        mitigations = []
        confidence = 0.80
        severity = max(
            vib.get("severity", 1),
            mcsa.get("severity", 1),
            oil.get("severity", 1),
            thermal.get("severity", 1),
            dga.get("severity", 1),
            pd.get("severity", 1)
        )

        primary_failure = "Normal Operation / In-Service Baseline"

        # 1. BEARING MULTI-MODAL FUSION RULE
        # Correlates: Vibration BPFO/BPFI + MCSA Bearing Sideband + Tribology Fe Debris + Thermal Bearing Temp
        bearing_evidence_count = 0
        if "Bearing" in vib_mode and vib.get("severity", 1) >= 2:
            bearing_evidence_count += 2
            fused_evidence.append(f"• Vibration: {vib_mode} ({vib.get('metrics', {}).get('bpfo_amp', 0):.2f} mm/s)")
        mcsa_evs = mcsa.get("evidence") or []
        if (mcsa_evs and any("Bearing" in str(e) for e in mcsa_evs)) or mcsa.get("metrics", {}).get("bearing_status") in ["Alarm", "High"]:
            bearing_evidence_count += 1
            fused_evidence.append("• MCSA: Fluktuasi air-gap frekuensi bearing terdeteksi pada spektrum arus")
        if "Bearing" in oil_mode or oil.get("metrics", {}).get("fe_ppm", 0) >= 35.0:
            bearing_evidence_count += 2
            fused_evidence.append(f"• Tribology: Partikel keausan besi (Fe) meningkat ({oil.get('metrics', {}).get('fe_ppm', 0):.1f} ppm)")
        if "Bearing" in thermal_mode or thermal.get("metrics", {}).get("bearing_temp_c", 0) >= 75.0:
            bearing_evidence_count += 1
            fused_evidence.append(f"• Thermal: Suhu bearing elevated ({thermal.get('metrics', {}).get('bearing_temp_c', 0):.1f}°C)")

        if bearing_evidence_count >= 3:
            primary_failure = "Rolling Element Bearing Outer/Inner Race Fatigue Degradation"
            confidence = min(0.95, 0.82 + (bearing_evidence_count * 0.03))
            severity = max(severity, 3)
            root_causes.extend([
                "Inadequate / degraded lubrication film (lubricant starvation)",
                "Subsurface fatigue cracking due to cyclic dynamic loading",
                "Contaminant particle abrasive indentation in bearing raceway"
            ])
            mitigations.extend([
                "Lakukan inspeksi visual dan getaran demodulasi frekuensi tinggi pada bearing DE/NDE dalam 72 jam",
                "Periksa kondisi gemuk/oli pelumas dan lakukan re-greasing dengan grease grade yang sesuai",
                "Siapkan suku cadang bearing pengganti untuk penggantian pada outage terencana terdekat"
            ])

        # 2. ROTOR BAR & END RING FUSION RULE
        elif "Rotor Bar" in mcsa_mode and mcsa.get("severity", 1) >= 2:
            primary_failure = mcsa_mode
            confidence = 0.92
            if mcsa_evs:
                fused_evidence.append(f"• MCSA: {mcsa_evs[0]}")
            if vib.get("severity", 1) >= 2:
                fused_evidence.append(f"• Vibration: Modulasi amplitudo 1X terdeteksi ({vib.get('metrics', {}).get('amp_1x', 0):.2f} mm/s)")
            root_causes.extend([
                "Thermal stress & fatigue cracking pada sambungan rotor bar ke end-ring",
                "Sering mengalami high-inertia starting cycle",
                "Pengecoran rotor bar yang berpori (casting porosity defect)"
            ])
            mitigations.extend([
                "Lakukan static motor testing (MCE / PdMA) untuk verifikasi rotor balance",
                "Batasi frekuensi start-stop berurutan pada motor"
            ])

        # 3. MISALIGNMENT / COUPLING FUSION RULE
        elif "Misalignment" in vib_mode and vib.get("severity", 1) >= 2:
            primary_failure = "Shaft Misalignment & Coupling Stress"
            confidence = 0.88
            fused_evidence.append(f"• Vibration: {vib.get('evidence', [''])[0]}")
            if thermal.get("metrics", {}).get("delta_t_phase_c", 0) > 10.0 or thermal.get("severity", 1) >= 2:
                fused_evidence.append(f"• Thermal: Peningkatan suhu coupling housing")
            root_causes.extend([
                "Penyimpangan kelurusan poros (angular / parallel misalignment)",
                "Thermal expansion growth yang tidak terkompensasi pada cold alignment",
                "Kelonggaran baut pondasi atau soft foot pada kaki motor/pompa"
            ])
            mitigations.extend([
                "Lakukan dial indicator / laser alignment check saat unit shutdown",
                "Periksa nilai soft foot dan kondisi shim pada baseplate"
            ])

        # 4. TRANSFORMER DGA + PD FUSION RULE
        elif "DGA" in specialist_results and dga.get("severity", 1) >= 2:
            primary_failure = dga_mode
            confidence = dga.get("confidence", 0.90)
            fused_evidence.extend(dga.get("evidence", []))
            if pd.get("severity", 1) >= 2:
                fused_evidence.append(f"• PD: Aktivitas peluahan parsial {pd_mode}")
                confidence = min(0.96, confidence + 0.05)
            root_causes.extend([
                "Pelepasan muatan listrik berenergi tinggi (electrical arcing)",
                "Overheating lokal pada inti/winding akibat eddy current atau sirkulasi arus",
                "Degradasi termal isolasi kertas dan minyak trafo"
            ])
            mitigations.extend([
                "Lakukan acoustic PD pin-pointing dan tes dissolved water & breakdown voltage",
                "Monitor laju kenaikan gas (rate of change ppm/day) secara berkala"
            ])

        # Default fallback
        if not fused_evidence:
            for s_name, res in specialist_results.items():
                if res.get("evidence"):
                    fused_evidence.extend([f"• {s_name}: {e}" for e in res.get("evidence", [])])
            if not mitigations:
                for s_name, res in specialist_results.items():
                    mitigations.extend(res.get("recommendation", []))

        return {
            "primary_failure_mode": primary_failure,
            "confidence": round(confidence, 2),
            "severity": severity,
            "fused_evidence": fused_evidence,
            "root_causes": root_causes if root_causes else ["Normal operation / wear within operational tolerance"],
            "mitigation_recommendations": mitigations[:4]
        }


class RULPredictor:
    """
    Predicts Remaining Useful Life (RUL in days) and 30-Day Failure Probability
    based on physics-of-failure degradation velocity and health score decay.
    """
    def predict(self, health_score: float, severity: int, degradation_rate_per_week: float = 1.2) -> Dict[str, Any]:
        # Health score: 0 to 100
        # If health is 100, RUL is high (> 365 days)
        # If health is 30, RUL is low (< 30 days)
        if health_score >= 90:
            rul_min = 180
            rul_max = 365
            prob_30d = 0.03
            window = "Normal Maintenance Schedule (> 6 months)"
        elif health_score >= 75:
            rul_min = 90
            rul_max = 180
            prob_30d = 0.12
            window = "Next Scheduled Minor Inspection (3–6 months)"
        elif health_score >= 60:
            rul_min = 45
            rul_max = 90
            prob_30d = 0.35
            window = "Planned Maintenance / Scheduled Outage (1–3 months)"
        elif health_score >= 40:
            rul_min = 14
            rul_max = 45
            prob_30d = 0.72
            window = "Targeted Outage / High Priority Inspection (2–6 weeks)"
        else:
            rul_min = 3
            rul_max = 14
            prob_30d = 0.94
            window = "Immediate Action Required / Controlled Shutdown (< 2 weeks)"

        return {
            "estimated_rul_days": f"{rul_min}–{rul_max} hari",
            "rul_min_days": rul_min,
            "rul_max_days": rul_max,
            "failure_probability_30d": round(prob_30d * 100.0, 1),
            "recommended_window": window,
            "degradation_trend": "Accelerating" if severity >= 3 else ("Linear" if severity == 2 else "Stable")
        }


class RiskEngine:
    """
    Calculates Quantitative Operational Risk Matrix:
    Risk Score = Failure Probability x Consequence x Asset Criticality
    """
    def calculate_risk(self, failure_prob_pct: float, asset_criticality: str = "A") -> Dict[str, Any]:
        # Criticality Weight: A (High Critical, e.g. BFP, CWP) = 1.0, B (Med, e.g. Fans) = 0.7, C (Low, e.g. Aux) = 0.4
        crit_map = {"A": 1.0, "B": 0.75, "C": 0.5, "HIGH": 1.0, "MEDIUM": 0.75, "LOW": 0.5}
        c_weight = crit_map.get(str(asset_criticality).upper(), 0.75)

        # Consequence factor (Production + Safety + Financial impact)
        consequence_score = 4 if c_weight >= 1.0 else (3 if c_weight >= 0.75 else 2)

        # Probability Level (1 to 5)
        if failure_prob_pct >= 80.0:
            prob_level = 5
            prob_label = "Very High"
        elif failure_prob_pct >= 50.0:
            prob_level = 4
            prob_label = "High"
        elif failure_prob_pct >= 25.0:
            prob_level = 3
            prob_label = "Medium"
        elif failure_prob_pct >= 10.0:
            prob_level = 2
            prob_label = "Low"
        else:
            prob_level = 1
            prob_label = "Very Low"

        # Risk Index = Prob x Consequence (1 to 20)
        risk_index = prob_level * consequence_score
        if risk_index >= 15:
            risk_level = "CRITICAL RISK"
            color = "#EF4444"
        elif risk_index >= 10:
            risk_level = "HIGH RISK"
            color = "#F59E0B"
        elif risk_index >= 6:
            risk_level = "MEDIUM RISK"
            color = "#3B82F6"
        else:
            risk_level = "LOW RISK"
            color = "#10B981"

        return {
            "risk_index": risk_index,
            "risk_level": risk_level,
            "risk_color": color,
            "probability_level": prob_level,
            "probability_label": prob_label,
            "consequence_score": consequence_score,
            "asset_criticality": asset_criticality,
            "safety_impact": "High (Rotating Machinery)" if c_weight >= 0.75 else "Low",
            "production_impact": f"{int(c_weight * 100)}% Unit Derating / Trip Risk",
            "financial_impact_category": "Major" if risk_index >= 12 else ("Moderate" if risk_index >= 6 else "Minor")
        }


class MaintenanceDecisionAgent:
    """
    Determines actionable maintenance strategy and auto-generates Work Order (WO) drafts.
    """
    def determine_decision(
        self,
        equipment: str,
        failure_mode: str,
        health_score: float,
        severity: int,
        risk_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        if severity >= 4 or health_score < 40.0:
            action = "IMMEDIATE SHUTDOWN / EMERGENCY REPAIR"
            priority = "P1 - Critical"
            target_days = 2
        elif severity == 3 or health_score < 60.0:
            action = "CORRECTIVE MAINTENANCE / TARGETED INSPECTION"
            priority = "P2 - High"
            target_days = 5
        elif severity == 2 or health_score < 75.0:
            action = "ENHANCED MONITORING & RETEST"
            priority = "P3 - Medium"
            target_days = 14
        else:
            action = "CONTINUE OPERATION (ROUTINE MONITORING)"
            priority = "P4 - Low"
            target_days = 30

        # Draft Work Order details
        wo_id = f"WO-{datetime.now().strftime('%Y%m')}-{abs(hash(equipment)) % 10000:04d}"
        tools = ["Vibration Data Collector & Accelerometer", "Infrared Thermal Camera", "Multimeter & Insulation Tester"]
        parts = ["Standard Bearing Set (DE/NDE)", "Gasket & O-Ring Kit", "Synthetic Grease / Lubricant ISO VG 46"]

        if "Rotor" in failure_mode:
            tools.append("Motor Circuit Evaluator (MCE)")
            parts.append("Rotor Bar Braze Alloy / Spare Rotor")
        elif "Oil" in failure_mode or "Lubrication" in failure_mode:
            tools.append("Oil Sampling Kit & Syringe")
            parts.append("Lube Oil Filter Cartridge")
        elif "DGA" in failure_mode or "Transformer" in failure_mode:
            tools.append("Syringe DGA Oil Sampling Kit")
            parts.append("Silica Gel Breather")

        return {
            "action_decision": action,
            "priority": priority,
            "work_order": {
                "wo_number": wo_id,
                "equipment": equipment,
                "title": f"Investigasi & Tindak Lanjut: {failure_mode}",
                "priority": priority,
                "reason": f"AI Multi-Modal Diagnostic: {failure_mode} (Health {health_score:.0f}/100, {risk_info.get('risk_level', 'Risk')})",
                "required_tools": tools,
                "required_parts": parts,
                "required_manpower": "2 Predictive Maintenance Technicians + 1 Mechanical Engineer",
                "target_completion_date": (datetime.now() + timedelta(days=target_days)).strftime("%Y-%m-%d"),
                "status": "Draft - Awaiting Engineer Approval"
            }
        }


class ReliabilityFusionAgent:
    """
    Main Multi-Modal Reliability Fusion Orchestrator.
    Gathers evidence from all specialist domains, computes Asset Health Index (0-100),
    runs Failure Mode Diagnosis, predicts RUL, calculates Risk, and prepares Maintenance WO.
    """
    def __init__(self):
        # Specialist domain evaluation is delegated to pple's EngineeringModule
        # registry (docs/final.md Phase 10), same as SubAgentCoordinator - see
        # self._analyze().
        self.module_registry = ModuleRegistry()
        for module_cls in (
            VibrationModule,
            MCSAModule,
            DGAModule,
            PartialDischargeModule,
            TribologyModule,
            ThermalModule,
        ):
            self.module_registry.register(module_cls())

        self.diagnosis_agent = FailureModeDiagnosisAgent()
        self.rul_predictor = RULPredictor()
        self.risk_engine = RiskEngine()
        self.decision_agent = MaintenanceDecisionAgent()

    def _analyze(self, module_id: str, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run one domain evaluation through the pple EngineeringModule registry.

        Returns the same raw evaluation dict shape the legacy
        specialist_agents.*Agent.evaluate() calls used to return directly -
        LegacyAgentAdapterModule.analyze() passes it through unchanged.
        """
        module = self.module_registry.get(module_id)
        return module.analyze(data, {"equipment_id": equipment})

    def run_full_fusion(
        self,
        equipment: str,
        asset_type: str = "Motor-Pump",
        criticality: str = "A",
        vibration_data: Optional[Dict[str, Any]] = None,
        mcsa_data: Optional[Dict[str, Any]] = None,
        dga_data: Optional[Dict[str, Any]] = None,
        pd_data: Optional[Dict[str, Any]] = None,
        oil_data: Optional[Dict[str, Any]] = None,
        thermal_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        specialist_results = {}
        health_weights = {}

        # 1. Run individual specialist evaluations
        if vibration_data is not None:
            specialist_results["Vibration"] = self._analyze("vibration", equipment, vibration_data)
            health_weights["Vibration"] = 0.28
        if mcsa_data is not None:
            specialist_results["MCSA"] = self._analyze("mcsa", equipment, mcsa_data)
            health_weights["MCSA"] = 0.28
        if thermal_data is not None:
            specialist_results["Thermal"] = self._analyze("thermal", equipment, thermal_data)
            health_weights["Thermal"] = 0.20
        if oil_data is not None:
            specialist_results["Tribology"] = self._analyze("tribology", equipment, oil_data)
            health_weights["Tribology"] = 0.14
        if dga_data is not None:
            specialist_results["DGA"] = self._analyze("dga", equipment, dga_data)
            health_weights["DGA"] = 0.35
        if pd_data is not None:
            specialist_results["Partial Discharge"] = self._analyze("partial_discharge", equipment, pd_data)
            health_weights["Partial Discharge"] = 0.25

        # If transformer asset, rebalance weights
        if "Transformer" in asset_type or "DGA" in specialist_results:
            health_weights = {"DGA": 0.50, "Partial Discharge": 0.30, "Thermal": 0.20}

        # 2. Compute Consolidated Asset Health Index (0 to 100)
        total_w = sum(health_weights.get(k, 0.2) for k in specialist_results.keys())
        if total_w > 0:
            weighted_health = sum(
                res["health_score"] * health_weights.get(k, 0.2)
                for k, res in specialist_results.items()
            ) / total_w
        else:
            weighted_health = 90.0

        health_index = round(weighted_health, 1)

        # Apply critical severity bounding (ISO 13374 / MIMOSA bottleneck rule)
        max_severity = max((res.get("severity", 1) for res in specialist_results.values()), default=1)
        if max_severity >= 4:
            health_index = min(health_index, 45.0)
        elif max_severity == 3:
            health_index = min(health_index, 65.0)

        # Health Classification
        if health_index >= 90.0:
            health_status = "HEALTHY"
            health_color = "#10B981"
        elif health_index >= 75.0:
            health_status = "WATCH"
            health_color = "#3B82F6"
        elif health_index >= 60.0:
            health_status = "WARNING"
            health_color = "#F59E0B"
        elif health_index >= 40.0:
            health_status = "ALERT"
            health_color = "#F97316"
        else:
            health_status = "CRITICAL"
            health_color = "#EF4444"

        # 3. Multi-Modal Failure Mode Diagnosis
        diagnosis = self.diagnosis_agent.diagnose(specialist_results)

        # 4. Remaining Useful Life (RUL) Prediction
        rul_info = self.rul_predictor.predict(health_index, diagnosis["severity"])

        # 5. Risk Calculation
        risk_info = self.risk_engine.calculate_risk(rul_info["failure_probability_30d"], criticality)

        # 6. Maintenance Decision & Work Order
        decision_info = self.decision_agent.determine_decision(
            equipment=equipment,
            failure_mode=diagnosis["primary_failure_mode"],
            health_score=health_index,
            severity=diagnosis["severity"],
            risk_info=risk_info
        )

        return {
            "equipment": equipment,
            "asset_type": asset_type,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "health_index": health_index,
            "health_status": health_status,
            "health_color": health_color,
            "specialist_evaluations": specialist_results,
            "failure_mode_diagnosis": diagnosis,
            "predictive_rul": rul_info,
            "risk_assessment": risk_info,
            "maintenance_decision": decision_info
        }
