import json
import os
from typing import Optional

import pandas as pd
import plotly.express as px

from src.analytics import calculate_equipment_health_score, detect_equipment_anomalies
from src.components.status_colors import STATUS_BADGE_BG, STATUS_BADGE_FG, STATUS_PIE_COLORS, canon_condition_status
from src.components.theme import render_page_header
from src.data_loader import filter_mcsa_data, get_data_path, load_nameplate_csv
from src.equipment_canon import (
    canon_unit_name,
    canon_voltage_level,
    compute_overall_status_from_rows,
    norm_equipment,
)
from src.standards import (
    generate_esa_mcsa_quick_recommendations,
    generate_initial_analysis,
)


def render_dashboard_page(
    st,
    df: pd.DataFrame,
    df_latest: pd.DataFrame,
    df_latest_all: pd.DataFrame,
    filtered_df: pd.DataFrame,
    df_month: Optional[pd.DataFrame],
    date_start: str,
    date_end: str,
    sel_unit: str,
    sel_volt: str,
    sel_equipment: list,
    standby_enabled: bool,
    standby_report: Optional[dict],
    eq_master_df: pd.DataFrame,
    master_norm_to_unit: dict,
    master_norm_to_volt: dict,
    materi_page=None,
):
    render_page_header(st, "MCSA", "Overview kondisi equipment MCSA.")

    st.caption(f"Periode: {date_start} s/d {date_end}")

    unit_label = sel_unit if sel_unit != "All" else "PLTU Jeranjang"
    volt_label = sel_volt if sel_volt != "All" else "Semua Voltage"
    st.caption(f"{unit_label} | {volt_label}")

    master_by_norm = {}
    if isinstance(eq_master_df, pd.DataFrame) and not eq_master_df.empty:
        tmp = eq_master_df.copy()
        tmp["_norm"] = tmp["Equipment"].astype(str).map(norm_equipment)
        tmp = tmp.drop_duplicates(subset=["_norm"], keep="first")
        for _, r in tmp.iterrows():
            n = r.get("_norm")
            if not n:
                continue
            master_by_norm[n] = {
                "Equipment": r.get("Equipment"),
                "Full_Name": r.get("Full_Name"),
                "Unit_Name": r.get("Unit_Name"),
                "Voltage_Level": r.get("Voltage_Level"),
            }

    if standby_report is not None:
        show_sampling = st.checkbox("Sampling Compliance", value=False)
        if show_sampling:
            with st.expander("Sampling Compliance", expanded=True):
                month_label = standby_report["month_start"].strftime("%Y-%m")
                required_label = ", ".join(standby_report.get("required_params") or [])
                st.caption(f"Bulan: {month_label} | Parameter wajib: {required_label}")

                universe = standby_report.get("eq_universe") or []
                present = set(standby_report.get("eq_present") or [])
                missing = standby_report.get("eq_missing") or []
                reasons_for_month = standby_report.get("standby_reasons") or {}
                excluded = [
                    e for e in missing
                    if e in reasons_for_month and str(reasons_for_month[e].get("reason", "")).strip() != ""
                ]
                missing_visible = [e for e in missing if e not in excluded]

                total_expected = len(universe)
                updated = len(present)
                missing_cnt = len(missing_visible)
                compliance_pct = 0.0 if total_expected == 0 else (updated / total_expected) * 100.0

                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("Expected", total_expected)
                cc2.metric("Updated", updated)
                cc3.metric("Belum Update", missing_cnt)
                cc4.metric("Compliance %", round(compliance_pct, 1))

                # Load quality classification based on Load rule
                if present and df_month is not None:
                    dfm = df_month.copy()
                    dfm["Parameter"] = dfm["Parameter"].astype(str)
                    load_rows = dfm[dfm["Parameter"] == "Load"]
                    load_vals = pd.to_numeric(load_rows.get("Value", pd.NA), errors="coerce")
                    if "Raw_Value" in load_rows.columns:
                        load_vals = load_vals.fillna(pd.to_numeric(load_rows["Raw_Value"], errors="coerce"))
                    load_rows = load_rows.assign(_load=load_vals)
                    eq_load_last = (
                        load_rows.sort_values("Date")
                        .dropna(subset=["_load"])
                        .drop_duplicates(subset=["Equipment"], keep="last")
                    )
                    class_map = {}
                    for _, r in eq_load_last.iterrows():
                        lv = float(r["_load"])
                        if lv < 20.0:
                            class_map[r["Equipment"]] = "Invalid (<20%)"
                        elif lv < 40.0:
                            class_map[r["Equipment"]] = "Monitoring Only (20–40%)"
                        else:
                            class_map[r["Equipment"]] = "Valid Diagnosis (≥40%)"

                    # Fallback using Current and FLA from nameplate
                    name_df = load_nameplate_csv()
                    if not name_df.empty:
                        fla_map = name_df.set_index("Equipment")["FLA"].to_dict() if "FLA" in name_df.columns else {}
                        for eq in present:
                            if eq not in class_map and eq in fla_map and fla_map[eq] not in {None, "", "nan"}:
                                curr_rows = dfm[
                                    (dfm["Equipment"] == eq) &
                                    (dfm["Parameter"].isin(["Current 1", "Current 2", "Current 3"]))
                                ]
                                curr_vals = pd.to_numeric(curr_rows.get("Value", pd.NA), errors="coerce")
                                if "Raw_Value" in curr_rows.columns:
                                    curr_vals = curr_vals.fillna(pd.to_numeric(curr_rows["Raw_Value"], errors="coerce"))
                                if curr_vals.notna().any():
                                    avg_i = float(curr_vals.dropna().mean())
                                    try:
                                        fla = float(fla_map[eq])
                                        if fla > 0:
                                            lv = (avg_i / fla) * 100.0
                                            if lv < 20.0:
                                                class_map[eq] = "Invalid (<20%)"
                                            elif lv < 40.0:
                                                class_map[eq] = "Monitoring Only (20–40%)"
                                            else:
                                                class_map[eq] = "Valid Diagnosis (≥40%)"
                                    except Exception:
                                        pass

                    valid_cnt = sum(1 for e in present if class_map.get(e) == "Valid Diagnosis (≥40%)")
                    mon_cnt = sum(1 for e in present if class_map.get(e) == "Monitoring Only (20–40%)")
                    inv_cnt = sum(1 for e in present if class_map.get(e) == "Invalid (<20%)")
                    cv1, cv2, cv3 = st.columns(3)
                    cv1.metric("Valid Diagnosis", valid_cnt)
                    cv2.metric("Monitoring Only", mon_cnt)
                    cv3.metric("Invalid (Load<20%)", inv_cnt)

                if missing_cnt:
                    miss_df = pd.DataFrame({"Equipment": missing_visible})
                    st.dataframe(miss_df, width="stretch", hide_index=True)
                    st.download_button(
                        "Download CSV (Belum Update)",
                        data=miss_df.to_csv(index=False).encode("utf-8"),
                        file_name=f"belum_update_{month_label}.csv",
                        mime="text/csv",
                    )

                st.markdown("---")
                st.subheader("Alasan Standby (pengecualian kepatuhan)")
                reason_enum = [
                    "PLANNED_SHUTDOWN", "UNPLANNED_OUTAGE", "MAINTENANCE",
                    "UNIT_OFF", "VFD_BYPASS", "STARTUP_TEST", "OTHER"
                ]
                new_reasons = {}
                for eq in missing:
                    c1, c2 = st.columns([2, 3])
                    with c1:
                        default_reason_idx = (
                            reason_enum.index(reasons_for_month.get(eq, {}).get("reason", "OTHER"))
                            if reasons_for_month.get(eq)
                            else reason_enum.index("OTHER")
                        )
                        sel_reason = st.selectbox(f"{eq}", reason_enum, index=default_reason_idx)
                    with c2:
                        note_val = st.text_input(f"Catatan ({eq})", value=reasons_for_month.get(eq, {}).get("note", ""))
                    new_reasons[eq] = {"reason": sel_reason, "note": note_val}

                if st.button("Simpan Alasan Standby"):
                    reasons_path = get_data_path("config", "standby_reasons.json")
                    reasons_data = {}
                    try:
                        if os.path.exists(reasons_path):
                            with open(reasons_path, "r", encoding="utf-8") as fp:
                                reasons_data = json.load(fp)
                    except Exception:
                        reasons_data = {}

                    month_key = standby_report["month_start"].strftime("%Y-%m")
                    reasons_data[month_key] = new_reasons
                    try:
                        os.makedirs(os.path.dirname(reasons_path), exist_ok=True)
                        with open(reasons_path, "w", encoding="utf-8") as fp:
                            json.dump(reasons_data, fp, ensure_ascii=False, indent=2)
                        st.success("Alasan standby disimpan.")
                    except Exception as e:
                        st.error(f"Gagal menyimpan: {e}")

    if standby_enabled and standby_report and isinstance(standby_report.get("eq_universe"), list) and standby_report.get("eq_universe"):
        universe_eq = [str(x) for x in standby_report.get("eq_universe")]
    else:
        universe_eq = [str(x) for x in filtered_df.get("Equipment", pd.Series(dtype=str)).dropna().astype(str).unique()]
    universe_norm = [n for n in (pd.Series(universe_eq).map(norm_equipment).tolist()) if n and n.lower() not in {"nan", "none"}]

    missing_norm = set()
    if standby_enabled and standby_report and isinstance(standby_report.get("eq_missing"), list):
        missing_norm = set(pd.Series([str(x) for x in standby_report.get("eq_missing")]).map(norm_equipment).tolist())

    tmp = filtered_df.copy()
    if "Equipment" in tmp.columns:
        tmp["_norm"] = tmp["Equipment"].astype(str).map(norm_equipment)
    else:
        tmp["_norm"] = ""
    status_by_norm = {}
    if not tmp.empty:
        for n, g in tmp.groupby("_norm"):
            if not n or str(n).lower() in {"nan", "none"}:
                continue
            status_by_norm[n] = compute_overall_status_from_rows(g)

    status_by_universe = {}
    for n in universe_norm:
        if n in missing_norm:
            status_by_universe[n] = "Standby"
        else:
            status_by_universe[n] = status_by_norm.get(n, "Unknown")

    status_counts = pd.Series(list(status_by_universe.values())).value_counts()
    normal_count = int(status_counts.get("Normal", 0))
    alarm_count = int(status_counts.get("Alarm", 0))
    high_count = int(status_counts.get("High", 0))
    standby_count = int(status_counts.get("Standby", 0))
    unknown_count = int(status_counts.get("Unknown", 0))
    total_eq = len(universe_norm)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Equipment", total_eq)
    col2.metric("Normal (Hijau)", int(normal_count))
    col3.metric("Standby", int(standby_count))
    col4.metric("Alarm (Kuning)", int(alarm_count), delta_color="inverse")
    col5.metric("High (Merah)", int(high_count), delta_color="inverse")

    st.subheader(f"Distribusi Kondisi — {unit_label}")
    plot_order = ["Normal", "Alarm", "High", "Standby", "Unknown"]
    plot_df = pd.DataFrame({"Status": plot_order})
    plot_df["Count"] = plot_df["Status"].map(lambda s: int(status_counts.get(s, 0)))
    plot_df = plot_df[plot_df["Count"] > 0]
    if not plot_df.empty:
        color_map = STATUS_PIE_COLORS
        fig = px.pie(
            plot_df,
            names="Status",
            values="Count",
            title=f"Status Equipment — {unit_label}",
            color="Status",
            color_discrete_map=color_map,
            category_orders={"Status": plot_order},
        )
        fig.update_traces(hole=0.45, textinfo="percent+label", textposition="inside")
        fig.update_layout(
            height=420,
            margin=dict(l=10, r=10, t=40, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("Tidak ada data untuk filter ini.")

    # Detail Table
    st.subheader("Data Detail")
    detail_df = df_latest.copy()
    if sel_unit != "All":
        _unit_series = detail_df.get("Unit_Name", pd.Series(dtype=str)).astype(str).map(canon_unit_name)
        _norm_series = detail_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
        _unit_series = _norm_series.map(master_norm_to_unit).fillna(_unit_series)
        detail_df = detail_df[_unit_series == sel_unit]
    if sel_volt != "All":
        _volt_series = detail_df.get("Voltage_Level", pd.Series(dtype=str)).astype(str).map(canon_voltage_level)
        _norm_series = detail_df.get("Equipment", pd.Series(dtype=str)).astype(str).map(norm_equipment)
        _volt_series = _norm_series.map(master_norm_to_volt).fillna(_volt_series)
        detail_df = detail_df[_volt_series == sel_volt]
    if sel_equipment:
        detail_df = detail_df[detail_df.get("Equipment", pd.Series(dtype=str)).astype(str).isin(sel_equipment)]

    eq_meta_cols = ["Equipment"]
    if "Full_Name" in detail_df.columns:
        eq_meta_cols.append("Full_Name")
    eq_meta = detail_df[eq_meta_cols].drop_duplicates(subset=["Equipment"]).copy()
    if not eq_meta.empty:
        eq_meta["Equipment"] = eq_meta["Equipment"].astype(str)
        if "Full_Name" in eq_meta.columns:
            eq_meta["Full_Name"] = eq_meta["Full_Name"].astype(str)
        eq_meta["_norm"] = eq_meta["Equipment"].map(norm_equipment)
        if "Full_Name" not in eq_meta.columns:
            eq_meta["Full_Name"] = eq_meta["Equipment"]

        def _fill_full(row):
            fn = str(row.get("Full_Name") or "").strip()
            eq = str(row.get("Equipment") or "").strip()
            if fn == "" or fn.lower() in {"nan", "none"} or fn == eq:
                ref = master_by_norm.get(row.get("_norm"))
                if ref and str(ref.get("Full_Name") or "").strip():
                    return str(ref.get("Full_Name"))
            return fn if fn else eq

        eq_meta["Full_Name"] = eq_meta.apply(_fill_full, axis=1)
        eq_meta = eq_meta.sort_values("Equipment")

        eq_meta["_eq"] = eq_meta["Equipment"].astype(str)
        eq_meta["_full"] = eq_meta["Full_Name"].fillna("").astype(str).str.strip()
        eq_meta["_full"] = eq_meta["_full"].where(
            ~eq_meta["_full"].str.lower().isin(["", "nan", "none", "null"]),
            eq_meta["_eq"],
        )
        _same = eq_meta["_full"] == eq_meta["_eq"]
        eq_meta["_label"] = eq_meta["_full"].where(_same, eq_meta["_full"] + " (" + eq_meta["_eq"] + ")")
        display_map = dict(zip(eq_meta["_label"].tolist(), eq_meta["_eq"].tolist()))

        labels = list(display_map.keys())
        if not labels:
            st.warning("Tidak ada equipment yang dapat dipilih untuk filter ini.")
            st.stop()
        if "dashboard_eq" in st.session_state and st.session_state.dashboard_eq not in labels:
            st.session_state.dashboard_eq = labels[0]
        selected_label = st.selectbox("Pilih Equipment:", labels, key="dashboard_eq")
        selected_eq = display_map[selected_label]
        eq_data = detail_df[detail_df["Equipment"] == selected_eq]

        sel_norm = norm_equipment(selected_eq)
        u_name = master_norm_to_unit.get(sel_norm) or (
            eq_data["Unit_Name"].iloc[0]
            if "Unit_Name" in eq_data.columns and not eq_data.empty
            else "-"
        )
        u_volt = master_norm_to_volt.get(sel_norm) or (
            eq_data["Voltage_Level"].iloc[0]
            if "Voltage_Level" in eq_data.columns and not eq_data.empty
            else "-"
        )
        f_name = eq_data["Full_Name"].iloc[0] if "Full_Name" in eq_data.columns else "-"
        ref = master_by_norm.get(norm_equipment(selected_eq))
        if ref:
            if str(f_name).strip() in {"", "-", "Unknown", "nan", "None"}:
                f_name = ref.get("Full_Name") or f_name
            if str(u_name).strip() in {"", "-", "Unknown", "nan", "None"}:
                u_name = ref.get("Unit_Name") or u_name
            if str(u_volt).strip() in {"", "-", "Unknown", "nan", "None"}:
                u_volt = ref.get("Voltage_Level") or u_volt

        eq_status = status_by_norm.get(sel_norm, "Unknown") if isinstance(status_by_norm, dict) else "Unknown"
        badge_bg = STATUS_BADGE_BG.get(eq_status, STATUS_BADGE_BG["Unknown"])
        badge_fg = STATUS_BADGE_FG.get(eq_status, STATUS_BADGE_FG["Unknown"])
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:12px;">
              <h3 style="margin:0;">{f_name}</h3>
              <span style="padding:4px 10px; border-radius:999px; background:{badge_bg}; color:{badge_fg}; font-weight:700; border:1px solid rgba(0,0,0,0.08);">{eq_status}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(f"**Code:** {selected_eq} | **Unit:** {u_name} | **Voltage:** {u_volt}")

        detail_view = st.radio(
            "Tampilan Detail",
            ["Ringkasan", "Rekomendasi ESA/MCSA", "Analisa Mendalam", "Trend", "Spektrum", "Perbandingan"],
            horizontal=True,
            key="dashboard_detail_view",
        )

        base_cols = ["Parameter"]
        if "Raw_Value" in eq_data.columns:
            base_cols.append("Raw_Value")
        if "Value" in eq_data.columns:
            base_cols.append("Value")
        if "Unit" in eq_data.columns:
            base_cols.append("Unit")
        if "Status_Category" in eq_data.columns:
            base_cols.append("Status_Category")
        if "Status" in eq_data.columns:
            base_cols.append("Status")

        tmp = eq_data[base_cols].copy()
        tmp["Parameter"] = tmp.get("Parameter", "").astype(str)

        def _latest_param_row(param_name: str):
            src = df[df["Equipment"] == selected_eq]
            src = src[src["Parameter"] == param_name]
            if src.empty:
                return None

            if "Date" in src.columns:
                src = src.copy()
                src["Date"] = pd.to_datetime(src["Date"], errors="coerce")
                src = src.dropna(subset=["Date"])
                if not src.empty:
                    src = src.sort_values("Date", ascending=False)

            if "Raw_Value" in src.columns:
                has_val = src["Raw_Value"].notna() & src["Raw_Value"].astype(str).str.strip().ne("")
                if has_val.any():
                    src_val = src[has_val]
                    if not src_val.empty:
                        return src_val.iloc[0]

            if not src.empty:
                return src.iloc[0]
            return None

        thd_params = ["THD Voltage %", "THD Current %"]
        existing_params = set(tmp["Parameter"].astype(str))
        for p in thd_params:
            if p in existing_params:
                continue
            row = _latest_param_row(p)
            row_data = {c: None for c in base_cols}
            row_data["Parameter"] = p
            if row is not None:
                for c in base_cols:
                    if c in row.index:
                        row_data[c] = row.get(c)
            if "Unit" in base_cols:
                u = row_data.get("Unit")
                if u is None or str(u).strip() == "" or str(u).strip().lower() in {"nan", "none"}:
                    row_data["Unit"] = "%"
            if "Status" in base_cols and (row_data.get("Status") is None or str(row_data.get("Status")).strip() == ""):
                row_data["Status"] = "Unknown"
            if "Status_Category" in base_cols and (row_data.get("Status_Category") is None or str(row_data.get("Status_Category")).strip() == ""):
                row_data["Status_Category"] = row_data.get("Status")
            tmp = pd.concat([tmp, pd.DataFrame([row_data])], ignore_index=True)
            existing_params.add(p)

        raw_s = tmp.get("Raw_Value", pd.Series([""] * len(tmp), index=tmp.index)).astype(str)
        raw_s = raw_s.where(~raw_s.str.lower().isin({"nan", "none"}), "")
        val_s = tmp.get("Value", pd.Series([None] * len(tmp), index=tmp.index))
        try:
            val_num = pd.to_numeric(val_s, errors="coerce")
        except Exception:
            val_num = pd.Series([None] * len(tmp), index=tmp.index)
        val_fmt = val_num.map(lambda x: "" if pd.isna(x) else (f"{x:.3f}" if abs(float(x)) < 1000 else f"{x:,.0f}"))
        nilai = raw_s.copy()
        nilai = nilai.where(nilai.astype(str).str.strip().ne(""), val_fmt)
        unit_s = tmp.get("Unit", pd.Series([""] * len(tmp), index=tmp.index)).astype(str)
        unit_s = unit_s.where(~unit_s.str.lower().isin({"nan", "none"}), "")

        status_src = tmp.get("Status_Category")
        if status_src is None:
            status_src = tmp.get("Status")
        if status_src is None:
            status_src = tmp.get("Raw_Value")
        status_src = status_src.astype(str)
        status_disp = tmp["Parameter"].map(lambda p: str(p).strip().lower()).isin({"kondisi", "bearing"})
        status_col = status_src.where(status_disp, tmp.get("Status", status_src)).map(canon_condition_status)

        table_df = pd.DataFrame({
            "Parameter": tmp["Parameter"],
            "Nilai": nilai.astype(str),
            "Unit": unit_s,
            "Status": status_col,
        })
        table_df = table_df.replace({"nan": "", "None": ""})

        eq_history = df[df["Equipment"] == selected_eq].copy()
        health_params = {}
        for param_name in [
            "Load", "Dev Voltage", "Dev Current", "THD Voltage %", "THD Current %",
            "Bearing", "Rotorbar", "Upper Sideband", "Lower Sideband", "Rotorbar Health",
        ]:
            latest_row = _latest_param_row(param_name)
            if latest_row is None:
                continue
            latest_val = latest_row.get("Value")
            if latest_val is None or (isinstance(latest_val, float) and pd.isna(latest_val)):
                latest_val = latest_row.get("Raw_Value")
            health_params[param_name] = latest_val

        health_summary = calculate_equipment_health_score(health_params)
        anomaly_rows = detect_equipment_anomalies(eq_history)

        hm1, hm2, hm3 = st.columns(3)
        hm1.metric("Health Score", int(health_summary["score"]))
        hm2.metric("Risk Drivers", len(health_summary["drivers"]))
        hm3.metric("Anomali Trend", len(anomaly_rows))

        if health_summary["drivers"]:
            st.caption("Driver utama: " + ", ".join(health_summary["drivers"]))
        if anomaly_rows:
            st.dataframe(pd.DataFrame(anomaly_rows), width="stretch", hide_index=True)

        def _style_status_cell(v: str) -> str:
            bg = STATUS_BADGE_BG.get(str(v), STATUS_BADGE_BG["Unknown"])
            fg = STATUS_BADGE_FG.get(str(v), STATUS_BADGE_FG["Unknown"])
            return f"background-color: {bg}; color: {fg}; font-weight: 700;"

        # pandas >= 2.1 memakai Styler.map, versi lama masih Styler.applymap.
        styler = table_df.style
        style_cells = getattr(styler, "map", None) or styler.applymap

        st.dataframe(
            style_cells(_style_status_cell, subset=["Status"]),
            width="stretch",
            hide_index=True,
        )

        if detail_view == "Analisa Mendalam":
            st.subheader("Analisa & Rekomendasi Awal")

            analysis_data = generate_esa_mcsa_quick_recommendations(eq_data)
            detailed_report_text = analysis_data.get("detailed_report", "")

            if detailed_report_text:
                st.text_area("Laporan Analisa (Rule-Based)", value=detailed_report_text, height=450)
            else:
                st.info("Data tidak cukup untuk menghasilkan laporan analisa mendalam.")

            # AI Insights (Multi-Provider LLM)
            from src.llm_assistant import (
                DEFAULT_GEMINI_MODEL,
                DEFAULT_GROQ_MODEL,
                DEFAULT_OLLAMA_HOST,
                DEFAULT_OLLAMA_MODEL,
                DEFAULT_OPENCODE_BASE_URL,
                DEFAULT_OPENCODE_MODEL,
                MCSALLMAssistant,
                resolve_provider_key,
            )
            ai_provider = st.session_state.get("ai_provider", "gemini")
            ai_enabled = bool(st.session_state.get("ai_enabled", False))

            if ai_provider == "groq":
                ai_key = resolve_provider_key("groq", st.session_state.get("groq_api_key"), st)
                active_model = st.session_state.get("groq_model", DEFAULT_GROQ_MODEL)
                provider_label = f"Groq ({active_model})"
                is_ready = bool(ai_key)
            elif ai_provider == "opencode":
                ai_key = resolve_provider_key("opencode", st.session_state.get("opencode_api_key"), st)
                active_model = st.session_state.get("opencode_model", DEFAULT_OPENCODE_MODEL)
                provider_label = f"OpenCode ({active_model})"
                is_ready = True
            elif ai_provider == "ollama":
                ai_key = None
                active_model = st.session_state.get("ollama_model", DEFAULT_OLLAMA_MODEL)
                provider_label = f"Ollama ({active_model})"
                is_ready = True
            else:
                ai_key = resolve_provider_key("gemini", st.session_state.get("gemini_api_key"), st)
                active_model = st.session_state.get("gemini_model", DEFAULT_GEMINI_MODEL)
                provider_label = f"Gemini ({active_model})"
                is_ready = bool(ai_key)

            with st.expander(f":material/auto_awesome: Analisis Model LLM Lanjutan ({provider_label})", expanded=ai_enabled and is_ready):
                if not is_ready and ai_provider in {"gemini", "groq"}:
                    st.info(
                        f"Anda dapat memasukkan API Key {ai_provider.upper()} melalui menu **🤖 Pengaturan Model LLM** di sidebar sebelah kiri atau file `.env`.",
                        icon=":material/lightbulb:",
                    )
                else:
                    col_ai1, col_ai2 = st.columns([3, 1])
                    with col_ai1:
                        st.caption(f"Provider: **{ai_provider.upper()}** | Model: `{active_model}`")
                    with col_ai2:
                        gen_btn = st.button("Generate Analisis AI", icon=":material/psychology:", width="stretch")

                    if gen_btn:
                        with st.spinner(f"Model LLM ({provider_label}) sedang menganalisis data riwayat {selected_eq} & standar MCSA..."):
                            llm = MCSALLMAssistant(
                                enabled=True,
                                provider=ai_provider,
                                api_key=ai_key,
                                model=active_model,
                                base_url=st.session_state.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL) if ai_provider == "opencode" else None,
                                ollama_host=st.session_state.get("ollama_host", DEFAULT_OLLAMA_HOST),
                            )
                            ai_result = llm.generate_detailed_analysis(selected_eq, detailed_report_text, eq_history)
                            st.session_state[f"_ai_analysis_{selected_eq}"] = ai_result

                    saved_ai = st.session_state.get(f"_ai_analysis_{selected_eq}")
                    if saved_ai:
                        st.markdown(f"### :material/description: Executive Summary & Root Cause Analysis ({provider_label})")
                        st.markdown(saved_ai)


            st.subheader("Indikator Utama")
            analysis_cache = st.session_state.get("_analysis_cache") or {}
            analysis_key = (st.session_state.get("_mcsa_data_key"), selected_eq)
            analysis = analysis_cache.get(analysis_key)
            if analysis is None:
                analysis = generate_initial_analysis(eq_history)
                analysis_cache[analysis_key] = analysis
                st.session_state["_analysis_cache"] = analysis_cache
            indicators = analysis.get("indicators") or []
            if indicators:
                ind_df = pd.DataFrame(indicators)
                if not ind_df.empty:
                    for col in ind_df.columns:
                        if ind_df[col].dtype == object:
                            ind_df[col] = ind_df[col].astype(str)
                st.dataframe(ind_df, width="stretch", hide_index=True)

            def _to_num(v):
                if v is None:
                    return None
                if isinstance(v, (int, float)):
                    if pd.isna(v):
                        return None
                    return float(v)
                s = str(v).strip().replace(",", "")
                if s == "":
                    return None
                s = "".join(ch for ch in s if (ch.isdigit() or ch in {".", "-", "+", "e", "E"}))
                if s in {"", "+", "-", ".", "+.", "-."}:
                    return None
                try:
                    return float(s)
                except Exception:
                    return None

            key_params = [
                "Load", "Dev Voltage", "Dev Current", "THD Voltage %", "THD Current %",
                "Upper Sideband", "Lower Sideband", "Rotorbar Health", "Rotorbar Level %",
            ]

            trend_src = eq_history.copy()
            if "Date" in trend_src.columns:
                trend_src["Date"] = pd.to_datetime(trend_src["Date"], errors="coerce")
            else:
                trend_src["Date"] = pd.NaT
            trend_src = trend_src.dropna(subset=["Date"])
            trend_src = trend_src[trend_src["Parameter"].astype(str).isin(key_params)].copy()
            if not trend_src.empty:
                trend_src["Trend_Value"] = trend_src.get("Value", pd.Series([None] * len(trend_src), index=trend_src.index)).map(_to_num)
                if "Raw_Value" in trend_src.columns:
                    trend_src["Trend_Value"] = trend_src["Trend_Value"].fillna(trend_src["Raw_Value"].map(_to_num))
                trend_src = trend_src.dropna(subset=["Trend_Value"])
                if not trend_src.empty:
                    trend_src = trend_src.sort_values("Date")
                    fig_trend = px.line(
                        trend_src,
                        x="Date",
                        y="Trend_Value",
                        color="Parameter",
                        markers=True,
                        title="Trend Parameter Kunci",
                    )
                    st.plotly_chart(fig_trend, width="stretch")
            recs = analysis.get("recommendations") or []
            if recs:
                st.markdown("\n".join([f"- {r}" for r in recs]))
            refs = analysis.get("references") or []
            if refs:
                st.caption("Referensi: " + " | ".join(refs))

        def _classify_status(text: str) -> str:
            s = str(text or "").strip().lower()
            if "high" in s or "bad" in s or "critical" in s or "rusak" in s or "damage" in s:
                return "high"
            if "alarm" in s or "warning" in s:
                return "alarm"
            if "standby" in s:
                return "standby"
            if "normal" in s or s == "ok" or "good" in s:
                return "normal"
            return "unknown"

        def _open_materi(query_text: str = "", prefer_name_contains: Optional[str] = None):
            st.session_state["materi_query"] = query_text
            st.session_state["materi_prefer_name_contains"] = prefer_name_contains
            if materi_page is not None:
                st.switch_page(materi_page)
            else:
                st.rerun()

        cond_now = ""
        cond_row = eq_data[eq_data["Parameter"] == "Kondisi"]
        if not cond_row.empty:
            r0 = cond_row.iloc[0]
            if "Status_Category" in cond_row.columns and pd.notna(r0.get("Status_Category")):
                cond_now = r0.get("Status_Category")
            else:
                cond_now = r0.get("Raw_Value")
        cond_class = _classify_status(cond_now)

        esa_cache_key = (
            st.session_state.get("_mcsa_data_key"),
            selected_eq,
            date_start,
            date_end,
            sel_unit,
            sel_volt,
            tuple(sel_equipment),
        )
        _esa_cache = st.session_state.setdefault("_esa_quick_cache", {})

        def _esa_quick():
            cached = _esa_cache.get(esa_cache_key)
            if cached is None:
                cached = generate_esa_mcsa_quick_recommendations(eq_data)
                _esa_cache[esa_cache_key] = cached
            return cached

        if detail_view == "Rekomendasi ESA/MCSA":
            esa_quick = _esa_quick()
            st.subheader("Rekomendasi Cepat (ESA/MCSA)")
            c1, c2, c3 = st.columns(3)
            c1.metric("Overall", str(esa_quick.get("overall", "-")))
            load_pct = esa_quick.get("values", {}).get("Load %")
            c2.metric("Load %", "-" if load_pct is None else round(float(load_pct), 2))
            c3.metric("Load Quality", str(esa_quick.get("statuses", {}).get("Load Quality", "-")))

            status_items = []
            for k, v in (esa_quick.get("statuses") or {}).items():
                if k == "Load Quality":
                    continue
                status_items.append({"Indikator": k, "Status": v})
            if status_items:
                st.dataframe(pd.DataFrame(status_items), width="stretch", hide_index=True)

            recs = esa_quick.get("recommendations") or []
            if recs:
                st.markdown("\n".join([f"- {r}" for r in recs]))
            refs = esa_quick.get("references") or []
            if refs:
                st.caption("Referensi: " + " | ".join([str(r) for r in refs]))

        if detail_view == "Ringkasan":
            esa_quick = _esa_quick()
            st.subheader("Rekomendasi Cepat (ESA/MCSA)")
            recs = esa_quick.get("recommendations") or []
            if recs:
                st.markdown("\n".join([f"- {r}" for r in recs[:5]]))

            st.subheader("Materi Terkait")
            colm1, colm2, colm3, colm4, colm5 = st.columns(5)
            if colm1.button("SOP Pengukuran", width="stretch"):
                _open_materi("sop", "sop")
            if colm2.button("Rotor Bar", width="stretch"):
                _open_materi("rotor bar", "mcsa")
            if colm3.button("Bearing", width="stretch"):
                _open_materi("bearing", "mcsa")
            if colm4.button("Power Quality", width="stretch"):
                _open_materi("power quality", "power")
            if colm5.button("Pattern Recognition", width="stretch"):
                _open_materi("pattern", "pattern")

            if cond_class in {"alarm", "high"}:
                label = "Tindak Lanjut (Alarm/High)"
                if st.button(label, width="stretch"):
                    _open_materi("tindak lanjut", "sop")

            perf_rows = eq_data[eq_data["Parameter"].astype(str).str.startswith("Ringkasan Kinerja")].copy()
            if perf_rows.empty:
                fallback_perf = df_latest_all[df_latest_all["Equipment"] == selected_eq]
                perf_rows = fallback_perf[fallback_perf["Parameter"].astype(str).str.startswith("Ringkasan Kinerja")].copy()

            if not perf_rows.empty:
                st.subheader("Ringkasan Performance")
                perf_rows["Bagian"] = perf_rows["Parameter"].astype(str).str.replace("Ringkasan Kinerja -", "", regex=False).str.strip()
                show_perf = perf_rows[["Bagian", "Raw_Value"]].rename(columns={"Raw_Value": "Ringkasan"}).drop_duplicates(subset=["Bagian"], keep="last")
                show_perf = show_perf.sort_values("Bagian")
                st.dataframe(show_perf, width="stretch", hide_index=True)

        if detail_view == "Spektrum":
            st.subheader("Analisis Spektrum")

            img_dir = get_data_path("images")

            spectrum_images = []
            if os.path.exists(img_dir):
                for f in os.listdir(img_dir):
                    if f.upper().startswith(f"{selected_eq.upper()}_") and f.lower().endswith(".png"):
                        spectrum_images.append(f)

            spectrum_images.sort(reverse=True)

            if spectrum_images:
                c_img1, c_img2 = st.columns([1, 2])
                with c_img1:
                    sel_img = st.selectbox("Pilih Gambar Spektrum", spectrum_images)
                with c_img2:
                    if sel_img:
                        st.image(os.path.join(img_dir, sel_img), caption=sel_img, width="stretch")
            else:
                st.info("Tidak ada gambar spektrum yang tersedia untuk equipment ini.")

        if detail_view == "Trend":
            st.subheader("Trend Parameter")
            trend_params = sorted(df["Parameter"].unique())
            param_trend = st.selectbox(
                "Pilih Parameter untuk Trend:",
                trend_params,
                index=trend_params.index("Load") if "Load" in trend_params else 0,
                key="trend_param",
            )

            trend_range = st.segmented_control(
                "Rentang Waktu", ["3 Bulan", "6 Bulan", "12 Bulan", "Semua"], default="3 Bulan", key="trend_range"
            )
            agg_choice = st.segmented_control(
                "Agregasi", ["Harian", "Bulanan", "Tahunan"], default="Harian", key="trend_agg"
            )

            base_all = df[(df["Equipment"] == selected_eq) & (df["Parameter"] == param_trend)].copy()
            base_all["Date"] = pd.to_datetime(base_all.get("Date", pd.NaT), errors="coerce")
            base_all = base_all.dropna(subset=["Date"]).sort_values("Date")

            base = base_all.copy()
            if not base.empty:
                last_date = base["Date"].max()
                if trend_range == "3 Bulan":
                    start_date = last_date - pd.DateOffset(months=3)
                elif trend_range == "6 Bulan":
                    start_date = last_date - pd.DateOffset(months=6)
                elif trend_range == "12 Bulan":
                    start_date = last_date - pd.DateOffset(months=12)
                else:
                    start_date = base["Date"].min()
                base = base[base["Date"] >= start_date]

            if param_trend in ["Kondisi", "Bearing"]:
                show = base.copy()
                if "Status_Category" not in show.columns:
                    show["Status_Category"] = show.get("Raw_Value", "")
                if "Status_Level" not in show.columns:
                    s = show.get("Status_Category", "").astype(str).str.strip().str.lower()
                    lvl = pd.Series(-1, index=show.index)
                    lvl[s.str.contains("standby", na=False)] = 0
                    lvl[s.str.contains(r"normal|\bok\b|good", na=False)] = 1
                    lvl[s.str.contains("alarm|warning", na=False)] = 2
                    lvl[s.str.contains("high|bad|critical|rusak|damage", na=False)] = 3
                    show["Status_Level"] = lvl

                if agg_choice == "Bulanan":
                    show["YearMonth"] = show["Date"].dt.to_period("M").astype(str)
                    show = show.sort_values("Date").drop_duplicates(subset=["YearMonth"], keep="last")
                    x_col, title = "YearMonth", f"Trend Bulanan {param_trend} - {selected_eq}"
                elif agg_choice == "Tahunan":
                    show["Year"] = show["Date"].dt.year
                    show = show.sort_values("Date").drop_duplicates(subset=["Year"], keep="last")
                    x_col, title = "Year", f"Trend Tahunan {param_trend} - {selected_eq}"
                else:
                    x_col, title = "Date", f"Trend Harian {param_trend} - {selected_eq}"

                if not show.empty:
                    fig_trend = px.line(
                        show,
                        x=x_col,
                        y="Status_Level",
                        title=title,
                        markers=True,
                        hover_data={"Status_Category": True, "Raw_Value": True},
                    )
                    st.plotly_chart(fig_trend, width="stretch")
                else:
                    st.info("Belum ada data untuk menampilkan trend parameter ini.")
            else:
                show = base.copy()
                show["Value_num"] = pd.to_numeric(show.get("Value", pd.NA), errors="coerce")
                if "Raw_Value" in show.columns:
                    show["Value_num"] = show["Value_num"].fillna(pd.to_numeric(show["Raw_Value"], errors="coerce"))
                if agg_choice == "Bulanan":
                    show["YearMonth"] = show["Date"].dt.to_period("M").astype(str)
                    show = show.groupby("YearMonth", as_index=False)["Value_num"].mean()
                    x_col, y_col, title = "YearMonth", "Value_num", f"Trend Bulanan {param_trend} - {selected_eq}"
                elif agg_choice == "Tahunan":
                    show["Year"] = show["Date"].dt.year
                    show = show.groupby("Year", as_index=False)["Value_num"].mean()
                    x_col, y_col, title = "Year", "Value_num", f"Trend Tahunan {param_trend} - {selected_eq}"
                else:
                    x_col, y_col, title = "Date", "Value_num", f"Trend Harian {param_trend} - {selected_eq}"

                if not show.empty and show[y_col].notna().any():
                    fig_trend = px.line(show, x=x_col, y=y_col, title=title, markers=True)
                    st.plotly_chart(fig_trend, width="stretch")
                else:
                    st.info("Belum ada data numerik untuk menampilkan trend parameter ini.")

        if detail_view == "Perbandingan":
            st.subheader("Perbandingan Bulanan/Tahunan")
            trend_params = sorted(df["Parameter"].unique())
            param_cmp = st.selectbox(
                "Pilih Parameter:",
                trend_params,
                index=trend_params.index("Load") if "Load" in trend_params else 0,
                key="cmp_param",
            )

            base_all = df[(df["Equipment"] == selected_eq) & (df["Parameter"] == param_cmp)].copy()
            base_all["Date"] = pd.to_datetime(base_all.get("Date", pd.NaT), errors="coerce")
            base_all = base_all.dropna(subset=["Date"]).sort_values("Date")

            monthly = base_all.copy()
            if monthly.empty:
                st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
            else:
                monthly["YearMonth"] = monthly["Date"].dt.to_period("M").astype(str)

                if param_cmp in ["Kondisi", "Bearing"]:
                    if "Status_Category" not in monthly.columns:
                        monthly["Status_Category"] = monthly.get("Raw_Value", "")
                    rv = monthly.get("Raw_Value", pd.Series("", index=monthly.index)).astype(str).str.strip().str.lower()
                    has_any = monthly["Status_Category"].notna() & rv.ne("") & rv.ne("nan")
                    monthly = monthly[has_any].sort_values("Date").drop_duplicates(subset=["YearMonth"], keep="last")
                    month_options = monthly["YearMonth"].tolist()

                    if not month_options:
                        st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
                    else:
                        sel_month = st.selectbox(
                            "Pilih Bulan (YYYY-MM)",
                            month_options,
                            index=len(month_options) - 1,
                            key=f"month_cmp_{selected_eq}_{param_cmp}",
                        )
                        sel_idx = month_options.index(sel_month)
                        prev_month = month_options[sel_idx - 1] if sel_idx > 0 else None

                        this_row = monthly[monthly["YearMonth"] == sel_month].iloc[0]
                        this_cat = str(this_row.get("Status_Category", this_row.get("Raw_Value", "")))

                        prev_cat = None
                        if prev_month:
                            prev_row = monthly[monthly["YearMonth"] == prev_month].iloc[0]
                            prev_cat = str(prev_row.get("Status_Category", prev_row.get("Raw_Value", "")))

                        year, month = sel_month.split("-")
                        same_month_last_year = f"{int(year) - 1:04d}-{month}"
                        yoy_cat = None
                        if same_month_last_year in month_options:
                            yoy_row = monthly[monthly["YearMonth"] == same_month_last_year].iloc[0]
                            yoy_cat = str(yoy_row.get("Status_Category", yoy_row.get("Raw_Value", "")))

                        c1, c2, c3 = st.columns(3)
                        c1.metric(f"Status {sel_month}", this_cat)
                        c2.metric("Status Bulan Sebelumnya", prev_cat if prev_cat is not None else "-")
                        c3.metric("Status Bulan Sama Tahun Lalu", yoy_cat if yoy_cat is not None else "-")

                        st.dataframe(
                            monthly[["YearMonth", "Status_Category", "Raw_Value"]].sort_values("YearMonth", ascending=False).head(24),
                            width="stretch",
                        )
                else:
                    monthly["Value_num"] = pd.to_numeric(monthly.get("Value", pd.NA), errors="coerce")
                    if "Raw_Value" in monthly.columns:
                        monthly["Value_num"] = monthly["Value_num"].fillna(pd.to_numeric(monthly["Raw_Value"], errors="coerce"))
                    if "Raw_Value" in monthly.columns:
                        rv = monthly["Raw_Value"].astype(str).str.strip().str.lower()
                        has_any = monthly["Value_num"].notna() | (monthly["Raw_Value"].notna() & rv.ne("") & rv.ne("nan"))
                    else:
                        has_any = monthly["Value_num"].notna()

                    monthly = monthly[has_any].sort_values("Date").drop_duplicates(subset=["YearMonth"], keep="last")
                    month_options = monthly["YearMonth"].tolist()

                    if not month_options:
                        st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
                    else:
                        sel_month = st.selectbox(
                            "Pilih Bulan (YYYY-MM)",
                            month_options,
                            index=len(month_options) - 1,
                            key=f"month_cmp_{selected_eq}_{param_cmp}",
                        )
                        sel_idx = month_options.index(sel_month)
                        prev_month = month_options[sel_idx - 1] if sel_idx > 0 else None

                        this_row = monthly[monthly["YearMonth"] == sel_month].iloc[0]
                        this_num = this_row["Value_num"] if pd.notna(this_row["Value_num"]) else None
                        this_raw = this_row.get("Raw_Value", None)

                        prev_num = None
                        prev_raw = None
                        if prev_month:
                            prev_row = monthly[monthly["YearMonth"] == prev_month].iloc[0]
                            prev_num = prev_row["Value_num"] if pd.notna(prev_row["Value_num"]) else None
                            prev_raw = prev_row.get("Raw_Value", None)

                        year, month = sel_month.split("-")
                        same_month_last_year = f"{int(year) - 1:04d}-{month}"
                        yoy_num = None
                        yoy_raw = None
                        if same_month_last_year in month_options:
                            yoy_row = monthly[monthly["YearMonth"] == same_month_last_year].iloc[0]
                            yoy_num = yoy_row["Value_num"] if pd.notna(yoy_row["Value_num"]) else None
                            yoy_raw = yoy_row.get("Raw_Value", None)

                        c1, c2, c3 = st.columns(3)
                        if this_num is not None:
                            c1.metric(f"Nilai {sel_month}", float(this_num))
                        else:
                            c1.metric(f"Nilai {sel_month}", str(this_raw))

                        if prev_month:
                            if prev_num is not None:
                                delta_val = None if this_num is None else float(this_num - prev_num)
                                c2.metric(f"Nilai {prev_month}", float(prev_num), delta=delta_val)
                            else:
                                c2.metric(f"Nilai {prev_month}", str(prev_raw))
                        else:
                            c2.metric("Nilai Bulan Sebelumnya", "-")

                        if same_month_last_year in month_options:
                            if yoy_num is not None:
                                delta_yoy = None if this_num is None else float(this_num - yoy_num)
                                c3.metric(f"Nilai {same_month_last_year}", float(yoy_num), delta=delta_yoy)
                            else:
                                c3.metric(f"Nilai {same_month_last_year}", str(yoy_raw))
                        else:
                            c3.metric("Nilai Bulan Sama Tahun Lalu", "-")

                        table_cols = ["YearMonth"]
                        if monthly["Value_num"].notna().any():
                            table_cols.append("Value_num")
                        if "Raw_Value" in monthly.columns:
                            table_cols.append("Raw_Value")
                        st.dataframe(
                            monthly[table_cols].sort_values("YearMonth", ascending=False).head(24),
                            width="stretch",
                        )
    else:
        st.warning("Tidak ada equipment yang sesuai filter.")
