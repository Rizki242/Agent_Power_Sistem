import unittest
import pandas as pd
from src.standards import evaluate_vibration, evaluate_dga

class TestMultiDomainStandards(unittest.TestCase):

    def test_evaluate_vibration_normal(self):
        params = {'Velocity_RMS': 2.0}
        res = evaluate_vibration(params)
        self.assertEqual(res['Overall'], 'Normal')

    def test_evaluate_vibration_alarm(self):
        params = {'Velocity_RMS': 5.0}
        res = evaluate_vibration(params)
        self.assertEqual(res['Overall'], 'Alarm')

    def test_evaluate_vibration_high(self):
        params = {'Velocity_RMS': 10.0}
        res = evaluate_vibration(params)
        self.assertEqual(res['Overall'], 'High')

    def test_evaluate_dga_normal(self):
        params = {'H2': 100, 'CH4': 100} # TDCG = 200
        res = evaluate_dga(params)
        self.assertEqual(res['Overall'], 'Normal')

    def test_evaluate_dga_alarm_by_tdcg(self):
        params = {'H2': 500, 'CH4': 300} # TDCG = 800
        res = evaluate_dga(params)
        self.assertEqual(res['Overall'], 'Alarm')

    def test_evaluate_dga_high_by_c2h2(self):
        params = {'C2H2': 50} # Very critical
        res = evaluate_dga(params)
        self.assertEqual(res['Overall'], 'High')

if __name__ == '__main__':
    unittest.main()
