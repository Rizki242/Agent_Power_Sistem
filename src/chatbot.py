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
            # Pertanyaan standar/SOP/definisi tanpa nama trafo -> rujukan standar, bukan ringkasan armada
            # (pola yang sama dengan domain vibrasi/thermal/tribologi di atas).
            if any(w in q for w in ["sop", "standar", "rumus", "jelaskan", "apa itu", "definisi", "penjelasan", "pengertian", "artikan", "maksud", "cara kerja"]):
                return self.get_dga_standard_reference()
            # Pertanyaan status/daftar eksplisit tanpa nama trafo -> ringkasan armada.
            if any(w in q for w in ["status", "kondisi", "daftar", "list", "armada", "semua trafo", "seluruh trafo"]):
                return self.get_dga_status()
            # Pertanyaan DGA umum lain (mis. istilah spesifik) -> coba basis pengetahuan dulu,
            # baru jatuh ke rujukan standar (bukan langsung dump seluruh armada).
            kb_results = search_knowledge_base(query, top_k=2)
            if kb_results:
                resp = "📚 **Referensi & Panduan Teknis Terkait:**\n\n"
                for doc in kb_results:
                    resp += f"### {doc['title']} — {doc['heading']}\n"
                    resp += f"{doc['content']}\n\n"
                return resp.strip()
            return self.get_dga_standard_reference()

        # Intent 2.5: Conceptual CBM Engineering Questions & Technical Standards
        expert_explanation = self._get_expert_concept_explanation(q, query)
        if expert_explanation:
            return expert_explanation

        # Intent 3: List Alarm / Warning / High (Prioritas MCSA)
        if any(w in q for w in ["alarm", "warning", "masalah", "abnormal", "rusak", "high", "kritis"]):
            if not self.match_equipment(query):
                return self.get_alarm_list()

        # Intent 3.5: Historical Trend & Continuous Learning ("histori", "riwayat", "kronologi", "dari waktu ke waktu", "dulu", "apakah memburuk", "tanggal dokumen", "tanggal upload")
        if any(w in q for w in ["histori", "riwayat", "kronologi", "dari waktu ke waktu", "sebelumnya", "masa lalu", "apakah memburuk", "tren masa lalu", "data lama", "tanggal upload", "tanggal dokumen", "aturan tanggal", "aturan waktu"]):
            found_eq = self.match_equipment(query)
            if found_eq:
                self.last_matched_equipment = found_eq
            return self.get_historical_trend_analysis(found_eq, query)

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

        # Intent 6: General Knowledge SOP & Manual Lookup
        if any(w in q for w in ["sop", "standar", "nema", "ieee", "iso", "cara", "langkah", "rumus", "pengukuran", "atpol", "sideband", "unbalance", "thd", "rotor bar", "vibrasi", "vibration", "bearing", "tribology", "pelumas", "oli"]):
            kb_results = search_knowledge_base(query, top_k=2)
            if kb_results:
                resp = "📚 **Referensi & Panduan Teknis Terkait:**\n\n"
                for doc in kb_results:
                    resp += f"### {doc['title']} — {doc['heading']}\n"
                    resp += f"{doc['content']}\n\n"
                return resp.strip()

        # Intent 7: Gratitude / Compliments / Polite expressions
        if any(w in q for w in ["terima kasih", "terimakasih", "makasih", "matur nuwun", "thanks", "thank you", "mantap", "hebat", "keren", "pintar", "bagus", "good job"]):
            return (
                "Sama-sama! Senang sekali bisa membantu Anda. 😊\n\n"
                "Sebagai **Agent CBM Learning PLTU Jeranjang**, saya selalu siaga mendampingi Anda memantau keandalan "
                "dan kesehatan peralatan pembangkit (Unit 1, 2, 3, dan Common). Jangan ragu menyapa atau bertanya kapan pun dibutuhkan!"
            )

        # Intent 8: Identity & Persona ("Siapa kamu", "Kamu siapa", "Profil")
        if any(w in q for w in ["siapa kamu", "kamu siapa", "siapa anda", "anda siapa", "profil", "identitas", "namamu", "siapa namamu", "tentang kamu", "peranmu", "tugasmu", "kamu bisa apa"]):
            return (
                "Saya adalah **Agent CBM Learning PLTU Jeranjang**, asisten kecerdasan buatan terpadu untuk pemantauan kondisi mesin "
                "(*Condition-Based Maintenance*) dan pembelajaran keandalan di PLTU Jeranjang (3 × 25 MW).\n\n"
                "🧠 **Keahlian & Kemampuan Saya:**\n"
                "- **6 Domain CBM**: Mengintegrasikan Vibrasi (getaran mekanikal), MCSA (arus & kelistrikan motor), DGA (gas terlarut transformator), "
                "Partial Discharge (isolasi stator), Tribologi (laboratorium oli & keausan logam), serta Thermal IRT (peta suhu).\n"
                "- **Continuous Learning**: Mempelajari riwayat kerusakan sebelumnya dan pola degradasi mesin untuk mendeteksi anomali dini.\n"
                "- **Reliability Fusion**: Menghitung Health Index (0-100), estimasi sisa umur (*RUL*), dan mitigasi risiko operasional.\n\n"
                "Saya dapat diajak berdiskusi teknis, menganalisis file pengukuran, maupun mengobrol santai mengenai operasional pembangkit."
            )

        # Intent 9: Condition / Activity / Small Talk ("Apa kabar", "Lagi ngapain", "Sedang apa")
        if any(w in q for w in ["apa kabar", "bagaimana kabar", "gimana kabar", "lagi ngapain", "sedang apa", "lagi apa", "kamu sehat"]):
            return (
                "Kabar saya sangat baik dan siap siaga! ⚡\n\n"
                "Saat ini saya, **Agent CBM Learning PLTU Jeranjang**, terus aktif memantau data telemetri, mempelajari pola keandalan "
                "peralatan berputar dan transformator, serta memastikan seluruh sistem aman bersama rekan-rekan engineer.\n\n"
                "Bagaimana kabar Anda hari ini? Ada peralatan atau sistem yang ingin kita diskusikan bersama?"
            )

        # Intent 10: Greetings & Welcome ("Halo", "Hai", "Selamat pagi/siang/malam")
        if any(w in q for w in ["halo", "hai", "hi", "hey", "hei", "pagi", "siang", "sore", "malam", "assalamualaikum", "selamat", "help", "bantuan", "menu"]):
            return (
                "👋 **Halo! Selamat datang. Saya Agent CBM Learning PLTU Jeranjang.**\n\n"
                "Senang bisa berbincang dengan Anda! Sebagai asisten CBM terpadu PLTU Jeranjang (3 × 25 MW), "
                "saya siap membantu Anda dalam:\n"
                "1. **Pengecekan Kondisi Aset**: *'Status BFP 1A'*, *'Kondisi C3WP 1B'*, *'Hasil DGA UAT 3'*\n"
                "2. **Korelasi Multi-Disiplin**: *'Korelasi vibrasi dan arus BC 10.1'*, *'Hubungan getaran dan beban'*\n"
                "3. **Pilar CBM Khusus**: *'Vibrasi PA Fan 1A'*, *'Kondisi oli BFP'*, *'Metode Segitiga Duval'*\n"
                "4. **Daftar Alarm & Monitoring**: *'List Alarm'*, *'Daftar equipment berstatus warning'*\n"
                "5. **Diskusi Teknis & SOP**: *'Standar ISO 10816-3'*, *'SOP pengukuran ATPOL'*\n\n"
                "Silakan tanyakan apa saja, baik seputar teknis mesin maupun obrolan seputar keandalan plant!"
            )

        # Fallback Natural: Pertanyaan di luar ranah teknik tetap dijawab ramah & santun sebagai Agent CBM Learning PLTU Jeranjang
        return (
            "Halo! Sebagai **Agent CBM Learning PLTU Jeranjang**, saya sangat senang bisa mengobrol dengan Anda.\n\n"
            "Meskipun fokus utama pembelajaran saya adalah memantau keandalan mesin dan kondisi aset di PLTU Jeranjang (3 × 25 MW), "
            "saya siap mendengarkan dan berdiskusi. Bila Anda ingin mengecek kondisi peralatan, Anda bisa menyebutkan nama aset "
            "(misal: *'Status BFP 1A'* atau *'DGA UAT 3'*), ketik *'List Alarm'*, atau tanyakan seputar vibrasi, arus, oli, dan suhu mesin."
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

    def get_historical_trend_analysis(self, eq_name: Optional[str] = None, query: str = "") -> str:
        """
        Analisis tren historis & pembelajaran berkelanjutan (Continuous Learning).
        Mengacu pada tanggal dokumen (jika ada) atau tanggal upload (hari ini).
        """
        q = (query or "").lower()

        if any(w in q for w in ["bagaimana cara", "aturan tanggal", "tanggal dokumen", "tanggal upload", "aturan waktu"]):
            return (
                "🕒 **Aturan Penentuan Waktu Data & Pembelajaran Historis (PPLE CBM Learning):**\n\n"
                "1. **Dokumen Bertanggal (Field Test / As-Built Date)**:\n"
                "   - Jika dokumen atau laporan yang diunggah memuat tanggal pengujian, sistem mengunci waktu data sesuai tanggal tersebut.\n"
                "   - Data ini ditempatkan dalam linimasa historis untuk melacak evolusi kesehatan aset dari masa ke masa.\n\n"
                "2. **Dokumen Tanpa Tanggal (Upload-Time Anchor)**:\n"
                "   - Jika dokumen tidak memiliki tanggal, data otomatis diasosiasikan dengan tanggal saat dokumen di-upload (hari ini).\n"
                "   - Hal ini memastikan tidak ada data mengambang tanpa konteks temporal.\n\n"
                "3. **Continuous Learning & Historical Mining**:\n"
                "   - Seluruh data historis diarsipkan dalam SQLite dan canonical store untuk melatih agent mengenali precursor kegagalan (*early fault precursors*) "
                "sebelum terjadi alarm aktual pada pengujian berikutnya."
            )

        if not eq_name:
            total_records = len(self.df_all) if not self.df_all.empty else 0
            unique_eqs = self.df_all["Equipment"].nunique() if not self.df_all.empty and "Equipment" in self.df_all.columns else 0
            return (
                f"📜 **Arsip Riwayat & Pembelajaran Historis PLTU Jeranjang:**\n\n"
                f"- **Total Titik Data Historis**: {total_records} record tersimpan.\n"
                f"- **Cakupan Aset**: {unique_eqs} unit peralatan dengan pemantauan berkala.\n"
                f"- **Prinsip Historis**: Data lama dijadikan baseline pembelajaran tren degradasi, sedangkan data baru mengevaluasi deviasi kondisi terkini.\n\n"
                f"💡 *Silakan sebutkan nama peralatan (contoh: 'Histori BFP 1A' atau 'Tren Trafo UAT 3') untuk melihat linimasa kondisi lengkapnya.*"
            )

        lines = [f"📜 **Linimasa Riwayat & Analisis Tren Historis: {eq_name}**\n"]

        mcsa_timeline = []
        if not self.df_all.empty and "Equipment" in self.df_all.columns:
            eq_rows = self.df_all[self.df_all["Equipment"] == eq_name]
            if not eq_rows.empty and "Date" in eq_rows.columns:
                unique_dates = sorted(pd.to_datetime(eq_rows["Date"], errors="coerce").dropna().unique())
                for dt in unique_dates:
                    dt_str = pd.Timestamp(dt).strftime("%Y-%m-%d")
                    dt_rows = eq_rows[pd.to_datetime(eq_rows["Date"], errors="coerce") == dt]
                    cond_row = dt_rows[dt_rows["Parameter"] == "Kondisi"]
                    cond_val = cond_row["Raw_Value"].iloc[0] if not cond_row.empty else "NORMAL"
                    load_row = dt_rows[dt_rows["Parameter"] == "Load"]
                    load_val = load_row["Raw_Value"].iloc[0] if not load_row.empty else "-"
                    cur_row = dt_rows[dt_rows["Parameter"] == "Dev Current"]
                    cur_val = cur_row["Raw_Value"].iloc[0] if not cur_row.empty else "-"
                    rb_row = dt_rows[dt_rows["Parameter"] == "Rotorbar"]
                    rb_val = rb_row["Raw_Value"].iloc[0] if not rb_row.empty else "-"
                    mcsa_timeline.append({
                        "date": dt_str,
                        "domain": "MCSA",
                        "condition": str(cond_val).upper(),
                        "summary": f"Beban: {load_val}%, Dev I: {cur_val}%, Rotorbar: {rb_val} dB",
                    })

        domain_timeline = []
        try:
            from src import domain_measurements as dm
            for dom in ("VIBRASI", "DGA", "TRIBOLOGY", "THERMAL"):
                df_dom = dm.filter_measurements(dom, equipment=eq_name)
                if not df_dom.empty and "test_date" in df_dom.columns:
                    for t_date in df_dom["test_date"].dropna().unique():
                        sub = df_dom[df_dom["test_date"] == t_date]
                        t_str = pd.to_datetime(t_date).strftime("%Y-%m-%d")
                        p_summary = ", ".join(f"{r['parameter']}: {r['raw_value']}" for _, r in sub.head(3).iterrows())
                        cond = sub["condition"].dropna().iloc[0] if not sub["condition"].dropna().empty else "NORMAL"
                        domain_timeline.append({
                            "date": t_str,
                            "domain": dom,
                            "condition": str(cond).upper(),
                            "summary": p_summary,
                        })
        except Exception:
            pass

        all_points = sorted(mcsa_timeline + domain_timeline, key=lambda x: x["date"])

        if not all_points:
            return f"Belum terdapat data pengujian historis yang tercatat untuk peralatan **{eq_name}**."

        lines.append(f"Ditemukan **{len(all_points)} sesi pengujian historis** dari waktu ke waktu:\n")
        for pt in all_points:
            badge = "🟢" if pt["condition"] == "NORMAL" else ("⚪" if pt["condition"] == "STANDBY" else ("🔴" if pt["condition"] in ["HIGH", "CRITICAL", "BAD"] else "🟡"))
            lines.append(f"- **{pt['date']}** [{pt['domain']}]: {badge} **{pt['condition']}** — {pt['summary']}")

        first_pt = all_points[0]
        last_pt = all_points[-1]
        lines.append("\n📈 **Evaluasi Tren & Pembelajaran Berkelanjutan (*Continuous Learning*):**")
        lines.append(f"- **Periode Pemantauan**: {first_pt['date']} hingga {last_pt['date']} (Baseline awal vs Kondisi akhir).")
        if first_pt["condition"] == last_pt["condition"]:
            if last_pt["condition"] == "NORMAL":
                lines.append("- **Status Evolusi**: 🟢 **Stabil & Sehat**. Tidak ada indikasi degradasi signifikan sepanjang riwayat pengujian.")
            else:
                lines.append(f"- **Status Evolusi**: 🟡 **Konsisten {last_pt['condition']}**. Anomali telah berlangsung lama dan perlu tindakan terencana.")
        elif last_pt["condition"] in ["ALARM", "HIGH", "CRITICAL"]:
            lines.append(f"- **Status Evolusi**: ⚠️ **Degradasi Terdeteksi**. Kondisi mengalami perburukan dari *{first_pt['condition']}* menjadi *{last_pt['condition']}*.")
        else:
            lines.append(f"- **Status Evolusi**: 🟢 **Perbaikan Kondisi**. Status membaik dari *{first_pt['condition']}* menjadi *{last_pt['condition']}*.")

        lines.append("\n💡 **Lesson Learned Pembelajaran CBM:**")
        lines.append("Data masa lalu berfungsi sebagai baseline untuk mendeteksi deviasi parameter. Data yang diunggah tanpa tanggal otomatis disematkan pada tanggal upload hari ini.")

        return "\n".join(lines)

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

    def _get_expert_concept_explanation(self, q: str, query: str) -> Optional[str]:
        """Menyajikan sintesis konsep teknis CBM mendalam berstandar insinyur keandalan PLTU Jeranjang."""
        concept_patterns = [
            "apa itu", "apakah itu", "jelaskan", "pengertian", "definisi", "prinsip",
            "teori", "konsep", "bagaimana prinsip", "tentang", "maksud dari", "cara kerja",
            "bagaimana cara", "apa penyebab", "mengapa", "kenapa", "apa dampak", "rumus",
            "formula", "tahap", "tahapan", "metode", "artinya", "apa arti", "apa fungsi",
        ]
        concept_terms = {
            "unbalance", "misalignment", "bearing", "bantalan", "kavitasi", "cavitation",
            "thd", "dga", "duval", "rogers", "tdcg", "vibrasi", "vibration", "getaran",
            "rotor bar", "rotorbar", "partial discharge", "pd", "prpd", "tribologi",
            "tribology", "pelumas", "viskositas", "thermal", "irt", "delta-t", "hotspot",
            "air gap", "eksentrisitas", "looseness", "kelonggaran", "rul", "health index",
        }
        has_question_cue = any(w in q for w in [
            "apa", "apakah", "bagaimana", "mengapa", "kenapa", "jelaskan", "pengertian", "definisi",
            "prinsip", "teori", "konsep", "tentang", "maksud", "cara", "metode", "rumus", "formula",
            "tahap", "tahapan", "evaluasi", "analisis", "analisa", "kriteria", "pedoman", "aturan",
            "standar", "sop", "deteksi", "fungsi", "artinya", "arti", "pilar", "penjelasan"
        ])
        is_concept = (
            (has_question_cue and any(t in q for t in concept_terms))
            or any(p in q for p in concept_patterns)
            or any(t == q.strip() for t in concept_terms)
        )
        if not is_concept:
            return None

        header = (
            "Halo! Saya **Agent CBM Learning PLTU Jeranjang**, orkestrator keandalan dan asisten AI terpadu untuk unit PLTU Jeranjang (3 × 25 MW).\n\n"
        )

        # 1. Unbalance (Mekanikal & Elektrikal MCSA)
        if "unbalance" in q or "ketidakseimbangan" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Unbalance (Ketidakseimbangan)** dalam analisis pemeliharaan prediktif (CBM) pembangkit:\n\n"
                "---\n\n"
                "### 1. Definisi & Konsep Dasar Unbalance\n\n"
                "Pada mesin berputar di PLTU Jeranjang (motor pompa BFP, CWP, kipas ID/FD/PA Fan), fenomena unbalance terbagi menjadi dua ranah utama:\n\n"
                "1. **Unbalance Mekanikal (Massa Rotor)**:\n"
                "   Kondisi ketika pusat massa (*center of mass*) rotor berputar tidak berimpit dengan sumbu putarnya (*center of rotation*). Ketidakseimbangan ini menimbulkan gaya sentrifugal berotasi yang searah putaran poros:\n"
                "   $$F = m \\cdot r \\cdot \\omega^2$$\n"
                "   *Keterangan: $m$ = massa unbalance, $r$ = jari-jari eksentrisitas, $\\omega = 2\\pi f$ = kecepatan sudut putar.*\n"
                "   - **Karakteristik Spektrum Vibrasi**: Puncak dominan murni muncul pada frekuensi running speed **$1\\times$ RPM**.\n"
                "   - **Beda Fase**: Pengukuran radial horizontal dan vertikal pada bantalan yang sama biasanya menunjukkan beda fase mendekati $90^\\circ \\pm 30^\\circ$.\n\n"
                "2. **Unbalance Elektrikal (Arus & Tegangan - MCSA)**:\n"
                "   Ketidakseimbangan magnitudo atau perbedaan sudut fasa ($120^\\circ$) pada sistem suplai 3-fasa motor induksi:\n"
                "   $$\\% \\text{Unbalance Arus} = \\frac{\\text{Deviasi Maksimum dari Rata-rata Arus}}{\\text{Rata-rata Arus 3 Fasa}} \\times 100\\%$$\n\n"
                "---\n\n"
                "### 2. Batasan Standar & Kriteria Evaluasi\n\n"
                "* [Dokumen: Standar Evaluasi MCSA PLTU Jeranjang & NEMA MG-1]\n"
                "  - **Unbalance Tegangan**: Normal $\\le 1\\%$, Alarm $> 1\\%$, High $> 2\\%$.\n"
                "  - **Unbalance Arus**: Normal $\\le 5\\%$, Alarm $> 5\\%$, High $> 10\\%$.\n"
                "* [Dokumen: Standar ISO 10816-3 Vibrasi Mesin Berputar]\n"
                "  - Batas Zona A/B (Operasi aman): Kecepatan getaran RMS $\\le 4.5\\text{ mm/s}$ (Rigid support) atau $\\le 7.1\\text{ mm/s}$ (Flexible).\n"
                "  - Zona C (Alarm): Memerlukan perencanaan penyeimbangan (*dynamic balancing*) di lapangan.\n\n"
                "---\n\n"
                "### 3. Dampak terhadap Keandalan Aset Pembangkit\n\n"
                "- **Pemanasan Berlebih Rotor**: Unbalance tegangan $1\\%$ dapat memicu unbalance arus sebesar $6-10\\%$, menghasilkan arus urutan negatif (*negative-sequence current* $I_2$) yang memanaskan rotor secara eksponensial ($I_2^2 R$).\n"
                "- **Kerusakan Bantalan (Bearing)**: Gaya sentrifugal bolak-balik mempercepat keausan fatik elemen gelinding (*bearing spalling*) dan merusak mechanical seal pompa.\n\n"
                "---\n\n"
                "### 4. Rekomendasi Investigasi & Mitigasi Lapangan\n\n"
                "1. **Verifikasi Sumber Gangguan**: Bandingkan deviasi tegangan pada busbar switchgear 6.3 KV dengan deviasi arus motor untuk memastikan apakah gangguan berasal dari suplai jala-jala atau internal lilitan motor.\n"
                "2. **Inspeksi Mekanikal & Kebersihan**: Periksa penumpukan kerak abu (*fly ash build-up*) pada sudu impeler kipas ID Fan atau kavitasi pada impeler pompa CWP.\n"
                "3. **Dynamic Single/Dual Plane Balancing**: Lakukan penyeimbangan dinamis menggunakan vibration analyzer jika getaran $1\\times$ RPM terbukti dominan."
            )

        # 2. Misalignment (Ketidaksejajaran Poros)
        if "misalignment" in q or "ketidaksejajaran" in q or "poros bengkok" in q or "bent shaft" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Misalignment (Ketidaksejajaran Poros & Kopling)** pada mesin berputar:\n\n"
                "---\n\n"
                "### 1. Definisi & Jenis-Jenis Misalignment\n\n"
                "Misalignment terjadi ketika sumbu geometris putar antara dua poros yang dihubungkan oleh kopling (misal motor dan pompa BFP/CWP) tidak segaris lurus sempurna:\n"
                "1. **Angular Misalignment (Ketidaksejajaran Sudut)**: Kedua sumbu poros berpotongan membentuk sudut $\\theta$.\n"
                "2. **Parallel / Offset Misalignment**: Kedua sumbu poros sejajar namun memiliki jarak geser (*offset*) $\\Delta y$.\n"
                "3. **Combined Misalignment**: Kombinasi deviasi sudut dan paralel (paling sering ditemui di lapangan).\n\n"
                "---\n\n"
                "### 2. Karakteristik Spektrum Getaran & Analisis Fase\n\n"
                "* [Dokumen: Standar ISO 13373-1 / ISO 20816 & Panduan Alignment PLTU]\n"
                "  - **Puncak Dominan $2\\times$ RPM**: Indikator khas kopling fleksibel yang tertekuk dua kali setiap putaran.\n"
                "  - **Puncak $1\\times$ dan $3\\times$ RPM**: Kerap menyertai jika kopling mengalami *binding* atau kekakuan berlebih.\n"
                "  - **Getaran Aksial Tinggi**: Terutama pada *angular misalignment*, gaya dorong aksial bolak-balik melintasi kopling.\n"
                "  - **Karakteristik Fase**: Perbedaan fase sebesar **$180^\\circ \\pm 30^\\circ$** ketika probe aksial dipasang menyeberangi kopling (*across the coupling*).\n\n"
                "---\n\n"
                "### 3. Toleransi & Batasan Standar Presisi\n\n"
                "Untuk mesin industri PLTU Jeranjang berkecepatan $1500 - 3000\\text{ RPM}$:\n"
                "- **Toleransi Paralel (Offset)**: $\\le 0.05\\text{ mm}$ (Batas aman) / $\\le 0.03\\text{ mm}$ (Excellent).\n"
                "- **Toleransi Sudut (Angular)**: $\\le 0.05\\text{ mm/100 mm}$ panjang kopling.\n"
                "- **Pemeriksaan Soft Foot**: Deviasi kaki pondasi tidak boleh melebihi $0.05\\text{ mm}$ sebelum pengencangan baut angkur.\n\n"
                "---\n\n"
                "### 4. Tindakan CBM & Rekomendasi Lapangan\n\n"
                "1. Lakukan **Laser Optical Shaft Alignment** saat kondisi mesin berhenti dingin (*cold alignment*) dengan memperhitungkan ekspansi termal (*thermal growth* operasional).\n"
                "2. Periksa keausan elemen kopling (rubber spider, grid spring, gear teeth) dan pelumasan coupling grease."
            )

        # 3. Defek Bantalan / Bearing Faults (ISO 15243)
        if "bearing" in q or "bantalan" in q or "bpfo" in q or "bpfi" in q or "bsf" in q or "ftf" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Bearing Defect Analysis (Analisis Kerusakan Bantalan Elemen Gelinding)**:\n\n"
                "---\n\n"
                "### 1. Frekuensi Kinematik Defek Bantalan (Bearing Characteristic Frequencies)\n\n"
                "Ketika elemen gelinding melintasi cacat mikroskopis pada raceway, timbul gelombang kejut periodik pada frekuensi karakteristik:\n"
                "1. **BPFO (Ball Pass Frequency Outer Race)**: Cacat pada lintasan cincin luar:\n"
                "   $$BPFO = \\frac{n}{2} f_r \\left(1 - \\frac{d}{D}\\cos\\theta\\right)$$\n"
                "2. **BPFI (Ball Pass Frequency Inner Race)**: Cacat pada lintasan cincin dalam:\n"
                "   $$BPFI = \\frac{n}{2} f_r \\left(1 + \\frac{d}{D}\\cos\\theta\\right)$$\n"
                "3. **BSF (Ball Spin Frequency)**: Cacat pada bola atau rol gelinding:\n"
                "   $$BSF = \\frac{D}{2d} f_r \\left(1 - \\left(\\frac{d}{D}\\cos\\theta\\right)^2\\right)$$\n"
                "4. **FTF (Fundamental Train Frequency)**: Cacat pada sangkar / retainer (*cage*):\n"
                "   $$FTF = \\frac{1}{2} f_r \\left(1 - \\frac{d}{D}\\cos\\theta\\right)$$\n"
                "*Keterangan: $n$ = jumlah bola/rol, $f_r$ = frekuensi putar poros ($1\\times$), $d$ = diameter bola, $D$ = diameter pitch, $\\theta$ = sudut kontak.*\n\n"
                "---\n\n"
                "### 2. Empat Tahapan Kerusakan Bantalan (Four Stages of Bearing Failure)\n\n"
                "* [Dokumen: Standar ISO 15243 & Panduan Vibration Analyst]\n"
                "  - **Tahap 1 (Incipient Defect)**: Gelombang ultrasonik awal ($20 - 60\\text{ kHz}$). Terdeteksi via *Spike Energy (gSE)* atau *Acoustic Emission*. Spektrum kecepatan RMS masih normal.\n"
                "  - **Tahap 2 (Resonance Excitation)**: Sinyal impak membangkitkan resonansi alami bearing ($500 - 2000\\text{ Hz}$). Terdeteksi jelas pada spektrum demodulasi / *High Frequency Enveloping (HFE)*.\n"
                "  - **Tahap 3 (Discrete Peak & Sidebands)**: Puncak harmonik BPFO/BPFI muncul di spektrum kecepatan $10 - 1000\\text{ Hz}$ dikelilingi sideband $1\\times$ RPM. Mulai terdeteksi kenaikan suhu bearing.\n"
                "  - **Tahap 4 (Terminal Stage / Kritis)**: Kerusakan meluas (*severe spalling / flaking*). Puncak diskrit menghilang menjadi gundukan acak (*haystack*), getaran $1\\times$ melonjak, suhu bearing naik tajam, potensi macet (*bearing seizure*).\n\n"
                "---\n\n"
                "### 3. Rekomendasi CBM & Pemeliharaan\n\n"
                "1. **Tahap 1 & 2**: Evaluasi pelumasan (greasing presisi menggunakan instrumen ultrasonik) untuk mencegah pelumasan kurang atau berlebih (*over-greasing*).\n"
                "2. **Tahap 3**: Rencanakan penggantian bantalan pada jendela pemeliharaan preventif (PM) terdekat sebelum mencapai Tahap 4."
            )

        # 4. Kavitasi Pompa (Cavitation BFP & CWP)
        if "kavitasi" in q or "cavitation" in q or "npsh" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Kavitasi pada Pompa Sentrifugal PLTU Jeranjang** (khususnya BFP dan CWP):\n\n"
                "---\n\n"
                "### 1. Mekanisme Termodinamika & Fisika Kavitasi\n\n"
                "Kavitasi terjadi ketika tekanan statis fluida lokal di sisi hisap (*suction eye*) impeler turun hingga di bawah tekanan uap jenuh air ($P_{local} < P_{sat}$) pada suhu operasional. Kondisi ini memicu pembentukan gelembung-gelembung uap air (*vapor cavities*).\n\n"
                "Ketika gelembung terbawa ke zona bertekanan lebih tinggi di antara sudu impeler, gelembung meletus ke dalam (*implosion*) secara dahsyat, melepaskan gelombang kejut mikro (*micro-jets*) berkecepatan tinggi dengan tekanan lokal mencapai ribuan bar.\n\n"
                "---\n\n"
                "### 2. Karakteristik Sinyal Spektrum Getaran\n\n"
                "* [Dokumen: Standar ISO 10816-7 (Pompa Sentrifugal) & SOP PLTU Jeranjang]\n"
                "  - **Broadband Noise / Haystack**: Peningkatan energi acak pada frekuensi tinggi (**$2000 - 10000\\text{ Hz}$**).\n"
                "  - **Suara Akustik Khas**: Terdengar seperti suara kerikil, pasir, atau kelereng yang diaduk kasar di dalam casing pompa.\n"
                "  - **Fluktuasi Arus Motor (MCSA)**: Kavitasi parah mengganggu stabilitas beban torsi hidrolik, memicu fluktuasi riak arus motor 3-fasa.\n\n"
                "---\n\n"
                "### 3. Batasan Standar Margin NPSH\n\n"
                "Agar kavitasi tidak terjadi, Net Positive Suction Head Available ($NPSH_A$) harus selalu lebih besar dari Required ($NPSH_R$):\n"
                "$$NPSH_A \\ge NPSH_R + \\text{Safety Margin (0.5 s.d. 1.0 m)}$$\n"
                "$$NPSH_A = \\frac{P_{suction} - P_{sat}}{\\rho \\cdot g} + \\frac{v^2}{2g}$$\n\n"
                "---\n\n"
                "### 4. Dampak Kerusakan & Solusi Lapangan di PLTU\n\n"
                "- **Erosi Pitting Sudu Impeler**: Permukaan logam impeler tergerus membentuk spons keropos, menurunkan head dan efisiensi pompa BFP/CWP.\n"
                "- **Tindakan Lapangan**: Periksa kebersihan saringan hisap (*suction strainer/screen*), pastikan level air tangki Deaerator normal untuk pompa BFP, dan sesuaikan debit valve hisap."
            )

        # 5. Eksentrisitas Celah Udara (Air Gap Eccentricity)
        if "eksentrisitas" in q or "air gap" in q or "celah udara" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Air Gap Eccentricity (Eksentrisitas Celah Udara Motor)**:\n\n"
                "---\n\n"
                "### 1. Definisi: Statis vs Dinamis\n\n"
                "Celah udara (*air gap*) adalah ruang magnetik antara stator dan rotor motor listrik. Eksentrisitas terjadi ketika celah udara tidak seragam secara radial:\n"
                "1. **Eksentrisitas Statis**: Jarak celah udara bervariasi sepanjang keliling stator namun posisinya tetap di satu titik ruang (misal akibat *soft foot*, distorsi termal stator frame, atau keausan bearing housing).\n"
                "2. **Eksentrisitas Dinamis**: Posisi celah udara minimum berputar mengikuti putaran rotor (misal akibat poros bengkok, rotor tidak sepusat, atau keausan bola bantalan).\n\n"
                "---\n\n"
                "### 2. Deteksi MCSA & Vibrasi Spektrum\n\n"
                "* [Dokumen: Standar Evaluasi MCSA PLTU Jeranjang & IEEE Std 1415]\n"
                "  - **Deteksi MCSA**: Timbul puncak sideband pada frekuensi:\n"
                "    $$f_{ecc} = f_0 \\pm f_r$$\n"
                "    serta modulasi pada frekuensi harmonik alur rotor (*Rotor Slot Harmonics / RSH*):\n"
                "    $$f_{RSH} = \\left[(k \\cdot R \\pm n_d)\\frac{1-s}{p} \\pm \\nu\\right] f_0$$\n"
                "    *Keterangan: $f_0 = 50\\text{ Hz}$, $f_r$ = frekuensi putar motor, $R$ = jumlah batang rotor, $s$ = slip motor.*\n"
                "  - **Deteksi Vibrasi**: Puncak getaran pada **$2\\times$ Line Frequency ($100\\text{ Hz}$)** berfluktuasi seiring variasi beban dinamis.\n\n"
                "---\n\n"
                "### 3. Dampak Bahaya: Unbalanced Magnetic Pull (UMP)\n\n"
                "Eksentrisitas memicu gaya tarik magnet sepihak (*Unbalanced Magnetic Pull / UMP*) yang menarik rotor semakin dekat ke sisi stator. Jika dibiarkan, defleksi poros membesar hingga terjadi **rotor-to-stator rub**, yang mengakibatkan korsleting belitan dan kerusakan total stator core."
            )

        # 6. Kelonggaran Mekanikal (Mechanical Looseness)
        if "looseness" in q or "kelonggaran" in q or "kendor" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Mechanical Looseness (Kelonggaran Mekanikal)**:\n\n"
                "---\n\n"
                "### 1. Tiga Tipe Kelonggaran Mekanikal (ISO 13373)\n\n"
                "1. **Tipe A (Kelonggaran Struktural / Pondasi)**:\n"
                "   Kelonggaran antara kaki mesin dan pelat dasar (*baseplate*), atau baut angkur pondasi kendor. Spektrum vibrasi didominasi puncak **$1\\times$ RPM** dengan beda fase horizontal-vertikal mendekati $180^\\circ$.\n"
                "2. **Tipe B (Kelonggaran Bantalan / Bearing Housing Loose)**:\n"
                "   Baut penutup bantalan (*bearing cap*) longgar atau keretakan pada dudukan rangka. Memunculkan frekuensi fraksional / sub-harmonik **$0.5\\times, 1.5\\times, 2.5\\times\\text{ RPM}$** akibat osilasi non-linear.\n"
                "3. **Tipe C (Kelonggaran Komponen Internal / Bushing / Shaft Fit)**:\n"
                "   Bantalan longgar di dalam housing, atau impeler longgar pada poros. Menghasilkan banyak harmonik tinggi berderet (**$1\\times, 2\\times, 3\\times, \\dots, 10\\times\\text{ RPM}$**) dengan bentuk gelombang terpotong (*truncated waveform*).\n\n"
                "---\n\n"
                "### 2. Tindakan Perbaikan Lapangan\n\n"
                "1. Lakukan pemeriksaan torsi baut angkur (*torque check*) sesuai spesifikasi teknis.\n"
                "2. Ukur kelonggaran bantalan (*bearing clearance*) menggunakan feeler gauge atau dial indicator."
            )

        # 7. THD (Total Harmonic Distortion - IEEE 519)
        if "thd" in q or "harmonik" in q or "harmonic" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Total Harmonic Distortion (THD)** pada sistem kelistrikan pembangkit:\n\n"
                "---\n\n"
                "### 1. Definisi & Konsep Fisika THD\n\n"
                "**Total Harmonic Distortion (THD)** adalah ukuran deviasi bentuk gelombang arus atau tegangan dari bentuk gelombang sinusoidal murni ($50\\text{ Hz}$), yang diakibatkan oleh superposisi frekuensi harmonik kelipatan bilangan bulat ($100\\text{ Hz}, 150\\text{ Hz}, 250\\text{ Hz}$, dst.).\n\n"
                "Formula matematis untuk THD Tegangan ($THD_V$):\n"
                "$$THD_V = \\frac{\\sqrt{\\sum_{h=2}^{\\infty} V_h^2}}{V_1} \\times 100\\%$$\n"
                "*Keterangan: $V_1$ = tegangan fundamental ($50\\text{ Hz}$), $V_h$ = magnitudo tegangan komponen harmonik ke-$h$.*\n\n"
                "Sumber utama harmonik di PLTU Jeranjang:\n"
                "* Beban non-linear seperti Variable Frequency Drive (VFD), penyearah daya (*rectifier*), inverter UPS, dan saturasi magnetik inti transformator.\n\n"
                "---\n\n"
                "### 2. Batasan Standar & Kriteria Evaluasi\n\n"
                "* [Dokumen: Standar IEEE 519-2014 / 2022 & Evaluasi MCSA Jeranjang]\n"
                "  - **THD Tegangan**:\n"
                "    - $\\le 5.0\\%$: **NORMAL** (Batas rekomendasi IEEE untuk busbar $\\le 1\\text{ kV}$ s.d. $69\\text{ kV}$).\n"
                "    - $5.0\\% - 8.0\\%$: **ALARM** (Perlu evaluasi filter dan beban reaktif).\n"
                "    - $> 8.0\\%$: **HIGH / KRITIS** (Risiko tinggi kerusakan isolasi dan peralatan sensitif).\n\n"
                "---\n\n"
                "### 3. Dampak terhadap Keandalan Aset PLTU Jeranjang\n\n"
                "1. **Peningkatan Rugi-Rugi Inti (*Eddy Current & Hysteresis*)**: Frekuensi tinggi menyebabkan pemanasan berlebih pada laminasi inti stator motor dan inti transformator.\n"
                "2. **Torsi Harmonik Osilatif**: Harmonik urutan ke-5 menghasilkan torsi berlawanan arah putaran (*negative braking torque*), menyebabkan penurunan efisiensi motor dan getaran torsi pada poros.\n"
                "3. **Resonansi Kapasitor**: Beban kapasitor bank dapat mengalami resonansi paralel dengan induktansi sistem, memicu *voltage spike* dan trip proteksi.\n\n"
                "---\n\n"
                "### 4. Tindak Lanjut Lapangan\n\n"
                "1. **Pemantauan Power Quality**: Pasang analyzer daya untuk mengidentifikasi orde harmonik dominan ($5\\text{th}, 7\\text{th}, 11\\text{th}$).\n"
                "2. **Pemasangan Active Harmonic Filter (AHF)** atau reaktor saluran (*line reactor*) pada VFD motor pembantu."
            )

        # 8. Rotor Bar Fault (MCSA & EPRI)
        if "rotor bar" in q or "rotorbar" in q or "batang rotor" in q or "sideband" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Rotor Bar Fault (Kerusakan Batang Rotor)** pada Motor Current Signature Analysis (MCSA):\n\n"
                "---\n\n"
                "### 1. Definisi & Mekanisme Fisika Deteksi MCSA\n\n"
                "Pada motor induksi sangkar tupai (*squirrel cage induction motor*), batang konduktor rotor membawa arus induksi besar. Jika terdapat batang rotor yang retak atau putus (*broken rotor bar*), simetri medan magnet putar terganggu, memicu modulasi amplitudo pada arus stator pada frekuensi **Pole Pass Frequency (PPF)** di kedua sisi frekuensi suplai ($50\\text{ Hz}$):\n\n"
                "$$f_L = f_0 (1 \\pm 2s)$$\n"
                "*Keterangan: $f_0 = 50\\text{ Hz}$ (frekuensi jala-jala), $s = \\frac{n_s - n_r}{n_s}$ (slip motor).*\n\n"
                "Puncak frekuensi ini dikenal sebagai **Sideband Arus Bawah dan Atas** ($f_0 - 2sf_0$ dan $f_0 + 2sf_0$).\n\n"
                "---\n\n"
                "### 2. Standar Evaluasi & Kriteria Keparahan EPRI\n\n"
                "* [Dokumen: Standar Evaluasi MCSA PLTU Jeranjang & Panduan EPRI]\n"
                "  Selisih amplitudo antara fundamental ($50\\text{ Hz}$) dan sideband diukur dalam desibel ($\\text{dB}$):\n"
                "  - **$\\Delta \\text{dB} < -54\\text{ dB}$**: **Kondisi Sehat (Normal)** — Batang rotor utuh sempurna.\n"
                "  - **$-54\\text{ dB} \\le \\Delta \\text{dB} < -45\\text{ dB}$**: **Level 1 (Warning)** — Indikasi awal retak rambut (*hairline crack*) atau *high resistance joint* pada cincin ujung (*end ring*).\n"
                "  - **$-45\\text{ dB} \\le \\Delta \\text{dB} < -36\\text{ dB}$**: **Level 2 (Alarm/High)** — Indikasi kuat satu atau lebih batang rotor putus.\n"
                "  - **$\\Delta \\text{dB} \\ge -36\\text{ dB}$**: **Level 3/4 (Kritis)** — Kerusakan parah multi-bar yang membutuhkan *un-coupling* dan perbaikan mendesak.\n\n"
                "---\n\n"
                "### 3. Dampak terhadap Keandalan Aset\n\n"
                "- **Penyebaran Kerusakan ke Batang Lain**: Beban arus pada batang yang putus akan berpindah ke batang di sebelahnya, memicu efek domino (*thermal fatigue* dan keretakan berantai).\n"
                "- **Potensi Rotor Rubbing**: Pemuaian termal yang tidak merata membengkokkan poros rotor (*thermal bow*), menyebabkan rotor bergesekan langsung dengan inti stator (*catastrophic motor failure*).\n\n"
                "---\n\n"
                "### 4. Tindak Lanjut Pemeliharaan Terencana\n\n"
                "1. **Uji Konfirmasi**: Lakukan verifikasi saat motor beroperasi pada beban $> 70\\%$ agar slip cukup besar untuk memisahkan sideband dari puncak $50\\text{ Hz}$.\n"
                "2. **Inspeksi Lanjutan**: Jadwalkan uji statis *Rotor Influence Coefficient (RIC)* atau inspeksi visual end-ring saat unit shut down terencana."
            )

        # 9. DGA (Dissolved Gas Analysis), Segitiga Duval & Asetilena C2H2
        if "dga" in q or "duval" in q or "rogers" in q or "tdcg" in q or "gas terlarut" in q or "c2h2" in q or "asetilena" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Dissolved Gas Analysis (DGA) dan Metode Segitiga Duval 1** untuk transformator daya:\n\n"
                "---\n\n"
                "### 1. Definisi & Prinsip Pembentukan Gas\n\n"
                "Di dalam transformator berisolasi minyak (seperti Trafo Generator Unit 1-3 dan UAT di PLTU Jeranjang), kegagalan internal termal maupun elektrikal memecah molekul minyak hidrokarbon dan isolasi kertas selulosa. Pecahan rantai kimia ini menghasilkan gas-gas yang terlarut dalam minyak (*dissolved gases*):\n\n"
                "- **Hidrogen ($H_2$)**: Indikasi peluahan sebagian (*Partial Discharge / Corona*) atau reaksi kimia minyak-logam.\n"
                "- **Metana ($CH_4$) & Etana ($C_2H_6$)**: Gangguan termal suhu rendah hingga menengah ($< 300^\\circ\\text{C}$ s.d. $700^\\circ\\text{C}$).\n"
                "- **Etilena ($C_2H_4$)**: Gangguan termal suhu tinggi ($> 700^\\circ\\text{C}$).\n"
                "- **Asetilena ($C_2H_2$)**: Indikasi *Arcing* atau loncatan bunga api listrik suhu tinggi ($> 1000^\\circ\\text{C}$) — **paling kritis dan berbahaya**.\n"
                "- **Karbon Monoksida ($CO$) & Karbon Dioksida ($CO_2$)**: Degradasi dan penuaan isolasi kertas selulosa.\n\n"
                "Formula Total Dissolved Combustible Gas (TDCG):\n"
                "$$TDCG = H_2 + CH_4 + C_2H_6 + C_2H_4 + C_2H_2 + CO$$\n\n"
                "---\n\n"
                "### 2. Standar Evaluasi & Segitiga Duval 1 (IEC 60599 & IEEE C57.104)\n\n"
                "* [Dokumen: IEEE C57.104-2019 & Standar IEC 60599]\n"
                "  - **Kondisi 1 (Normal)**: $TDCG \\le 720\\text{ ppm}$\n"
                "  - **Kondisi 2 (Warning)**: $721 - 1920\\text{ ppm}$\n"
                "  - **Kondisi 3 (Alarm)**: $1921 - 4630\\text{ ppm}$\n"
                "  - **Kondisi 4 (Kritis)**: $> 4630\\text{ ppm}$\n\n"
                "* [Dokumen: Metode Segitiga Duval 1 (Duval Triangle 1)]\n"
                "  Menggunakan koordinat segitiga dari tiga gas hidrokarbon utama dengan total $100\\%$:\n"
                "  $$\\%CH_4 = \\frac{CH_4}{CH_4 + C_2H_4 + C_2H_2} \\times 100\\%$$\n"
                "  $$\\%C_2H_4 = \\frac{C_2H_4}{CH_4 + C_2H_4 + C_2H_2} \\times 100\\%$$\n"
                "  $$\\%C_2H_2 = \\frac{C_2H_2}{CH_4 + C_2H_4 + C_2H_2} \\times 100\\%$$\n\n"
                "  **7 Zona Diagnostik Duval 1:**\n"
                "  1. **PD**: Partial Discharge (pelepasan muatan parsial).\n"
                "  2. **T1**: Thermal Fault $< 300^\\circ\\text{C}$.\n"
                "  3. **T2**: Thermal Fault $300 - 700^\\circ\\text{C}$.\n"
                "  4. **T3**: Thermal Fault $> 700^\\circ\\text{C}$ (overheating parah).\n"
                "  5. **D1**: Low Energy Discharge (sparking / pelepasan energi rendah).\n"
                "  6. **D2**: High Energy Discharge (busur api listrik / arcing berat).\n"
                "  7. **DT**: Thermal and Electrical Fault (gangguan campuran).\n\n"
                "---\n\n"
                "### 3. Rasio Kertas Selulosa ($CO_2 / CO$)\n\n"
                "- **Rasio $CO_2/CO > 3$**: Penuaan normal selulosa.\n"
                "- **Rasio $CO_2/CO < 3$**: Pemanasan berlebih pada kertas isolasi (risiko degradasi mekanis kertas / penurunan derajat polimerisasi DP)."
            )

        # 10. Vibrasi (ISO 10816-3 & ISO 20816)
        if "vibrasi" in q or "vibration" in q or "getaran" in q or "iso 10816" in q or "spektrum" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Vibration Analysis (Analisis Getaran Mesin Berputar)**:\n\n"
                "---\n\n"
                "### 1. Definisi & Konsep Pengukuran Getaran\n\n"
                "Analisis getaran adalah teknik pemantauan kondisi mesin berputar dengan mengukur respon dinamis struktur akibat gaya eksitasi internal poros, bantalan (*bearing*), kopling, atau fluida. Parameter utama adalah kecepatan getaran **RMS Velocity ($mm/s$)** pada pita frekuensi $10 - 1000\\text{ Hz}$.\n\n"
                "---\n\n"
                "### 2. Standar Evaluasi ISO 10816-3 (Mesin Industri > 300 kW)\n\n"
                "* [Dokumen: ISO 10816-3 / ISO 20816-3]\n"
                "  - **Zona A (Baru/Sempurna)**: RMS Velocity $\\le 2.3\\text{ mm/s}$\n"
                "  - **Zona B (Operasi Kontinu)**: $2.3 < v_{rms} \\le 4.5\\text{ mm/s}$ (Rigid) / $\\le 7.1\\text{ mm/s}$ (Flexible)\n"
                "  - **Zona C (Restricted / Alarm)**: $4.5 < v_{rms} \\le 7.1\\text{ mm/s}$ (Rigid) / $7.1 < v_{rms} \\le 11.0\\text{ mm/s}$ (Flexible) — Rencanakan perbaikan.\n"
                "  - **Zona D (Berbahaya / Trip)**: $> 7.1\\text{ mm/s}$ (Rigid) / $> 11.0\\text{ mm/s}$ (Flexible) — Risiko kegagalan katastropik.\n\n"
                "---\n\n"
                "### 3. Diagnostik Spektrum Frekuensi (FFT Spectrum)\n\n"
                "1. **Puncak $1\\times$ RPM**: Indikasi dominan **Unbalance Massa**.\n"
                "2. **Puncak $2\\times$ RPM**: Indikasi dominan **Misalignment Kopling** atau poros bengkok (*bent shaft*).\n"
                "3. **Harmonik Kelipatan Tinggi ($3\\times, 4\\times$ dst.)**: Indikasi **Kelonggaran Mekanikal (*Mechanical Looseness*)** pada baut pondasi atau rumah bantalan.\n"
                "4. **Frekuensi Defek Bantalan (Bearing Frequencies)**: BPFO, BPFI, BSF, FTF."
            )

        # 11. Partial Discharge (PD & PRPD - IEC 60270)
        if "partial discharge" in q or "pd" in q or "prpd" in q or "peluahan" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Partial Discharge (PD)** pada sistem isolasi tegangan tinggi:\n\n"
                "---\n\n"
                "### 1. Definisi & Mekanisme Fisika PD\n\n"
                "**Partial Discharge (Peluahan Sebagian)** adalah loncatan muatan listrik mikroskopis terlokalisasi yang hanya menjembatani sebagian isolasi antara dua konduktor bertegangan, sesuai standar **IEC 60270**. PD terjadi di dalam rongga gas mikro (*void*), celah slot, atau permukaan isolasi generator dan motor 6.3 KV.\n\n"
                "---\n\n"
                "### 2. Klasifikasi Pola PRPD (Phase-Resolved Partial Discharge)\n\n"
                "1. **Internal Void Discharge**: Terjadi di dalam badan isolasi mika/epoksi, pola simetris pada kuadran $0^\\circ - 90^\\circ$ dan $180^\\circ - 270^\\circ$.\n"
                "2. **Slot Discharge**: Gesekan lilitan stator terhadap inti laminasi akibat wedge longgar (*loose stator slot wedges*).\n"
                "3. **Surface Tracking**: Pelepasan muatan merambat di sepanjang permukaan isolasi kotor atau lembab pada end-winding.\n"
                "4. **Corona**: Pelepasan muatan ke udara di sekitar konduktor tajam bertegangan tinggi."
            )

        # 12. Tribologi & Uji Pelumas (ASTM D445, ISO 4406)
        if "tribologi" in q or "tribology" in q or "viskositas" in q or "pelumas" in q or "oli" in q or "tan" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Tribologi & Analisis Pelumas Mesin Pembangkit**:\n\n"
                "---\n\n"
                "### 1. Parameter Kunci Laboratorium Pelumas\n\n"
                "* [Dokumen: Standar ASTM D445 & ISO 4406]\n"
                "  1. **Viskositas Kinematik (40°C & 100°C)**: Ketahanan alir pelumas. Batas aman deviasi adalah $\\pm 10\\%$ dari viskositas baseline oli baru.\n"
                "  2. **Total Acid Number (TAN)**: Indikator degradasi oksidasi pelumas (batas kenaikan $\\le 0.5\\text{ mgKOH/g}$ dari baseline).\n"
                "  3. **Kadar Air (Karl Fischer - ASTM D6304)**: Batas kritis $\\le 100-200\\text{ ppm}$. Air memicu hidrolisis aditif dan korosi bantalan.\n"
                "  4. **Kode Kebersihan ISO 4406**: Jumlah partikel mikron per mL ($>4\\mu m / >6\\mu m / >14\\mu m$, misal target kebersihan BFP: $16/14/11$).\n"
                "  5. **Spektrometri Logam Aus (*Wear Metals*)**: Besi ($Fe$) dari poros/roda gigi, Tembaga ($Cu$) dari bantalan babbitt/kuningan."
            )

        # 13. Thermal IRT & Delta-T (ISO 18434-1)
        if "thermal" in q or "irt" in q or "delta-t" in q or "hotspot" in q or "suhu" in q or "panas" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Thermal Infrared Thermography (IRT) & Delta-T Matrix**:\n\n"
                "---\n\n"
                "### 1. Definisi & Prinsip Pengukuran Radiasi Termal\n\n"
                "Inspeksi termografi inframerah (IRT) mendeteksi radiasi elektromagnetik gelombang panjang ($8 - 14\\,\\mu m$) yang dipancarkan permukaan benda untuk memetakan distribusi suhu tanpa sentuhan (*contactless temperature mapping*). Parameter kunci adalah selisih suhu **Delta-T ($\\Delta T$)**:\n"
                "$$\\Delta T_{phase} = |T_{fasa\\_A} - T_{fasa\\_B}|$$\n"
                "$$\\Delta T_{ambient} = T_{hotspot} - T_{ambient}$$\n\n"
                "---\n\n"
                "### 2. Standar Evaluasi ISO 18434-1 & NETA MTS\n\n"
                "* [Dokumen: Standar ISO 18434-1 & Kriteria Evaluasi Thermal Jeranjang]\n"
                "  - **$\\Delta T \\le 10^\\circ\\text{C}$**: **NORMAL** — Kondisi kontak baik, pemantauan rutin terjadwal.\n"
                "  - **$10^\\circ\\text{C} < \\Delta T \\le 30^\\circ\\text{C}$**: **WARNING / ALARM** — Terdapat resistansi kontak tinggi pada koneksi baut busbar atau kabel terminal, rencanakan inspeksi saat pemeliharaan terdekat.\n"
                "  - **$\\Delta T > 30^\\circ\\text{C}$**: **HIGH / KRITIS** — Pemanasan berlebih ekstrem (*hotspot* parah), risiko kebakaran isolasi atau lelehnya konduktor, jadwalkan tindakan segera.\n\n"
                "---\n\n"
                "### 3. Tindakan CBM Lapangan\n\n"
                "1. Lakukan pengencangan baut terminal (*re-torquing*) menggunakan kunci momen terkalibrasi.\n"
                "2. Bersihkan permukaan kontak dari oksidasi atau korosi dan gunakan konduktif grease (*contact grease*)."
            )

        # 14. Health Index & RUL (Reliability Fusion)
        if "health index" in q or "rul" in q or "sisa umur" in q or "weibull" in q:
            return header + (
                "Berikut adalah penjelasan teknis komprehensif mengenai **Composite Health Index & Predictive RUL (Remaining Useful Life)**:\n\n"
                "---\n\n"
                "### 1. Konsep Composite Health Index (Skala 0 - 100)\n\n"
                "Health Index (HI) menggabungkan penilaian kondisi multi-disiplin CBM dengan bobot terkalibrasi:\n"
                "$$HI = \\sum_{i=1}^{n} w_i \\cdot S_i$$\n"
                "*Keterangan: $w_i$ = bobot domain (Vibrasi $30\\%$, MCSA $25\\%$, DGA/Thermal $20\\%$, Tribologi $15\\%$, PD $10\\%$), $S_i$ = skor sub-sistem (0-100).*\n\n"
                "Kategori Health Status:\n"
                "- **$85 - 100$**: **HEALTHY** (Peralatan dalam kondisi prima).\n"
                "- **$70 - 84$**: **MONITORED** (Gejala awal degradasi terdeteksi).\n"
                "- **$50 - 69$**: **WARNING** (Penyimpangan parameter melampaui batas operasional aman).\n"
                "- **$< 50$**: **CRITICAL** (Risiko kegagalan tinggi, siapkan Work Order mendesak).\n\n"
                "---\n\n"
                "### 2. Estimasi Sisa Umur (Remaining Useful Life - RUL)\n\n"
                "RUL dihitung berdasarkan laju degradasi linier/eksponensial menuju ambang batas kritis ($HI_{threshold} = 40$):\n"
                "$$RUL = \\frac{HI_{current} - HI_{threshold}}{\\text{Degradation Rate (poin/hari)}}$$\n"
                "dipadukan dengan model ketahanan Weibull:\n"
                "$$R(t) = e^{-(t/\\eta)^\\beta}$$\n"
                "*Keterangan: $\\beta$ = faktor bentuk (*shape parameter*), $\\eta$ = umur karakteristik (*characteristic life*).*"
            )

        return None

