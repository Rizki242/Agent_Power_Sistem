import re
from typing import Optional

import pandas as pd

from src.knowledge_retriever import search_knowledge_base, build_knowledge_context
from src.standards import generate_initial_analysis


def _norm_code(text: str) -> str:
    """Normalize code string by removing non-alphanumeric characters and converting to uppercase."""
    return re.sub(r"[^A-Za-z0-9]", "", str(text or "")).upper()


def _is_missing_value(value) -> bool:
    """True jika nilai kosong atau placeholder NaN/None hasil pembacaan CSV."""
    return str(value).strip().lower() in ("", "nan", "none")


class MCSAChatbot:
    def __init__(self, df_latest: pd.DataFrame, df_all: Optional[pd.DataFrame] = None):
        self.df_latest = df_latest if df_latest is not None else pd.DataFrame()
        self.df_all = df_all if df_all is not None else self.df_latest
        self.df = self.df_latest

        self.equipments = self.df_latest["Equipment"].dropna().unique().tolist() if not self.df_latest.empty else []
        self.alias_to_canonical = {}

        # MCSA equipment canonical map
        for eq in self.equipments:
            eq_str = str(eq).strip()
            if eq_str:
                self.alias_to_canonical[eq_str.upper()] = eq_str

        # Tambahkan equipment dari registry (termasuk transformer, aliases, kks)
        try:
            from src.asset_registry import list_assets
            for a in list_assets():
                c_name = str(a.get("name", "")).strip()
                if c_name:
                    if c_name not in self.equipments:
                        self.equipments.append(c_name)
                    self.alias_to_canonical[c_name.upper()] = c_name
                    asset_id = str(a.get("asset_id", "")).strip()
                    if asset_id:
                        self.alias_to_canonical[asset_id.upper()] = c_name
                    for al in a.get("aliases", []):
                        al_str = str(al).strip()
                        if al_str:
                            self.alias_to_canonical[al_str.upper()] = c_name
        except Exception:
            pass

        # Tambahkan transformer dari DGA data & history
        try:
            from src.dga_data import search_dga_transformers
            for t in search_dga_transformers():
                t_name = str(t.get("name", "")).strip()
                if t_name:
                    if t_name not in self.equipments:
                        self.equipments.append(t_name)
                    if t_name.upper() not in self.alias_to_canonical:
                        self.alias_to_canonical[t_name.upper()] = t_name
                    t_id = str(t.get("transformer_id", "")).strip()
                    if t_id:
                        self.alias_to_canonical[t_id.upper()] = t_name
        except Exception:
            pass

        # Tambahkan equipment dari domain vibrasi
        try:
            from src.vibration_data import load_vibration_assets
            v_df = load_vibration_assets()
            if not v_df.empty and "equipment" in v_df.columns:
                for v_eq in v_df["equipment"].dropna():
                    v_str = str(v_eq).strip()
                    if v_str and v_str not in self.equipments:
                        self.equipments.append(v_str)
                        self.alias_to_canonical[v_str.upper()] = v_str
        except Exception:
            pass

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

        # 1. Alias & exact substring match (sorted longest key first)
        for alias_key, canon in sorted(self.alias_to_canonical.items(), key=lambda x: len(x[0]), reverse=True):
            if len(alias_key) >= 3 and alias_key.lower() in q_lower:
                return canon

        # 2. Token-based matching for transformers & common power plant naming
        q_tokens = set(re.findall(r"[a-z0-9]+", q_lower))

        # UAT (Unit Auxiliary Transformer)
        if "uat" in q_tokens:
            for alias_key, canon in self.alias_to_canonical.items():
                if "UAT" in alias_key and ("3" in q_tokens or "unit" in q_tokens):
                    return canon
            return self.alias_to_canonical.get("UAT 3", "Unit Auxiliary Transformer 3 (UAT 3)")

        # Ash Handling Transformer
        if "ash" in q_tokens and "handling" in q_tokens:
            if "1" in q_tokens:
                return self.alias_to_canonical.get("ASH HANDLING-1", "Ash Handling Transformer 1")
            if "2" in q_tokens:
                return self.alias_to_canonical.get("ASH HANDLING-2", "Ash Handling Transformer 2")

        # Main Transformer / GT
        if any(w in q_tokens for w in ["main", "gt", "utama"]) and any(w in q_tokens for w in ["trafo", "transformer"]):
            if "1" in q_tokens:
                return self.alias_to_canonical.get("MAIN TRAFO UNIT 1", "Main Transformer Unit 1")
            if "2" in q_tokens:
                return self.alias_to_canonical.get("MAIN TRAFO UNIT 2", "Main Transformer Unit 2")
            if "3" in q_tokens:
                return self.alias_to_canonical.get("MAIN TRAFO UNIT 3", "Main Transformer Unit 3")

        # ESP Transformer Rectifiers
        if "esp" in q_tokens and any(w in q_tokens for w in ["trafo", "transformer", "tr"]):
            unit_num = "1"
            if "2" in q_tokens and ("unit2" in q_tokens or "unit" in q_tokens):
                unit_num = "2"
            elif "3" in q_tokens and ("unit3" in q_tokens or "unit" in q_tokens):
                unit_num = "3"
            for esp_n in ("1", "2", "3", "4"):
                if esp_n in q_tokens:
                    key = f"TRAFO {esp_n} ESP UNIT {unit_num}".upper()
                    if key in self.alias_to_canonical:
                        return self.alias_to_canonical[key]

        # 3. Exact string match in equipment names
        for eq in self.equipments:
            if str(eq).lower() in q_lower and len(str(eq)) >= 3:
                return self.alias_to_canonical.get(str(eq).upper(), eq)

        # 4. Normalized token / substring matching
        for norm_code, original_name in sorted(self.eq_norm_map.items(), key=lambda x: len(x[0]), reverse=True):
            if len(norm_code) >= 3 and norm_code in q_norm:
                return original_name

        # 5. Regex pattern for equipment codes like (BC 10.1, C3WP 1A, CEP-3B, etc.)
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

        # Intent 1: Multi-domain Correlation (Korelasi getaran dan arus / mekanik dan elektrik)
        if any(w in q for w in ["korelasi", "hubungan getaran", "vibrasi dan arus", "getaran dan arus", "hubungan arus", "korelasi vibrasi", "korelasi arus", "korelasi suhu"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
            return self.get_correlation_analysis(found_eq)

        # Intent 2: Domain-Specific Deep Dive (Vibrasi, Thermal, Tribology, DGA)
        if any(w in q for w in ["vibrasi", "getaran", "spektrum", "iso 10816"]) and not any(w in q for w in ["sop", "standar", "rumus"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
                return self.get_vibration_status(found_eq)
            elif any(w in q for w in ["alarm", "kritis", "warning", "list"]):
                return self.get_vibration_alarm_list()

        if any(w in q for w in ["suhu", "thermal", "irt", "thermography", "hotspot", "panas"]) and not any(w in q for w in ["sop", "standar"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
                return self.get_thermal_status(found_eq)

        if any(w in q for w in ["pelumas", "oli", "oil", "tribologi", "viskositas", "keausan"]) and not any(w in q for w in ["sop", "standar"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
                return self.get_tribology_status(found_eq)

        if any(w in q for w in ["dga", "gas trafo", "duval", "rogers", "tdcg", "c2h2", "asetilena", "minyak trafo"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
                return self.get_dga_status(found_eq)
            # Pertanyaan standar/SOP tanpa nama trafo -> rujukan standar, bukan ringkasan armada
            # (pola yang sama dengan domain vibrasi/thermal/tribologi di atas).
            if any(w in q for w in ["sop", "standar", "rumus"]):
                return self.get_dga_standard_reference()
            return self.get_dga_status()

        # Intent 3: List Alarm / Warning / High (Prioritas MCSA)
        if any(w in q for w in ["alarm", "warning", "masalah", "abnormal", "rusak", "high", "kritis"]):
            if not self.match_equipment(query):
                return self.get_alarm_list()

        # Intent 4: Specific Equipment Status & Trend (Holistik MCSA + Multi-Domain 360°)
        found_eq = self.match_equipment(query)
        if found_eq:
            self.last_matched_equipment = found_eq
            return self.get_asset_status(found_eq)

        # Intent 5: Group Status (Unit / Voltage / Period)
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

        # Intent 6: SOP / Standards / Knowledge Base Technical Questions
        if any(w in q for w in ["sop", "standar", "nema", "ieee", "iso", "cara", "langkah", "rumus", "pengukuran", "atpol", "sideband", "unbalance", "thd", "rotor bar", "vibrasi", "vibration", "bearing", "tribology", "pelumas", "oli"]):
            kb_results = search_knowledge_base(query, top_k=2)
            if kb_results:
                resp = "📚 **Referensi & Panduan Teknis Terkait:**\n\n"
                for doc in kb_results:
                    resp += f"### {doc['title']} — {doc['heading']}\n"
                    resp += f"{doc['content']}\n\n"
                return resp.strip()

        # Intent 7: Help / Greeting
        if any(w in q for w in ["halo", "hai", "hi", "help", "bantuan", "menu", "selamat"]):
            return (
                "👋 **Halo! Saya CBM & MCSA AI Virtual Assistant.**\n\n"
                "Saya dapat membantu mendiagnosa kondisi aset secara terpadu lintas 5 pilar CBM:\n"
                "1. **Kondisi Peralatan Holistik**: *'Status BC 10.1'*, *'Tren C3WP 1A'*\n"
                "2. **Korelasi Multi-Domain**: *'Korelasi vibrasi dan arus BC 10.1'*, *'Hubungan getaran dan beban'*\n"
                "3. **Pilar Spesifik**: *'Vibrasi BC 10.1'*, *'Suhu PA Fan'*, *'Kondisi Oli BFP 1A'*, *'Standar DGA Trafo'*\n"
                "4. **Daftar Alarm & Masalah**: *'List Alarm'*, *'Equipment yang berstatus High'*\n"
                "5. **Filter Unit & Gardu**: *'Status Unit 1 6.3 KV'*, *'Data 2026-05'*\n"
                "6. **Knowledge Base & SOP**: *'Bagaimana SOP pengukuran ATPOL?'*, *'Standar vibrasi ISO 10816-3'*"
            )

        return (
            "Maaf, saya belum menemukan data spesifik untuk pertanyaan tersebut.\n"
            "Cobalah sebutkan nama equipment (contoh: *'Status BC 10.1'*), ketik *'List Alarm'*, "
            "tanyakan *'Korelasi vibrasi dan arus'*, atau tanyakan panduan teknis/SOP."
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
            icon = "🟢" if st_val == "NORMAL" else ("⚪" if st_val == "STANDBY" else ("🔴" if st_val in ["HIGH", "CRITICAL", "BAD", "RUSAK"] else "🟡"))
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
        eq_latest = pd.DataFrame()
        if not self.df_latest.empty and "Equipment" in self.df_latest.columns:
            eq_latest = self.df_latest[self.df_latest["Equipment"] == eq_name]
        if eq_latest.empty and not self.df_all.empty and "Equipment" in self.df_all.columns:
            # Try match in full dataframe
            eq_latest = self.df_all[self.df_all["Equipment"] == eq_name]

        # Multi-domain cross check
        v_match = None
        try:
            from src.vibration_data import load_vibration_monthly_tests, match_monthly_test_by_equipment
            v_match = match_monthly_test_by_equipment(eq_name, load_vibration_monthly_tests())
        except Exception:
            pass

        t_records = []
        try:
            from src.thermal_data import search_thermal_records
            t_records = search_thermal_records(search=eq_name)
        except Exception:
            pass

        o_samples = []
        try:
            from src.tribology_data import search_tribology_samples
            o_samples = search_tribology_samples(search=eq_name)
        except Exception:
            pass

        dga_match = None
        try:
            from src.dga_data import get_dga_transformer_detail
            dga_match = get_dga_transformer_detail(eq_name)
        except Exception:
            pass

        if eq_latest.empty:
            if dga_match:
                return self.get_dga_status(eq_name)
            if not v_match and not t_records and not o_samples:
                return f"Data untuk {eq_name} tidak ditemukan dalam database."

            resp = f"📊 **Status Terpadu {eq_name} (Data Pemantauan Non-MCSA):**\n\n"
            if v_match:
                v_st = v_match.get("status", "NORMAL")
                v_max = v_match.get("velocity_max", 0.0)
                v_badge = "🟢" if v_st == "NORMAL" else ("🟡" if "WARN" in v_st or "PRE" in v_st else "🔴")
                resp += f"- **Vibrasi Mekanikal**: {v_badge} {v_st} (Velocity Vmax: **{v_max:.2f} mm/s** - {v_match.get('iso_group', 'ISO 10816')})\n"
            if t_records:
                t_rec = t_records[0]
                t_st = t_rec.get("status", "NORMAL")
                t_badge = "🟢" if t_st == "NORMAL" else ("🟡" if "WARN" in t_st or "PRE" in t_st else "🔴")
                resp += f"- **Thermal IRT**: {t_badge} {t_st} ({t_rec.get('raw_status', 'Normal')})\n"
            if o_samples:
                o_sam = o_samples[0]
                o_st = o_sam.get("status", "NORMAL")
                o_badge = "🟢" if o_st == "NORMAL" else ("🟡" if "WARN" in o_st or "PRE" in o_st else "🔴")
                resp += f"- **Pelumas & Oli**: {o_badge} {o_st} (Oli: {o_sam.get('oil_brand', 'ISO VG')})\n"

            return resp

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
            if param != "Kondisi" and not _is_missing_value(val):
                response += f"- {param}: **{val}** {unit}\n"

        # Cross-domain 360 insights
        cross_items = []
        if v_match:
            v_st = v_match.get("status", "NORMAL")
            v_max = v_match.get("velocity_max", 0.0)
            v_badge = "🟢" if v_st == "NORMAL" else ("🟡" if "WARN" in v_st or "PRE" in v_st else "🔴")
            cross_items.append(f"- **Vibrasi Mekanikal**: {v_badge} {v_st} (Vmax: **{v_max:.2f} mm/s** — {v_match.get('iso_group', 'ISO 10816-3')})")
        if t_records:
            t_rec = t_records[0]
            t_st = t_rec.get("status", "NORMAL")
            t_badge = "🟢" if t_st == "NORMAL" else ("🟡" if "WARN" in t_st or "PRE" in t_st else "🔴")
            cross_items.append(f"- **Thermal IRT**: {t_badge} {t_st} ({t_rec.get('raw_status', 'Normal')})")
        if o_samples:
            o_sam = o_samples[0]
            o_st = o_sam.get("status", "NORMAL")
            o_badge = "🟢" if o_st == "NORMAL" else ("🟡" if "WARN" in o_st or "PRE" in o_st else "🔴")
            w_ppm = o_sam.get("water_ppm", "-")
            cross_items.append(f"- **Pelumas & Oli**: {o_badge} {o_st} (Oli: {o_sam.get('oil_brand', 'ISO VG')}, Air: {w_ppm} ppm)")

        if cross_items:
            response += "\n🌐 **Diagnosa Lintas Domain (Asset 360°):**\n" + "\n".join(cross_items) + "\n"

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
                        pts = [f"{pd.to_datetime(r['Date']).strftime('%b %y')}: {r['Raw_Value']}" for _, r in tail_rows.iterrows() if not _is_missing_value(r.get("Raw_Value", ""))]
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

    def get_correlation_analysis(self, eq_name: Optional[str] = None) -> str:
        """Berikan analisis korelasi multi-domain (mekanikal-elektrikal-termal-pelumas)."""
        if not eq_name:
            return (
                "🔍 **Panduan Korelasi Multi-Domain CBM (MCSA, Vibrasi, Thermal, Tribology):**\n\n"
                "1. **Korelasi Vibrasi & Arus MCSA:**\n"
                "- **Unbalance Mekanik**: Puncak getaran 1X tinggi pada spektrum vibrasi tanpa diiringi unbalance arus stator.\n"
                "- **Air Gap Eccentricity**: Menghasilkan komponen getaran 2X frekuensi jala-jala (100 Hz) dan sideband 2*s*fL di sekitar arus fundamental.\n"
                "- **Broken Rotor Bar**: Memunculkan sideband arus ±2*s*fL pada MCSA dengan fluktuasi periodik amplitudo getaran mekanik.\n\n"
                "2. **Korelasi Suhu (Thermal) & Pelumas (Tribology):**\n"
                "- Overheating bearing (>70°C) sering dipicu oleh penurunan viskositas pelumas akibat kontaminasi air (>200 ppm) atau oksidasi oli (TAN > 0.6).\n\n"
                "3. **Korelasi Vibrasi & Keausan Logam (Fe/Cu):**\n"
                "- Cacat bearing pada frekuensi BPFO/BPFI yang berlanjut selalu diikuti oleh lonjakan partikel keausan logam Fe (>50 ppm) pada oli.\n\n"
                "💡 *Sebutkan nama peralatan (misal: 'Korelasi BC 10.1') untuk melihat analisis korelasi terpadu spesifik aset tersebut.*"
            )

        parts = [f"🔍 **Analisis Korelasi Multi-Domain untuk {eq_name}:**\n"]

        # 1. MCSA
        mcsa_data = self.df_latest[self.df_latest["Equipment"] == eq_name] if not self.df_latest.empty else pd.DataFrame()
        cond_mcsa = "NORMAL"
        load_val = "-"
        if not mcsa_data.empty:
            c_row = mcsa_data[mcsa_data["Parameter"] == "Kondisi"]
            if not c_row.empty:
                cond_mcsa = str(c_row["Raw_Value"].iloc[0]).upper()
            l_row = mcsa_data[mcsa_data["Parameter"] == "Load"]
            if not l_row.empty and not _is_missing_value(l_row["Raw_Value"].iloc[0]):
                load_val = f"{l_row['Raw_Value'].iloc[0]} %"

        parts.append(f"1. **Elektrikal (MCSA)**: Kondisi **{cond_mcsa}** (Beban Motor: {load_val})")

        # 2. Vibrasi
        try:
            from src.vibration_data import load_vibration_monthly_tests, match_monthly_test_by_equipment
            v_match = match_monthly_test_by_equipment(eq_name, load_vibration_monthly_tests())
            if v_match:
                parts.append(f"2. **Mekanikal (Vibrasi)**: Status **{v_match.get('status', 'NORMAL')}** (Velocity Vmax: {v_match.get('velocity_max', 0.0):.2f} mm/s)")
            else:
                parts.append("2. **Mekanikal (Vibrasi)**: Data baseline belum terdata pada periode terakhir.")
        except Exception:
            parts.append("2. **Mekanikal (Vibrasi)**: -")

        # 3. Thermal
        try:
            from src.thermal_data import search_thermal_records
            t_match = search_thermal_records(search=eq_name)
            if t_match:
                parts.append(f"3. **Thermal (IRT)**: Status **{t_match[0].get('status', 'NORMAL')}** ({t_match[0].get('raw_status', '-')})")
            else:
                parts.append("3. **Thermal (IRT)**: Normal / Delta-T tidak menunjukkan anomali signifikan.")
        except Exception:
            parts.append("3. **Thermal (IRT)**: -")

        # 4. Tribology
        try:
            from src.tribology_data import search_tribology_samples
            o_match = search_tribology_samples(search=eq_name)
            if o_match:
                parts.append(f"4. **Pelumas (Tribology)**: Status **{o_match[0].get('status', 'NORMAL')}** (Air: {o_match[0].get('water_ppm', '-')} ppm, Fe: {o_match[0].get('wear_fe', '-')} ppm)")
            else:
                parts.append("4. **Pelumas (Tribology)**: Sampel laboratorium terjadwal normal.")
        except Exception:
            parts.append("4. **Pelumas (Tribology)**: -")

        parts.append(
            "\n💡 **Kesimpulan Korelasi & Diagnosa Terpadu:**\n"
            f"- Parameter kelistrikan MCSA ({cond_mcsa}) disinkronkan dengan respon mekanikal dan kondisi pelumas.\n"
            "- Jika getaran mekanikal naik namun arus stator stabil, fokus inspeksi pada alignment kopling, pondasi (soft foot), atau balancing.\n"
            "- Jika temperatur bearing termonitor naik bersamaan dengan peningkatan partikel Fe, segera periksa kondisi pelumas dan kecukupan grease."
        )

        return "\n".join(parts)

    def get_vibration_status(self, eq_name: str) -> str:
        """Pemeriksaan khusus domain vibrasi untuk peralatan."""
        try:
            from src.vibration_data import load_vibration_monthly_tests, match_monthly_test_by_equipment
            m_tests = load_vibration_monthly_tests()
            v_match = match_monthly_test_by_equipment(eq_name, m_tests)
        except Exception:
            v_match = None

        if not v_match:
            return f"Data vibrasi spesifik untuk {eq_name} tidak ditemukan dalam database pengujian bulanan."

        st_val = v_match.get("status", "NORMAL")
        v_max = v_match.get("velocity_max", 0.0)
        badge = "🟢" if st_val == "NORMAL" else ("🟡" if "WARN" in st_val or "PRE" in st_val else "🔴")
        unit = v_match.get("unit", "-")
        iso_grp = v_match.get("iso_group", "GROUP 1")

        lines = [
            f"📊 **Status Vibrasi Mekanikal {eq_name}**: {badge} {st_val}",
            f"- **Unit**: {unit} | **Kategori ISO 10816-3**: {iso_grp}",
            f"- **Velocity RMS Max (Vmax)**: **{v_max:.2f} mm/s**",
            f"- **Tanggal Pengujian**: {v_match.get('test_date', '-')}",
        ]

        pts = v_match.get("points", {})
        if pts:
            pts_str = ", ".join(f"{k}: {v:.2f} mm/s" for k, v in pts.items())
            lines.append(f"- **Titik Pengukuran**: {pts_str}")

        if st_val == "NORMAL":
            lines.append("\n✅ Tingkat vibrasi dalam batas aman (Zone A/B ISO 10816-3). Kondisi mekanis dan bearing prima.")
        elif "WARN" in st_val or "PRE" in st_val:
            lines.append("\n⚠️ Tingkat vibrasi dalam batas perhatian (Zone C ISO 10816-3). Disarankan inspeksi unbalance/misalignment dan pelumasan bearing.")
        else:
            lines.append("\n🚨 Tingkat vibrasi kritis (Zone D ISO 10816-3). Resiko kerusakan struktural/bearing tinggi, jadwalkan investigasi segera.")

        return "\n".join(lines)

    def get_thermal_status(self, eq_name: str) -> str:
        """Pemeriksaan khusus domain termal (IRT) untuk peralatan."""
        try:
            from src.thermal_data import search_thermal_records
            t_records = search_thermal_records(search=eq_name)
        except Exception:
            t_records = []

        if not t_records:
            return f"Data inspeksi termal (IRT) untuk {eq_name} tidak ditemukan dalam database."

        rec = t_records[0]
        st_val = rec.get("status", "NORMAL")
        badge = "🟢" if st_val == "NORMAL" else ("🟡" if "WARN" in st_val or "PRE" in st_val else "🔴")

        lines = [
            f"🌡️ **Status Suhu & Thermography (IRT) {eq_name}**: {badge} {st_val}",
            f"- **Unit**: {rec.get('unit', '-')} | **KKS**: {rec.get('kks', '-')}",
            f"- **Deskripsi**: {rec.get('equipment', eq_name)}",
            f"- **Status Lapangan**: **{rec.get('raw_status', '-')}**",
            f"- **Standar Evaluasi**: {rec.get('standard', 'Delta-T FLIR')}",
            f"- **Tanggal Inspeksi**: {rec.get('test_date', '-')}",
        ]
        if st_val == "NORMAL":
            lines.append("\n✅ Temperatur dalam batas normal (Delta-T < 10°C). Tidak terdeteksi hotspot atau sambungan kendor.")
        else:
            lines.append("\n⚠️ Terdeteksi anomali temperatur / delta-T berlebih. Periksa koneksi baut, kontaktor, atau pendinginan motor.")

        return "\n".join(lines)

    def get_tribology_status(self, eq_name: str) -> str:
        """Pemeriksaan khusus domain pelumas/oli (Tribology) untuk peralatan."""
        try:
            from src.tribology_data import search_tribology_samples
            o_samples = search_tribology_samples(search=eq_name)
        except Exception:
            o_samples = []

        if not o_samples:
            return f"Data pengujian laboratorium pelumas (Tribology) untuk {eq_name} tidak ditemukan."

        sample = o_samples[0]
        st_val = sample.get("status", "NORMAL")
        badge = "🟢" if st_val == "NORMAL" else ("🟡" if "WARN" in st_val or "PRE" in st_val else "🔴")

        lines = [
            f"🛢️ **Status Pelumasan & Laboratorium Oli {eq_name}**: {badge} {st_val}",
            f"- **Sample ID**: {sample.get('sample_id', '-')} | **Brand Oli**: {sample.get('oil_brand', '-')} ({sample.get('oil_type', '-')})",
            f"- **Viskositas @ 40°C**: **{sample.get('viscosity_40c', '-')} cSt**",
            f"- **Kandungan Air**: **{sample.get('water_ppm', '-')} ppm** (Batas aman < 200 ppm)",
            f"- **Nilai Asam (TAN)**: **{sample.get('tan', '-')} mgKOH/g** (Batas aman < 0.6)",
            f"- **Partikel Keausan Fe**: **{sample.get('wear_fe', '-')} ppm** | **Cu**: **{sample.get('wear_cu', '-')} ppm**",
            f"- **Kebersihan ISO 4406**: {sample.get('iso_cleanliness', '-')}",
            f"- **Tanggal Sampling**: {sample.get('sampling_date', '-')}",
        ]
        eval_findings = sample.get("evaluation", {}).get("findings", [])
        if eval_findings:
            lines.append("\n📋 **Temuan Analisa:**")
            for f in eval_findings:
                lines.append(f"- {f}")

        return "\n".join(lines)

    def get_dga_status(self, eq_name: Optional[str] = None) -> str:
        """Pemeriksaan khusus dan diagnosa DGA trafo berdasarkan hasil uji laboratorium terkini."""
        if eq_name:
            try:
                from src.dga_data import get_dga_transformer_detail
                trf = get_dga_transformer_detail(eq_name)
                if trf:
                    st_val = trf.get("status", "NORMAL")
                    badge = "🟢" if st_val == "NORMAL" else ("🟡" if "WARN" in st_val or "PRE" in st_val else "🔴")
                    g = trf.get("gases", {})
                    diag = trf.get("diagnosis", {})

                    lines = [
                        f"⚡ **Hasil Analisis DGA & Minyak Trafo: {trf.get('name', eq_name)}**",
                        f"- **Asset ID**: `{trf.get('transformer_id', '-')}` | **Unit**: {trf.get('unit', '-')}",
                        f"- **Status Keseluruhan**: {badge} **{st_val}** ({diag.get('ieee_condition', 'IEEE C57.104')})",
                        f"- **Tanggal Uji Lab Terakhir**: **{trf.get('sampling_date', '-')}**",
                        f"- **Nameplate**: Tegangan: {trf.get('voltage_ratio', '-')} | Kapasitas: {trf.get('rated_capacity', '-')} | Volume Minyak: {trf.get('oil_volume', '-')}",
                        "",
                        "🧪 **Konsentrasi Gas Terlarut (Dissolved Gas Analysis - ppm):**",
                        f"- **H₂ (Hidrogen)**: **{g.get('H2', 0.0)} ppm** (Indikasi PD/Corona, Batas aman < 100 ppm)",
                        f"- **CH₄ (Metana)**: **{g.get('CH4', 0.0)} ppm** (Indikasi Thermal T < 300°C, Batas aman < 120 ppm)",
                        f"- **C₂H₆ (Etana)**: **{g.get('C2H6', 0.0)} ppm** (Indikasi Thermal T < 300°C, Batas aman < 65 ppm)",
                        f"- **C₂H₄ (Etilena)**: **{g.get('C2H4', 0.0)} ppm** (Indikasi Thermal T > 300°C, Batas waspada > 50 ppm)",
                        f"- **C₂H₂ (Asetilena)**: **{g.get('C2H2', 0.0)} ppm** (Indikasi Arcing Listrik, Batas kritis > 1 ppm)",
                        f"- **CO (Karbon Monoksida)**: **{g.get('CO', 0.0)} ppm** | **CO₂**: **{g.get('CO2', 0.0)} ppm**",
                        f"- **TDCG (Total Combustible Gas)**: **{diag.get('tdcg', 0.0)} ppm** (Kategori IEEE C57.104: {diag.get('ieee_condition', 'Condition 1')})",
                        "",
                        "📐 **Diagnosa Segitiga Duval 1 & Rasio Gas:**",
                        f"- **Metode Duval Triangle 1**: **{diag.get('duval_diagnosis', 'Normal Operation')}**",
                        f"- **Rasio CO₂/CO**: **{diag.get('co2_co_ratio', 0.0)}** ({diag.get('paper_status', 'Normal')})",
                        f"- **Rogers Ratios**: **{diag.get('rogers_diagnosis', 'Normal')}**",
                    ]

                    w_ppm = trf.get("water_content", g.get("H2O", 0.0))
                    bdv_val = trf.get("bdv", 0.0)
                    lines.extend([
                        "",
                        "💧 **Kualitas Fisik Minyak & Uji Dielektrik:**",
                        f"- **Kandungan Air (Water Content)**: **{w_ppm} ppm** (Batas aman < 20 ppm — Isolasi Kering)",
                        f"- **Tegangan Tembus (Dielectric Breakdown Voltage / BDV)**: **{bdv_val} kV** (Standar IEC 156 > 30 kV — Sangat Baik)",
                    ])

                    history = trf.get("history", [])
                    if len(history) > 1:
                        lines.append("\n📈 **Riwayat & Tren DGA Sebelumnya:**")
                        for h in history:
                            lines.append(
                                f"- **{h.get('date')}**: TDCG={h.get('tdcg')} ppm | H₂={h.get('H2')} ppm, CH₄={h.get('CH4')} ppm, C₂H₄={h.get('C2H4')} ppm, CO={h.get('CO')} ppm | Status: {h.get('status')}"
                            )

                    rec = trf.get("recommendation")
                    if rec:
                        lines.append(f"\n🛠️ **Rekomendasi Pemeliharaan:**\n- {rec}")

                    return "\n".join(lines)
            except Exception:
                pass

        # Ringkasan armada transformer jika tidak menyebut peralatan spesifik
        try:
            from src.dga_data import search_dga_transformers
            trafos = search_dga_transformers()
            if trafos:
                lines = [
                    "⚡ **Status Armada Transformer & Standar DGA PLTU Jeranjang:**\n",
                    f"Total transformer termonitor: **{len(trafos)} unit** (Data terintegrasi Laporan CI19048).",
                    "\n**Ringkasan Status Trafo Terkini:**",
                ]
                for t in trafos:
                    st = t.get("status", "NORMAL")
                    b = "🟢" if st == "NORMAL" else ("🟡" if "WARN" in st or "PRE" in st else "🔴")
                    g = t.get("gases", {})
                    tdcg_val = round(sum([g.get('H2', 0), g.get('CH4', 0), g.get('C2H6', 0), g.get('C2H4', 0), g.get('C2H2', 0), g.get('CO', 0)]), 1)
                    lines.append(f"- {b} **{t.get('name')}** ({t.get('unit')}): Status **{st}** | TDCG: {tdcg_val} ppm | Sampling: {t.get('sampling_date')}")
                lines.append("\n💡 *Sebutkan nama trafo (misal: 'DGA UAT 3' atau 'Kondisi Main Trafo Unit 1') untuk melihat rincian gas, rasio, dan Segitiga Duval.*")
                return "\n".join(lines)
        except Exception:
            pass

        return self.get_dga_standard_reference()

    def get_dga_standard_reference(self) -> str:
        """Rujukan standar DGA (IEEE C57.104, Duval Triangle) tanpa data peralatan spesifik."""
        return (
            "⚡ **Status & Standar DGA (Dissolved Gas Analysis) Trafo:**\n\n"
            "Diagnosa gas terlarut pada minyak transformator mengacu pada standar **IEEE C57.104** dan metode **Duval Triangle**.\n\n"
            "**Parameter Kunci:**\n"
            "- **H2 (Hidrogen)**: Mengindikasikan lucutan parsial (Partial Discharge) atau corona (>100 ppm: Perhatian).\n"
            "- **CH4 (Metana) & C2H6 (Etana)**: Mengindikasikan overheating termal minyak suhu rendah (<300°C).\n"
            "- **C2H4 (Etilena)**: Overheating minyak suhu tinggi (>300°C - 700°C, >50 ppm: Waspada).\n"
            "- **C2H2 (Asetilena)**: Indikasi arcing listrik berenergi tinggi (Batas kritis >1-2 ppm!).\n"
            "- **CO & CO2**: Degradasi dan penuaan isolasi kertas selulosa trafo (Rasio CO2/CO < 3 atau > 10).\n\n"
            "💡 *Sebutkan nama trafo spesifik (misal: 'UAT 3') untuk melihat hasil DGA terkini.*"
        )

    def get_vibration_alarm_list(self) -> str:
        """Daftar peralatan yang mengalami alarm/warning pada domain vibrasi."""
        try:
            from src.vibration_data import load_vibration_monthly_tests
            v_tests = load_vibration_monthly_tests()
            warns = [t for t in v_tests if t.get("status") in ("WARNING", "ALARM", "HIGH", "CRITICAL")]
            if not warns:
                return "✅ Semua titik vibrasi berada dalam batas Normal/Satisfactory (ISO 10816-3)."
            res = "⚠️ **Daftar Equipment Alarm / Warning Vibrasi:**\n"
            for w in warns:
                res += f"- 🟡 **{w.get('equipment')}** ({w.get('unit')}): Status **{w.get('status')}** — Vmax: {w.get('velocity_max', 0):.2f} mm/s\n"
            return res
        except Exception as e:
            return f"Gagal memuat data alarm vibrasi: {e}"

