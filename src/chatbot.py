import re
from typing import Optional

import pandas as pd

from src.knowledge_retriever import search_knowledge_base, build_knowledge_context
from src.standards import generate_initial_analysis


def _norm_code(text: str) -> str:
    """Normalize code string by removing non-alphanumeric characters and converting to uppercase."""
    return re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()


class MCSAChatbot:
    def __init__(self, df_latest: pd.DataFrame, df_all: Optional[pd.DataFrame] = None):
        self.df_latest = df_latest if df_latest is not None else pd.DataFrame()
        self.df_all = df_all if df_all is not None else self.df_latest
        self.df = self.df_latest

        self.equipments = self.df_latest["Equipment"].dropna().unique().tolist() if not self.df_latest.empty else []
        self.eq_norm_map = {}
        for eq in self.equipments:
            norm = _norm_code(eq)
            if norm:
                self.eq_norm_map[norm] = eq

        self.last_export = None
        self.last_matched_equipment = None
        self.last_matched_history = None

    def match_equipment(self, query: str) -> Optional[str]:
        """Fuzzy match equipment name from query string."""
        q_clean = query.strip()
        q_lower = q_clean.lower()
        q_norm = _norm_code(q_clean)

        # 1. Exact string match in equipment names
        for eq in self.equipments:
            if str(eq).lower() in q_lower and len(str(eq)) >= 3:
                return eq

        # 2. Normalized token / substring matching
        for norm_code, original_name in sorted(self.eq_norm_map.items(), key=lambda x: len(x[0]), reverse=True):
            if len(norm_code) >= 3 and norm_code in q_norm:
                return original_name

        # 3. Regex pattern for equipment codes like (BC 10.1, C3WP 1A, CEP-3B, etc.)
        candidates = re.findall(r"\b([A-Za-z]{2,5}\s*[-.]?\s*\d{1,3}\s*[A-Za-z0-9]?)\b", q_clean)
        for cand in candidates:
            c_norm = _norm_code(cand)
            if c_norm in self.eq_norm_map:
                return self.eq_norm_map[c_norm]

        return None

    def process_query(self, query: str) -> str:
        q = query.lower().strip()
        self.last_matched_equipment = None
        self.last_matched_history = None

        # Intent 1: List Alarm / Warning / High
        if any(w in q for w in ["alarm", "warning", "masalah", "abnormal", "rusak", "high", "kritis"]):
            if not self.match_equipment(query):
                return self.get_alarm_list()

        # Intent 2: Specific Equipment Status & Trend
        found_eq = self.match_equipment(query)
        if found_eq:
            self.last_matched_equipment = found_eq
            return self.get_asset_status(found_eq)

        # Intent 3: Group Status (Unit / Voltage / Period)
        unit = None
        volt = None
        month_key = None
        m_unit = re.search(r"unit\s*(1|2|3|common)", q)
        if m_unit:
            u = m_unit.group(1).upper()
            unit = "UNIT " + u if u in {"1", "2", "3"} else "UNIT COMMON"
        if re.search(r"6[.,]3\s*kv|\b6\.3\b", q):
            volt = "6.3 KV"
        elif re.search(r"\b(380|400)\b", q):
            volt = "380/400 V"
        m_month = re.search(r"(20\d{2}-\d{2})", q)
        if m_month:
            month_key = m_month.group(1)

        if unit or volt or month_key:
            return self.get_group_status(unit=unit, volt=volt, month_key=month_key)

        # Intent 4: SOP / Standards / Knowledge Base Technical Questions
        if any(w in q for w in ["sop", "standar", "nema", "ieee", "iso", "cara", "langkah", "rumus", "pengukuran", "atpol", "sideband", "unbalance", "thd", "rotor bar", "vibrasi", "vibration", "bearing", "tribology", "pelumas", "oli"]):
            kb_results = search_knowledge_base(query, top_k=2)
            if kb_results:
                resp = "📚 **Referensi & Panduan Teknis Terkait:**\n\n"
                for doc in kb_results:
                    resp += f"### {doc['title']} — {doc['heading']}\n"
                    resp += f"{doc['content']}\n\n"
                return resp.strip()

        # Intent 5: Help / Greeting
        if any(w in q for w in ["halo", "hai", "hi", "help", "bantuan", "menu", "selamat"]):
            return (
                "👋 **Halo! Saya MCSA AI Virtual Assistant.**\n\n"
                "Anda dapat menanyakan hal-hal berikut:\n"
                "1. **Kondisi Equipment**: *'Status BC 10.1'*, *'Bagaimana tren C3WP1A?'*\n"
                "2. **Daftar Masalah**: *'List Alarm'*, *'Equipment yang berstatus High'*\n"
                "3. **Filter Unit**: *'Status Unit 1 6.3 KV'*, *'Data 2026-05'*\n"
                "4. **Knowledge Base & SOP**: *'Bagaimana SOP pengukuran ATPOL?'*, *'Berapa batas unbalance tegangan?'*"
            )

        return (
            "Maaf, saya belum menemukan data spesifik untuk pertanyaan tersebut.\n"
            "Cobalah sebutkan nama equipment (contoh: *'Status BC 10.1'*), ketik *'List Alarm'*, "
            "atau tanyakan panduan teknis/SOP pengukuran."
        )

    def get_alarm_list(self) -> str:
        if self.df_latest.empty or "Parameter" not in self.df_latest.columns:
            return "✅ Tidak ada data kondisi equipment yang tersedia."
        cond_rows = self.df_latest[self.df_latest["Parameter"] == "Kondisi"]
        if cond_rows.empty or "Raw_Value" not in cond_rows.columns:
            return "✅ Tidak ada data kondisi equipment yang tersedia."

        rv = cond_rows["Raw_Value"].astype(str).str.strip()
        rv_lower = rv.str.lower()
        valid = rv.ne("") & ~rv_lower.isin(["nan", "none"])
        alarms = cond_rows[valid & ~rv_lower.isin(["normal", "standby"])]

        if alarms.empty:
            return "✅ Semua equipment dalam kondisi Normal/Standby."

        response = "⚠️ **Daftar Equipment Warning/Alarm:**\n"
        for _, row in alarms.iterrows():
            status = str(row["Raw_Value"]).strip().upper()
            icon = "🔴" if status in ["HIGH", "CRITICAL", "BAD", "RUSAK"] else "🟡"
            response += f"- {icon} **{row['Equipment']}**: {status}\n"

        self.last_export = alarms[["Equipment", "Raw_Value"]].rename(columns={"Raw_Value": "Status"}).to_csv(index=False)
        return response

    def get_group_status(self, unit=None, volt=None, month_key=None) -> str:
        df = self.df_all.copy()
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        if unit and "Unit_Name" in df.columns:
            df = df[df["Unit_Name"].astype(str).str.upper() == unit]
        if volt and "Voltage_Level" in df.columns:
            df = df[df["Voltage_Level"].astype(str) == volt]
        if month_key and "Date" in df.columns:
            try:
                year, month = month_key.split("-")
                start = pd.Timestamp(int(year), int(month), 1)
                end = start + pd.offsets.MonthEnd(0)
                df = df[(df["Date"] >= start) & (df["Date"] <= end)]
            except Exception:
                pass

        if df.empty or "Parameter" not in df.columns:
            return "Tidak ada data kondisi untuk filter yang dipilih."
        cond = df[df["Parameter"] == "Kondisi"]
        if cond.empty or "Raw_Value" not in cond.columns:
            return "Tidak ada data kondisi untuk filter yang dipilih."

        latest = cond.sort_values("Date").drop_duplicates(subset=["Equipment"], keep="last")
        status_map = latest[["Equipment", "Raw_Value"]]
        lines = []
        for _, r in status_map.iterrows():
            st_val = str(r["Raw_Value"]).strip().upper()
            icon = "🟢" if st_val == "NORMAL" else ("⚪" if st_val == "STANDBY" else "🔴")
            lines.append(f"- {icon} {r['Equipment']}: {st_val}")

        title_parts = []
        if unit:
            title_parts.append(unit)
        if volt:
            title_parts.append(volt)
        if month_key:
            title_parts.append(month_key)
        filter_desc = f" ({' | '.join(title_parts)})" if title_parts else ""

        text = f"📊 **Ringkasan Status Equipment{filter_desc}** (Total: {len(latest)} unit):\n\n" + "\n".join(lines)
        self.last_export = status_map.to_csv(index=False)
        return text

    def get_asset_status(self, eq_name: str) -> str:
        eq_latest = self.df_latest[self.df_latest["Equipment"] == eq_name]
        if eq_latest.empty:
            # Try fuzzy match in full dataframe
            eq_latest = self.df_all[self.df_all["Equipment"] == eq_name]

        if eq_latest.empty:
            return f"Data untuk {eq_name} tidak ditemukan dalam database."

        eq_hist = self.df_all[self.df_all["Equipment"] == eq_name].copy() if not self.df_all.empty else pd.DataFrame()
        self.last_matched_history = eq_hist

        cond_row = eq_latest[eq_latest["Parameter"] == "Kondisi"]
        condition = cond_row["Raw_Value"].iloc[0] if not cond_row.empty else "Unknown"

        last_dt_str = "-"
        if not eq_hist.empty and "Date" in eq_hist.columns:
            dt = pd.to_datetime(eq_hist["Date"], errors="coerce")
            if dt.notna().any():
                last_dt_str = dt.max().strftime("%Y-%m-%d")

        badge = "🟢" if str(condition).upper() == "NORMAL" else ("⚪" if str(condition).upper() == "STANDBY" else "🔴")
        response = f"📊 **Status {eq_name}**: {badge} {str(condition).upper()}\n\n"
        response += f"**Tanggal Pengukuran Terakhir:** {last_dt_str}\n\n"

        # Key parameters table
        response += "**Parameter Pengukuran Terakhir:**\n"
        for _, row in eq_latest.iterrows():
            param = row["Parameter"]
            val = str(row["Raw_Value"]).strip()
            unit = row["Unit"] if pd.notna(row.get("Unit")) else ""
            if param != "Kondisi" and val and val != "nan":
                response += f"- {param}: **{val}** {unit}\n"

        # Historical trend comparison
        if not eq_hist.empty and "Date" in eq_hist.columns:
            eq_hist_dates = pd.to_datetime(eq_hist["Date"], errors="coerce").dropna().unique()
            if len(eq_hist_dates) > 1:
                response += "\n📈 **Riwayat & Tren Parameter:**\n"
                key_trend_params = ["Load", "Dev Voltage", "Dev Current", "THD Voltage %", "THD Current %", "Rotorbar", "Bearing"]
                for tp in key_trend_params:
                    tp_rows = eq_hist[eq_hist["Parameter"] == tp]
                    if not tp_rows.empty:
                        tail_rows = tp_rows.sort_values("Date").tail(3)
                        pts = [f"{pd.to_datetime(r['Date']).strftime('%b %y')}: {r['Raw_Value']}" for _, r in tail_rows.iterrows() if str(r.get("Raw_Value", "")).strip() != ""]
                        if pts:
                            response += f"- *{tp}*: " + " → ".join(pts) + "\n"

        # Diagnostic recommendation
        if not eq_hist.empty:
            analysis = generate_initial_analysis(eq_hist)
            recs = analysis.get("recommendations") or []
            if recs:
                response += "\n🛠️ **Analisa & Rekomendasi Tindak Lanjut:**\n"
                for r in recs[:6]:
                    response += f"- {r}\n"
            refs = analysis.get("references") or []
            if refs:
                response += "\n📖 **Referensi Standar:** " + " | ".join(refs) + "\n"

        return response
