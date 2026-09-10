"""Trend and period-comparison presenters for the MCSA dashboard."""

import pandas as pd
import plotly.express as px


def _parameter_history(df: pd.DataFrame, equipment: str, parameter: str) -> pd.DataFrame:
    history = df[
        (df["Equipment"] == equipment) & (df["Parameter"] == parameter)
    ].copy()
    history["Date"] = pd.to_datetime(history.get("Date", pd.NaT), errors="coerce")
    return history.dropna(subset=["Date"]).sort_values("Date")


def render_trend_view(st, df: pd.DataFrame, selected_equipment: str) -> None:
    """Render configurable numeric or categorical equipment trends."""
    st.subheader("Trend Parameter")
    trend_parameters = sorted(df["Parameter"].unique())
    selected_parameter = st.selectbox(
        "Pilih Parameter untuk Trend:",
        trend_parameters,
        index=trend_parameters.index("Load") if "Load" in trend_parameters else 0,
        key="trend_param",
    )

    trend_range = st.segmented_control(
        "Rentang Waktu",
        ["3 Bulan", "6 Bulan", "12 Bulan", "Semua"],
        default="3 Bulan",
        key="trend_range",
    )
    aggregation = st.segmented_control(
        "Agregasi",
        ["Harian", "Bulanan", "Tahunan"],
        default="Harian",
        key="trend_agg",
    )

    history = _parameter_history(df, selected_equipment, selected_parameter)
    selected_history = history.copy()
    if not selected_history.empty:
        last_date = selected_history["Date"].max()
        if trend_range == "3 Bulan":
            start_date = last_date - pd.DateOffset(months=3)
        elif trend_range == "6 Bulan":
            start_date = last_date - pd.DateOffset(months=6)
        elif trend_range == "12 Bulan":
            start_date = last_date - pd.DateOffset(months=12)
        else:
            start_date = selected_history["Date"].min()
        selected_history = selected_history[selected_history["Date"] >= start_date]

    if selected_parameter in ["Kondisi", "Bearing"]:
        chart_data = selected_history.copy()
        if "Status_Category" not in chart_data.columns:
            chart_data["Status_Category"] = chart_data.get("Raw_Value", "")
        if "Status_Level" not in chart_data.columns:
            statuses = (
                chart_data.get("Status_Category", "")
                .astype(str)
                .str.strip()
                .str.lower()
            )
            levels = pd.Series(-1, index=chart_data.index)
            levels[statuses.str.contains("standby", na=False)] = 0
            levels[statuses.str.contains(r"normal|\bok\b|good", na=False)] = 1
            levels[statuses.str.contains("alarm|warning", na=False)] = 2
            levels[
                statuses.str.contains("high|bad|critical|rusak|damage", na=False)
            ] = 3
            chart_data["Status_Level"] = levels

        if aggregation == "Bulanan":
            chart_data["YearMonth"] = chart_data["Date"].dt.to_period("M").astype(str)
            chart_data = chart_data.sort_values("Date").drop_duplicates(
                subset=["YearMonth"], keep="last"
            )
            x_column = "YearMonth"
            title = f"Trend Bulanan {selected_parameter} - {selected_equipment}"
        elif aggregation == "Tahunan":
            chart_data["Year"] = chart_data["Date"].dt.year
            chart_data = chart_data.sort_values("Date").drop_duplicates(
                subset=["Year"], keep="last"
            )
            x_column = "Year"
            title = f"Trend Tahunan {selected_parameter} - {selected_equipment}"
        else:
            x_column = "Date"
            title = f"Trend Harian {selected_parameter} - {selected_equipment}"

        if chart_data.empty:
            st.info("Belum ada data untuk menampilkan trend parameter ini.")
            return
        figure = px.line(
            chart_data,
            x=x_column,
            y="Status_Level",
            title=title,
            markers=True,
            hover_data={"Status_Category": True, "Raw_Value": True},
        )
        st.plotly_chart(figure, width="stretch")
        return

    chart_data = selected_history.copy()
    chart_data["Value_num"] = pd.to_numeric(
        chart_data.get("Value", pd.NA), errors="coerce"
    )
    if "Raw_Value" in chart_data.columns:
        chart_data["Value_num"] = chart_data["Value_num"].fillna(
            pd.to_numeric(chart_data["Raw_Value"], errors="coerce")
        )
    if aggregation == "Bulanan":
        chart_data["YearMonth"] = chart_data["Date"].dt.to_period("M").astype(str)
        chart_data = chart_data.groupby("YearMonth", as_index=False)["Value_num"].mean()
        x_column, y_column = "YearMonth", "Value_num"
        title = f"Trend Bulanan {selected_parameter} - {selected_equipment}"
    elif aggregation == "Tahunan":
        chart_data["Year"] = chart_data["Date"].dt.year
        chart_data = chart_data.groupby("Year", as_index=False)["Value_num"].mean()
        x_column, y_column = "Year", "Value_num"
        title = f"Trend Tahunan {selected_parameter} - {selected_equipment}"
    else:
        x_column, y_column = "Date", "Value_num"
        title = f"Trend Harian {selected_parameter} - {selected_equipment}"

    if chart_data.empty or not chart_data[y_column].notna().any():
        st.info("Belum ada data numerik untuk menampilkan trend parameter ini.")
        return
    figure = px.line(
        chart_data,
        x=x_column,
        y=y_column,
        title=title,
        markers=True,
    )
    st.plotly_chart(figure, width="stretch")


def render_comparison_view(st, df: pd.DataFrame, selected_equipment: str) -> None:
    """Render latest, previous available month, and same-month prior-year values."""
    st.subheader("Perbandingan Bulanan/Tahunan")
    parameters = sorted(df["Parameter"].unique())
    selected_parameter = st.selectbox(
        "Pilih Parameter:",
        parameters,
        index=parameters.index("Load") if "Load" in parameters else 0,
        key="cmp_param",
    )

    monthly = _parameter_history(df, selected_equipment, selected_parameter)
    if monthly.empty:
        st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
        return
    monthly["YearMonth"] = monthly["Date"].dt.to_period("M").astype(str)

    if selected_parameter in ["Kondisi", "Bearing"]:
        _render_categorical_comparison(st, monthly, selected_equipment, selected_parameter)
    else:
        _render_numeric_comparison(st, monthly, selected_equipment, selected_parameter)


def _render_categorical_comparison(
    st,
    monthly: pd.DataFrame,
    selected_equipment: str,
    selected_parameter: str,
) -> None:
    if "Status_Category" not in monthly.columns:
        monthly["Status_Category"] = monthly.get("Raw_Value", "")
    raw_values = (
        monthly.get("Raw_Value", pd.Series("", index=monthly.index))
        .astype(str)
        .str.strip()
        .str.lower()
    )
    has_value = monthly["Status_Category"].notna() & raw_values.ne("") & raw_values.ne("nan")
    monthly = (
        monthly[has_value]
        .sort_values("Date")
        .drop_duplicates(subset=["YearMonth"], keep="last")
    )
    month_options = monthly["YearMonth"].tolist()
    if not month_options:
        st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
        return

    selected_month = st.selectbox(
        "Pilih Bulan (YYYY-MM)",
        month_options,
        index=len(month_options) - 1,
        key=f"month_cmp_{selected_equipment}_{selected_parameter}",
    )
    selected_index = month_options.index(selected_month)
    previous_month = month_options[selected_index - 1] if selected_index > 0 else None
    current_row = monthly[monthly["YearMonth"] == selected_month].iloc[0]
    current_status = str(
        current_row.get("Status_Category", current_row.get("Raw_Value", ""))
    )
    previous_status = None
    if previous_month:
        previous_row = monthly[monthly["YearMonth"] == previous_month].iloc[0]
        previous_status = str(
            previous_row.get("Status_Category", previous_row.get("Raw_Value", ""))
        )

    year, month = selected_month.split("-")
    prior_year_month = f"{int(year) - 1:04d}-{month}"
    prior_year_status = None
    if prior_year_month in month_options:
        prior_year_row = monthly[monthly["YearMonth"] == prior_year_month].iloc[0]
        prior_year_status = str(
            prior_year_row.get("Status_Category", prior_year_row.get("Raw_Value", ""))
        )

    current_col, previous_col, prior_year_col = st.columns(3)
    current_col.metric(f"Status {selected_month}", current_status)
    previous_col.metric(
        "Status Bulan Sebelumnya",
        previous_status if previous_status is not None else "-",
    )
    prior_year_col.metric(
        "Status Bulan Sama Tahun Lalu",
        prior_year_status if prior_year_status is not None else "-",
    )
    st.dataframe(
        monthly[["YearMonth", "Status_Category", "Raw_Value"]]
        .sort_values("YearMonth", ascending=False)
        .head(24),
        width="stretch",
    )


def _render_numeric_comparison(
    st,
    monthly: pd.DataFrame,
    selected_equipment: str,
    selected_parameter: str,
) -> None:
    monthly["Value_num"] = pd.to_numeric(monthly.get("Value", pd.NA), errors="coerce")
    if "Raw_Value" in monthly.columns:
        monthly["Value_num"] = monthly["Value_num"].fillna(
            pd.to_numeric(monthly["Raw_Value"], errors="coerce")
        )
        raw_values = monthly["Raw_Value"].astype(str).str.strip().str.lower()
        has_value = monthly["Value_num"].notna() | (
            monthly["Raw_Value"].notna() & raw_values.ne("") & raw_values.ne("nan")
        )
    else:
        has_value = monthly["Value_num"].notna()
    monthly = (
        monthly[has_value]
        .sort_values("Date")
        .drop_duplicates(subset=["YearMonth"], keep="last")
    )
    month_options = monthly["YearMonth"].tolist()
    if not month_options:
        st.info("Belum ada data untuk perbandingan bulanan/tahunan.")
        return

    selected_month = st.selectbox(
        "Pilih Bulan (YYYY-MM)",
        month_options,
        index=len(month_options) - 1,
        key=f"month_cmp_{selected_equipment}_{selected_parameter}",
    )
    selected_index = month_options.index(selected_month)
    previous_month = month_options[selected_index - 1] if selected_index > 0 else None

    current_row = monthly[monthly["YearMonth"] == selected_month].iloc[0]
    current_value = current_row["Value_num"] if pd.notna(current_row["Value_num"]) else None
    current_raw = current_row.get("Raw_Value", None)

    previous_value = None
    previous_raw = None
    if previous_month:
        previous_row = monthly[monthly["YearMonth"] == previous_month].iloc[0]
        previous_value = (
            previous_row["Value_num"] if pd.notna(previous_row["Value_num"]) else None
        )
        previous_raw = previous_row.get("Raw_Value", None)

    year, month = selected_month.split("-")
    prior_year_month = f"{int(year) - 1:04d}-{month}"
    prior_year_value = None
    prior_year_raw = None
    if prior_year_month in month_options:
        prior_year_row = monthly[monthly["YearMonth"] == prior_year_month].iloc[0]
        prior_year_value = (
            prior_year_row["Value_num"]
            if pd.notna(prior_year_row["Value_num"])
            else None
        )
        prior_year_raw = prior_year_row.get("Raw_Value", None)

    current_col, previous_col, prior_year_col = st.columns(3)
    if current_value is not None:
        current_col.metric(f"Nilai {selected_month}", float(current_value))
    else:
        current_col.metric(f"Nilai {selected_month}", str(current_raw))

    if previous_month:
        if previous_value is not None:
            delta = None if current_value is None else float(current_value - previous_value)
            previous_col.metric(f"Nilai {previous_month}", float(previous_value), delta=delta)
        else:
            previous_col.metric(f"Nilai {previous_month}", str(previous_raw))
    else:
        previous_col.metric("Nilai Bulan Sebelumnya", "-")

    if prior_year_month in month_options:
        if prior_year_value is not None:
            delta = None if current_value is None else float(current_value - prior_year_value)
            prior_year_col.metric(
                f"Nilai {prior_year_month}", float(prior_year_value), delta=delta
            )
        else:
            prior_year_col.metric(f"Nilai {prior_year_month}", str(prior_year_raw))
    else:
        prior_year_col.metric("Nilai Bulan Sama Tahun Lalu", "-")

    table_columns = ["YearMonth"]
    if monthly["Value_num"].notna().any():
        table_columns.append("Value_num")
    if "Raw_Value" in monthly.columns:
        table_columns.append("Raw_Value")
    st.dataframe(
        monthly[table_columns].sort_values("YearMonth", ascending=False).head(24),
        width="stretch",
    )
