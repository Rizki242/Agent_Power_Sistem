"""Transformasi data murni untuk dashboard MCSA.

Modul ini tidak bergantung pada Streamlit sehingga fallback metadata, tabel
parameter, dan ringkasan health dapat diuji tanpa menjalankan UI.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analytics import calculate_equipment_health_score, detect_equipment_anomalies
from src.components.status_colors import canon_condition_status
from src.equipment_canon import canon_unit_name, canon_voltage_level, norm_equipment


@dataclass
class EquipmentSelectionModel:
    detail_df: pd.DataFrame
    display_map: dict[str, str]
    master_by_norm: dict[str, dict]


@dataclass
class EquipmentDetailModel:
    selected_equipment: str
    full_name: str
    unit_name: str
    voltage_level: str
    status: str
    condition_class: str
    eq_data: pd.DataFrame
    history: pd.DataFrame
    table_df: pd.DataFrame
    health_summary: dict
    anomaly_rows: list[dict]


def build_equipment_selection_model(
    latest_data: pd.DataFrame,
    selected_unit: str,
    selected_voltage: str,
    selected_equipment: list,
    equipment_master: pd.DataFrame,
    master_norm_to_unit: dict,
    master_norm_to_voltage: dict,
) -> EquipmentSelectionModel:
    """Filter snapshot terbaru dan susun label equipment yang stabil."""
    master_by_norm = _build_master_lookup(equipment_master)
    detail_df = latest_data.copy()

    if selected_unit != "All":
        unit_series = (
            detail_df.get("Unit_Name", pd.Series(dtype=str))
            .astype(str)
            .map(canon_unit_name)
        )
        norm_series = (
            detail_df.get("Equipment", pd.Series(dtype=str))
            .astype(str)
            .map(norm_equipment)
        )
        unit_series = norm_series.map(master_norm_to_unit).fillna(unit_series)
        detail_df = detail_df[unit_series == selected_unit]

    if selected_voltage != "All":
        voltage_series = (
            detail_df.get("Voltage_Level", pd.Series(dtype=str))
            .astype(str)
            .map(canon_voltage_level)
        )
        norm_series = (
            detail_df.get("Equipment", pd.Series(dtype=str))
            .astype(str)
            .map(norm_equipment)
        )
        voltage_series = norm_series.map(master_norm_to_voltage).fillna(voltage_series)
        detail_df = detail_df[voltage_series == selected_voltage]

    if selected_equipment:
        equipment_series = detail_df.get("Equipment", pd.Series(dtype=str)).astype(str)
        detail_df = detail_df[equipment_series.isin(selected_equipment)]

    display_map = _build_equipment_display_map(detail_df, master_by_norm)
    return EquipmentSelectionModel(
        detail_df=detail_df,
        display_map=display_map,
        master_by_norm=master_by_norm,
    )


def _build_master_lookup(equipment_master: pd.DataFrame) -> dict[str, dict]:
    if not isinstance(equipment_master, pd.DataFrame) or equipment_master.empty:
        return {}

    master = equipment_master.copy()
    if "Equipment" not in master.columns:
        return {}
    master["_norm"] = master["Equipment"].astype(str).map(norm_equipment)
    master = master.drop_duplicates(subset=["_norm"], keep="first")

    lookup = {}
    for _, row in master.iterrows():
        normalized = row.get("_norm")
        if normalized:
            lookup[normalized] = {
                "Equipment": row.get("Equipment"),
                "Full_Name": row.get("Full_Name"),
                "Unit_Name": row.get("Unit_Name"),
                "Voltage_Level": row.get("Voltage_Level"),
            }
    return lookup


def _build_equipment_display_map(
    detail_df: pd.DataFrame,
    master_by_norm: dict[str, dict],
) -> dict[str, str]:
    if detail_df.empty or "Equipment" not in detail_df.columns:
        return {}

    metadata_columns = ["Equipment"]
    if "Full_Name" in detail_df.columns:
        metadata_columns.append("Full_Name")
    metadata = detail_df[metadata_columns].drop_duplicates(subset=["Equipment"]).copy()
    metadata["Equipment"] = metadata["Equipment"].astype(str)
    if "Full_Name" not in metadata.columns:
        metadata["Full_Name"] = metadata["Equipment"]
    else:
        metadata["Full_Name"] = metadata["Full_Name"].astype(str)
    metadata["_norm"] = metadata["Equipment"].map(norm_equipment)

    def resolve_full_name(row) -> str:
        full_name = str(row.get("Full_Name") or "").strip()
        equipment = str(row.get("Equipment") or "").strip()
        if not full_name or full_name.lower() in {"nan", "none"} or full_name == equipment:
            reference = master_by_norm.get(row.get("_norm"))
            reference_name = str((reference or {}).get("Full_Name") or "").strip()
            if reference_name:
                return reference_name
        return full_name or equipment

    metadata["Full_Name"] = metadata.apply(resolve_full_name, axis=1)
    metadata = metadata.sort_values("Equipment")
    equipment_codes = metadata["Equipment"].astype(str)
    full_names = metadata["Full_Name"].fillna("").astype(str).str.strip()
    full_names = full_names.where(
        ~full_names.str.lower().isin(["", "nan", "none", "null"]),
        equipment_codes,
    )
    labels = full_names.where(
        full_names == equipment_codes,
        full_names + " (" + equipment_codes + ")",
    )
    return dict(zip(labels.tolist(), equipment_codes.tolist()))


def build_equipment_detail_model(
    history: pd.DataFrame,
    detail_df: pd.DataFrame,
    selected_equipment: str,
    master_by_norm: dict[str, dict],
    master_norm_to_unit: dict,
    master_norm_to_voltage: dict,
    status_by_norm: dict,
) -> EquipmentDetailModel:
    """Susun seluruh data yang diperlukan presenter detail satu equipment."""
    eq_data = detail_df[detail_df["Equipment"] == selected_equipment].copy()
    eq_history = history[history["Equipment"] == selected_equipment].copy()
    normalized = norm_equipment(selected_equipment)
    reference = master_by_norm.get(normalized) or {}

    unit_name = master_norm_to_unit.get(normalized) or _first_value(
        eq_data, "Unit_Name", "-"
    )
    voltage_level = master_norm_to_voltage.get(normalized) or _first_value(
        eq_data, "Voltage_Level", "-"
    )
    full_name = _first_value(eq_data, "Full_Name", "-")

    if _is_missing_metadata(full_name) or str(full_name).strip() == selected_equipment:
        full_name = reference.get("Full_Name") or full_name
    if _is_missing_metadata(unit_name):
        unit_name = reference.get("Unit_Name") or unit_name
    if _is_missing_metadata(voltage_level):
        voltage_level = reference.get("Voltage_Level") or voltage_level

    table_df = _build_parameter_table(eq_data, eq_history)
    health_parameters = _build_health_parameters(eq_history)
    health_summary = calculate_equipment_health_score(health_parameters)
    anomaly_rows = detect_equipment_anomalies(eq_history)
    condition_class = classify_condition_status(_current_condition(eq_data))

    return EquipmentDetailModel(
        selected_equipment=selected_equipment,
        full_name=str(full_name),
        unit_name=str(unit_name),
        voltage_level=str(voltage_level),
        status=(
            status_by_norm.get(normalized, "Unknown")
            if isinstance(status_by_norm, dict)
            else "Unknown"
        ),
        condition_class=condition_class,
        eq_data=eq_data,
        history=eq_history,
        table_df=table_df,
        health_summary=health_summary,
        anomaly_rows=anomaly_rows,
    )


def _first_value(data: pd.DataFrame, column: str, default):
    if column not in data.columns or data.empty:
        return default
    return data[column].iloc[0]


def _is_missing_metadata(value) -> bool:
    return str(value).strip() in {"", "-", "Unknown", "nan", "None"}


def _latest_parameter_row(history: pd.DataFrame, parameter: str):
    source = history[history["Parameter"] == parameter]
    if source.empty:
        return None

    if "Date" in source.columns:
        source = source.copy()
        source["Date"] = pd.to_datetime(source["Date"], errors="coerce")
        source = source.dropna(subset=["Date"])
        if not source.empty:
            source = source.sort_values("Date", ascending=False)

    if "Raw_Value" in source.columns:
        has_value = source["Raw_Value"].notna() & source["Raw_Value"].astype(str).str.strip().ne("")
        if has_value.any():
            return source[has_value].iloc[0]
    return source.iloc[0] if not source.empty else None


def _build_parameter_table(
    eq_data: pd.DataFrame,
    eq_history: pd.DataFrame,
) -> pd.DataFrame:
    base_columns = ["Parameter"]
    for column in ["Raw_Value", "Value", "Unit", "Status_Category", "Status"]:
        if column in eq_data.columns:
            base_columns.append(column)

    rows = eq_data[base_columns].copy()
    rows["Parameter"] = rows.get("Parameter", "").astype(str)
    existing_parameters = set(rows["Parameter"].astype(str))

    for parameter in ["THD Voltage %", "THD Current %"]:
        if parameter in existing_parameters:
            continue
        latest = _latest_parameter_row(eq_history, parameter)
        row_data = {column: None for column in base_columns}
        row_data["Parameter"] = parameter
        if latest is not None:
            for column in base_columns:
                if column in latest.index:
                    row_data[column] = latest.get(column)
        if "Unit" in base_columns and _is_blank(row_data.get("Unit")):
            row_data["Unit"] = "%"
        if "Status" in base_columns and _is_blank(row_data.get("Status")):
            row_data["Status"] = "Unknown"
        if "Status_Category" in base_columns and _is_blank(row_data.get("Status_Category")):
            row_data["Status_Category"] = row_data.get("Status")
        rows = pd.concat([rows, pd.DataFrame([row_data])], ignore_index=True)
        existing_parameters.add(parameter)

    raw_values = rows.get(
        "Raw_Value", pd.Series([""] * len(rows), index=rows.index)
    ).astype(str)
    raw_values = raw_values.where(~raw_values.str.lower().isin({"nan", "none"}), "")
    values = rows.get("Value", pd.Series([None] * len(rows), index=rows.index))
    try:
        numeric_values = pd.to_numeric(values, errors="coerce")
    except Exception:
        numeric_values = pd.Series([None] * len(rows), index=rows.index)
    formatted_values = numeric_values.map(
        lambda value: ""
        if pd.isna(value)
        else (f"{value:.3f}" if abs(float(value)) < 1000 else f"{value:,.0f}")
    )
    display_values = raw_values.where(raw_values.str.strip().ne(""), formatted_values)
    units = rows.get("Unit", pd.Series([""] * len(rows), index=rows.index)).astype(str)
    units = units.where(~units.str.lower().isin({"nan", "none"}), "")

    status_source = rows.get("Status_Category")
    if status_source is None:
        status_source = rows.get("Status")
    if status_source is None:
        status_source = rows.get("Raw_Value")
    status_source = status_source.astype(str)
    display_condition_status = rows["Parameter"].map(
        lambda parameter: str(parameter).strip().lower()
    ).isin({"kondisi", "bearing"})
    status_values = status_source.where(
        display_condition_status,
        rows.get("Status", status_source),
    ).map(canon_condition_status)

    table = pd.DataFrame(
        {
            "Parameter": rows["Parameter"],
            "Nilai": display_values.astype(str),
            "Unit": units,
            "Status": status_values,
        }
    )
    return table.replace({"nan": "", "None": ""})


def _is_blank(value) -> bool:
    if value is None:
        return True
    return str(value).strip().lower() in {"", "nan", "none"}


def _build_health_parameters(eq_history: pd.DataFrame) -> dict:
    parameters = {}
    for parameter in [
        "Load",
        "Dev Voltage",
        "Dev Current",
        "THD Voltage %",
        "THD Current %",
        "Bearing",
        "Rotorbar",
        "Upper Sideband",
        "Lower Sideband",
        "Rotorbar Health",
    ]:
        latest = _latest_parameter_row(eq_history, parameter)
        if latest is None:
            continue
        value = latest.get("Value")
        if value is None or (isinstance(value, float) and pd.isna(value)):
            value = latest.get("Raw_Value")
        parameters[parameter] = value
    return parameters


def _current_condition(eq_data: pd.DataFrame):
    rows = eq_data[eq_data["Parameter"] == "Kondisi"]
    if rows.empty:
        return ""
    row = rows.iloc[0]
    if "Status_Category" in rows.columns and pd.notna(row.get("Status_Category")):
        return row.get("Status_Category")
    return row.get("Raw_Value")


def classify_condition_status(text: str) -> str:
    """Kelompokkan status kondisi untuk menentukan aksi materi lanjutan."""
    value = str(text or "").strip().lower()
    if any(token in value for token in ("high", "bad", "critical", "rusak", "damage")):
        return "high"
    if "alarm" in value or "warning" in value:
        return "alarm"
    if "standby" in value:
        return "standby"
    if "normal" in value or value == "ok" or "good" in value:
        return "normal"
    return "unknown"
