import os
import tempfile
import unittest
from src.agents.env_harness import (
    DiagnosticEnvironment,
    StageWrapper,
    ContractWrapper,
    ChainWrapper,
    CompositeEnvHarness,
    EnvRigger
)

class TestEnvHarnessAndRigger(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.base_telemetry = {
            'vibration': {'overall_rms': 2.1, 'amp_1x': 1.2},
            'mcsa': {'upper_sb': -58.0, 'lower_sb': -60.0},
            'oil': {'water_ppm': 45.0, 'viscosity_40c': 46.0}
        }
        self.env = DiagnosticEnvironment(
            equipment='BFP 1A',
            base_telemetry=self.base_telemetry,
            expected_failure_mode='Rotor Bar Degradation / Unbalance',
            expected_min_severity=3
        )

    def tearDown(self):
        for fn in os.listdir(self.tmpdir):
            try:
                os.remove(os.path.join(self.tmpdir, fn))
            except Exception:
                pass
        try:
            os.rmdir(self.tmpdir)
        except Exception:
            pass

    def test_base_diagnostic_environment(self):
        obs = self.env.reset()
        self.assertEqual(obs['equipment'], 'BFP 1A')
        self.assertIn('vibration', obs['available_domains'])
        
        obs, reward, done, info = self.env.step({'type': 'query_domain', 'domain': 'vibration'})
        self.assertEqual(info['status'], 'SUCCESS')
        self.assertIn('overall_rms', info['telemetry_data'])
        self.assertFalse(done)

        obs, reward, done, info = self.env.step({
            'type': 'submit_diagnosis',
            'failure_mode': 'Rotor Bar Degradation',
            'severity': 3,
            'confidence': 0.9
        })
        self.assertTrue(done)
        self.assertGreater(reward, 0.5)

    def test_stage_wrapper_mutates_initial_state(self):
        stage = StageWrapper(
            name='Stage-HighVibDisturbance',
            description='Injects severe vibration unbalance',
            disturbance_payload={'vibration': {'overall_rms': 8.5, 'amp_1x': 7.1}}
        )
        wrapped_env = stage.wrap(self.env)
        obs = wrapped_env.reset()
        self.assertEqual(wrapped_env.state['telemetry']['vibration']['overall_rms'], 8.5)
        self.assertEqual(wrapped_env.state['telemetry']['vibration']['amp_1x'], 7.1)

    def test_contract_wrapper_enforces_rules(self):
        contract = ContractWrapper(
            name='Contract-StrictDiscipline',
            description='Requires multi-modal verification and masks oil',
            masked_domains=['oil'],
            enforce_multi_modal=True,
            enforce_safety_first=True,
            noise_std=0.05
        )
        wrapped_env = contract.wrap(self.env)
        obs = wrapped_env.reset()
        
        self.assertNotIn('oil', obs['available_domains'])
        self.assertIn('masked_domains', obs)

        obs, reward, done, info = wrapped_env.step({'type': 'query_domain', 'domain': 'vibration'})
        obs, reward, done, info = wrapped_env.step({
            'type': 'submit_diagnosis',
            'failure_mode': 'Rotor Bar',
            'severity': 3
        })
        self.assertEqual(info.get('status'), 'CONTRACT_VIOLATION_SINGLE_SENSOR')
        self.assertFalse(done)

    def test_chain_wrapper_extends_lifecycle(self):
        chain = ChainWrapper(
            name='Chain-DiagnosisToWorkOrder',
            description='Extends diagnosis to Work Order generation',
            require_work_order=True,
            require_safety=True
        )
        wrapped_env = chain.wrap(self.env)
        wrapped_env.reset()

        obs, reward, done, info = wrapped_env.step({
            'type': 'submit_diagnosis',
            'failure_mode': 'Rotor Bar Degradation',
            'severity': 3
        })
        self.assertFalse(done)
        self.assertEqual(info.get('chain_status'), 'DIAGNOSIS_ACCEPTED_AWAITING_WORK_ORDER')

        wrapped_env.step({'type': 'safety_check', 'plan': 'Investigasi terencana sesuai SOP'})
        
        obs, reward, done, info = wrapped_env.step({
            'type': 'create_work_order',
            'title': 'WO-BFP-1A-RotorInspection',
            'priority': 'P2 - High',
            'tasks': ['Visual Inspection']
        })
        self.assertTrue(done)
        self.assertEqual(info.get('chain_status'), 'CHAIN_COMPLETED_SUCCESSFULLY')

    def test_composite_env_harness_stacking(self):
        harness = CompositeEnvHarness('TEST-HARNESS')
        harness.add_component(StageWrapper('S1', 'Desc1', {'vibration': {'overall_rms': 6.0}}))
        harness.add_component(ContractWrapper('C1', 'Desc2', enforce_multi_modal=True))
        harness.add_component(ChainWrapper('CH1', 'Desc3', require_work_order=True))

        self.assertEqual(len(harness.list_components()), 3)
        wrapped = harness.apply(self.env)
        obs = wrapped.reset()
        self.assertEqual(wrapped.state['telemetry']['vibration']['overall_rms'], 6.0)

    def test_env_rigger_4_stage_cycle(self):
        rigger = EnvRigger(storage_dir=self.tmpdir)
        status_before = rigger.get_status()
        self.assertEqual(status_before['status'], 'ACTIVE')

        res = rigger.run_rigger_cycle(
            equipment='IDF 1A',
            base_telemetry={
                'vibration': {'overall_rms': 7.2, 'amp_1x': 6.0},
                'mcsa': {'upper_sb': -42.0}
            },
            expected_failure_mode='Severe Unbalance / Misalignment',
            expected_min_severity=3
        )

        self.assertIn('stage_1_observe', res)
        self.assertIn('stage_2_diagnose', res)
        self.assertIn('stage_3_write', res)
        self.assertIn('stage_4_validate', res)
        self.assertTrue(res['stage_4_validate']['accepted'])

        status_after = rigger.get_status()
        self.assertGreater(status_after['total_rigger_cycles'], 0)
        self.assertGreaterEqual(status_after['total_harness_components'], 3)

if __name__ == '__main__':
    unittest.main()
