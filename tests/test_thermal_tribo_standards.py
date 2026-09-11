import unittest
from src.standards import evaluate_thermal, evaluate_tribology

class TestThermalTribologyStandards(unittest.TestCase):

    def test_evaluate_thermal_normal(self):
        params = {'Temperature': 60}
        res = evaluate_thermal(params)
        self.assertEqual(res['Overall'], 'Normal')

    def test_evaluate_thermal_alarm(self):
        params = {'Temperature': 90}
        res = evaluate_thermal(params)
        self.assertEqual(res['Overall'], 'Alarm')

    def test_evaluate_tribology_alarm_tan(self):
        params = {'TAN': 0.8}
        res = evaluate_tribology(params)
        self.assertEqual(res['Overall'], 'Alarm')

    def test_evaluate_tribology_high_water(self):
        params = {'Water_ppm': 1500}
        res = evaluate_tribology(params)
        self.assertEqual(res['Overall'], 'High')

if __name__ == '__main__':
    unittest.main()
