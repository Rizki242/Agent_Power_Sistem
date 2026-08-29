import unittest

from src.tribology_data import (
    build_tribology_agent_input,
    parse_iso_vg_nominal,
)


class ParseIsoVgNominalTests(unittest.TestCase):
    def test_extracts_grade_number(self):
        self.assertEqual(parse_iso_vg_nominal("ISO VG 46"), 46.0)
        self.assertEqual(parse_iso_vg_nominal("ISO VG 220"), 220.0)
        self.assertEqual(parse_iso_vg_nominal("ISO VG 68"), 68.0)

    def test_unparseable_input_defaults_to_46(self):
        self.assertEqual(parse_iso_vg_nominal("garbage"), 46.0)
        self.assertEqual(parse_iso_vg_nominal(""), 46.0)
        self.assertEqual(parse_iso_vg_nominal(None), 46.0)


class BuildTribologyAgentInputTests(unittest.TestCase):
    def test_maps_wear_fields_and_nominal_viscosity(self):
        sample = {
            "viscosity_40c": 44.2,
            "tan": 0.12,
            "water_ppm": 45,
            "wear_fe": 8,
            "wear_cu": 2,
            "iso_cleanliness": "16/14/11",
            "oil_type": "ISO VG 46",
        }
        result = build_tribology_agent_input(sample)
        self.assertEqual(result["fe_ppm"], 8)
        self.assertEqual(result["cu_ppm"], 2)
        self.assertEqual(result["nominal_viscosity"], 46.0)
        self.assertEqual(result["viscosity_40c"], 44.2)
        self.assertEqual(result["tan"], 0.12)
        self.assertEqual(result["water_ppm"], 45)
        self.assertEqual(result["iso_cleanliness"], "16/14/11")


if __name__ == "__main__":
    unittest.main()
