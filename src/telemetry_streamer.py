"""Real-Time Physics-Based Telemetry & Oscillogram/Spectrum Engine.

Generates and buffers live high-fidelity time waveforms and frequency spectra for:
- Vibration: Time Waveform (TWF) and FFT Spectrum with ISO 10816-3 thresholds
- MCSA: 3-Phase Current Waveforms (Ia, Ib, Ic) & Sideband FFT Spectrum (dB)
- Thermal & Multi-Domain Sensor Telemetry
- Real-time fault injection simulation (Unbalance, Misalignment, Bearing BPFO, Broken Rotor Bar, Thermal Spike)
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np


FAULT_PROFILES = {
    "NORMAL_BASELINE": "Kondisi Normal / Baseline",
    "UNBALANCE_1X": "Ketidakseimbangan Massa / Unbalance 1X",
    "MISALIGNMENT_2X": "Ketidaklurusan Poros / Misalignment 2X",
    "BEARING_BPFO": "Cacat Bantalan / Outer Race Bearing Fault (BPFO)",
    "BROKEN_ROTOR_BAR": "Batang Rotor Retak / Broken Rotor Bar (MCSA)",
    "THERMAL_OVERHEAT": "Lonjakan Panas Berlebih / Thermal Spike",
}


def generate_vibration_telemetry(
    equipment: str,
    fault_profile: str = "NORMAL_BASELINE",
    rpm: float = 1485.0,
    sample_count: int = 256,
) -> Dict[str, Any]:
    """Generates continuous physics-based vibration time waveform and FFT frequency spectrum."""
    f1 = rpm / 60.0  # ~24.75 Hz (1X running speed)
    f2 = 2.0 * f1    # ~49.5 Hz (2X)
    f_bpfo = 3.56 * f1  # ~88.1 Hz (BPFO outer race)

    # Determine amplitude components based on fault profile
    if fault_profile == "UNBALANCE_1X":
        a1 = 5.8
        a2 = 0.8
        a_bpfo = 0.2
        noise_amp = 0.25
        status = "Alarm"
        primary_fault = "1X Unbalance"
    elif fault_profile == "MISALIGNMENT_2X":
        a1 = 3.2
        a2 = 6.4
        a_bpfo = 0.3
        noise_amp = 0.3
        status = "Alarm"
        primary_fault = "2X Misalignment"
    elif fault_profile == "BEARING_BPFO":
        a1 = 2.2
        a2 = 1.1
        a_bpfo = 5.6
        noise_amp = 0.5
        status = "High"
        primary_fault = "BPFO Outer Race Defect"
    else:  # NORMAL_BASELINE
        a1 = 1.4
        a2 = 0.4
        a_bpfo = 0.15
        noise_amp = 0.15
        status = "Normal"
        primary_fault = "Normal Baseline"

    # Time array: 0 to 0.25 seconds (~6 full 1X cycles)
    t = np.linspace(0, 0.25, sample_count)
    dt = t[1] - t[0]
    sampling_rate = 1.0 / dt

    # Time waveform signal x(t) in mm/s
    pure_signal = (
        a1 * np.sin(2.0 * np.pi * f1 * t)
        + a2 * np.sin(2.0 * np.pi * f2 * t + 0.5)
        + a_bpfo * np.sin(2.0 * np.pi * f_bpfo * t + 1.2)
    )

    # Add pseudo-random noise & transient impacts if bearing fault
    noise = np.random.normal(0, noise_amp, sample_count)
    if fault_profile == "BEARING_BPFO":
        # Add sharp periodic impulses
        impact_indices = np.arange(0, sample_count, int(sampling_rate / f_bpfo))
        impact_indices = impact_indices[impact_indices < sample_count]
        noise[impact_indices] += 4.5

    waveform = pure_signal + noise

    # Metrics
    rms_val = round(float(np.sqrt(np.mean(waveform ** 2))), 2)
    pk_val = round(float(np.max(np.abs(waveform))), 2)
    pk_pk = round(float(np.max(waveform) - np.min(waveform)), 2)
    crest_factor = round(pk_val / max(0.01, rms_val), 2)

    # ISO 10816-3 evaluation (Group 1/2)
    if rms_val < 2.8:
        iso_zone = "Zone A / B (Good / Acceptable)"
        status = "Normal"
    elif rms_val < 4.5:
        iso_zone = "Zone C (Warning)"
        status = "Alarm"
    elif rms_val < 7.1:
        iso_zone = "Zone C/D (Alarm)"
        status = "Alarm"
    else:
        iso_zone = "Zone D (Unacceptable / High Trip)"
        status = "High"

    # FFT Computation
    fft_vals = np.abs(np.fft.rfft(waveform)) * (2.0 / sample_count)
    freqs = np.fft.rfftfreq(sample_count, d=dt)

    # Filter frequencies up to 300 Hz for clear visualization
    mask = freqs <= 300.0
    freq_points = [round(float(f), 1) for f in freqs[mask]]
    amp_points = [round(float(a), 2) for a in fft_vals[mask]]

    return {
        "equipment": equipment,
        "domain": "VIBRASI",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fault_profile": fault_profile,
        "primary_fault": primary_fault,
        "status": status,
        "iso_zone": iso_zone,
        "metrics": {
            "rms_velocity_mm_s": rms_val,
            "peak_velocity_mm_s": pk_val,
            "peak_to_peak_mm_s": pk_pk,
            "crest_factor": crest_factor,
            "rpm": rpm,
            "running_frequency_1x_hz": round(f1, 1),
        },
        "waveform": {
            "time_ms": [round(float(val * 1000.0), 1) for val in t],
            "amplitude_mm_s": [round(float(val), 2) for val in waveform],
        },
        "spectrum": {
            "frequency_hz": freq_points,
            "amplitude_mm_s": amp_points,
            "threshold_warning_mm_s": 2.8,
            "threshold_alarm_mm_s": 4.5,
            "threshold_trip_mm_s": 7.1,
        },
    }


def generate_mcsa_telemetry(
    equipment: str,
    fault_profile: str = "NORMAL_BASELINE",
    nominal_current: float = 85.0,
    sample_count: int = 256,
) -> Dict[str, Any]:
    """Generates 3-phase instantaneous current waveforms and MCSA sideband FFT spectrum."""
    f_line = 50.0  # 50 Hz grid line frequency
    slip = 0.025    # ~2.5% slip for induction motor
    f_sideband = f_line * 2.0 * slip  # ~2.5 Hz pole pass sideband

    # Current amplitudes
    if fault_profile == "BROKEN_ROTOR_BAR":
        # Broken rotor bar causes sidebands at f_L +- 2sf to rise to -36 dB
        # and phase unbalance
        sideband_db = -36.5
        unbalance_pct = 7.2
        status = "Alarm"
        primary_fault = "Broken Rotor Bar Indication"
        mod_depth = 0.12
    elif fault_profile == "UNBALANCE_1X":
        sideband_db = -52.0
        unbalance_pct = 5.8
        status = "Alarm"
        primary_fault = "Stator Phase Current Unbalance"
        mod_depth = 0.04
    else:  # NORMAL_BASELINE
        sideband_db = -56.0
        unbalance_pct = 1.4
        status = "Normal"
        primary_fault = "Normal Motor Condition"
        mod_depth = 0.01

    t = np.linspace(0, 0.08, sample_count)  # 4 electrical cycles (80 ms)

    # 3-Phase currents with modulation
    env = 1.0 + (mod_depth * np.sin(2.0 * np.pi * f_sideband * t))
    i_a = nominal_current * env * np.sin(2.0 * np.pi * f_line * t)
    i_b = (nominal_current * (1.0 - (unbalance_pct / 200.0))) * np.sin(2.0 * np.pi * f_line * t - (2.0 * np.pi / 3.0))
    i_c = (nominal_current * (1.0 + (unbalance_pct / 200.0))) * np.sin(2.0 * np.pi * f_line * t + (2.0 * np.pi / 3.0))

    rms_a = round(float(np.sqrt(np.mean(i_a ** 2))), 1)
    rms_b = round(float(np.sqrt(np.mean(i_b ** 2))), 1)
    rms_c = round(float(np.sqrt(np.mean(i_c ** 2))), 1)

    # Simulated high-resolution spectrum around 50 Hz (35 to 65 Hz)
    spec_freqs = np.linspace(35.0, 65.0, 120)
    spec_db = []
    for f in spec_freqs:
        # Fundamental at 50 Hz = 0 dB
        if abs(f - 50.0) < 0.25:
            db_val = 0.0
        # Lower sideband f_L - 2sf (~47.5 Hz)
        elif abs(f - (50.0 - f_sideband)) < 0.35:
            db_val = sideband_db
        # Upper sideband f_L + 2sf (~52.5 Hz)
        elif abs(f - (50.0 + f_sideband)) < 0.35:
            db_val = sideband_db + 1.2
        else:
            db_val = -68.0 + np.random.uniform(-2.0, 2.0)
        spec_db.append(round(float(db_val), 1))

    return {
        "equipment": equipment,
        "domain": "MCSA",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fault_profile": fault_profile,
        "primary_fault": primary_fault,
        "status": status,
        "metrics": {
            "nominal_current_a": nominal_current,
            "current_rms_phase_a": rms_a,
            "current_rms_phase_b": rms_b,
            "current_rms_phase_c": rms_c,
            "current_unbalance_pct": round(unbalance_pct, 1),
            "sideband_db_down": round(sideband_db, 1),
            "pole_pass_frequency_hz": round(f_sideband, 2),
        },
        "waveforms": {
            "time_ms": [round(float(val * 1000.0), 1) for val in t],
            "current_phase_a": [round(float(v), 2) for v in i_a],
            "current_phase_b": [round(float(v), 2) for v in i_b],
            "current_phase_c": [round(float(v), 2) for v in i_c],
        },
        "spectrum": {
            "frequency_hz": [round(float(f), 1) for f in spec_freqs],
            "amplitude_db": spec_db,
            "threshold_alarm_db": -45.0,
            "threshold_critical_db": -40.0,
        },
    }


def generate_live_frame(
    equipment: str,
    domain: str = "VIBRASI",
    fault_profile: str = "NORMAL_BASELINE",
) -> Dict[str, Any]:
    """Unified entry point for real-time telemetry streaming."""
    dom_upper = str(domain).upper()
    if dom_upper in ("MCSA", "ELECTRICAL", "MOTOR"):
        return generate_mcsa_telemetry(equipment=equipment, fault_profile=fault_profile)
    return generate_vibration_telemetry(equipment=equipment, fault_profile=fault_profile)

