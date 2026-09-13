"""
Multi-Agent Orchestrator and Specialist Sub-Agent Coordinator for Power Plant Predictive Maintenance.
Orchestrates domain sub-agents (Vibration, MCSA, DGA, PD, Tribology, Thermal, Fusion, Safety),
manages inter-agent communication, aggregates diagnostic evidence, and generates collaborative insights.
"""

from typing import Dict, Any, List, Optional
import time
from .fusion_engine import ReliabilityFusionAgent
from .safety_guard import SafetyGuardrailAgent
from .asset_graph import AssetKnowledgeGraph
from .continuous_learning import PowerPlantSkillLearner
from pple.engineering.equipment_modules import EquipmentModuleStore
from pple.engineering.registry import ModuleRegistry
from pple.engineering.modules.vibration import VibrationModule
from pple.engineering.modules.mcsa import MCSAModule
from pple.engineering.modules.dga import DGAModule
from pple.engineering.modules.partial_discharge import PartialDischargeModule
from pple.engineering.modules.tribology import TribologyModule
from pple.engineering.modules.thermal import ThermalModule


class SubAgentDescriptor:
    """Descriptor metadata for a specialist sub-agent."""
    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        domain: str,
        standards: List[str],
        icon: str,
        capabilities: List[str]
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.domain = domain
        self.standards = standards
        self.icon = icon
        self.capabilities = capabilities

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "domain": self.domain,
            "standards": self.standards,
            "icon": self.icon,
            "capabilities": self.capabilities,
            "status": "ONLINE"
        }


class SubAgentCoordinator:
    """
    Coordinates multi-agent delegation, domain analysis, evidence correlation,
    and consensus diagnostic synthesis.
    """
    def __init__(self):
        # Specialist domain evaluation is delegated to pple's EngineeringModule
        # registry (docs/final.md Phase 10) instead of instantiating each
        # specialist_agents.*Agent directly - see self._analyze().
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

        # Per-equipment module enable/disable overrides (docs/final.md Phase 8) -
        # gates the trace-building _analyze() calls below the same way
        # ReliabilityFusionAgent gates its own specialist_results.
        self.equipment_module_store = EquipmentModuleStore()

        self.fusion_agent = ReliabilityFusionAgent()
        self.safety_guard = SafetyGuardrailAgent()
        self.asset_graph = AssetKnowledgeGraph()
        self.skill_learner = PowerPlantSkillLearner()

        self._registry = {
            "vibration": SubAgentDescriptor(
                agent_id="subagent-vib-01",
                name="Vibration Specialist Agent",
                role="Mechanical FFT & ISO 10816 Diagnostics",
                domain="Vibration",
                standards=["ISO 10816-3", "ISO 13373-1", "VDI 2056"],
                icon="🌀",
                capabilities=[
                    "Overall RMS velocity evaluation (Zone A-D)",
                    "1X unbalance & 2X misalignment spectral peak detection",
                    "High-frequency bearing defect analysis (BPFO, BPFI, BSF, FTF)",
                    "Mechanical looseness and structural resonance detection"
                ]
            ),
            "mcsa": SubAgentDescriptor(
                agent_id="subagent-mcsa-01",
                name="Electrical MCSA Specialist Agent",
                role="Motor Current Signature & Stator/Rotor Health",
                domain="MCSA",
                standards=["IEEE 519", "EPRI MCSA Standards", "NEMA MG-1"],
                icon="⚡",
                capabilities=[
                    "Pole-pass sideband dB calculation (Severity Level 1-4)",
                    "Dynamic air-gap eccentricity evaluation",
                    "3-phase voltage & current unbalance percentage calculation",
                    "Total Harmonic Distortion (THD-V & THD-I) compliance monitoring"
                ]
            ),
            "dga": SubAgentDescriptor(
                agent_id="subagent-dga-01",
                name="DGA Transformer Specialist Agent",
                role="Dissolved Gas Analysis & Dielectric Fault Classification",
                domain="DGA",
                standards=["IEEE C57.104-2019", "IEC 60599", "Duval Triangle 1"],
                icon="🧪",
                capabilities=[
                    "Total Dissolved Combustible Gas (TDCG) calculation",
                    "Duval Triangle 1 coordinate mapping (%CH4, %C2H4, %C2H2)",
                    "Rogers Ratios & IEC 60599 gas ratio fault diagnostics",
                    "CO2/CO paper insulation thermal degradation assessment"
                ]
            ),
            "pd": SubAgentDescriptor(
                agent_id="subagent-pd-01",
                name="Partial Discharge (PD) Specialist Agent",
                role="High-Voltage Insulation & PRPD Pattern Recognition",
                domain="Partial Discharge",
                standards=["IEC 60270", "IEEE 1434", "CIGRE WG D1.33"],
                icon="💥",
                capabilities=[
                    "Phase-Resolved Partial Discharge (PRPD) clustering",
                    "Apparent charge pulse magnitude (pC) & NQN tracking",
                    "Classification of Corona, Surface, Slot, and Void discharges"
                ]
            ),
            "tribology": SubAgentDescriptor(
                agent_id="subagent-tribo-01",
                name="Tribology & Oil Specialist Agent",
                role="Lubricant Quality & Wear Debris Analysis",
                domain="Tribology",
                standards=["ASTM D445", "ASTM D6304", "ISO 4406:2021"],
                icon="🛢️",
                capabilities=[
                    "Kinematic viscosity 40°C deviation tracking",
                    "Total Acid Number (TAN) oxidation evaluation",
                    "Karl Fischer water content contamination monitoring (ppm)",
                    "Spectrometric wear debris analysis (Fe, Cu, Al) & ISO cleanliness"
                ]
            ),
            "thermal": SubAgentDescriptor(
                agent_id="subagent-therm-01",
                name="Thermal & Infrared Specialist Agent",
                role="Thermography Hotspot & Gradient Analysis",
                domain="Thermal",
                standards=["ISO 18434-1", "NFPA 70B", "NETA MTS"],
                icon="🌡️",
                capabilities=[
                    "Infrared thermography delta-T phase-to-phase evaluation",
                    "Bearing housing & stator RTD temperature limit monitoring",
                    "Electrical connection contact resistance hotspot localization"
                ]
            ),
            "fusion": SubAgentDescriptor(
                agent_id="subagent-fusion-01",
                name="Reliability Fusion & RUL Agent",
                role="Multi-Modal Evidence Correlator & Risk Engine",
                domain="Reliability Fusion",
                standards=["ISO 13374 (MIMOSA-OSA-CBM)", "MIL-STD-1629A (FMEA)"],
                icon="🔗",
                capabilities=[
                    "Consolidated Equipment Health Index (0-100) computation",
                    "Cross-sensor failure mode correlation & root cause confidence",
                    "Predictive Remaining Useful Life (RUL) & failure probability",
                    "Quantitative Operational Risk Index (5x5 matrix)",
                    "Automated CMMS / SAP Work Order generation"
                ]
            ),
            "safety": SubAgentDescriptor(
                agent_id="subagent-safety-01",
                name="Safety Guardrail & Compliance Agent",
                role="Human-in-the-Loop Verification & Safety Enforcement",
                domain="Safety Guardrail",
                standards=["PLN K3L Standards", "IEC 61508 Functional Safety"],
                icon="🛡️",
                capabilities=[
                    "High-risk command interception (Trip, Shutdown, Breaker Open)",
                    "CCR Chief Engineer authorization enforcement",
                    "Safety compliance validation on AI recommendations"
                ]
            )
        }

    def list_specialists(self) -> List[Dict[str, Any]]:
        """List all registered specialist sub-agents."""
        return [desc.to_dict() for desc in self._registry.values()]

    def identify_relevant_agents(self, query: str, asset_type: Optional[str] = None) -> List[str]:
        """
        Dynamically determine which sub-agents need to be activated for a query or equipment.
        """
        q_lower = query.lower()
        active_agents = set()

        # Keyword mapping to sub-agent domains
        if any(w in q_lower for w in ["vibrasi", "getaran", "vibration", "unbalance", "misalignment", "bearing", "looseness", "rms", "fft", "1x", "2x", "bpfo", "bpfi"]):
            active_agents.add("vibration")
        if any(w in q_lower for w in ["mcsa", "arus", "current", "tegangan", "voltage", "rotor", "rotorbar", "sideband", "thd", "power factor", "motor", "stator"]):
            active_agents.add("mcsa")
        if any(w in q_lower for w in ["dga", "trafo", "transformer", "gas", "h2", "ch4", "c2h2", "c2h4", "tdcg", "duval", "rogers", "uat", "sst"]):
            active_agents.add("dga")
        if any(w in q_lower for w in ["pd", "partial discharge", "peluahan", "insulasi", "insulation", "corona", "prpd", "tan delta"]):
            active_agents.add("pd")
        if any(w in q_lower for w in ["oli", "oil", "pelumas", "tribology", "tribologi", "viskositas", "viscosity", "tan", "water ppm", "keausan", "fe", "cu"]):
            active_agents.add("tribology")
        if any(w in q_lower for w in ["thermal", "suhu", "temperature", "panas", "hotspot", "inframerah", "infrared", "delta t", "rtd"]):
            active_agents.add("thermal")

        if asset_type and ("transformer" in asset_type.lower() or "trafo" in asset_type.lower()):
            active_agents.add("dga")

        # Context-based defaults if general reliability question
        if any(w in q_lower for w in ["kondisi", "status", "kesehatan", "health", "rusak", "anomali", "diagnosa", "evaluasi", "rekomendasi", "work order", "wo", "risk", "rul", "fusion", "semua"]):
            active_agents.update(["vibration", "mcsa", "tribology", "thermal", "fusion"])

        if not active_agents:
            active_agents = {"mcsa", "vibration", "fusion"}

        # Always include fusion when multi-domain is active
        if len(active_agents) > 1:
            active_agents.add("fusion")

        # Always include safety for review
        active_agents.add("safety")

        return list(active_agents)

    def _analyze(self, module_id: str, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run one domain evaluation through the pple EngineeringModule registry.

        Returns the same raw evaluation dict shape the legacy
        specialist_agents.*Agent.evaluate() calls used to return directly
        (condition, health_score, failure_mode, severity, confidence,
        evidence, recommendation, metrics) - LegacyAgentAdapterModule.analyze()
        passes it through unchanged, so this is not a behavior change.
        """
        module = self.module_registry.get(module_id)
        return module.analyze(data, {"equipment_id": equipment})

    def run_collaborative_diagnosis(
        self,
        equipment: str,
        query: str = "",
        custom_telemetry: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes a multi-agent collaborative diagnosis across specialist sub-agents.
        """
        start_time = time.time()
        node = self.asset_graph.get_equipment_node(equipment)
        asset_type = node.get("type", "Electric Motor-Driven Rotating Equipment")
        criticality = node.get("criticality", "B")

        # Safety Check first
        safety_res = self.safety_guard.check_safety(query or f"Diagnosa {equipment}")
        
        # Telemetry data unpacking
        data = custom_telemetry or {}
        # Missing modalities stay missing. Synthetic healthy baselines would
        # make an absent measurement indistinguishable from a real normal one.
        vib_data = data.get("vibration")
        mcsa_data = data.get("mcsa")
        dga_data = data.get("dga")
        pd_data = data.get("pd")
        oil_data = data.get("oil")
        thermal_data = data.get("thermal")

        if not dga_data:
            try:
                from src.dga_data import get_dga_transformer_detail
                trf_rec = get_dga_transformer_detail(equipment)
                if trf_rec:
                    dga_data = dict(trf_rec.get("gases", {}))
                    dga_data["tdcg"] = trf_rec.get("tdcg", trf_rec.get("diagnosis", {}).get("tdcg", 0))
                    dga_data["water_content"] = trf_rec.get("water_content", 0)
                    dga_data["bdv"] = trf_rec.get("bdv", 0)
                    dga_data["sampling_date"] = trf_rec.get("sampling_date", "")
                    dga_data["duval_diag"] = trf_rec.get("duval_diag", trf_rec.get("diagnosis", {}).get("duval_diagnosis", "Normal"))
                    if "transformer_id" in trf_rec:
                        dga_data["transformer_id"] = trf_rec["transformer_id"]
                    if asset_type == "Electric Motor-Driven Rotating Equipment":
                        asset_type = "Power Transformer"
            except Exception:
                pass

        # 1. Run Specialist Sub-Agents - a module disabled for this equipment
        # (EquipmentModuleStore, Phase 8) is left out of the trace entirely,
        # the same way ReliabilityFusionAgent excludes it from health weighting.
        traces = []
        store = self.equipment_module_store

        # Vibration Sub-Agent
        if vib_data and store.is_enabled(equipment, "vibration"):
            vib_eval = self._analyze("vibration", equipment, vib_data)
            traces.append({
                "subagent": self._registry["vibration"].to_dict(),
                "evaluation": vib_eval,
                "status": vib_eval.get("condition", "HEALTHY"),
                "health_score": vib_eval.get("health_score", 90.0),
                "key_finding": f"ISO 10816 RMS: {vib_data.get('overall_rms', 2.6)} mm/s | Failure Mode: {vib_eval.get('failure_mode')}"
            })

        # MCSA Sub-Agent
        if mcsa_data and store.is_enabled(equipment, "mcsa"):
            mcsa_eval = self._analyze("mcsa", equipment, mcsa_data)
            traces.append({
                "subagent": self._registry["mcsa"].to_dict(),
                "evaluation": mcsa_eval,
                "status": mcsa_eval.get("condition", "HEALTHY"),
                "health_score": mcsa_eval.get("health_score", 90.0),
                "key_finding": f"Upper SB: {mcsa_data.get('upper_sb', -56.0)} dB (Level {mcsa_eval.get('severity', 1)}) | Rotor Bar: {mcsa_eval.get('condition')}"
            })

        # Tribology Sub-Agent
        if oil_data and store.is_enabled(equipment, "tribology"):
            oil_eval = self._analyze("tribology", equipment, oil_data)
            traces.append({
                "subagent": self._registry["tribology"].to_dict(),
                "evaluation": oil_eval,
                "status": oil_eval.get("condition", "HEALTHY"),
                "health_score": oil_eval.get("health_score", 90.0),
                "key_finding": f"Viscosity: {oil_data.get('viscosity_40c', 46.0)} cSt | Wear Fe: {oil_data.get('fe_ppm', 12.0)} ppm"
            })

        # Thermal Sub-Agent
        if thermal_data and store.is_enabled(equipment, "thermal"):
            therm_eval = self._analyze("thermal", equipment, thermal_data)
            traces.append({
                "subagent": self._registry["thermal"].to_dict(),
                "evaluation": therm_eval,
                "status": therm_eval.get("condition", "HEALTHY"),
                "health_score": therm_eval.get("health_score", 90.0),
                "key_finding": f"Bearing Temp: {thermal_data.get('bearing_temp', 58.0)}°C | Delta-T: {thermal_data.get('delta_t_phase', 2.5)}°C"
            })

        # DGA Sub-Agent (for Transformers)
        is_trf = any(w in equipment.lower() for w in ["transformer", "trafo", "uat", "sst", "gt", "ash"]) or bool(dga_data)
        if dga_data and is_trf and store.is_enabled(equipment, "dga"):
            dga_eval = self._analyze("dga", equipment, dga_data)
            traces.append({
                "subagent": self._registry["dga"].to_dict(),
                "evaluation": dga_eval,
                "status": dga_eval.get("condition", "HEALTHY"),
                "health_score": dga_eval.get("health_score", 90.0),
                "key_finding": f"TDCG: {dga_data.get('tdcg', 0)} ppm | Duval: {dga_eval.get('failure_mode')} | Gas: H2={dga_data.get('H2', 0)}, CH4={dga_data.get('CH4', 0)}, C2H6={dga_data.get('C2H6', 0)}, C2H4={dga_data.get('C2H4', 0)}, C2H2={dga_data.get('C2H2', 0)}, CO={dga_data.get('CO', 0)}, CO2={dga_data.get('CO2', 0)} ppm, H2O={dga_data.get('water_content', 0)} ppm, BDV={dga_data.get('bdv', 0)} kV"
            })

        # 2. Run Reliability Fusion Sub-Agent
        fusion_eval = self.fusion_agent.run_full_fusion(
            equipment=equipment,
            asset_type=asset_type,
            criticality=criticality,
            vibration_data=vib_data,
            mcsa_data=mcsa_data,
            dga_data=dga_data,
            pd_data=pd_data,
            oil_data=oil_data,
            thermal_data=thermal_data
        )

        traces.append({
            "subagent": self._registry["fusion"].to_dict(),
            "evaluation": fusion_eval,
            "status": fusion_eval.get("health_status", "HEALTHY"),
            "health_score": fusion_eval.get("health_index", 90.0),
            "key_finding": f"Consolidated Health: {fusion_eval.get('health_index')}/100 | RUL: {fusion_eval.get('predictive_rul', {}).get('estimated_rul_days')} | Primary: {fusion_eval.get('failure_mode_diagnosis', {}).get('primary_failure_mode')}"
        })

        # 3. Safety Guard Sub-Agent Trace
        traces.append({
            "subagent": self._registry["safety"].to_dict(),
            "evaluation": safety_res,
            "status": "APPROVED" if safety_res.get("safe") else "BLOCKED",
            "health_score": 100.0 if safety_res.get("safe") else 0.0,
            "key_finding": "Operational Safety Clearance Verified (Human-in-the-Loop Active)" if safety_res.get("safe") else safety_res.get("message")
        })

        duration_ms = round((time.time() - start_time) * 1000, 1)

        # Query dynamically learned skills & disturbance case studies
        learned_skills = self.skill_learner.query_learned_knowledge(equipment, query)

        return {
            "equipment": equipment,
            "unit": node.get("unit", "UNIT 1"),
            "system": node.get("system", "General Plant"),
            "asset_type": asset_type,
            "criticality": criticality,
            "execution_duration_ms": duration_ms,
            "safety_clearance": safety_res.get("safe", True),
            "consensus_health_index": fusion_eval.get("health_index", 90.0),
            "consensus_health_status": fusion_eval.get("health_status", "HEALTHY"),
            "consensus_failure_mode": fusion_eval.get("failure_mode_diagnosis", {}).get("primary_failure_mode", "Normal Operation"),
            "consensus_confidence": fusion_eval.get("failure_mode_diagnosis", {}).get("confidence", 0.95),
            "fused_evidence": fusion_eval.get("failure_mode_diagnosis", {}).get("fused_evidence", []),
            "predictive_rul": fusion_eval.get("predictive_rul", {}),
            "risk_assessment": fusion_eval.get("risk_assessment", {}),
            "maintenance_decision": fusion_eval.get("maintenance_decision", {}),
            "active_subagents_count": len(traces),
            "subagent_traces": traces,
            "learned_skills_applied": learned_skills
        }
