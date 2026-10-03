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
    """Missing measurements remain unknown rather than example readings."""

    def test_only_iso_measured_remains_unknown_without_fabricated_metrics(self):
        from src.agents.specialist_agents import TribologyAgent

        sample = {
            "viscosity_40c": None, "tan": None, "water_ppm": None,
            "wear_fe": None, "wear_cu": None, "iso_cleanliness": "20/18/15",
            "oil_type": "",
        }
        agent_input = build_tribology_agent_input(sample)
        result = TribologyAgent().evaluate("PAF 1B", agent_input)
        self.assertEqual(result["condition"], "UNKNOWN")
        self.assertIsNone(result["health_score"])
        self.assertEqual(result["metrics"]["iso_cleanliness"], "20/18/15")
        for key in ("viscosity_40c", "viscosity_dev_pct", "tan_mgkoh_g", "water_ppm", "fe_ppm", "cu_ppm"):
            self.assertIsNone(result["metrics"][key], key)
        self.assertEqual(result["data_quality"]["status"], "insufficient_data")
        self.assertIn("fe_ppm", result["next_data_needed"])

    def test_partial_normal_reading_does_not_claim_overall_healthy(self):
        from src.agents.specialist_agents import TribologyAgent

        result = TribologyAgent().evaluate("PAF 1B", {"water_ppm": 0})
        self.assertEqual(result["metrics"]["water_ppm"], 0)
        self.assertIsNone(result["metrics"]["fe_ppm"])
        self.assertEqual(result["condition"], "UNKNOWN")
        self.assertIsNone(result["health_score"])

    def test_partial_abnormal_reading_preserves_real_alarm_with_lower_confidence(self):
        from src.agents.specialist_agents import TribologyAgent

        agent = TribologyAgent()
        partial = agent.evaluate("BFP 1A", {"fe_ppm": 85})
        full = agent.evaluate("BFP 1A", {
            "fe_ppm": 85, "cu_ppm": 2, "water_ppm": 45, "tan": 0.12,
            "viscosity_40c": 44.2, "nominal_viscosity": 46,
            "iso_cleanliness": "16/14/11",
        })
        self.assertEqual(partial["condition"], "CRITICAL")
        self.assertEqual(partial["health_score"], full["health_score"])
        self.assertLess(partial["confidence"], full["confidence"])
        self.assertEqual(partial["data_quality"]["status"], "partial")
        self.assertIsNone(partial["metrics"]["water_ppm"])
        self.assertTrue(partial["evidence"])

    def test_blank_nonfinite_and_metadata_only_values_are_not_measurements(self):
        from src.agents.specialist_agents import TribologyAgent

        for data in ({"water_ppm": " "}, {"fe_ppm": float("nan")},
                     {"tan": float("inf")}, {"nominal_viscosity": 46},
                     {"fe_ppm": "invalid"}, {"water_ppm": -1}):
            with self.subTest(data=data):
                result = TribologyAgent().evaluate("BFP 1A", data)
                self.assertEqual(result["condition"], "UNKNOWN")
                self.assertIsNone(result["health_score"])

    def test_viscosity_deviation_requires_real_nominal_value(self):
        from src.agents.specialist_agents import TribologyAgent

        for nominal in (None, 0):
            result = TribologyAgent().evaluate("BFP 1A", {
                "viscosity_40c": 44.2, "nominal_viscosity": nominal,
            })
            self.assertEqual(result["metrics"]["viscosity_40c"], 44.2)
            self.assertIsNone(result["metrics"]["viscosity_dev_pct"])

    def test_existing_alarm_boundaries_are_unchanged(self):
        from src.agents.specialist_agents import TribologyAgent

        for key, boundary, condition in (("fe_ppm", 40, "ALERT"),
                                         ("fe_ppm", 80, "CRITICAL"),
                                         ("water_ppm", 500, "ALERT"),
                                         ("tan", 0.8, "ALERT")):
            for offset in (-0.001, 0, 0.001):
                with self.subTest(key=key, boundary=boundary, offset=offset):
                    result = TribologyAgent().evaluate("BFP 1A", {key: boundary + offset})
                    if offset >= 0:
                        self.assertEqual(result["condition"], condition)
                    else:
                        self.assertNotEqual(result["condition"], condition)

    def test_complete_sample_preserves_legacy_score_and_real_metrics(self):
        from src.agents.specialist_agents import TribologyAgent

        result = TribologyAgent().evaluate("BFP 1A", {
            "viscosity_40c": 44.2, "nominal_viscosity": 46,
            "tan": 0.12, "water_ppm": 45, "fe_ppm": 8, "cu_ppm": 2,
            "iso_cleanliness": "16/14/11",
        })
        self.assertEqual(result["condition"], "HEALTHY")
        self.assertEqual(result["health_score"], 95)
        self.assertEqual(result["confidence"], 0.94)
        self.assertEqual(result["metrics"]["viscosity_dev_pct"], 3.9)
        self.assertEqual(result["next_data_needed"], [])
        self.assertEqual(result["data_quality"]["status"], "valid")


if __name__ == "__main__":
    unittest.main()
