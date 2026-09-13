"""Unit tests for Real-Time Physics-Based Telemetry & Oscillogram Streamer."""

import unittest
from fastapi.testclient import TestClient

from api_server import app
from src.telemetry_streamer import (
    FAULT_PROFILES,
    generate_live_frame,
    generate_mcsa_telemetry,
    generate_vibration_telemetry,
)


class TestTelemetryStreamer(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_generate_vibration_telemetry_normal(self):
        frame = generate_vibration_telemetry("CWP 1A", fault_profile="NORMAL_BASELINE")
        self.assertEqual(frame["equipment"], "CWP 1A")
        self.assertEqual(frame["domain"], "VIBRASI")
        self.assertEqual(frame["status"], "Normal")
        self.assertIn("waveform", frame)
        self.assertIn("spectrum", frame)
        self.assertEqual(len(frame["waveform"]["time_ms"]), 256)
        self.assertGreater(len(frame["spectrum"]["frequency_hz"]), 10)
        self.assertLess(frame["metrics"]["rms_velocity_mm_s"], 2.8)

    def test_generate_vibration_telemetry_faults(self):
        # 1X Unbalance
        unbalance = generate_vibration_telemetry("PA FAN 1A", fault_profile="UNBALANCE_1X")
        self.assertIn("Unbalance", unbalance["primary_fault"])
        self.assertIn(unbalance["status"], ["Alarm", "High"])

        # BPFO Bearing
        bpfo = generate_vibration_telemetry("BFP 1A", fault_profile="BEARING_BPFO")
        self.assertIn("BPFO", bpfo["primary_fault"])
        self.assertIn(bpfo["status"], ["Alarm", "High"])


    def test_generate_mcsa_telemetry(self):
        # Normal
        norm = generate_mcsa_telemetry("CWP 1A", fault_profile="NORMAL_BASELINE")
        self.assertEqual(norm["domain"], "MCSA")
        self.assertEqual(norm["status"], "Normal")
        self.assertIn("waveforms", norm)
        self.assertIn("current_phase_a", norm["waveforms"])
        self.assertIn("current_phase_b", norm["waveforms"])
        self.assertIn("current_phase_c", norm["waveforms"])

        # Broken rotor bar
        brb = generate_mcsa_telemetry("CWP 1A", fault_profile="BROKEN_ROTOR_BAR")
        self.assertEqual(brb["status"], "Alarm")
        self.assertIn("Broken Rotor Bar", brb["primary_fault"])
        self.assertGreater(brb["metrics"]["sideband_db_down"], -40.0)

    def test_generate_live_frame_router(self):
        f_vib = generate_live_frame("CRUSHER 1", domain="VIBRASI")
        self.assertEqual(f_vib["domain"], "VIBRASI")

        f_mcsa = generate_live_frame("CRUSHER 1", domain="MCSA")
        self.assertEqual(f_mcsa["domain"], "MCSA")

    def test_api_endpoint_oscillogram(self):
        resp = self.client.get("/api/v2/domain/telemetry/oscillogram/CWP%201A?domain=VIBRASI&fault_profile=UNBALANCE_1X")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["equipment"], "CWP 1A")
        self.assertEqual(data["domain"], "VIBRASI")
        self.assertIn("waveform", data)
        self.assertIn("spectrum", data)


if __name__ == "__main__":
    unittest.main()
