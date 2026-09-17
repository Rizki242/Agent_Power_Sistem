"""Register the plant equipment that only ever showed up in the monthly
"Exsume Vibrasi" test reports and never in the Asset_Master workbook - spare
pumps, standby compressors, fire-fighting units, jacking-oil pumps.

These 35 names survived exact- and alias-matching against the central Asset
Registry (see ingest_vibration_monthly_tests.py's per-run "no matching
registered asset" count) even after normalising whitespace/non-breaking
spaces, which ruled out a few more that were just formatting mismatches
(e.g. "ROLLER SCREEN 1" with a non-breaking space already existed under a
plain-space name). What's left is genuinely unregistered equipment: it has
vibration trend data in data/domain/VIBRASI/measurements.csv already, but no
asset_id, so it never got a condition-history entry and can't be found via
Register Aset / Asset 360.

This only sets monitoring_modules=["VIBRASI"] - these equipment appear
solely in the vibration report, not the Asset_Master spec workbook that
seeded MCSA/THERMAL/TRIBOLOGY for the other ~90 assets, so claiming those
modules here would be a fabricated capability, not a derived one.

After running this, re-run ingest_vibration_monthly_tests.py against the
already-ingested monthly reports so it can now find these assets and add
their condition-history entries too (it is idempotent, so this is safe).
"""

from src.asset_registry import upsert_asset

_EQUIPMENT = [
    ("Motor Condensat Pump 1#1", "UNIT 1"),
    ("Motor Boiler Feed Pump 2#1", "UNIT 1"),
    ("Motor BWRO 2#1", "UNIT 1"),
    ("Motor SWRO 1 #1", "UNIT 1"),
    ("DC OIL PUMP UNIT 1", "UNIT 1"),
    ("DIESEL FIRE FIGHTING UNIT 1", "UNIT 1"),
    ("ELECTRIC FIRE FIGHTING UNIT 1", "UNIT 1"),
    ("JOCKEY FIGHTING UNIT 1", "UNIT 1"),
    ("Motor Condensat Pump 2#2", "UNIT 2"),
    ("Motor Boiler Feed Pump 1#2", "UNIT 2"),
    ("Motor CCCWP 2C", "UNIT 2"),
    ("AC OIL PUMP UNIT 2", "UNIT 2"),
    ("DC OIL PUMP UNIT 2", "UNIT 2"),
    ("Motor Recirculating Air Fan 1#3", "UNIT 3"),
    ("Motor Condensat Pump 3#3", "UNIT 3"),
    ("Motor Water jet Pump 1#3", "UNIT 3"),
    ("Motor Boiler Feed Pump 2#3", "UNIT 3"),
    ("Motor CWP 355 Kw 2#3", "UNIT 3"),
    ("Motor BWRO 2#3", "UNIT 3"),
    ("Motor SWRO 2#3", "UNIT 3"),
    ("Fire Fighting Jockey Pump 1", "UNIT 3"),
    ("Fire Fighting Jockey Pump 2", "UNIT 3"),
    ("Fire Fighting Pump With Motor", "UNIT 3"),
    ("Fire Fighting Pump With Diesel", "UNIT 3"),
    ("DC Oil Pump Unit 3", "UNIT 3"),
    ("Jacking Oil Pump 3B", "UNIT 3"),
    ("Compressor For Instrument 1#1", "UNIT COMMON"),
    ("Compressor For Instrument 2#1", "UNIT COMMON"),
    ("Compressor For Instrument 3#1", "UNIT COMMON"),
    ("Compressor For Ash Handling 1#1", "UNIT COMMON"),
    ("Compressor For Ash Handling 2#1", "UNIT COMMON"),
    ("Compressor For Ash Handling 3#1", "UNIT COMMON"),
    ("Compressor For Service 1#1", "UNIT COMMON"),
    ("Compressor For Service 2#1", "UNIT COMMON"),
    ("Compressor For Service 3#1", "UNIT COMMON"),
]


def _infer_equipment_type(name: str) -> str:
    upper = name.upper()
    if "COMPRESSOR" in upper:
        return "Air Compressor"
    if "FIGHTING" in upper:
        return "Fire Fighting Pump"
    if "FAN" in upper:
        return "Motor Fan / Blower"
    if "PUMP" in upper:
        return "Motor Pump"
    return "Electric Drive"


def main() -> None:
    added = 0
    for name, unit in _EQUIPMENT:
        result = upsert_asset({
            "name": name,
            "unit": unit,
            "equipment_type": _infer_equipment_type(name),
            "voltage_level": "-",
            "lifecycle_status": "Aktif",
            "monitoring_modules": ["VIBRASI"],
            "notes": "Diimpor dari laporan Exsume Vibrasi bulanan - tidak ada di Asset_Master, "
                     "sehingga hanya modul VIBRASI yang ditetapkan.",
        })
        print(f"Upserted: {result['asset_id']} - {result['name']} ({result['unit']}, {result['equipment_type']})")
        added += 1
    print(f"\nDone. {added} equipment registered/updated.")


if __name__ == "__main__":
    main()
