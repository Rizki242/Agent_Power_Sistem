import unittest
from datetime import date

from src.time_filters import clamp_period, month_period, preset_period


class TimeFilterTests(unittest.TestCase):
    def test_preset_semua_uses_available_data_bounds(self):
        start, end = preset_period("Semua", date(2024, 1, 10), date(2026, 5, 25))

        self.assertEqual(start, date(2024, 1, 10))
        self.assertEqual(end, date(2026, 5, 25))

    def test_preset_kondisi_saat_ini_uses_latest_data_month(self):
        start, end = preset_period("Kondisi saat Ini", date(2024, 1, 10), date(2026, 5, 25))

        self.assertEqual(start, date(2026, 5, 1))
        self.assertEqual(end, date(2026, 5, 25))

    def test_preset_pengujian_terakhir_returns_previous_calendar_month(self):
        start, end = preset_period("Pengujian Terakhir", date(2024, 1, 10), date(2026, 5, 25))

        self.assertEqual(start, date(2026, 4, 1))
        self.assertEqual(end, date(2026, 4, 30))

    def test_preset_rolling_months_is_clamped_to_min_date(self):
        start, end = preset_period("12 Bulan", date(2026, 1, 5), date(2026, 5, 25))

        self.assertEqual(start, date(2026, 1, 5))
        self.assertEqual(end, date(2026, 5, 25))

    def test_month_period_snaps_to_whole_months_and_sorts_reversed_input(self):
        start, end = month_period(date(2026, 5, 25), date(2026, 3, 11))

        self.assertEqual(start, date(2026, 3, 1))
        self.assertEqual(end, date(2026, 5, 31))

    def test_clamp_period_sorts_and_limits_to_available_data(self):
        start, end = clamp_period(
            date(2026, 8, 1),
            date(2023, 1, 1),
            date(2024, 1, 10),
            date(2026, 5, 25),
        )

        self.assertEqual(start, date(2024, 1, 10))
        self.assertEqual(end, date(2026, 5, 25))


if __name__ == "__main__":
    unittest.main()
