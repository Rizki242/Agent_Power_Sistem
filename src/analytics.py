from datetime import datetime, timedelta

import pandas as pd

from src.rotorbar import evaluate_rotorbar
from src.utils import safe_float as _safe_float


def calculate_equipment_health_score(params):
    score = 100
    drivers = []

    rotor = str(params.get("Rotorbar") or "").strip()
    if not rotor and any(key in params for key in ["Upper Sideband", "Lower Sideband", "Rotorbar Health"]):
        rotor = evaluate_rotorbar(params).get("Status") or ""
    rotor = rotor.lower()
    if "high" in rotor:
        score -= 35
        drivers.append("Rotorbar")
    elif "alarm" in rotor:
        score -= 20
        drivers.append("Rotorbar")

    for field, warn_limit, high_limit, warn_penalty, high_penalty in [
        ("THD Voltage %", 5.0, 8.0, 8, 15),
        ("THD Current %", 5.0, 8.0, 8, 15),
        ("Dev Voltage", 1.0, 2.0, 6, 12),
        ("Dev Current", 5.0, 10.0, 10, 18),
    ]:
        value = _safe_float(params.get(field))
        if value is None:
            continue
        if value > high_limit:
            score -= high_penalty
            drivers.append(field)
        elif value > warn_limit:
            score -= warn_penalty
            drivers.append(field)

    bearing = str(params.get("Bearing") or "").strip().lower()
    if any(token in bearing for token in ["high", "bad", "damage", "rusak"]):
        score -= 20
        drivers.append("Bearing")
    elif any(token in bearing for token in ["alarm", "warning"]):
        score -= 10
        drivers.append("Bearing")

    load = _safe_float(params.get("Load"))
    if load is not None and load < 20:
        score -= 10
        drivers.append("Load")

    score = max(0, min(100, score))
    return {"score": score, "drivers": sorted(set(drivers))}


def build_risk_summary(df_latest, top_n=10):
    if df_latest is None or df_latest.empty:
        return []

    rows = []
    work = df_latest.copy()
    for equipment, group in work.groupby("Equipment"):
        params = {}
        unit_name = group["Unit_Name"].iloc[0] if "Unit_Name" in group.columns else ""
        voltage_level = group["Voltage_Level"].iloc[0] if "Voltage_Level" in group.columns else ""
        full_name = group["Full_Name"].iloc[0] if "Full_Name" in group.columns else equipment
        for _, row in group.iterrows():
            value = row.get("Value")
            if value is None or (isinstance(value, float) and pd.isna(value)):
                value = row.get("Raw_Value")
            params[str(row.get("Parameter"))] = value
        summary = calculate_equipment_health_score(params)
        rows.append(
            {
                "Equipment": equipment,
                "Full_Name": full_name,
                "Unit_Name": unit_name,
                "Voltage_Level": voltage_level,
                "Health Score": summary["score"],
                "Drivers": ", ".join(summary["drivers"]),
            }
        )
    risk_df = pd.DataFrame(rows).sort_values(["Health Score", "Equipment"], ascending=[True, True])
    return risk_df.head(top_n).to_dict("records")


def detect_equipment_anomalies(history_df):
    if history_df is None or history_df.empty:
        return []

    work = history_df.copy()
    work["Date"] = pd.to_datetime(work.get("Date", pd.NaT), errors="coerce")
    value_num = pd.to_numeric(work.get("Value", pd.NA), errors="coerce")
    value_num = value_num.fillna(pd.to_numeric(work.get("Raw_Value", pd.NA), errors="coerce"))
    work["_value_num"] = value_num
    work = work.dropna(subset=["Date", "_value_num", "Equipment", "Parameter"])

    rules = {
        "THD Voltage %": 0.30,
        "THD Current %": 0.30,
        "Dev Current": 0.20,
        "Rotorbar Health": -0.20,
    }
    anomalies = []
    for (equipment, parameter), group in work.groupby(["Equipment", "Parameter"]):
        if parameter not in rules or len(group) < 4:
            continue
        group = group.sort_values("Date")
        latest = float(group["_value_num"].iloc[-1])
        baseline = float(group["_value_num"].iloc[-4:-1].mean())
        if baseline == 0:
            continue
        pct_change = (latest - baseline) / abs(baseline)
        threshold = rules[parameter]
        is_hit = pct_change >= threshold if threshold > 0 else pct_change <= threshold
        if is_hit:
            anomalies.append(
                {
                    "Equipment": equipment,
                    "Parameter": parameter,
                    "Latest": latest,
                    "Baseline": baseline,
                    "Percent Change": round(pct_change * 100.0, 1),
                    "Date": group["Date"].iloc[-1].date().isoformat(),
                }
            )
    return anomalies


def summarize_word_report_quality(df_word, report, required_params, max_future_days=30):
    summary = {
        "failed_files_count": len((report or {}).get("failures") or []),
        "failed_files": (report or {}).get("failures") or [],
        "missing_parameter_rows": [],
        "numeric_flag_rows": [],
        "duplicate_rows": [],
        "weird_date_rows": [],
        "missing_metadata_rows": [],
    }
    if df_word is None or df_word.empty:
        return summary

    work = df_word.copy()
    work["Date"] = pd.to_datetime(work.get("Date", pd.NaT), errors="coerce")
    now_limit = datetime.now().date() + timedelta(days=max_future_days)
    future_mask = work["Date"].dt.date > now_limit
    summary["weird_date_rows"] = work.loc[future_mask, ["Equipment", "Parameter", "Date"]].to_dict("records")

    latest_word = work.sort_values("Date").drop_duplicates(subset=["Equipment", "Parameter"], keep="last")
    present = latest_word.groupby("Equipment")["Parameter"].apply(lambda values: set(values.astype(str))).to_dict()
    for equipment, params in present.items():
        missing = [param for param in required_params if param not in params]
        if missing:
            summary["missing_parameter_rows"].append(
                {"Equipment": equipment, "Missing_Count": len(missing), "Missing": ", ".join(missing)}
            )

    work["_value_num"] = pd.to_numeric(work.get("Value", pd.NA), errors="coerce")
    work["_value_num"] = work["_value_num"].fillna(pd.to_numeric(work.get("Raw_Value", pd.NA), errors="coerce"))
    qc = work[work["Parameter"].isin(["Load", "THD Current %", "THD Voltage %", "Dev Voltage", "Dev Current"])]
    for _, row in qc.dropna(subset=["_value_num"]).iterrows():
        value = float(row["_value_num"])
        parameter = row["Parameter"]
        bad = False
        if parameter == "Load" and (value < 0 or value > 120):
            bad = True
        if parameter in {"THD Current %", "THD Voltage %"} and (value < 0 or value > 50):
            bad = True
        if parameter in {"Dev Voltage", "Dev Current"} and (value < 0 or value > 50):
            bad = True
        if bad:
            summary["numeric_flag_rows"].append(
                {"Equipment": row["Equipment"], "Parameter": parameter, "Date": row["Date"], "Value": value}
            )

    dup_mask = work.duplicated(subset=["Equipment", "Parameter", "Date"], keep=False)
    summary["duplicate_rows"] = work.loc[dup_mask, ["Equipment", "Parameter", "Date"]].to_dict("records")

    def _is_unknown(value):
        text = str(value or "").strip().lower()
        return text in {"", "unknown", "nan", "none"}

    meta_mask = work.apply(
        lambda row: _is_unknown(row.get("Unit_Name")) or _is_unknown(row.get("Voltage_Level")),
        axis=1,
    )
    summary["missing_metadata_rows"] = work.loc[
        meta_mask, ["Equipment", "Parameter", "Unit_Name", "Voltage_Level"]
    ].to_dict("records")
    return summary


def build_word_qc_export(summary, report):
    """Flatten hasil quality check agar dapat diekspor dan ditindaklanjuti."""
    summary = summary or {}
    report = report or {}
    rows = [
        {
            "Kategori": "Ringkasan",
            "Item": "Total file",
            "Jumlah": int(report.get("total_files", 0)),
            "Alasan": "",
        },
        {
            "Kategori": "Ringkasan",
            "Item": "File berhasil diparsing",
            "Jumlah": int(report.get("parsed_files", 0)),
            "Alasan": "",
        },
        {
            "Kategori": "Ringkasan",
            "Item": "File gagal diparsing",
            "Jumlah": int(summary.get("failed_files_count", 0)),
            "Alasan": "",
        },
    ]

    def add_details(category, details, default_reason):
        for item in details or []:
            item = item or {}
            rows.append({
                "Kategori": category,
                "Item": item.get("file") or item.get("Equipment") or "-",
                "Equipment": item.get("Equipment", ""),
                "Parameter": item.get("Parameter", ""),
                "Tanggal": item.get("Date", ""),
                "Jumlah": item.get("Missing_Count", ""),
                "Alasan": item.get("error") or item.get("Missing") or default_reason,
            })

    add_details("Gagal diproses", summary.get("failed_files"), "Parser tidak dapat membaca laporan")
    add_details("Parameter wajib hilang", summary.get("missing_parameter_rows"), "Parameter wajib tidak ditemukan")
    add_details("Nilai numerik tidak wajar", summary.get("numeric_flag_rows"), "Nilai di luar rentang quality check")
    add_details("Duplikasi", summary.get("duplicate_rows"), "Equipment, parameter, dan tanggal sama")
    add_details("Tanggal tidak wajar", summary.get("weird_date_rows"), "Tanggal melebihi batas quality check")
    add_details("Metadata belum lengkap", summary.get("missing_metadata_rows"), "Unit atau voltage belum dikenali")
    return pd.DataFrame(rows)
