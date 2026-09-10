"""Presenter untuk view detail pada dashboard MCSA."""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
import plotly.express as px

from src.data_loader import get_data_path
from src.components.mcsa_dashboard_view_model import classify_condition_status
from src.standards import (
    generate_esa_mcsa_quick_recommendations,
    generate_initial_analysis,
)


def get_cached_esa_quick(st, eq_data: pd.DataFrame, cache_key: tuple) -> dict:
    """Ambil rekomendasi ESA/MCSA tanpa menghitung ulang pada rerun yang sama."""
    cache = st.session_state.setdefault("_esa_quick_cache", {})
    cached = cache.get(cache_key)
    if cached is None:
        cached = generate_esa_mcsa_quick_recommendations(eq_data)
        cache[cache_key] = cached
    return cached


def render_deep_analysis_view(
    st,
    eq_data: pd.DataFrame,
    eq_history: pd.DataFrame,
    selected_equipment: str,
) -> None:
    """Render laporan rule-based, insight LLM opsional, dan tren indikator utama."""
    st.subheader("Analisa & Rekomendasi Awal")

    analysis_data = generate_esa_mcsa_quick_recommendations(eq_data)
    detailed_report_text = analysis_data.get("detailed_report", "")

    if detailed_report_text:
        st.text_area("Laporan Analisa (Rule-Based)", value=detailed_report_text, height=450)
    else:
        st.info("Data tidak cukup untuk menghasilkan laporan analisa mendalam.")

    _render_optional_llm_analysis(
        st,
        selected_equipment=selected_equipment,
        detailed_report_text=detailed_report_text,
        eq_history=eq_history,
    )

    st.subheader("Indikator Utama")
    analysis_cache = st.session_state.get("_analysis_cache") or {}
    analysis_key = (st.session_state.get("_mcsa_data_key"), selected_equipment)
    analysis = analysis_cache.get(analysis_key)
    if analysis is None:
        analysis = generate_initial_analysis(eq_history)
        analysis_cache[analysis_key] = analysis
        st.session_state["_analysis_cache"] = analysis_cache

    indicators = analysis.get("indicators") or []
    if indicators:
        indicator_df = pd.DataFrame(indicators)
        if not indicator_df.empty:
            for column in indicator_df.columns:
                if indicator_df[column].dtype == object:
                    indicator_df[column] = indicator_df[column].astype(str)
        st.dataframe(indicator_df, width="stretch", hide_index=True)

    _render_key_parameter_trend(st, eq_history)

    recommendations = analysis.get("recommendations") or []
    if recommendations:
        st.markdown("\n".join([f"- {item}" for item in recommendations]))
    references = analysis.get("references") or []
    if references:
        st.caption("Referensi: " + " | ".join(references))


def _render_optional_llm_analysis(
    st,
    selected_equipment: str,
    detailed_report_text: str,
    eq_history: pd.DataFrame,
) -> None:
    # Import tetap lokal agar provider AI tidak menjadi dependensi bootstrap dashboard.
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

    with st.expander(
        f":material/auto_awesome: Analisis Model LLM Lanjutan ({provider_label})",
        expanded=ai_enabled and is_ready,
    ):
        if not is_ready and ai_provider in {"gemini", "groq"}:
            st.info(
                f"Anda dapat memasukkan API Key {ai_provider.upper()} melalui menu "
                "**Pengaturan Model LLM** di sidebar sebelah kiri atau file `.env`.",
                icon=":material/lightbulb:",
            )
            return

        provider_column, action_column = st.columns([3, 1])
        with provider_column:
            st.caption(f"Provider: **{ai_provider.upper()}** | Model: `{active_model}`")
        with action_column:
            generate_clicked = st.button(
                "Generate Analisis AI",
                icon=":material/psychology:",
                width="stretch",
            )

        if generate_clicked:
            with st.spinner(
                f"Model LLM ({provider_label}) sedang menganalisis data riwayat "
                f"{selected_equipment} & standar MCSA..."
            ):
                llm = MCSALLMAssistant(
                    enabled=True,
                    provider=ai_provider,
                    api_key=ai_key,
                    model=active_model,
                    base_url=(
                        st.session_state.get("opencode_base_url", DEFAULT_OPENCODE_BASE_URL)
                        if ai_provider == "opencode"
                        else None
                    ),
                    ollama_host=st.session_state.get("ollama_host", DEFAULT_OLLAMA_HOST),
                )
                result = llm.generate_detailed_analysis(
                    selected_equipment,
                    detailed_report_text,
                    eq_history,
                )
                st.session_state[f"_ai_analysis_{selected_equipment}"] = result

        saved_analysis = st.session_state.get(f"_ai_analysis_{selected_equipment}")
        if saved_analysis:
            st.markdown(
                "### :material/description: Executive Summary & Root Cause Analysis "
                f"({provider_label})"
            )
            st.markdown(saved_analysis)


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        if pd.isna(value):
            return None
        return float(value)
    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None
    cleaned = "".join(
        character
        for character in cleaned
        if character.isdigit() or character in {".", "-", "+", "e", "E"}
    )
    if cleaned in {"", "+", "-", ".", "+.", "-."}:
        return None
    try:
        return float(cleaned)
    except Exception:
        return None


def _render_key_parameter_trend(st, eq_history: pd.DataFrame) -> None:
    key_parameters = [
        "Load",
        "Dev Voltage",
        "Dev Current",
        "THD Voltage %",
        "THD Current %",
        "Upper Sideband",
        "Lower Sideband",
        "Rotorbar Health",
        "Rotorbar Level %",
    ]

    trend_source = eq_history.copy()
    if "Date" in trend_source.columns:
        trend_source["Date"] = pd.to_datetime(trend_source["Date"], errors="coerce")
    else:
        trend_source["Date"] = pd.NaT
    trend_source = trend_source.dropna(subset=["Date"])
    trend_source = trend_source[
        trend_source["Parameter"].astype(str).isin(key_parameters)
    ].copy()
    if trend_source.empty:
        return

    values = trend_source.get(
        "Value",
        pd.Series([None] * len(trend_source), index=trend_source.index),
    ).map(_to_number)
    trend_source["Trend_Value"] = values
    if "Raw_Value" in trend_source.columns:
        trend_source["Trend_Value"] = trend_source["Trend_Value"].fillna(
            trend_source["Raw_Value"].map(_to_number)
        )
    trend_source = trend_source.dropna(subset=["Trend_Value"])
    if trend_source.empty:
        return

    trend_source = trend_source.sort_values("Date")
    figure = px.line(
        trend_source,
        x="Date",
        y="Trend_Value",
        color="Parameter",
        markers=True,
        title="Trend Parameter Kunci",
    )
    st.plotly_chart(figure, width="stretch")


def render_recommendation_view(st, esa_quick: dict) -> None:
    """Render metrik, status, rekomendasi, dan referensi cepat ESA/MCSA."""
    st.subheader("Rekomendasi Cepat (ESA/MCSA)")
    overall_column, load_column, quality_column = st.columns(3)
    overall_column.metric("Overall", str(esa_quick.get("overall", "-")))
    load_percentage = esa_quick.get("values", {}).get("Load %")
    load_column.metric(
        "Load %",
        "-" if load_percentage is None else round(float(load_percentage), 2),
    )
    quality_column.metric(
        "Load Quality",
        str(esa_quick.get("statuses", {}).get("Load Quality", "-")),
    )

    status_items = [
        {"Indikator": key, "Status": value}
        for key, value in (esa_quick.get("statuses") or {}).items()
        if key != "Load Quality"
    ]
    if status_items:
        st.dataframe(pd.DataFrame(status_items), width="stretch", hide_index=True)

    recommendations = esa_quick.get("recommendations") or []
    if recommendations:
        st.markdown("\n".join([f"- {item}" for item in recommendations]))
    references = esa_quick.get("references") or []
    if references:
        st.caption("Referensi: " + " | ".join([str(item) for item in references]))


def render_summary_view(
    st,
    eq_data: pd.DataFrame,
    df_latest_all: pd.DataFrame,
    selected_equipment: str,
    esa_quick: dict,
    condition_class: str,
    materi_page=None,
) -> None:
    """Render rekomendasi singkat, pintasan materi, dan ringkasan performance."""
    st.subheader("Rekomendasi Cepat (ESA/MCSA)")
    recommendations = esa_quick.get("recommendations") or []
    if recommendations:
        st.markdown("\n".join([f"- {item}" for item in recommendations[:5]]))

    st.subheader("Materi Terkait")
    material_actions = [
        ("SOP Pengukuran", "sop", "sop"),
        ("Rotor Bar", "rotor bar", "mcsa"),
        ("Bearing", "bearing", "mcsa"),
        ("Power Quality", "power quality", "power"),
        ("Pattern Recognition", "pattern", "pattern"),
    ]
    columns = st.columns(len(material_actions))
    for column, (label, query, preferred_name) in zip(columns, material_actions):
        if column.button(label, width="stretch"):
            _open_materi(st, query, preferred_name, materi_page)

    if condition_class in {"alarm", "high"}:
        if st.button("Tindak Lanjut (Alarm/High)", width="stretch"):
            _open_materi(st, "tindak lanjut", "sop", materi_page)

    performance_rows = eq_data[
        eq_data["Parameter"].astype(str).str.startswith("Ringkasan Kinerja")
    ].copy()
    if performance_rows.empty:
        fallback = df_latest_all[df_latest_all["Equipment"] == selected_equipment]
        performance_rows = fallback[
            fallback["Parameter"].astype(str).str.startswith("Ringkasan Kinerja")
        ].copy()

    if performance_rows.empty:
        return

    st.subheader("Ringkasan Performance")
    performance_rows["Bagian"] = (
        performance_rows["Parameter"]
        .astype(str)
        .str.replace("Ringkasan Kinerja -", "", regex=False)
        .str.strip()
    )
    display_rows = (
        performance_rows[["Bagian", "Raw_Value"]]
        .rename(columns={"Raw_Value": "Ringkasan"})
        .drop_duplicates(subset=["Bagian"], keep="last")
        .sort_values("Bagian")
    )
    st.dataframe(display_rows, width="stretch", hide_index=True)


def _open_materi(st, query_text: str, preferred_name: Optional[str], materi_page) -> None:
    st.session_state["materi_query"] = query_text
    st.session_state["materi_prefer_name_contains"] = preferred_name
    if materi_page is not None:
        st.switch_page(materi_page)
    else:
        st.rerun()


def render_spectrum_view(
    st,
    selected_equipment: str,
    image_directory: Optional[str] = None,
) -> None:
    """Render pemilih gambar spektrum equipment bila aset gambarnya tersedia."""
    st.subheader("Analisis Spektrum")
    image_directory = image_directory or get_data_path("images")

    spectrum_images = []
    if os.path.exists(image_directory):
        spectrum_images = [
            filename
            for filename in os.listdir(image_directory)
            if filename.upper().startswith(f"{selected_equipment.upper()}_")
            and filename.lower().endswith(".png")
        ]
    spectrum_images.sort(reverse=True)

    if not spectrum_images:
        st.info("Tidak ada gambar spektrum yang tersedia untuk equipment ini.")
        return

    selector_column, image_column = st.columns([1, 2])
    with selector_column:
        selected_image = st.selectbox("Pilih Gambar Spektrum", spectrum_images)
    with image_column:
        if selected_image:
            st.image(
                os.path.join(image_directory, selected_image),
                caption=selected_image,
                width="stretch",
            )
