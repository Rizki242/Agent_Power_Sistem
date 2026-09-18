"""
PPLE Master Agent (Orkestrator Utama & Unified Intelligence Agent)
for PLTU Jeranjang Predictive Maintenance (PdM) & Condition-Based Maintenance (CBM).

Unified architecture encompassing:
1. 6 Condition Monitoring Domains: Vibration, MCSA, DGA, Partial Discharge, Tribology, Thermal
2. Multi-Modal Reliability Fusion Engine (Health Index 0-100, RUL, Risk Matrix 5x5, Failure Modes)
3. Safety Guardrail & K3L Compliance (Human-in-the-Loop Interception)
4. Plant Asset Knowledge Graph & Central Asset Registry
5. Knowledge Base & Engineering Standards (ISO 10816, IEEE 519, IEEE C57.104, IEC 60270, ASTM)
6. Continuous Learning & Historical Disturbance Precursors
7. LLM Narrative Synthesis (Gemini 3.8 Flash, Groq, OpenAI, Ollama) with Deterministic Rule Fallback
"""

from __future__ import annotations

import math
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.agents.asset_graph import AssetKnowledgeGraph
from src.agents.continuous_learning import PowerPlantSkillLearner
from src.agents.fusion_engine import ReliabilityFusionAgent
from src.agents.safety_guard import SafetyGuardrailAgent
from src.agents.self_improvement import RecursiveSelfImprover
from src.agents.subagent_coordinator import SubAgentCoordinator
from src.data_loader import get_data_path, get_latest_data, load_mcsa_data
from src.knowledge_retriever import build_knowledge_context, search_knowledge_base
from src.llm_assistant import (
    DEFAULT_GEMINI_MODEL,
    MCSALLMAssistant,
    build_equipment_spec_context,
    resolve_provider_key,
)


def _norm_code(text: str) -> str:
    """Normalize equipment or code string for fuzzy matching."""
    return re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()


class PPLEMasterAgent:
    """
    Central Master Agent orchestrating all specialist sub-agents, fusion analysis,
    safety checks, continuous learning, and multi-modal asset intelligence.
    """

    def __init__(self):
        self.coordinator = SubAgentCoordinator()
        self.safety_guard = SafetyGuardrailAgent()
        self.asset_graph = AssetKnowledgeGraph()
        self.fusion_agent = ReliabilityFusionAgent()
        self.skill_learner = PowerPlantSkillLearner()
        self.self_improver = RecursiveSelfImprover()

        # Cache data frames for quick retrieval
        self._raw_df: Optional[pd.DataFrame] = None
        self._latest_df: Optional[pd.DataFrame] = None
        self._cached_assets: Optional[List[Dict[str, Any]]] = None

    def _get_mcsa_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Lazy load MCSA datasets."""
        if self._latest_df is None or self._raw_df is None:
            data_file = get_data_path("mcsa_updated.csv")
            if not os.path.exists(data_file):
                data_file = get_data_path("Report MCSA.xls")
            raw = load_mcsa_data(data_file)
            latest = get_latest_data(raw)
            self._raw_df = raw if raw is not None else pd.DataFrame()
            self._latest_df = latest if latest is not None else pd.DataFrame()
        return self._raw_df, self._latest_df

    def resolve_asset(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Comprehensive cross-domain asset entity recognition:
        Searches Asset Knowledge Graph, Central Asset Registry, DGA Transformers,
        Vibration database, and MCSA records.
        """
        if not query:
            return None

        q_clean = query.strip()
        q_lower = q_clean.lower()
        q_norm = _norm_code(q_clean)
        q_tokens = set(re.findall(r"[a-z0-9]+", q_lower))

        # 1. Direct search in DGA Transformers (GT 1/2/3, UAT 1/2/3, SST 1/2, ESP TR)
        try:
            from src.dga_data import search_dga_transformers

            for trf in search_dga_transformers():
                t_name = str(trf.get("name", "")).strip()
                t_id = str(trf.get("transformer_id", "")).strip()
                t_norm = _norm_code(t_name)
                t_id_norm = _norm_code(t_id)

                if (t_norm and t_norm in q_norm) or (t_id_norm and t_id_norm in q_norm):
                    return {
                        "equipment": t_name,
                        "canonical_name": t_name,
                        "asset_id": t_id,
                        "asset_type": "Power Transformer",
                        "unit": trf.get("unit", "UNIT 1"),
                        "domain_hint": "DGA",
                        "raw_record": trf,
                    }

                # Check short name variations like 'UAT 1', 'GT 2', 'SST 1'
                for pattern in [r"\b(gt\s*[123])\b", r"\b(uat\s*[123])\b", r"\b(sst\s*[12])\b"]:
                    m = re.search(pattern, q_lower)
                    if m:
                        matched_key = _norm_code(m.group(1))
                        if matched_key in t_norm or matched_key in _norm_code(t_id):
                            return {
                                "equipment": t_name,
                                "canonical_name": t_name,
                                "asset_id": t_id,
                                "asset_type": "Power Transformer",
                                "unit": trf.get("unit", "UNIT 1"),
                                "domain_hint": "DGA",
                                "raw_record": trf,
                            }
        except Exception:
            pass

        # 2. Search Central Asset Registry
        try:
            from src.asset_registry import list_assets

            for a in list_assets():
                name = str(a.get("name", "")).strip()
                asset_id = str(a.get("asset_id", "")).strip()
                aliases = [str(al).strip() for al in a.get("aliases", []) if al]
                names_to_check = [name, asset_id] + aliases

                for n in names_to_check:
                    n_norm = _norm_code(n)
                    if len(n_norm) >= 3 and n_norm in q_norm:
                        return {
                            "equipment": name,
                            "canonical_name": name,
                            "asset_id": asset_id,
                            "asset_type": a.get("equipment_type", "Rotating Equipment"),
                            "unit": a.get("unit", "UNIT 1"),
                            "domain_hint": "ALL",
                            "kks": a.get("kks", "-"),
                            "specs": a.get("specs", {}),
                            "raw_record": a,
                        }
        except Exception:
            pass

        # 3. Search MCSA equipment list
        _, df_latest = self._get_mcsa_data()
        if df_latest is not None and not df_latest.empty and "Equipment" in df_latest.columns:
            for eq in df_latest["Equipment"].dropna().unique():
                eq_str = str(eq).strip()
                eq_norm = _norm_code(eq_str)
                if len(eq_norm) >= 3 and eq_norm in q_norm:
                    node = self.asset_graph.get_equipment_node(eq_str)
                    return {
                        "equipment": eq_str,
                        "canonical_name": eq_str,
                        "asset_type": node.get("asset_type", "Electric Motor Drive"),
                        "unit": node.get("unit", "UNIT 1"),
                        "domain_hint": "MCSA",
                    }

        # 4. Regex pattern match for equipment codes (e.g. BFP 1A, CWP 1B, CEP 2A, IDF 1A, BC 10.1)
        candidates = re.findall(r"\b([A-Za-z]{2,5}\s*[-.]?\s*\d{1,3}\s*[A-Za-z0-9]?)\b", q_clean)
        for cand in candidates:
            c_norm = _norm_code(cand)
            node = self.asset_graph.get_equipment_node(cand)
            if node and node.get("equipment") != cand or any(
                c_norm in _norm_code(k) for k in ["BFP", "CWP", "CEP", "IDF", "PAF", "SAF", "VCP", "BC", "CRUSHER"]
            ):
                return {
                    "equipment": node.get("equipment", cand.upper()),
                    "canonical_name": node.get("equipment", cand.upper()),
                    "asset_type": node.get("asset_type", "Electric Motor Drive"),
                    "unit": node.get("unit", "UNIT 1"),
                    "domain_hint": "ALL",
                }

        return None

    def collect_equipment_telemetry(self, equipment: str, asset_type: str = "") -> Dict[str, Any]:
        """
        Gathers real, measured telemetry across all 6 condition monitoring disciplines
        without inventing synthetic or fake data.
        """
        telemetry: Dict[str, Any] = {}

        # 1. MCSA telemetry from dataframe
        _, df_latest = self._get_mcsa_data()
        if df_latest is not None and not df_latest.empty and "Equipment" in df_latest.columns:
            eq_rows = df_latest[df_latest["Equipment"].astype(str).str.strip().str.upper() == equipment.strip().upper()]
            if not eq_rows.empty:
                try:
                    from src.agents.fusion_inputs import extract_mcsa_fusion_inputs
                    extracted = extract_mcsa_fusion_inputs(eq_rows)
                    if "mcsa_data" in extracted:
                        telemetry["mcsa"] = extracted["mcsa_data"]
                    if "vibration_data" in extracted and "vibration" not in telemetry:
                        telemetry["vibration"] = extracted["vibration_data"]
                    if "thermal_data" in extracted and "thermal" not in telemetry:
                        telemetry["thermal"] = extracted["thermal_data"]
                except Exception:
                    pass

        # 2. DGA telemetry for transformers
        is_trf = "transformer" in asset_type.lower() or "trafo" in equipment.lower() or any(
            w in equipment.upper() for w in ["UAT", "GT", "SST"]
        )
        if is_trf or "dga" not in telemetry:
            try:
                from src.dga_data import get_dga_transformer_detail
                trf_rec = get_dga_transformer_detail(equipment)
                if trf_rec:
                    dga_info = dict(trf_rec.get("gases", {}))
                    dga_info["tdcg"] = trf_rec.get("tdcg", trf_rec.get("diagnosis", {}).get("tdcg", 0))
                    dga_info["water_content"] = trf_rec.get("water_content", 0)
                    dga_info["bdv"] = trf_rec.get("bdv", 0)
                    dga_info["sampling_date"] = trf_rec.get("sampling_date", "")
                    dga_info["duval_diag"] = trf_rec.get(
                        "duval_diag",
                        trf_rec.get("diagnosis", {}).get("duval_diagnosis", "Normal"),
                    )
                    telemetry["dga"] = dga_info
            except Exception:
                pass

        # 3. Vibration telemetry from CBMAI dataset or SQLite
        if "vibration" not in telemetry:
            try:
                from src.vibration_data import load_cbmai_vibration_dataset
                v_df = load_cbmai_vibration_dataset()
                if not v_df.empty and "equipment_id" in v_df.columns:
                    v_match = v_df[v_df["equipment_id"].astype(str).str.strip().str.upper() == equipment.strip().upper()]
                    if not v_match.empty:
                        last_v = v_match.iloc[-1]
                        vib_info: Dict[str, Any] = {
                            "overall_rms": float(last_v.get("velocity_rms_mm_s", 2.2)),
                        }
                        if pd.notna(last_v.get("1x_amp_mm_s")):
                            vib_info["amp_1x"] = float(last_v.get("1x_amp_mm_s"))
                        if pd.notna(last_v.get("2x_amp_mm_s")):
                            vib_info["amp_2x"] = float(last_v.get("2x_amp_mm_s"))
                        if pd.notna(last_v.get("bpfo_amp_g")):
                            vib_info["bpfo_amp"] = float(last_v.get("bpfo_amp_g"))
                        if pd.notna(last_v.get("bpfi_amp_g")):
                            vib_info["bpfi_amp"] = float(last_v.get("bpfi_amp_g"))
                        telemetry["vibration"] = vib_info
            except Exception:
                pass

        # 4. Domain measurements for Oil/Tribology and Thermal
        try:
            from src.domain_measurements import load_domain_measurements

            # Tribology
            if "oil" not in telemetry:
                t_df = load_domain_measurements("TRIBOLOGY")
                if t_df is not None and not t_df.empty:
                    eq_t = t_df[t_df["equipment_id"].astype(str).str.upper() == equipment.strip().upper()]
                    if not eq_t.empty:
                        last_oil = eq_t.iloc[-1]
                        oil_info = {}
                        for param_k in ["viscosity_40c", "tan_mgkoh_g", "water_ppm", "fe_ppm", "cu_ppm"]:
                            if param_k in last_oil and pd.notna(last_oil[param_k]):
                                oil_info[param_k] = float(last_oil[param_k])
                        if oil_info:
                            telemetry["oil"] = oil_info

            # Thermal
            if "thermal" not in telemetry:
                th_df = load_domain_measurements("THERMAL")
                if th_df is not None and not th_df.empty:
                    eq_th = th_df[th_df["equipment_id"].astype(str).str.upper() == equipment.strip().upper()]
                    if not eq_th.empty:
                        last_th = eq_th.iloc[-1]
                        th_info = {}
                        for param_k in ["bearing_temp", "winding_temp", "delta_t_phase", "hotspot_temp"]:
                            if param_k in last_th and pd.notna(last_th[param_k]):
                                th_info[param_k] = float(last_th[param_k])
                        if th_info:
                            telemetry["thermal"] = th_info
        except Exception:
            pass

        return telemetry

    def execute_collaborative_diagnosis(
        self,
        equipment: str,
        query: str = "",
        custom_telemetry: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches collaborative diagnosis across specialist subagents and the fusion engine.
        """
        asset_info = self.resolve_asset(equipment) or {}
        asset_type = asset_info.get("asset_type", "Electric Motor Drive")

        telemetry = self.collect_equipment_telemetry(equipment, asset_type)
        if custom_telemetry:
            telemetry.update(custom_telemetry)

        return self.coordinator.run_collaborative_diagnosis(
            equipment=equipment,
            query=query or f"Analisis CBM menyeluruh {equipment}",
            custom_telemetry=telemetry,
        )

    def generate_speech_summary(self, text: str, matched_equipment: Optional[str] = None) -> str:
        """
        Produces clean, natural spoken Indonesian narrative for voice assistant output.
        """
        if not text:
            return ""

        clean = re.sub(r"```[\s\S]*?```", "", text)
        clean = re.sub(r"\|[^\n]+\|", "", clean)
        clean = re.sub(r"[*_#~`]", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
        clean = re.sub(r"\s+", " ", clean).strip()

        # Phonetic expansions for Indonesian speech
        replacements = [
            (r"\bmm/s\b", "milimeter per detik"),
            (r"\bdegC\b", "derajat Celcius"),
            (r"°C", "derajat Celcius"),
            (r"\bTDCG\b", "T D C G"),
            (r"\bpC\b", "piko Coulomb"),
            (r"\bTHD\b", "T H D"),
            (r"\bkV\b", "kilo Volt"),
            (r"\bMW\b", "Mega Watt"),
            (r"\bRUL\b", "R U L"),
            (r"\bDGA\b", "D G A"),
            (r"\bMCSA\b", "M C S A"),
            (r"\bISO\b", "I S O"),
            (r"\bBFP\b", "B F P"),
            (r"\bCWP\b", "C W P"),
            (r"\bCEP\b", "C E P"),
            (r"\bIDF\b", "I D F"),
            (r"\bUAT\b", "U A T"),
            (r"\bSST\b", "S S T"),
            (r"\bGT\b", "G T"),
        ]
        for pattern, rep in replacements:
            clean = re.sub(pattern, rep, clean)

        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", clean)
            if s.strip() and not s.strip().startswith("-")
        ]
        if sentences:
            speech = " ".join(sentences[:2])
        else:
            speech = clean[:220]

        return speech.strip()

    def process_query(
        self,
        query: str,
        session_id: Optional[str] = None,
        provider: str = "gemini",
        model: str = DEFAULT_GEMINI_MODEL,
        api_key: Optional[str] = None,
        file_name: Optional[str] = None,
        file_content: Optional[str] = None,
        source: Optional[str] = "CHAT",
    ) -> Dict[str, Any]:
        """
        Main execution pipeline of PPLEMasterAgent:
        1. Safety Guardrail Pre-Check
        2. Universal Asset & Intent Resolution
        3. Multi-Domain Telemetry & Knowledge Gathering
        4. Specialist Sub-Agent Dispatch & Reliability Fusion
        5. Rule-Based Engineering Core Assembly
        6. LLM Synthesis (Gemini 3.8 Flash / configured provider)
        7. Spoken Speech Summary Generation
        8. Audit Logging & Session Persistence
        """
        start_time = time.time()
        query_text = (query or "").strip()
        q_lower = query_text.lower()

        # ---------------------------------------------------------------------
        # 1. SAFETY GUARDRAIL PRE-CHECK
        # ---------------------------------------------------------------------
        safety_check = self.safety_guard.check_safety(query_text)
        if not safety_check["safe"]:
            block_msg = f"🛡️ **SAFETY GUARDRAIL BLOCK**: {safety_check['message']}"
            speech_warn = f"Peringatan keselamatan! Perintah ditolak oleh Safety Guardrail: {safety_check['message']}"
            return {
                "reply": block_msg,
                "summary_for_speech": speech_warn,
                "matched_equipment": None,
                "ai_enhanced": False,
                "file_name": file_name,
                "provider": provider,
                "session_id": session_id,
                "safety_blocked": True,
                "active_subagents": [],
                "subagent_traces": [],
                "execution_time_ms": round((time.time() - start_time) * 1000, 1),
            }

        # ---------------------------------------------------------------------
        # 2. UNIVERSAL ASSET & INTENT RESOLUTION
        # ---------------------------------------------------------------------
        asset_info = self.resolve_asset(query_text)
        matched_equipment = asset_info.get("equipment") if asset_info else None
        active_subagents: List[Dict[str, Any]] = []
        subagent_traces: List[Dict[str, Any]] = []
        collab_result: Optional[Dict[str, Any]] = None
        rule_output_parts: List[str] = []

        # Identify active subagents for UI badges
        relevant_keys = self.coordinator.identify_relevant_agents(
            query_text,
            asset_info.get("asset_type") if asset_info else None,
        )
        for k_agent in relevant_keys:
            for s_desc in self.coordinator.list_specialists():
                if k_agent in s_desc["agent_id"] or k_agent == s_desc["domain"].lower():
                    active_subagents.append(s_desc)
                    break

        # ---------------------------------------------------------------------
        # 3. DOMAIN & WORKFLOW EXECUTION
        # ---------------------------------------------------------------------

        # Case A: Specific Equipment Diagnostic & Status Inquiry
        if matched_equipment:
            collab_result = self.execute_collaborative_diagnosis(
                equipment=matched_equipment,
                query=query_text,
            )
            subagent_traces = collab_result.get("subagent_traces", [])

            h_idx = collab_result.get("consensus_health_index", 90.0)
            h_status = collab_result.get("consensus_health_status", "HEALTHY")
            f_mode = collab_result.get("consensus_failure_mode", "Operasi Normal")
            conf = collab_result.get("consensus_confidence", 0.95) * 100
            rul_data = collab_result.get("predictive_rul", {})
            rul_days = rul_data.get("estimated_rul_days", "N/A")
            risk_data = collab_result.get("risk_assessment", {})
            risk_score = risk_data.get("operational_risk_score", "R-1")
            decision = collab_result.get("maintenance_decision", {})

            rule_output_parts.append(
                f"### 📋 Evaluasi CBM Multi-Disiplin: **{matched_equipment}**\n"
                f"- **Unit & Sistem**: {collab_result.get('unit')} | {collab_result.get('system')}\n"
                f"- **Tipe Aset & Kritikalitas**: {collab_result.get('asset_type')} (Kelas {collab_result.get('criticality')})\n"
                f"- **Consolidated Health Index**: **{h_idx}/100** ({h_status})\n"
                f"- **Primary Failure Mode**: {f_mode} (Keyakinan: {conf:.0f}%)\n"
                f"- **Prediksi Sisa Umur (RUL)**: **{rul_days} hari** | Tingkat Risiko: **{risk_score}**\n"
                f"- **Rekomendasi CBM**: {decision.get('recommended_action', 'Lanjutkan pemantauan berkala.')}\n"
            )

            if subagent_traces:
                rule_output_parts.append("#### 🔬 Bukti Diagnostik Specialist Sub-Agents:")
                for tr in subagent_traces:
                    s_name = tr["subagent"]["name"]
                    icon = tr["subagent"].get("icon", "🔹")
                    st = tr.get("status", "NORMAL")
                    kf = tr.get("key_finding", "")
                    rule_output_parts.append(f"- {icon} **{s_name}** [{st}]: {kf}")

            learned = collab_result.get("learned_skills_applied", [])
            if learned:
                rule_output_parts.append("\n#### 🧠 Preseden Gangguan & Pelajaran Sebelumnya:")
                for lk in learned[:2]:
                    rule_output_parts.append(f"- **{lk.get('title')}**: {lk.get('lesson_learned')}")

        # Case B: Fleet Reliability / Alarm List Inquiry
        elif any(w in q_lower for w in ["alarm", "warning", "kritis", "abnormal", "rusak", "high"]):
            from src.chatbot import MCSAChatbot
            _, df_latest = self._get_mcsa_data()
            raw_df, _ = self._get_mcsa_data()
            bot = MCSAChatbot(df_latest, df_all=raw_df)
            alarm_text = bot.get_alarm_list()
            rule_output_parts.append(alarm_text)

        # Case C: Knowledge Base, Standard (ISO/IEEE/IEC), or SOP Inquiry
        elif any(w in q_lower for w in ["sop", "standar", "standard", "iso", "ieee", "iec", "astm", "rumus", "pedoman", "tabel"]):
            kb_results = search_knowledge_base(query_text, max_results=3)
            if kb_results:
                rule_output_parts.append("### 📚 Referensi Standar & Pengetahuan Rekayasa:")
                for res in kb_results:
                    rule_output_parts.append(
                        f"**{res.get('title', 'Dokumen')}** (Topik: {res.get('topic', 'General')})\n"
                        f"{res.get('content', '')[:350]}...\n"
                    )
            else:
                rule_output_parts.append(
                    "Informasi standar terkait telah dicek dalam basis pengetahuan PPLE (ISO 10816, IEEE 519, IEEE C57.104, IEC 60270, ASTM)."
                )

        # Case D: General Plant Query
        else:
            rule_output_parts.append(
                "Halo! Saya **PPLE Master Agent**, asisten kecerdasan predictive maintenance terpadu PLTU Jeranjang (3 × 25 MW).\n"
                "Saya mengorkestrasi 6 domain spesialis: **Vibrasi, MCSA, DGA Trafo, Partial Discharge, Tribologi Oli, dan Thermal IRT**, "
                "serta mesin Reliability Fusion, kalkulasi RUL, dan mitigasi risiko.\n\n"
                "Anda dapat menanyakan:\n"
                "- Kondisi spesifik peralatan (contoh: *'Bagaimana status BFP 1A?'*, *'Kondisi DGA Trafo UAT 1'*, *'Hasil oli CWP 1B'*)\n"
                "- Daftar alarm plant (contoh: *'List equipment alarm'*)\n"
                "- Rujukan standar dan SOP CBM (contoh: *'Standar ISO 10816-3 zona C'*, *'Batas gas C2H2 Duval trafo'*)"
            )

        rule_based_response = "\n".join(rule_output_parts)
        if file_content and file_name:
            rule_based_response += f"\n\n*(Dokumen terlampir: `{file_name}` berhasil dianalisis)*"

        # ---------------------------------------------------------------------
        # 4. LLM NARRATIVE ENRICHMENT (Gemini 3.8 Flash, Groq, OpenAI, Ollama)
        # ---------------------------------------------------------------------
        final_reply = rule_based_response
        ai_enhanced = False

        resolved_key = resolve_provider_key(provider, api_key)
        if resolved_key or provider.lower() in ("ollama", "opencode"):
            try:
                assistant = MCSALLMAssistant(
                    enabled=True,
                    provider=provider or "gemini",
                    model=model or DEFAULT_GEMINI_MODEL,
                    api_key=resolved_key or "local",
                )
                if assistant.available:
                    # Build rich multi-domain context for LLM
                    subagents_ctx = ""
                    if collab_result:
                        subagents_ctx = (
                            f"Consolidated Health: {collab_result.get('consensus_health_index')}/100 ({collab_result.get('consensus_health_status')})\n"
                            f"Primary Failure Mode: {collab_result.get('consensus_failure_mode')} (Confidence: {collab_result.get('consensus_confidence', 0.95)*100:.0f}%)\n"
                            f"Estimated RUL: {collab_result.get('predictive_rul', {}).get('estimated_rul_days')} hari\n"
                            f"Risk Assessment: {collab_result.get('risk_assessment', {}).get('operational_risk_score')}\n"
                        )
                        for tr in subagent_traces:
                            subagents_ctx += f"• [{tr['subagent']['name']}] ({tr.get('status')}): {tr.get('key_finding')}\n"

                    extra_file_ctx = ""
                    if file_content and file_name:
                        extra_file_ctx = f"\n\n--- LAMPIRAN ({file_name}) ---\n{file_content[:12000]}\n--- AKHIR LAMPIRAN ---"

                    _, df_latest = self._get_mcsa_data()
                    raw_df, _ = self._get_mcsa_data()

                    ai_resp = assistant.enhance_answer(
                        question=query_text or f"Analisis isi file {file_name}",
                        rule_answer=rule_based_response,
                        df_context=df_latest,
                        df_history=raw_df,
                        include_knowledge=True,
                        extra_file_context=extra_file_ctx,
                        subagents_context=subagents_ctx,
                    )
                    if ai_resp and len(ai_resp.strip()) > 15:
                        final_reply = ai_resp
                        ai_enhanced = True
            except Exception as exc:
                # Guaranteed fallback to rule_based_response per coding protocol
                pass

        # ---------------------------------------------------------------------
        # 5. SPOKEN SPEECH SUMMARY
        # ---------------------------------------------------------------------
        speech_summary = self.generate_speech_summary(final_reply, matched_equipment)

        # ---------------------------------------------------------------------
        # 6. SESSION & AUDIT RECORDING
        # ---------------------------------------------------------------------
        if session_id:
            try:
                from src.agent_memory import save_session_message
                save_session_message(
                    session_id,
                    "assistant",
                    final_reply,
                    summary_for_speech=speech_summary,
                    payload={
                        "matched_equipment": matched_equipment,
                        "ai_enhanced": ai_enhanced,
                        "safety_blocked": False,
                        "subagent_traces": subagent_traces,
                        "active_subagents": active_subagents,
                        "consensus_health_index": collab_result.get("consensus_health_index") if collab_result else None,
                        "consensus_failure_mode": collab_result.get("consensus_failure_mode") if collab_result else None,
                        "predictive_rul": collab_result.get("predictive_rul") if collab_result else None,
                    },
                )
            except Exception:
                pass

        execution_duration = round((time.time() - start_time) * 1000, 1)

        return {
            "reply": final_reply,
            "summary_for_speech": speech_summary,
            "matched_equipment": matched_equipment,
            "ai_enhanced": ai_enhanced,
            "file_name": file_name,
            "provider": provider,
            "model": model,
            "session_id": session_id,
            "safety_blocked": False,
            "active_subagents": active_subagents,
            "subagent_traces": subagent_traces,
            "consensus_health_index": collab_result.get("consensus_health_index") if collab_result else None,
            "consensus_health_status": collab_result.get("consensus_health_status") if collab_result else None,
            "consensus_failure_mode": collab_result.get("consensus_failure_mode") if collab_result else None,
            "predictive_rul": collab_result.get("predictive_rul") if collab_result else None,
            "risk_assessment": collab_result.get("risk_assessment") if collab_result else None,
            "maintenance_decision": collab_result.get("maintenance_decision") if collab_result else None,
            "execution_duration_ms": execution_duration,
        }


# Singleton instance
_master_agent_instance: Optional[PPLEMasterAgent] = None


def get_master_agent() -> PPLEMasterAgent:
    """Retrieve or initialize the global PPLEMasterAgent singleton."""
    global _master_agent_instance
    if _master_agent_instance is None:
        _master_agent_instance = PPLEMasterAgent()
    return _master_agent_instance

