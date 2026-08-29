import unittest

from src.vibration_data import (
    load_vibration_assets,
    load_vibration_report_records,
    get_vibration_asset,
    search_vibration_assets,
    get_vibration_summary,
    get_equipment_class_list,
    get_asset_ids_for_unit,
    get_bearing_info,
    match_monthly_test_by_equipment,
    build_vibration_agent_input,
    update_vibration_asset,
)


class VibrationDataTests(unittest.TestCase):
    """Tests for the vibration asset database loader."""

    def test_load_assets_returns_dataframe_with_rows(self):
        df = load_vibration_assets()
        self.assertGreater(len(df), 0)
        self.assertIn('asset_id', df.columns)
        self.assertIn('equipment', df.columns)
        self.assertIn('unit_group', df.columns)

    def test_load_report_records_returns_dataframe(self):
        df = load_vibration_report_records()
        self.assertGreater(len(df), 0)
        self.assertIn('record_id', df.columns)

    def test_get_asset_returns_dict_for_existing_id(self):
        asset = get_vibration_asset('AST-001')
        self.assertIsNotNone(asset)
        self.assertEqual(asset['asset_id'], 'AST-001')
        self.assertIn('equipment', asset)
        self.assertIn('kks', asset)

    def test_get_asset_returns_none_for_missing_id(self):
        asset = get_vibration_asset('AST-999')
        self.assertIsNone(asset)

    def test_summary_has_expected_keys(self):
        summary = get_vibration_summary()
        self.assertIn('total_assets', summary)
        self.assertIn('by_unit', summary)
        self.assertIn('by_status', summary)
        self.assertIn('by_category', summary)
        self.assertGreater(summary['total_assets'], 0)

    def test_summary_unit_groups(self):
        summary = get_vibration_summary()
        units = summary['by_unit']
        self.assertIn('UNIT 1', units)
        self.assertIn('UNIT 3', units)
        self.assertIn('COMMON', units)

    def test_equipment_class_list_non_empty(self):
        classes = get_equipment_class_list()
        self.assertGreater(len(classes), 0)
        # Should contain at least one ISO standard reference
        self.assertTrue(any('10816' in c for c in classes))

    def test_asset_ids_for_unit(self):
        ids = get_asset_ids_for_unit('UNIT 1')
        self.assertGreater(len(ids), 0)
        self.assertTrue(all(i.startswith('AST-') for i in ids))

    def test_search_by_status(self):
        results = search_vibration_assets(status='NORMAL')
        self.assertGreater(len(results), 0)
        self.assertTrue(all(r['status_vibrasi'] == 'NORMAL' for r in results))

    def test_search_by_unit(self):
        results = search_vibration_assets(unit_group='COMMON')
        self.assertGreater(len(results), 0)
        self.assertTrue(all(r['unit_group'] == 'COMMON' for r in results))

    def test_search_by_keyword(self):
        results = search_vibration_assets(keyword='Fan')
        self.assertGreater(len(results), 0)
        self.assertTrue(all('Fan' in r['equipment'] or 'fan' in r['equipment'].lower() for r in results))

    def test_search_no_results(self):
        results = search_vibration_assets(keyword='XYZNONEXISTENT')
        self.assertEqual(len(results), 0)

    def test_bearing_info_returns_dict(self):
        info = get_bearing_info('AST-003')
        self.assertIsNotNone(info)
        self.assertIn('c1_bearing_type', info)
        self.assertIn('c1_inboard_bearing', info)

    def test_bearing_info_missing_asset(self):
        info = get_bearing_info('AST-999')
        self.assertIsNone(info)


class MatchMonthlyTestByEquipmentTests(unittest.TestCase):
    def setUp(self):
        self.monthly_tests = [
            {"equipment": "Motor ID Fan 1#1", "velocity_max": 1.39},
            {"equipment": "Motor Primary Air Fan 1#1", "velocity_max": 2.9},
        ]

    def test_exact_match(self):
        result = match_monthly_test_by_equipment("Motor ID Fan 1#1", self.monthly_tests)
        self.assertIsNotNone(result)
        self.assertEqual(result["velocity_max"], 1.39)

    def test_case_insensitive_match(self):
        result = match_monthly_test_by_equipment("motor id fan 1#1", self.monthly_tests)
        self.assertIsNotNone(result)
        self.assertEqual(result["velocity_max"], 1.39)

    def test_no_match_returns_none(self):
        result = match_monthly_test_by_equipment("Nonexistent Equipment XYZ", self.monthly_tests)
        self.assertIsNone(result)

    def test_empty_inputs_return_none(self):
        self.assertIsNone(match_monthly_test_by_equipment("", self.monthly_tests))
        self.assertIsNone(match_monthly_test_by_equipment("Motor ID Fan 1#1", []))


class BuildVibrationAgentInputTests(unittest.TestCase):
    def test_maps_velocity_max_to_overall_rms_only(self):
        record = {"equipment": "Motor ID Fan 1#1", "velocity_max": 5.2, "points": {"1V": 0.63}}
        result = build_vibration_agent_input(record)
        self.assertEqual(result, {"overall_rms": 5.2})

    def test_missing_velocity_max_defaults_to_zero(self):
        result = build_vibration_agent_input({})
        self.assertEqual(result, {"overall_rms": 0.0})


class UpdateVibrationAssetTests(unittest.TestCase):
    """Round-trips a real asset's status so the checked-in DB ends up unchanged."""

    def setUp(self):
        self.asset_id = 'AST-001'
        original = get_vibration_asset(self.asset_id)
        self.assertIsNotNone(original, 'fixture asset AST-001 must exist for this test')
        self.original_status = original['status_vibrasi']

    def tearDown(self):
        update_vibration_asset(self.asset_id, {'status_vibrasi': self.original_status})

    def test_update_changes_status_and_persists(self):
        new_status = 'ALARM' if self.original_status != 'ALARM' else 'NORMAL'
        updated = update_vibration_asset(self.asset_id, {'status_vibrasi': new_status})
        self.assertTrue(updated)
        self.assertEqual(get_vibration_asset(self.asset_id)['status_vibrasi'], new_status)

    def test_update_missing_asset_returns_false(self):
        updated = update_vibration_asset('AST-999-DOES-NOT-EXIST', {'status_vibrasi': 'ALARM'})
        self.assertFalse(updated)

    def test_update_ignores_non_editable_fields(self):
        updated = update_vibration_asset(self.asset_id, {'asset_id': 'AST-HACKED'})
        self.assertFalse(updated)
        self.assertEqual(get_vibration_asset(self.asset_id)['asset_id'], self.asset_id)

    def test_update_only_touches_targeted_asset(self):
        other = get_vibration_asset('AST-002')
        if other is None:
            self.skipTest('AST-002 fixture not present')
        other_status_before = other['status_vibrasi']
        new_status = 'ALARM' if self.original_status != 'ALARM' else 'NORMAL'
        update_vibration_asset(self.asset_id, {'status_vibrasi': new_status})
        self.assertEqual(get_vibration_asset('AST-002')['status_vibrasi'], other_status_before)


if __name__ == '__main__':
    unittest.main()
