import re

import pandas as pd


def normalize_equipment_code(value) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(value or "")).upper()


def canonical_unit_name(value) -> str:
    s = str(value or "").strip().upper()
    s = re.sub(r"[_\-]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    if s in {"", "NAN", "NONE", "UNKNOWN"}:
        return "Unknown"
    if re.search(r"\b(COMMON|COMM|COM|CMN)\b", s):
        return "UNIT COMMON"
    match = re.search(r"\bUNIT\b\s*([1-3]|I|II|III)\b", s) or re.search(r"\bU\s*([1-3])\b", s)
    if not match:
        return "Unknown"
    roman = {"I": "1", "II": "2", "III": "3"}
    unit_no = roman.get(match.group(1), match.group(1))
    return f"UNIT {unit_no}"


def canonical_voltage_level(value) -> str:
    s = str(value or "").strip().upper().replace(" ", "")
    if s in {"", "NAN", "NONE", "UNKNOWN"}:
        return "Unknown"
    if "6.3" in s or "63KV" in s or "6KV" in s:
        return "6.3 KV"
    if any(token in s for token in ["400", "380"]):
        return "380/400 V"
    return "Unknown"


def enrich_equipment_metadata(df, master_df=None, folder_metadata=None):
    if df is None or df.empty:
        return df

    work = df.copy()
    for col in ["Equipment", "Unit_Name", "Voltage_Level", "Full_Name"]:
        if col not in work.columns:
            work[col] = ""

    work["Equipment"] = work["Equipment"].astype(str)
    work["_equip_norm"] = work["Equipment"].map(normalize_equipment_code)

    master_lookup = {}
    if isinstance(master_df, pd.DataFrame) and not master_df.empty:
        master = master_df.copy()
        for col in ["Equipment", "Unit_Name", "Voltage_Level", "Full_Name"]:
            if col not in master.columns:
                master[col] = ""
        master["_equip_norm"] = master["Equipment"].astype(str).map(normalize_equipment_code)
        master = master.drop_duplicates(subset=["_equip_norm"], keep="first")
        master_lookup = {
            row["_equip_norm"]: {
                "Unit_Name": canonical_unit_name(row.get("Unit_Name")),
                "Voltage_Level": canonical_voltage_level(row.get("Voltage_Level")),
                "Full_Name": str(row.get("Full_Name") or "").strip(),
            }
            for _, row in master.iterrows()
            if row.get("_equip_norm")
        }

    folder_lookup = {}
    for code, meta in (folder_metadata or {}).items():
        folder_lookup[normalize_equipment_code(code)] = {
            "Unit_Name": canonical_unit_name(meta.get("Unit")),
            "Voltage_Level": canonical_voltage_level(meta.get("Voltage")),
            "Full_Name": str(meta.get("Full_Name") or "").strip(),
        }

    def _should_fill_text(value):
        s = str(value or "").strip()
        return s == "" or s.lower() in {"unknown", "nan", "none"}

    for idx, row in work.iterrows():
        norm = row.get("_equip_norm")
        master_meta = master_lookup.get(norm, {})
        folder_meta = folder_lookup.get(norm, {})
        merged = {
            "Unit_Name": master_meta.get("Unit_Name") if master_meta.get("Unit_Name") not in {None, "", "Unknown"} else folder_meta.get("Unit_Name"),
            "Voltage_Level": master_meta.get("Voltage_Level") if master_meta.get("Voltage_Level") not in {None, "", "Unknown"} else folder_meta.get("Voltage_Level"),
            "Full_Name": master_meta.get("Full_Name") or folder_meta.get("Full_Name"),
        }

        if _should_fill_text(row.get("Unit_Name")) and merged.get("Unit_Name"):
            work.at[idx, "Unit_Name"] = merged["Unit_Name"]
        if _should_fill_text(row.get("Voltage_Level")) and merged.get("Voltage_Level"):
            work.at[idx, "Voltage_Level"] = merged["Voltage_Level"]
        current_full_name = str(row.get("Full_Name") or "").strip()
        if (current_full_name == str(row.get("Equipment") or "").strip() or _should_fill_text(current_full_name)) and merged.get("Full_Name"):
            work.at[idx, "Full_Name"] = merged["Full_Name"]

    work["Unit_Name"] = work["Unit_Name"].map(canonical_unit_name)
    work["Voltage_Level"] = work["Voltage_Level"].map(canonical_voltage_level)
    work["Full_Name"] = work.apply(
        lambda row: str(row.get("Full_Name") or "").strip() or str(row.get("Equipment") or "").strip(),
        axis=1,
    )
    return work.drop(columns=["_equip_norm"], errors="ignore")
