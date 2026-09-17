# EnvHarness & EnvRigger Implementation
import copy, json, math, os, random, time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.agents.specialist_agents import DGAAgent, MCSAAgent, ThermalAgent, TribologyAgent, VibrationAgent
from src.agents.safety_guard import SafetyGuardrailAgent
from src.agents.fusion_engine import ReliabilityFusionAgent

DEFAULT_HARNESS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'learning', 'env_harness'
)

class DiagnosticEnvironment:
    def __init__(self, equipment: str, base_telemetry: Dict[str, Any], expected_failure_mode: str, expected_min_severity: int = 1, max_steps: int = 10):
        self.equipment = equipment
        self.base_telemetry = copy.deepcopy(base_telemetry)
        self.expected_failure_mode = expected_failure_mode
        self.expected_min_severity = expected_min_severity
        self.max_steps = max_steps
        self.state: Dict[str, Any] = {}
        self.step_count = 0
        self.history: List[Dict[str, Any]] = []
        self.done = False
        self.diagnosis_result: Optional[Dict[str, Any]] = None
        self.safety_cleared = False
        self.work_order: Optional[Dict[str, Any]] = None
        self.reset()

    def reset(self) -> Dict[str, Any]:
        self.state = {
            'equipment': self.equipment,
            'telemetry': copy.deepcopy(self.base_telemetry),
            'queried_domains': set(),
            'safety_verified': False,
            'work_order_generated': False,
        }
        self.step_count = 0
        self.history = []
        self.done = False
        self.diagnosis_result = None
        self.safety_cleared = False
        self.work_order = None
        return self._get_observation()

    def _get_observation(self) -> Dict[str, Any]:
        return {
            'equipment': self.state['equipment'],
            'available_domains': list(self.state['telemetry'].keys()),
            'step': self.step_count,
            'max_steps': self.max_steps,
            'done': self.done,
            'safety_cleared': self.safety_cleared,
        }

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self.done:
            return self._get_observation(), 0.0, True, {'msg': 'Episode already finished'}
        self.step_count += 1
        action_type = action.get('type', '')
        reward = 0.0
        info: Dict[str, Any] = {'action': action_type}

        if action_type == 'query_domain':
            domain = action.get('domain', '').lower()
            if domain in self.state['telemetry']:
                self.state['queried_domains'].add(domain)
                info['telemetry_data'] = self.state['telemetry'][domain]
                info['status'] = 'SUCCESS'
                reward += 0.1
            else:
                info['status'] = 'DOMAIN_NOT_FOUND'
                info['telemetry_data'] = {}
        elif action_type == 'safety_check':
            plan = action.get('plan', '')
            guard = SafetyGuardrailAgent()
            check = guard.check_safety(plan)
            self.safety_cleared = check['safe']
            self.state['safety_verified'] = self.safety_cleared
            info['safety_result'] = check
            reward += 0.2 if self.safety_cleared else -0.5
        elif action_type == 'submit_diagnosis':
            fm = str(action.get('failure_mode', ''))
            sev = int(action.get('severity', 1))
            conf = float(action.get('confidence', 0.5))
            self.diagnosis_result = {'failure_mode': fm, 'severity': sev, 'confidence': conf}
            diag_score = self._evaluate_diagnosis(fm, sev, conf)
            reward += diag_score
            info['diagnostic_score'] = diag_score
            self.done = True
        elif action_type == 'create_work_order':
            if not self.diagnosis_result:
                info['status'] = 'ERROR_NO_PRIOR_DIAGNOSIS'
                reward -= 0.3
            else:
                self.work_order = {
                    'title': action.get('title', f'WO-{self.equipment}'),
                    'priority': action.get('priority', 'P3 - Medium'),
                    'tasks': action.get('tasks', []),
                }
                self.state['work_order_generated'] = True
                info['status'] = 'WORK_ORDER_CREATED'
                reward += 0.5
        else:
            info['status'] = 'UNKNOWN_ACTION'
            reward -= 0.1

        if self.step_count >= self.max_steps:
            self.done = True
            info['timeout'] = True
        self.history.append({'step': self.step_count, 'action': action, 'reward': reward, 'info': info})
        return self._get_observation(), reward, self.done, info

    def _evaluate_diagnosis(self, failure_mode: str, severity: int, confidence: float) -> float:
        score = 0.0
        if severity >= self.expected_min_severity:
            score += 0.5
        else:
            score += 0.1
        exp_keywords = [w.lower() for w in self.expected_failure_mode.replace('/', ' ').replace('-', ' ').split() if len(w) > 2]
        fm_lower = failure_mode.lower()
        matches = sum(1 for kw in exp_keywords if kw in fm_lower)
        if exp_keywords:
            precision = matches / len(exp_keywords)
            score += 0.5 * precision
        return score

class StageWrapper:
    def __init__(self, name: str, description: str, disturbance_payload: Dict[str, Any]):
        self.name = name
        self.description = description
        self.disturbance_payload = disturbance_payload
        self.component_type = 'STAGE'

    def wrap(self, env: DiagnosticEnvironment) -> DiagnosticEnvironment:
        wrapped_env = copy.deepcopy(env)
        orig_reset = wrapped_env.reset
        def stage_reset():
            obs = orig_reset()
            for domain, params in self.disturbance_payload.items():
                if domain not in wrapped_env.state['telemetry']:
                    wrapped_env.state['telemetry'][domain] = {}
                wrapped_env.state['telemetry'][domain].update(params)
            return obs
        wrapped_env.reset = stage_reset
        wrapped_env.reset()
        return wrapped_env

class ContractWrapper:
    def __init__(self, name: str, description: str, masked_domains: Optional[List[str]] = None, noise_std: float = 0.0, enforce_multi_modal: bool = False, enforce_safety_first: bool = False):
        self.name = name
        self.description = description
        self.masked_domains = masked_domains or []
        self.noise_std = noise_std
        self.enforce_multi_modal = enforce_multi_modal
        self.enforce_safety_first = enforce_safety_first
        self.component_type = 'CONTRACT'

    def wrap(self, env: DiagnosticEnvironment) -> DiagnosticEnvironment:
        wrapped_env = copy.deepcopy(env)
        orig_step = wrapped_env.step
        orig_get_obs = wrapped_env._get_observation

        def contract_get_obs():
            obs = orig_get_obs()
            if self.masked_domains:
                obs['available_domains'] = [d for d in obs['available_domains'] if d not in self.masked_domains]
                obs['masked_domains'] = self.masked_domains
            return obs

        def contract_step(action: Dict[str, Any]):
            action_type = action.get('type', '')
            if self.enforce_multi_modal and action_type == 'submit_diagnosis':
                queried = wrapped_env.state.get('queried_domains', set())
                if len(queried) < 2:
                    obs = wrapped_env._get_observation()
                    info = {'status': 'CONTRACT_VIOLATION_SINGLE_SENSOR', 'message': 'Kontrak mensyaratkan minimal 2 modalitas sensor independen.'}
                    return obs, -0.4, False, info
            if self.enforce_safety_first and action_type == 'create_work_order':
                if not wrapped_env.safety_cleared:
                    obs = wrapped_env._get_observation()
                    info = {'status': 'CONTRACT_VIOLATION_SAFETY_UNCLEARED', 'message': 'Kontrak mewajibkan verifikasi Safety Guardrail.'}
                    return obs, -0.5, False, info

            obs, reward, done, info = orig_step(action)
            if self.noise_std > 0 and 'telemetry_data' in info and isinstance(info['telemetry_data'], dict):
                noisy_data = {}
                for k, v in info['telemetry_data'].items():
                    if isinstance(v, (int, float)):
                        jitter = v * random.gauss(0, self.noise_std)
                        noisy_data[k] = round(v + jitter, 2)
                    else:
                        noisy_data[k] = v
                info['telemetry_data'] = noisy_data
                info['contract_noise_applied'] = True
            return obs, reward, done, info

        wrapped_env._get_observation = contract_get_obs
        wrapped_env.step = contract_step
        return wrapped_env

class ChainWrapper:
    def __init__(self, name: str, description: str, require_work_order: bool = True, require_safety: bool = True):
        self.name = name
        self.description = description
        self.require_work_order = require_work_order
        self.require_safety = require_safety
        self.component_type = 'CHAIN'

    def wrap(self, env: DiagnosticEnvironment) -> DiagnosticEnvironment:
        wrapped_env = copy.deepcopy(env)
        orig_step = wrapped_env.step

        def chain_step(action: Dict[str, Any]):
            action_type = action.get('type', '')
            if action_type == 'submit_diagnosis':
                obs, reward, _, info = orig_step(action)
                if self.require_work_order and not wrapped_env.state.get('work_order_generated'):
                    wrapped_env.done = False
                    info['chain_status'] = 'DIAGNOSIS_ACCEPTED_AWAITING_WORK_ORDER'
                    return obs, reward, False, info
                return obs, reward, True, info

            obs, reward, done, info = orig_step(action)
            if self.require_work_order and wrapped_env.state.get('work_order_generated'):
                if self.require_safety and not wrapped_env.safety_cleared:
                    info['chain_status'] = 'WORK_ORDER_CREATED_BUT_SAFETY_NOT_CLEARED'
                else:
                    info['chain_status'] = 'CHAIN_COMPLETED_SUCCESSFULLY'
                    reward += 1.0
                    wrapped_env.done = True
                    done = True
            return obs, reward, done, info

        wrapped_env.step = chain_step
        return wrapped_env

class CompositeEnvHarness:
    def __init__(self, harness_id: str = 'HARNESS-PLTU-CORE'):
        self.harness_id = harness_id
        self.wrappers: List[Union[StageWrapper, ContractWrapper, ChainWrapper]] = []

    def add_component(self, wrapper: Union[StageWrapper, ContractWrapper, ChainWrapper]) -> 'CompositeEnvHarness':
        self.wrappers.append(wrapper)
        return self

    def apply(self, base_env: DiagnosticEnvironment) -> DiagnosticEnvironment:
        current_env = base_env
        for wrapper in self.wrappers:
            current_env = wrapper.wrap(current_env)
        return current_env

    def list_components(self) -> List[Dict[str, Any]]:
        return [
            {'type': getattr(w, 'component_type', 'UNKNOWN'), 'name': w.name, 'description': w.description}
            for w in self.wrappers
        ]

class EnvRigger:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or DEFAULT_HARNESS_DIR
        os.makedirs(self.storage_dir, exist_ok=True)
        self.active_harness = CompositeEnvHarness()
        self._init_default_harness()

    def _init_default_harness(self):
        self.active_harness.add_component(
            StageWrapper(
                name='Stage-CrossCoupledDisturbance',
                description='Menyuntikkan gangguan kopling getaran 1X/2X dan deviasi sideband -42 dB.',
                disturbance_payload={
                    'vibration': {'overall_rms': 6.8, 'amp_1x': 5.4, 'amp_2x': 3.8},
                    'mcsa': {'upper_sb': -42.5, 'lower_sb': -44.0, 'dev_current': 4.2}
                }
            )
        )
        self.active_harness.add_component(
            ContractWrapper(
                name='Contract-MultiModalSafetyDiscipline',
                description='Menegakkan keharusan minimal 2 sensor terverifikasi dan Safety Guardrail clearance.',
                enforce_multi_modal=True,
                enforce_safety_first=True,
                noise_std=0.03
            )
        )
        self.active_harness.add_component(
            ChainWrapper(
                name='Chain-DiagnosticToWorkOrder',
                description='Mewajibkan alur diagnosa diteruskan hingga pembuatan Work Order terencana.',
                require_work_order=True,
                require_safety=True
            )
        )

    def run_rigger_cycle(
        self,
        equipment: str,
        base_telemetry: Dict[str, Any],
        expected_failure_mode: str,
        expected_min_severity: int = 3,
        policy_runner: Optional[Callable[[DiagnosticEnvironment], Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        base_env = DiagnosticEnvironment(
            equipment=equipment,
            base_telemetry=base_telemetry,
            expected_failure_mode=expected_failure_mode,
            expected_min_severity=expected_min_severity
        )
        if policy_runner is None:
            policy_runner = self._default_subagent_policy

        initial_rollout = policy_runner(base_env)
        success = initial_rollout.get('success', False)
        steps_taken = initial_rollout.get('steps', 0)
        trajectory = initial_rollout.get('trajectory', [])

        diagnosis = self._diagnose_trajectory(initial_rollout, expected_failure_mode)
        candidate_wrapper = self._synthesize_candidate(diagnosis)

        test_env = candidate_wrapper.wrap(base_env)
        val_rollout = policy_runner(test_env)
        val_success = val_rollout.get('success', False)

        accepted = False
        decision_reason = ''
        if val_success:
            accepted = True
            decision_reason = 'Kandidat wrapper melatih kelemahan spesifik dan episode berhasil diselesaikan secara valid.'
            self.active_harness.add_component(candidate_wrapper)
        else:
            decision_reason = 'Kandidat terlalu ketat / unsolvable oleh policy; ditolak atau memerlukan tuning lebih lanjut.'

        cycle_result = {
            'timestamp': datetime.now().isoformat(),
            'equipment': equipment,
            'stage_1_observe': {
                'base_success': success,
                'steps': steps_taken,
                'actions_count': len(trajectory)
            },
            'stage_2_diagnose': diagnosis,
            'stage_3_write': {
                'wrapper_type': getattr(candidate_wrapper, 'component_type', 'STAGE'),
                'name': candidate_wrapper.name,
                'description': candidate_wrapper.description,
            },
            'stage_4_validate': {
                'validation_success': val_success,
                'accepted': accepted,
                'decision_reason': decision_reason,
            },
            'active_harness_components_count': len(self.active_harness.wrappers)
        }
        self._persist_cycle(cycle_result)
        return cycle_result

    def _default_subagent_policy(self, env: DiagnosticEnvironment) -> Dict[str, Any]:
        obs = env.reset()
        trajectory = []
        for domain in ['vibration', 'mcsa', 'dga', 'oil', 'thermal']:
            if domain in obs.get('available_domains', []):
                _, r, _, info = env.step({'type': 'query_domain', 'domain': domain})
                trajectory.append({'action': 'query_domain', 'domain': domain, 'info': info})

        _, r, _, info = env.step({
            'type': 'safety_check',
            'plan': f'Lakukan investigasi terencana pada {env.equipment} sesuai SOP isolasi energi'
        })
        trajectory.append({'action': 'safety_check', 'info': info})

        tel = env.state.get('telemetry', {})
        f_mode = 'Normal Operation'
        sev = 1
        if 'vibration' in tel and tel['vibration'].get('overall_rms', 0) > 4.5:
            f_mode = 'Severe Unbalance / Misalignment'
            sev = 4
        elif 'mcsa' in tel and tel['mcsa'].get('upper_sb', -99) > -45:
            f_mode = 'Rotor Bar Degradation'
            sev = 3
        elif 'dga' in tel and tel['dga'].get('c2h4', 0) > 100:
            f_mode = 'Thermal Fault >700°C'
            sev = 3
        elif 'oil' in tel and tel['oil'].get('water_ppm', 0) > 200:
            f_mode = 'Lubricant Contamination & Severe Wear'
            sev = 3

        _, r, done, info = env.step({
            'type': 'submit_diagnosis',
            'failure_mode': f_mode,
            'severity': sev,
            'confidence': 0.92
        })
        trajectory.append({'action': 'submit_diagnosis', 'info': info})

        if not done:
            _, r, done, info = env.step({
                'type': 'create_work_order',
                'title': f'WO-{env.equipment}-Corrective Maintenance',
                'priority': 'P2 - High',
                'tasks': ['Inspeksi Alignment', 'Greasing Ulang', 'Pengujian MCSA Ulang']
            })
            trajectory.append({'action': 'create_work_order', 'info': info})

        success = env.diagnosis_result is not None and env.diagnosis_result['severity'] >= env.expected_min_severity
        return {
            'success': success,
            'steps': env.step_count,
            'trajectory': trajectory,
            'diagnosis': env.diagnosis_result,
            'work_order': env.work_order,
            'safety_cleared': env.safety_cleared
        }

    def _diagnose_trajectory(self, rollout: Dict[str, Any], expected_fm: str) -> Dict[str, Any]:
        steps = rollout.get('steps', 0)
        success = rollout.get('success', False)
        if not success:
            return {
                'issue': 'DIAGNOSTIC_SEVERITY_UNDERESTIMATION',
                'recommendation': 'Suntikkan Stage disturbance dengan kontras telemetri lebih tinggi.',
                'target_wrapper': 'STAGE'
            }
        elif steps <= 3:
            return {
                'issue': 'SHORTCUT_RELIANCE',
                'recommendation': 'Agent mengambil jalan pintas tanpa verifikasi modalitas lain. Terapkan Contract.',
                'target_wrapper': 'CONTRACT'
            }
        else:
            return {
                'issue': 'TASK_HORIZON_TOO_SHORT',
                'recommendation': 'Agent menguasai diagnosa dasar. Terapkan Chain ke mitigasi & WO.',
                'target_wrapper': 'CHAIN'
            }

    def _synthesize_candidate(self, diagnosis: Dict[str, Any]) -> Union[StageWrapper, ContractWrapper, ChainWrapper]:
        target = diagnosis.get('target_wrapper', 'STAGE')
        tag = int(time.time()) % 1000
        if target == 'CONTRACT':
            return ContractWrapper(
                name=f'Contract-DynamicJitter-{tag}',
                description='Menyuntikkan jitter sensor 4% dan masking observasi parsial.',
                noise_std=0.04,
                enforce_multi_modal=True
            )
        elif target == 'CHAIN':
            return ChainWrapper(
                name=f'Chain-ExtendedLifecycle-{tag}',
                description='Perpanjangan alur investigasi akar masalah ke penerbitan Work Order terverifikasi.',
                require_work_order=True,
                require_safety=True
            )
        else:
            return StageWrapper(
                name=f'Stage-InjectedThermalHotspot-{tag}',
                description='Injeksi hotspot termal dan kenaikan getaran komposit.',
                disturbance_payload={
                    'thermal': {'delta_t_phase': 16.5, 'bearing_temp': 74.0},
                    'vibration': {'overall_rms': 5.2}
                }
            )

    def _persist_cycle(self, record: Dict[str, Any]):
        path = os.path.join(self.storage_dir, 'rigger_history.json')
        history = []
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                history = []
        history.append(record)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[EnvRigger] Gagal menyimpan riwayat: {e}')

    def get_status(self) -> Dict[str, Any]:
        history_path = os.path.join(self.storage_dir, 'rigger_history.json')
        history = []
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception:
                pass
        return {
            'status': 'ACTIVE',
            'framework': 'EnvHarness (Google Cloud AI Research 2026)',
            'total_harness_components': len(self.active_harness.wrappers),
            'components': self.active_harness.list_components(),
            'total_rigger_cycles': len(history),
            'recent_cycles': history[-5:] if history else []
        }
