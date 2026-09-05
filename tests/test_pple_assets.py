"""Tests for pple/assets/ (docs/final.md Phase 3 - Asset Engine MVP slice).

AssetRegistry is a read-through view over the real src.dga_data /
src.vibration_data sources (see pple/assets/registry.py's module docstring
for why), so these tests exercise it against the real fixture data rather
than mocking those modules out - consistent with how
tests/test_dga_data.py and tests/test_vibration_data.py already test
against the real fixtures.
"""

import unittest

from pple.assets import AssetRegistry, Equipment, Plant, Unit


class AssetRegistryTests(unittest.TestCase):
    def setUp(self):
        self.registry = AssetRegistry()

    def test_available_domains(self):
        self.assertEqual(AssetRegistry.available_domains(), ["dga", "vibration"])

    def test_plant_has_expected_units(self):
        plant = self.registry.plant()
        self.assertIsInstance(plant, Plant)
        self.assertEqual(plant.id, "PLTU-JERANJANG")
        unit_names = {u.name for u in plant.units}
        self.assertEqual(unit_names, {"UNIT 1", "UNIT 2", "UNIT 3", "COMMON"})

    def test_units_aggregate_both_domains(self):
        plant = self.registry.plant()
        for unit in plant.units:
            self.assertIsInstance(unit, Unit)
            domains = {e.domain for e in unit.equipment}
            self.assertTrue(domains, f"{unit.name} has no equipment at all")
            self.assertTrue(domains.issubset({"dga", "vibration"}))

    def test_plant_domain_filter_restricts_equipment(self):
        plant = self.registry.plant(domain="dga")
        all_domains = {e.domain for u in plant.units for e in u.equipment}
        self.assertEqual(all_domains, {"dga"})

    def test_list_equipment_unit_filter(self):
        equipment = self.registry.list_equipment(unit="UNIT 1")
        self.assertGreater(len(equipment), 0)
        for eq in equipment:
            self.assertIsInstance(eq, Equipment)
            self.assertEqual(eq.unit, "UNIT 1")

    def test_list_equipment_domain_filter(self):
        equipment = self.registry.list_equipment(domain="vibration")
        self.assertGreater(len(equipment), 0)
        for eq in equipment:
            self.assertEqual(eq.domain, "vibration")

    def test_get_equipment_roundtrip(self):
        sample = self.registry.list_equipment(domain="dga")[0]
        fetched = self.registry.get_equipment(sample.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, sample.id)
        self.assertEqual(fetched.name, sample.name)

    def test_get_equipment_unknown_id_returns_none(self):
        self.assertIsNone(self.registry.get_equipment("DOES-NOT-EXIST"))

    def test_equipment_to_dict_shape(self):
        eq = self.registry.list_equipment()[0]
        d = eq.to_dict()
        for key in ("id", "name", "unit", "domain", "equipment_class", "status", "metadata"):
            self.assertIn(key, d)

    def test_plant_to_dict_shape(self):
        d = self.registry.plant().to_dict()
        self.assertIn("units", d)
        self.assertIn("unit_count", d)
        self.assertEqual(d["unit_count"], len(d["units"]))
        first_unit = d["units"][0]
        self.assertIn("equipment", first_unit)
        self.assertIn("equipment_count", first_unit)


if __name__ == "__main__":
    unittest.main()
