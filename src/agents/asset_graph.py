"""
Power Plant Asset Knowledge Graph.
Models plant hierarchy: Plant -> Unit -> System -> Equipment -> Sub-components -> Sensor Streams.
"""

from typing import Dict, Any, List, Optional


class AssetKnowledgeGraph:
    """
    Asset Knowledge Graph representing PLTU Jeranjang's critical equipment hierarchy
    and sensor correlation mappings.
    """
    def __init__(self):
        self.plant_name = "PLTU Jeranjang (3 x 25 MW)"
        self.hierarchy = {
            "UNIT 1": {
                "Systems": {
                    "Boiler & Draft System": ["IDF 1A", "IDF 1B", "PAF 1A", "PAF 1B", "SAF 1A", "SAF 1B"],
                    "Feedwater & Condensate": ["BFP 1A", "BFP 1B", "CEP 1A", "CEP 1B"],
                    "Circulating Cooling Water": ["CWP 1A", "CWP 1B", "C3WP 1A", "C3WP 1B"],
                    "Vacuum System": ["VCP 1A", "VCP 1B"],
                    "Electrical & Transformer": ["Generator 1", "Main Transformer 1", "UAT 1"]
                }
            },
            "UNIT 2": {
                "Systems": {
                    "Feedwater & Condensate": ["CEP 2A", "CEP 2B"],
                    "Circulating Cooling Water": ["C3WP 2A", "C3WP 2B", "C3WP 2C"],
                    "Vacuum System": ["VCP 2A", "VCP 2B"]
                }
            },
            "UNIT 3": {
                "Systems": {
                    "Boiler & Draft System": ["IDF 3A", "IDF 3B", "PAF 3", "SAF 3", "RAF 3A", "RAF 3B"],
                    "Feedwater & Condensate": ["BFP 3A", "BFP 3B", "CEP 3A", "CEP 3B"],
                    "Circulating Cooling Water": ["CWP 3A", "CWP 3B", "C3WP 3A", "C3WP 3B", "CTF 3A", "CTF 3B"],
                    "High Pressure Wash": ["WJP 3A", "WJP 3B"]
                }
            },
            "UNIT COMMON": {
                "Systems": {
                    "Coal Handling System": ["BC 10.1", "BC 10.2", "BC 8.1", "BC 8.2", "BC 7.1", "BC 7.2", "CRUSHER 1", "CRUSHER 2"]
                }
            }
        }

    def get_equipment_node(self, equipment_name: str) -> Dict[str, Any]:
        eq_clean = equipment_name.upper().strip()
        for unit_name, unit_data in self.hierarchy.items():
            for sys_name, eq_list in unit_data["Systems"].items():
                for eq in eq_list:
                    if eq.upper() == eq_clean or eq_clean in eq.upper():
                        is_transformer = "Transformer" in sys_name or "Transformer" in eq
                        return {
                            "equipment": eq,
                            "unit": unit_name,
                            "system": sys_name,
                            "criticality": "A" if any(k in eq for k in ["BFP", "CWP", "IDF", "Generator", "Transformer"]) else "B",
                            "asset_type": "Oil-Filled Transformer" if is_transformer else "Electric Motor-Pump / Fan Drive",
                            "components": [
                                "Drive End (DE) Bearing",
                                "Non-Drive End (NDE) Bearing",
                                "Stator Winding & Core",
                                "Squirrel-Cage Rotor & End Rings",
                                "Flexible Coupling & Shaft"
                            ] if not is_transformer else [
                                "Primary/Secondary Windings",
                                "Insulating Mineral Oil & Core",
                                "On-Load Tap Changer (OLTC)",
                                "High-Voltage Bushings",
                                "Conservator & Cooling Radiator"
                            ],
                            "active_monitoring_streams": [
                                "Vibration Spectrum (DE/NDE)",
                                "Motor Current Signature (MCSA)",
                                "Infrared Thermography & RTD",
                                "Lube Oil Tribology"
                            ] if not is_transformer else [
                                "Dissolved Gas Analysis (DGA)",
                                "Online Partial Discharge (PRPD)",
                                "Oil Quality & Breakdown Voltage",
                                "Thermal Hotspot Monitoring"
                            ]
                        }

        return {
            "equipment": equipment_name,
            "unit": "UNIT COMMON",
            "system": "Auxiliary Drive",
            "criticality": "B",
            "asset_type": "Electric Motor Drive",
            "components": ["DE Bearing", "NDE Bearing", "Stator", "Rotor"],
            "active_monitoring_streams": ["Vibration", "MCSA", "Thermal"]
        }
