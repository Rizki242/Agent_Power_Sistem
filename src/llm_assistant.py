import json
import os
import urllib.error
import urllib.request
from typing import Optional

import pandas as pd

from src.knowledge_retriever import build_knowledge_context


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
AVAILABLE_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-2.5-pro",
]

DEFAULT_GEMINI_ENTERPRISE_MODEL = "gemini-2.5-pro"
AVAILABLE_GEMINI_ENTERPRISE_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
]

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
AVAILABLE_GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "deepseek-r1-distill-llama-70b",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "llama-3.1-8b-instant",
]

DEFAULT_OPENCODE_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENCODE_MODEL = "gpt-4o-mini"
AVAILABLE_OPENCODE_MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "deepseek-chat",
    "deepseek-reasoner",
    "qwen/qwen-2.5-coder-32b-instruct",
]

DEFAULT_OLLAMA_HOST = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"
AVAILABLE_OLLAMA_MODELS = [
    "llama3.2",
    "llama3.1",
    "llama3",
    "qwen2.5",
    "deepseek-r1",
    "mistral",
    "phi3",
    "gemma2",
]

# Backward compatibility alias
DEFAULT_MODEL = DEFAULT_GEMINI_MODEL
AVAILABLE_MODELS = AVAILABLE_GEMINI_MODELS


def _read_env_file() -> dict[str, str]:
    """Parse key-value pairs from .env in project root."""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file = os.path.join(root_dir, ".env")
    res = {}
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        res[k.strip()] = v.strip().strip("'\"")
        except Exception:
            pass
    return res


def resolve_api_key(api_key: Optional[str] = None, st=None) -> Optional[str]:
    """Backward compatible helper for Gemini key resolution."""
    return resolve_provider_key("gemini", api_key, st)


def resolve_provider_key(provider: str, api_key: Optional[str] = None, st=None) -> Optional[str]:
    """Resolve API Key for a specific provider from argument, Streamlit session/secrets, or env vars."""
    if api_key and str(api_key).strip():
        return str(api_key).strip()

    provider_clean = str(provider or "gemini").lower()

    key_names_map = {
        "gemini_enterprise": ["GEMINI_ENTERPRISE_API_KEY", "VERTEX_AI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "vertex_ai": ["VERTEX_AI_API_KEY", "GEMINI_ENTERPRISE_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"],
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_ENTERPRISE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "opencode": ["OPENCODE_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY"],
        "openai": ["OPENAI_API_KEY", "OPENCODE_API_KEY", "OPENROUTER_API_KEY"],
    }
    keys_to_check = key_names_map.get(provider_clean, [f"{provider_clean.upper()}_API_KEY"])

    if st is not None:
        try:
            session_key = st.session_state.get(f"{provider_clean}_api_key") or st.session_state.get("gemini_api_key")
            if session_key and str(session_key).strip():
                return str(session_key).strip()
        except Exception:
            pass

        try:
            for k in keys_to_check:
                secret_key = st.secrets.get(k)
                if secret_key and str(secret_key).strip():
                    return str(secret_key).strip()
        except Exception:
            pass

    for k in keys_to_check:
        env_val = os.getenv(k)
        if env_val and str(env_val).strip():
            return str(env_val).strip()

    env_dict = _read_env_file()
    for k in keys_to_check:
        if k in env_dict and env_dict[k]:
            return env_dict[k]

    return None


def is_any_ai_configured(st=None) -> bool:
    """Check if any AI provider (Gemini, Groq, OpenCode, or Ollama) is configured."""
    for p in ["gemini", "groq", "opencode", "openai"]:
        if resolve_provider_key(p, st=st):
            return True
    return False


class OpenAICompatibleClient:
    """Client for OpenAI, Groq, OpenCode, OpenRouter, vLLM, LMStudio compatible endpoints."""

    def __init__(
        self,
        base_url: str = DEFAULT_OPENCODE_BASE_URL,
        api_key: Optional[str] = None,
        timeout: int = 45,
    ):
        self.base_url = str(base_url or DEFAULT_OPENCODE_BASE_URL).rstrip("/")
        self.api_key = str(api_key or "").strip()
        self.timeout = timeout

    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        endpoint = f"{self.base_url}/chat/completions" if not self.base_url.endswith("/chat/completions") else self.base_url
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "MCSA-LLM-Assistant",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status in {200, 201}:
                    body = json.loads(response.read().decode("utf-8"))
                    choices = body.get("choices", [])
                    if choices and isinstance(choices, list):
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "")
                        if content:
                            return str(content).strip()
                    return ""
                raise ValueError(f"Endpoint HTTP {response.status}")
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"HTTP {exc.code}: {err_body}") from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Gagal terhubung ke {endpoint}: {exc}") from exc


class GroqClient(OpenAICompatibleClient):
    """Ultra-fast inference client for Groq Cloud API."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        super().__init__(
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            timeout=timeout,
        )


class OllamaClient:
    """Lightweight client for local Ollama server using Python standard library."""

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, timeout: int = 60):
        self.host = str(host or DEFAULT_OLLAMA_HOST).rstrip("/")
        self.timeout = timeout

    def list_models(self) -> list[str]:
        url = f"{self.host}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MCSA-LLM-Assistant"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        except Exception:
            pass
        return []

    def generate(self, model: str, prompt: str, system: Optional[str] = None) -> str:
        url = f"{self.host}/api/generate"
        payload = {
            "model": model or DEFAULT_OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "MCSA-LLM-Assistant"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    result = json.loads(response.read().decode("utf-8"))
                    return result.get("response", "").strip()
                raise ValueError(f"Ollama server returned HTTP {response.status}")
        except urllib.error.URLError as exc:
            if "refused" in str(exc).lower() or "connect" in str(exc).lower():
                raise ConnectionError(
                    f"Tidak dapat terhubung ke server Ollama di {self.host}. "
                    "Pastikan aplikasi Ollama sudah berjalan (`ollama serve`)."
                ) from exc
            raise


# Connection Probe Helpers
def test_gemini_connection(api_key: str, model: str = DEFAULT_GEMINI_MODEL) -> tuple[bool, str]:
    resolved_key = str(api_key or "").strip()
    if not resolved_key:
        return False, "API key kosong. Masukkan Gemini API Key terlebih dahulu."

    try:
        from google import genai
    except Exception as exc:
        return False, f"Library google-genai belum terinstall: {exc}"

    try:
        client = genai.Client(api_key=resolved_key)
        response = client.models.generate_content(
            model=model or DEFAULT_GEMINI_MODEL,
            contents="Ping. Jawab hanya satu kata: OK",
        )
        text = getattr(response, "text", "")
        if text:
            return True, f"Berhasil terhubung ke model {model or DEFAULT_GEMINI_MODEL}."
        return False, "Respons dari Gemini kosong."
    except Exception as exc:
        return False, f"Gagal terhubung ke Gemini: {exc}"


def test_groq_connection(api_key: str, model: str = DEFAULT_GROQ_MODEL) -> tuple[bool, str]:
    resolved_key = str(api_key or "").strip()
    if not resolved_key:
        return False, "Groq API Key kosong. Masukkan Groq API Key terlebih dahulu."

    client = GroqClient(api_key=resolved_key)
    try:
        res = client.generate(model=model or DEFAULT_GROQ_MODEL, prompt="Ping. Jawab hanya satu kata: OK")
        if res:
            return True, f"Berhasil terhubung ke Groq ({model or DEFAULT_GROQ_MODEL})."
        return False, "Respons dari Groq kosong."
    except Exception as exc:
        return False, f"Gagal terhubung ke Groq: {exc}"


def test_opencode_connection(
    base_url: str = DEFAULT_OPENCODE_BASE_URL,
    api_key: Optional[str] = None,
    model: str = DEFAULT_OPENCODE_MODEL,
) -> tuple[bool, str]:
    client = OpenAICompatibleClient(base_url=base_url, api_key=api_key)
    try:
        res = client.generate(model=model or DEFAULT_OPENCODE_MODEL, prompt="Ping. Jawab hanya satu kata: OK")
        if res:
            return True, f"Berhasil terhubung ke endpoint ({model or DEFAULT_OPENCODE_MODEL})."
        return False, "Respons dari endpoint kosong."
    except Exception as exc:
        return False, f"Gagal terhubung ke endpoint: {exc}"


def test_ollama_connection(
    host: str = DEFAULT_OLLAMA_HOST,
    model: Optional[str] = None,
) -> tuple[bool, str, list[str]]:
    client = OllamaClient(host=host)
    models = client.list_models()
    if not models:
        try:
            url = f"{client.host}/api/tags"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    return (
                        True,
                        f"Server Ollama aktif di {client.host}, namun belum ada model yang diunduh (misal jalankan `ollama pull {DEFAULT_OLLAMA_MODEL}`).",
                        [],
                    )
        except Exception as exc:
            return (
                False,
                f"Gagal terhubung ke Ollama di {client.host}. Pastikan Ollama sudah berjalan: {exc}",
                [],
            )

    return (
        True,
        f"Berhasil terhubung ke Ollama ({len(models)} model terdeteksi: {', '.join(models[:4])}).",
        models,
    )


def build_mcsa_context(df: pd.DataFrame, max_rows: int = 40) -> str:
    if df is None or df.empty:
        return "Tidak ada konteks data MCSA yang tersedia."

    preferred_columns = [
        "Equipment",
        "Full_Name",
        "Unit_Name",
        "Voltage_Level",
        "Date",
        "Parameter",
        "Raw_Value",
        "Value",
        "Unit",
    ]
    columns = [col for col in preferred_columns if col in df.columns]
    if not columns:
        return "Data MCSA tersedia, tetapi kolom utama tidak ditemukan."

    limited = df.loc[:, columns].head(max_rows).fillna("")
    lines = []
    for _, row in limited.iterrows():
        parts = []
        for col in columns:
            value = str(row[col]).strip()
            if value:
                parts.append(f"{col}={value}")
        if parts:
            lines.append("- " + "; ".join(parts))

    total_rows = len(df)
    if total_rows > len(limited):
        lines.append(f"Catatan: ditampilkan {len(limited)} dari {total_rows} baris konteks.")

    return "\n".join(lines) if lines else "Data MCSA tersedia, tetapi semua nilai konteks kosong."


def build_history_summary_context(df_history: pd.DataFrame, max_params: int = 10) -> str:
    if df_history is None or df_history.empty:
        return ""

    df = df_history.copy()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"]).sort_values("Date")
    else:
        return ""

    if df.empty:
        return ""

    lines = []
    earliest = df["Date"].min().strftime("%Y-%m-%d")
    latest = df["Date"].max().strftime("%Y-%m-%d")
    lines.append(f"Rentang Waktu Data: {earliest} s/d {latest} (Total {len(df)} pengukuran)")

    key_params = [
        "Kondisi", "Bearing", "Rotorbar", "Rotorbar Severity Level", "Upper Sideband", "Lower Sideband",
        "Load", "Dev Voltage", "Dev Current", "THD Voltage %", "THD Current %",
    ]

    for p in key_params:
        p_rows = df[df["Parameter"].astype(str) == p]
        if p_rows.empty:
            continue
        vals = p_rows.tail(4)
        history_points = []
        for _, r in vals.iterrows():
            dt_str = r["Date"].strftime("%Y-%m")
            raw_v = str(r.get("Raw_Value", "") or r.get("Value", "")).strip()
            if raw_v and raw_v != "nan":
                history_points.append(f"{dt_str}: {raw_v}")
        if history_points:
            lines.append(f"- Tren {p}: " + " → ".join(history_points))

    return "\n".join(lines)


def build_equipment_spec_context(query: str) -> str:
    try:
        from src.data_loader import load_nameplate_csv
        df_spec = load_nameplate_csv()
        if df_spec.empty:
            return ""
        
        q_norm = str(query).upper().replace(" ", "").replace(".", "").replace("-", "")
        matches = []
        for _, row in df_spec.iterrows():
            eq_name = str(row.get("Equipment", ""))
            full_name = str(row.get("Full_Name", ""))
            eq_norm = eq_name.upper().replace(" ", "").replace(".", "").replace("-", "")
            
            if eq_norm and (eq_norm in q_norm or (len(q_norm) >= 3 and q_norm in eq_norm)):
                matches.append(row)
                
        if not matches:
            return ""
            
        spec_lines = ["--- SPESIFIKASI & NAMEPLATE MOTOR / EQUIPMENT TERKAIT ---"]
        for row in matches[:3]:
            spec_lines.append(
                f"• Equipment: {row.get('Equipment')} ({row.get('Full_Name', '')})\n"
                f"  - Unit & Voltage: {row.get('Unit_Name', '')} | {row.get('Voltage_Nominal', '')}\n"
                f"  - Rated Power: {row.get('Rated_Power_kW', '')} kW | FLA: {row.get('FLA', '')} A | PF: {row.get('PF_Nominal', '')}\n"
                f"  - Speed: {row.get('RPM', '')} RPM ({row.get('Poles', '')} Poles)\n"
                f"  - Manufacturer: {row.get('Manufacturer', '')} | Insulation: {row.get('Insulation_Class', '')}\n"
                f"  - Bearing Type: DE={row.get('Bearing_DE', '')}, NDE={row.get('Bearing_NDE', '')}\n"
                f"  - VFD Control: {row.get('VFD_Flag', 'No')}"
            )
        return "\n".join(spec_lines)
    except Exception:
        return ""


class MCSALLMAssistant:
    """Universal Multi-Provider LLM Assistant (Gemini, Groq, OpenCode, Ollama)."""

    def __init__(
        self,
        enabled: bool = False,
        provider: str = "gemini",  # "gemini" | "groq" | "opencode" | "openai" | "ollama"
        client=None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
    ):
        self.enabled = enabled
        self.provider = str(provider or "gemini").lower()
        self.ollama_host = ollama_host or DEFAULT_OLLAMA_HOST
        self.base_url = base_url or DEFAULT_OPENCODE_BASE_URL
        self.client = client
        self.last_error = None
        self.last_citations = []

        # Model resolution per provider
        if self.provider in {"gemini_enterprise", "vertex_ai"}:
            self.model = model or DEFAULT_GEMINI_ENTERPRISE_MODEL
        elif self.provider == "groq":
            self.model = model or DEFAULT_GROQ_MODEL
        elif self.provider in {"opencode", "openai"}:
            self.model = model or DEFAULT_OPENCODE_MODEL
        elif self.provider == "ollama":
            self.model = model or DEFAULT_OLLAMA_MODEL
        else:
            self.model = model or DEFAULT_GEMINI_MODEL

        if api_key or client or enabled:
            self.enabled = True

        if self.enabled and self.client is None:
            self.client = self._create_provider_client(api_key)

    @property
    def available(self) -> bool:
        return self.enabled and self.client is not None

    def _create_provider_client(self, api_key: Optional[str]):
        if self.provider == "ollama":
            return OllamaClient(host=self.ollama_host)

        resolved_key = resolve_provider_key(self.provider, api_key)

        if self.provider == "groq":
            if not resolved_key:
                self.last_error = "GROQ_API_KEY belum diset."
                return None
            return GroqClient(api_key=resolved_key)

        if self.provider in {"opencode", "openai"}:
            return OpenAICompatibleClient(base_url=self.base_url, api_key=resolved_key)

        # Gemini / Gemini Enterprise / Vertex AI
        vertex_project = os.getenv("VERTEX_AI_PROJECT_ID")
        if self.provider in {"gemini_enterprise", "vertex_ai"} and vertex_project:
            try:
                from google import genai
                return genai.Client(
                    vertexai=True,
                    project=vertex_project,
                    location=os.getenv("VERTEX_AI_LOCATION", "asia-southeast1")
                )
            except Exception as exc:
                self.last_error = f"Gagal membuat Vertex AI Enterprise client: {exc}"
                return None

        if not resolved_key:
            self.last_error = "GEMINI_API_KEY / GEMINI_ENTERPRISE_API_KEY belum diset."
            return None

        try:
            from google import genai
            return genai.Client(api_key=resolved_key)
        except Exception as exc:
            self.last_error = f"Gagal membuat Gemini client: {exc}"
            return None

    def enhance_answer(
        self,
        question: str,
        rule_answer: str,
        df_context: pd.DataFrame,
        df_history: Optional[pd.DataFrame] = None,
        include_knowledge: bool = True,
        extra_file_context: str = "",
        subagents_context: str = "",
    ) -> str:
        if not self.available:
            return rule_answer

        mcsa_context = build_mcsa_context(df_context)
        history_context = build_history_summary_context(df_history) if df_history is not None else ""

        knowledge_context = ""
        self.last_citations = []
        if include_knowledge:
            knowledge_context, self.last_citations = build_knowledge_context(question)

        prompt = self._build_rag_prompt(
            question=question,
            rule_answer=rule_answer,
            mcsa_context=mcsa_context,
            history_context=history_context,
            knowledge_context=knowledge_context,
            extra_file_context=extra_file_context,
            subagents_context=subagents_context,
        )

        try:
            if self.provider in {"groq", "opencode", "openai", "ollama"}:
                text = self.client.generate(model=self.model, prompt=prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                text = getattr(response, "text", None)

            if text:
                return str(text).strip()
        except Exception as exc:
            self.last_error = f"LLM ({self.provider.upper()}) gagal menjawab: {exc}"
            return rule_answer

        self.last_error = f"Respons LLM ({self.provider.upper()}) kosong."
        return rule_answer

    def answer_question(
        self,
        question: str,
        rule_answer: str,
        df_latest: pd.DataFrame,
        df_all: Optional[pd.DataFrame] = None,
        include_knowledge: bool = True,
    ) -> str:
        return self.enhance_answer(
            question=question,
            rule_answer=rule_answer,
            df_context=df_latest,
            df_history=df_all,
            include_knowledge=include_knowledge
        )

    def generate_detailed_analysis(
        self,
        equipment_name: str,
        rule_report: str,
        df_history: pd.DataFrame,
    ) -> str:
        if not self.available:
            return rule_report

        context = build_mcsa_context(df_history, max_rows=50)
        history_summary = build_history_summary_context(df_history)
        knowledge_context, self.last_citations = build_knowledge_context(f"{equipment_name} rotor bar bearing unbalance THD")

        prompt = (
            f"Anda adalah tenaga ahli Predictive Maintenance dan spesialis MCSA/ESA untuk PLTU.\n"
            f"Berikut adalah data dan rekomendasi teknis rule-based untuk equipment {equipment_name}:\n\n"
            f"--- LAPORAN RULE-BASED ---\n{rule_report}\n\n"
            f"--- TREN RIWAYAT PENGUKURAN ---\n{history_summary}\n\n"
            f"--- DATA PENGUKURAN RINCI ---\n{context}\n\n"
            f"--- STANDAR & PANDUAN TEKNIS TERKAIT ---\n{knowledge_context}\n\n"
            f"Tugas Anda:\n"
            f"1. Berikan Ringkasan Eksekutif (Executive Summary) 2-3 kalimat mengenai kondisi equipment saat ini dan perubahannya dari riwayat sebelumnya.\n"
            f"2. Analisis Kemungkinan Penyebab (Root Cause Analysis) jika terdapat parameter Alarm/High "
            f"(misal Rotor Bar, Unbalance Arus/Tegangan, THD, atau Bearing) dengan merujuk standar terkait (IEEE 519 / NEMA MG-1 / ISO 15243).\n"
            f"3. Rekomendasi Tindak Lanjut Spesifik untuk tim teknisi di lapangan (inspeksi, re-sampling, atau scheduling perbaikan).\n"
            f"Gunakan Bahasa Indonesia baku, tegas, teknis, dan grounded 100% pada data di atas."
        )

        try:
            if self.provider in {"groq", "opencode", "openai", "ollama"}:
                text = self.client.generate(model=self.model, prompt=prompt)
            else:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                text = getattr(response, "text", None)

            if text:
                return str(text).strip()
        except Exception as exc:
            self.last_error = f"LLM ({self.provider.upper()}) gagal menghasilkan analisa: {exc}"

        return rule_report

    def _build_rag_prompt(
        self,
        question: str,
        rule_answer: str,
        mcsa_context: str,
        history_context: str,
        knowledge_context: str,
        extra_file_context: str = "",
        subagents_context: str = "",
    ) -> str:
        parts = [
            "Anda adalah AI O&M Reliability Orchestrator PLTU Jeranjang yang memimpin tim Specialist Sub-Agents:",
            "1. ⚡ MCSA Specialist (EPRI Sideband dB, Unbalance, THD, Rotor Bar Severity Level 1-4)",
            "2. 🌀 Vibration Specialist (ISO 10816-3 RMS Zone A-D, 1X Unbalance, 2X Misalignment, BPFO/BPFI Bearing)",
            "3. 🧪 DGA Specialist (IEEE C57.104 TDCG, Duval Triangle 1, Rogers Ratios)",
            "4. 💥 PD Specialist (IEC 60270, PRPD cluster, pulse pC)",
            "5. 🛢️ Tribology Specialist (ASTM D445, TAN, ISO 4406 Cleanliness, Fe/Cu wear)",
            "6. 🌡️ Thermal Specialist (ISO 18434-1, IR Delta-T, Hotspot)",
            "7. 🔗 Reliability Fusion & Risk Specialist (Health Index 0-100, RUL, Risk Matrix, Work Order)",
            "8. 🛡️ Safety Guardrail (Human-in-the-Loop clearance)",
            "\nJawablah pertanyaan user secara profesional, teknis, terstruktur, dan solutif dalam Bahasa Indonesia.",
            "PANDUAN KETAT:",
            "- Gunakan fakta dari data pengukuran, bukti spesialis sub-agent, file terlampir, dan knowledge base. Jangan mengarang angka atau tanggal.",
            "- Jika pertanyaan melibatkan multi-domain (misal: getaran + arus + oli), sintesiskan hasil dari sub-agent terkait secara terpadu.",
            "- Sertakan estimasi Health Index, kemungkinan akar penyebab (root cause), dan rekomendasi tindakan / Work Order terencana.",
            "\n--- PERTANYAAN USER ---",
            question,
        ]

        if subagents_context:
            parts.extend(["\n--- TEMUAN & BUKTI SPECIALIST SUB-AGENTS ---", subagents_context])

        if extra_file_context:
            parts.extend(["\n--- DOKUMEN / DATA TERLAMPIR DARI USER ---", extra_file_context])

        spec_context = build_equipment_spec_context(question)
        if spec_context:
            parts.extend(["\n" + spec_context])

        if rule_answer:
            parts.extend(["\n--- JAWABAN RULE-BASED SISTEM ---", rule_answer])

        if mcsa_context and "tidak ada konteks" not in mcsa_context.lower():
            parts.extend(["\n--- DATA PENGUKURAN MCSA TERBARU ---", mcsa_context])

        if history_context:
            parts.extend(["\n--- RIWAYAT & TREN PENGUKURAN ---", history_context])

        if knowledge_context:
            parts.extend(["\n--- KNOWLEDGE BASE & MATERI SOP PLTU JERANJANG ---", knowledge_context])

        parts.append(
            "\nBerikan jawaban komprehensif, sebutkan bukti dari sub-agent yang relevan, berikan diagnosis konsensus, dan tindak lanjut maintenance."
        )

        return "\n\n".join(parts)
