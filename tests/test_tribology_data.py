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


class TribologyAgentPartialDataTests(unittest.TestCase):
    """A real sample (e.g. only ISO 4406 read, viscosity/TAN/water not
    measured this cycle) makes build_tribology_agent_input emit every key
    with an explicit None for what's missing. TribologyAgent.evaluate() must
    treat that None as "use the default", not crash on float(None)."""

    def test_only_iso_measured_does_not_crash_and_falls_back_to_defaults(self):
        from src.agents.specialist_agents import TribologyAgent

        sample = {
            "viscosity_40c": None, "tan": None, "water_ppm": None,
            "wear_fe": None, "wear_cu": None, "iso_cleanliness": "20/18/15",
            "oil_type": "",
        }
        agent_input = build_tribology_agent_input(sample)
        result = TribologyAgent().evaluate("PAF 1B", agent_input)
        self.assertNotEqual(result.get("condition"), "UNKNOWN")
        self.assertEqual(result["metrics"]["iso_cleanliness"], "20/18/15")


if __name__ == "__main__":
    unittest.main()
