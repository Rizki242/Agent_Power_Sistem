"""
Specialist Condition Monitoring Agents for Power Plant Predictive Maintenance.
Domains: Vibration, MCSA, DGA, Partial Discharge (PD), Tribology, Thermal.
Each agent evaluates raw sensor/laboratory data and returns standardized diagnostic evidence.
"""

from typing import Dict, Any, List, Optional
import math

from src.agents.fault_taxonomy import FaultCode, MechanismTag


class BaseSpecialistAgent:
    """Base class for all condition monitoring specialist agents."""
    def __init__(self, domain_name: str):
        self.domain_name = domain_name

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def _insufficient_if_empty(
        self, equipment: str, data: Dict[str, Any], recognized_fields: set[str]
    ) -> Optional[Dict[str, Any]]:
        normalized = {str(key).lower(): value for key, value in (data or {}).items()}
        observed = sorted(
            key for key in recognized_fields
            if key in normalized and normalized[key] is not None and str(normalized[key]).strip() != ""
        )
        if observed:
            return None
        return {
            "equipment": equipment,
            "domain": self.domain_name,
            "condition": "UNKNOWN",
            "health_score": None,
            "failure_mode": "Insufficient measurement data",
            "fault_code": FaultCode.UNKNOWN.value,
            "mechanism_tags": [],
            "severity": 0,
            "confidence": 0.0,
            "evidence": [],
            "recommendation": [
                "Lengkapi data pengukuran yang relevan sebelum menetapkan kondisi aset."
            ],
            "metrics": {},
            "data_quality": {
                "status": "insufficient_data",
                "observed_fields": [],
                "limitations": ["Tidak ada field pengukuran yang dikenali."],
            },
        }


class VibrationAgent(BaseSpecialistAgent):
    """
    Evaluates vibration spectrum (1X, 2X, 3X, Harmonics, Sub-harmonics, BPFO, BPFI, BSF, FTF)
    and overall RMS against ISO 10816-3 limits.
    """
    def __init__(self):
        super().__init__("Vibration")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        insufficient = self._insufficient_if_empty(equipment, data, {
            "overall_rms", "rms", "bpfo_amp", "bpfo", "bpfi_amp", "bpfi",
            "amp_1x", "1x", "amp_2x", "2x", "axial_1x",
        })
        if insufficient:
            return insufficient
        overall_rms = float(data.get("overall_rms", data.get("rms", 2.2)))
        bpfo = float(data.get("bpfo_amp", data.get("bpfo", 0.0)))
        bpfi = float(data.get("bpfi_amp", data.get("bpfi", 0.0)))
        f1x = float(data.get("amp_1x", data.get("1x", 1.2)))
        f2x = float(data.get("amp_2x", data.get("2x", 0.6)))
        axial_1x = float(data.get("axial_1x", 0.5))

        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal Operation"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.95
        health_score = 95.0

        # ISO 10816-3 Evaluation (Class Group 1/2: <2.8 Good, 2.8-4.5 Acceptable, 4.5-7.1 Alert, >7.1 Danger)
        if overall_rms >= 7.1:
            severity = 4
            condition = "CRITICAL"
            health_score = 35.0
            evidence.append(f"Overall vibration RMS kritis ({overall_rms:.2f} mm/s > 7.1 mm/s ISO Zone D)")
        elif overall_rms >= 4.5:
            severity = 3
            condition = "ALERT"
            health_score = 55.0
            evidence.append(f"Overall vibration RMS tinggi ({overall_rms:.2f} mm/s ISO Zone C Alert)")
        elif overall_rms >= 2.8:
            severity = 2
            condition = "WATCH"
            health_score = 75.0
            evidence.append(f"Overall vibration RMS termonitor ({overall_rms:.2f} mm/s ISO Zone B)")

        # Spectral Pattern Matching
        if bpfo > 0.8 or bpfi > 0.8:
            defect_type = "Outer Race (BPFO)" if bpfo > bpfi else "Inner Race (BPFI)"
            severity = max(severity, 3)
            condition = "ALERT" if severity < 4 else "CRITICAL"
            failure_mode = f"Bearing {defect_type} Defect"
            fault_code = (
                FaultCode.BEARING_OUTER_RACE.value
                if bpfo > bpfi else FaultCode.BEARING_INNER_RACE.value
            )
            mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            confidence = 0.89
            health_score = min(health_score, 50.0)
            evidence.append(f"Frekuensi cacat bearing terdeteksi: {defect_type} amplitudo {max(bpfo, bpfi):.2f} mm/s pk")
            recommendations.append("Inspeksi kondisi pelumasan dan rolling element bearing DE/NDE")
            recommendations.append("Lakukan pengukuran envelope / demodulasi akselerasi dalam 72 jam")
        elif f2x > 0.6 * f1x and f2x > 2.0 or (axial_1x > 1.8):
            severity = max(severity, 2)
            condition = "WARNING" if severity == 2 else condition
            failure_mode = "Shaft Misalignment / Coupling Angularity"
            fault_code = FaultCode.SHAFT_MISALIGNMENT.value
            mechanism_tags.append(MechanismTag.SHAFT_ALIGNMENT.value)
            confidence = 0.86
            health_score = min(health_score, 65.0)
            evidence.append(f"Dominasi spektrum 2X ({f2x:.2f} mm/s) dan getaran aksial 1X ({axial_1x:.2f} mm/s)")
            recommendations.append("Verifikasi kelurusan poros (laser alignment check) dan periksa kondisi coupling")
        elif f1x > 3.5:
            severity = max(severity, 2)
            condition = "WARNING" if severity == 2 else condition
            failure_mode = "Rotor Dynamic Unbalance"
            fault_code = FaultCode.ROTOR_UNBALANCE.value
            confidence = 0.88
            health_score = min(health_score, 68.0)
            evidence.append(f"Puncak getaran dominan 1X rotasi tinggi ({f1x:.2f} mm/s)")
            recommendations.append("Periksa kebersihan sudu/impeller dan pertimbangkan single/two-plane field balancing")

        if not recommendations:
            recommendations.append("Lanjutkan pemantauan getaran berkala sesuai rute inspeksi prediktif")

        return {
            "equipment": equipment,
            "domain": "Vibration",
            "condition": condition,
            "health_score": round(health_score, 1),
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "metrics": {
                "overall_rms": overall_rms,
                "amp_1x": f1x,
                "amp_2x": f2x,
                "bpfo_amp": bpfo,
                "bpfi_amp": bpfi,
                "axial_1x": axial_1x
            }
        }


class MCSAAgent(BaseSpecialistAgent):
    """
    Evaluates Motor Current Signature Analysis:
    Rotor bar sideband dB (EPRI/IEEE), current unbalance %, voltage unbalance %, THD %.
    """
    def __init__(self):
        super().__init__("MCSA")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        insufficient = self._insufficient_if_empty(equipment, data, {
            "upper_sb", "lower_sb", "bearing_status", "dev_current", "i_unbalance",
            "dev_voltage", "v_unbalance", "thd_current", "thd_i", "thd_voltage", "thd_v",
        })
        if insufficient:
            return insufficient
        upper_sb = float(data.get("upper_sb", data.get("Upper Sideband", -55.0)))
        lower_sb = float(data.get("lower_sb", data.get("Lower Sideband", -56.0)))
        dev_curr = float(data.get("dev_current", data.get("Dev Current", 1.2)))
        dev_volt = float(data.get("dev_voltage", data.get("Dev Voltage", 0.5)))
        thd_i = float(data.get("thd_current", data.get("THD Current %", 3.0)))
        bearing_stat = str(data.get("bearing_status", data.get("Bearing", "Normal"))).capitalize()

        max_sb = max(upper_sb, lower_sb)
        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal Operation"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.92
        health_score = 94.0

        # Rotor Bar Sideband Delta (IEEE / EPRI guidelines)
        if max_sb >= -45.0:
            severity = 4
            condition = "CRITICAL"
            failure_mode = "Multiple Broken Rotor Bars / Severe End Ring Crack"
            fault_code = FaultCode.ROTOR_BAR_DEGRADATION.value
            mechanism_tags.append(MechanismTag.ROTOR_ELECTRICAL_DEGRADATION.value)
            confidence = 0.94
            health_score = 30.0
            evidence.append(f"Sideband pole-pass rotor bar kritis ({max_sb:.1f} dB >= -45 dB) - Level 4")
            recommendations.append("Jadwalkan inspeksi visual rotor bar dan pengujian static motor analyzer segera")
        elif max_sb >= -48.0:
            severity = 3
            condition = "ALERT"
            failure_mode = "Single Broken Rotor Bar / High Resistance Joint"
            fault_code = FaultCode.ROTOR_BAR_DEGRADATION.value
            mechanism_tags.append(MechanismTag.ROTOR_ELECTRICAL_DEGRADATION.value)
            confidence = 0.88
            health_score = 55.0
            evidence.append(f"Sideband rotor bar tinggi ({max_sb:.1f} dB) - Level 3 Alert")
            recommendations.append("Lakukan pengujian konfirmasi MCSA berbeban penuh dan pantau tren arus start")
        elif max_sb >= -54.0:
            severity = 2
            condition = "WATCH"
            failure_mode = "Rotor Bar Porosity / Early Resistance Imbalance"
            fault_code = FaultCode.ROTOR_BAR_DEGRADATION.value
            mechanism_tags.append(MechanismTag.ROTOR_ELECTRICAL_DEGRADATION.value)
            confidence = 0.82
            health_score = 75.0
            evidence.append(f"Sideband rotor bar termonitor ({max_sb:.1f} dB) - Level 2 Watch")
            recommendations.append("Pantau tren modulasi arus pada siklus pengukuran berikutnya")

        # Current & Voltage Unbalance
        if dev_curr >= 5.0:
            severity = max(severity, 3)
            condition = "ALERT" if severity >= 3 else condition
            evidence.append(f"Ketidakseimbangan arus fasa tinggi ({dev_curr:.1f}% > 5.0%)")
            recommendations.append("Periksa koneksi terminal motor, breaker contact resistance, dan tegangan suplai")
            health_score = min(health_score, 60.0)

        # Bearing Indication in MCSA
        if bearing_stat in ["Alarm", "High"]:
            mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            evidence.append(f"Indikasi fluktuasi air-gap frekuensi bearing MCSA berstatus {bearing_stat}")
            health_score = min(health_score, 65.0)

        if not recommendations:
            recommendations.append("Kondisi elektromagnetik dan rotor bar motor dalam batas aman operasional")

        return {
            "equipment": equipment,
            "domain": "MCSA",
            "condition": condition,
            "health_score": round(health_score, 1),
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "metrics": {
                "max_sideband_db": max_sb,
                "upper_sideband": upper_sb,
                "lower_sideband": lower_sb,
                "dev_current_pct": dev_curr,
                "dev_voltage_pct": dev_volt,
                "thd_current_pct": thd_i,
                "bearing_status": bearing_stat
            }
        }


class DGAAgent(BaseSpecialistAgent):
    """
    Evaluates Dissolved Gas Analysis for Oil-Filled Transformers:
    Duval Triangle 1, Rogers Ratios, Key Gas, TDCG (IEEE C57.104 & IEC 60599).
    """
    def __init__(self):
        super().__init__("DGA")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        insufficient = self._insufficient_if_empty(equipment, data, {
            "h2", "ch4", "c2h2", "c2h4", "c2h6", "co", "co2", "tdcg",
        })
        if insufficient:
            return insufficient
        h2 = float(data.get("h2", data.get("H2", 15.0)))
        ch4 = float(data.get("ch4", data.get("CH4", 25.0)))
        c2h2 = float(data.get("c2h2", data.get("C2H2", 0.5)))
        c2h4 = float(data.get("c2h4", data.get("C2H4", 12.0)))
        c2h6 = float(data.get("c2h6", data.get("C2H6", 18.0)))
        co = float(data.get("co", data.get("CO", 250.0)))
        co2 = float(data.get("co2", data.get("CO2", 2200.0)))

        tdcg = h2 + ch4 + c2h2 + c2h4 + c2h6 + co
        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal In-Service"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.95
        health_score = 96.0

        # Duval Triangle 1 calculations: %CH4, %C2H4, %C2H2
        duval_sum = ch4 + c2h4 + c2h2
        if duval_sum > 0:
            pct_ch4 = (ch4 / duval_sum) * 100.0
            pct_c2h4 = (c2h4 / duval_sum) * 100.0
            pct_c2h2 = (c2h2 / duval_sum) * 100.0
        else:
            pct_ch4, pct_c2h4, pct_c2h2 = 100.0, 0.0, 0.0

        # Fault Classification
        if c2h2 >= 5.0 or pct_c2h2 >= 13.0:
            severity = 4
            condition = "CRITICAL"
            failure_mode = "D2 - High Energy Electrical Arc Discharge"
            fault_code = FaultCode.DGA_HIGH_ENERGY_DISCHARGE.value
            mechanism_tags.append(MechanismTag.ELECTRICAL_DISCHARGE.value)
            confidence = 0.96
            health_score = 25.0
            evidence.append(f"Acetylene (C2H2) terdeteksi tinggi ({c2h2:.1f} ppm, Duval %C2H2={pct_c2h2:.1f}%)")
            recommendations.append("Lakukan pengujian acoustic PD dan investigasi darurat pada tap changer / winding")
        elif pct_c2h4 >= 50.0 or (c2h4 > 100.0 and c2h4 > ch4):
            severity = 3
            condition = "ALERT"
            failure_mode = "T3 - Thermal Fault T > 700°C (Hotspot/Overheating)"
            fault_code = FaultCode.DGA_THERMAL_FAULT.value
            confidence = 0.91
            health_score = 48.0
            evidence.append(f"Ethylene (C2H4) dominan ({c2h4:.1f} ppm) mengindikasikan overheating termal parah")
            recommendations.append("Periksa pembebanan trafo, pendingin (fans/pumps), dan lakukan thermovision koneksi busbar")
        elif pct_ch4 >= 98.0 and h2 > 100.0:
            severity = 2
            condition = "WARNING"
            failure_mode = "PD - Partial Discharge / Corona in Gas Bubbles"
            fault_code = FaultCode.DGA_PARTIAL_DISCHARGE.value
            mechanism_tags.append(MechanismTag.ELECTRICAL_DISCHARGE.value)
            confidence = 0.85
            health_score = 70.0
            evidence.append(f"Konsentrasi Hydrogen ({h2:.1f} ppm) dan Methane tinggi mengindikasikan pelepasan muatan parsial")
            recommendations.append("Tingkatkan frekuensi sampling DGA menjadi 1 bulan sekali")

        # TDCG Limits (IEEE C57.104)
        if tdcg > 4630:
            severity = max(severity, 4)
            condition = "CRITICAL"
            health_score = min(health_score, 30.0)
            evidence.append(f"Total Dissolved Combustible Gas (TDCG) kritis ({tdcg:.0f} ppm > 4630 ppm Condition 4)")
        elif tdcg > 1920:
            severity = max(severity, 3)
            condition = "ALERT"
            health_score = min(health_score, 55.0)
            evidence.append(f"TDCG tinggi ({tdcg:.0f} ppm Condition 3 Alert)")

        if not recommendations:
            recommendations.append("Gas terlarut dalam batas normal IEEE C57.104 Kondisi 1. Lanjutkan jadwal sampling tahunan")

        return {
            "equipment": equipment,
            "domain": "DGA",
            "condition": condition,
            "health_score": round(health_score, 1),
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "metrics": {
                "tdcg_ppm": tdcg,
                "h2_ppm": h2,
                "ch4_ppm": ch4,
                "c2h2_ppm": c2h2,
                "c2h4_ppm": c2h4,
                "c2h6_ppm": c2h6,
                "co_ppm": co,
                "co2_ppm": co2,
                "duval_zone": failure_mode.split(" - ")[0]
            }
        }


class PDAgent(BaseSpecialistAgent):
    """
    Evaluates Partial Discharge: PRPD Pattern, Pulse Magnitude (pC/mV),
    Discharge Type (Corona, Surface, Internal Void, Slot Discharge).
    """
    def __init__(self):
        super().__init__("Partial Discharge")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        insufficient = self._insufficient_if_empty(equipment, data, {
            "pulse_magnitude_pc", "magnitude", "pd_type", "phase_clustering_deg", "nqn",
        })
        if insufficient:
            return insufficient
        pulse_mag = float(data.get("pulse_magnitude_pc", data.get("magnitude", 120.0)))
        pd_type = str(data.get("pd_type", "Internal Void")).strip()
        phase_clustering = float(data.get("phase_clustering_deg", 45.0))
        nqn = float(data.get("nqn", 15.0))

        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal Insulation"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.90
        health_score = 95.0

        if pulse_mag >= 1500.0 or nqn >= 100.0:
            severity = 4
            condition = "CRITICAL"
            failure_mode = f"Severe {pd_type} Activity"
            fault_code = FaultCode.PARTIAL_DISCHARGE_ACTIVE.value
            mechanism_tags.extend([
                MechanismTag.ELECTRICAL_DISCHARGE.value,
                MechanismTag.INSULATION_DEGRADATION.value,
            ])
            confidence = 0.93
            health_score = 30.0
            evidence.append(f"Amplitudo pelepasan parsial sangat tinggi ({pulse_mag:.0f} pC > 1500 pC)")
            evidence.append(f"Normalized Quantity Number NQN kritis ({nqn:.1f})")
            recommendations.append("Segera rencanakan pengujian Tan Delta dan offline high-voltage insulation test")
        elif pulse_mag >= 500.0:
            severity = 3
            condition = "ALERT"
            failure_mode = f"Active {pd_type}"
            fault_code = FaultCode.PARTIAL_DISCHARGE_ACTIVE.value
            mechanism_tags.extend([
                MechanismTag.ELECTRICAL_DISCHARGE.value,
                MechanismTag.INSULATION_DEGRADATION.value,
            ])
            confidence = 0.87
            health_score = 55.0
            evidence.append(f"Aktivitas PRPD terdeteksi aktif ({pulse_mag:.0f} pC)")
            recommendations.append("Tingkatkan frekuensi pemantauan online PD dan lokalisasi acoustic sensor")
        elif pulse_mag >= 250.0:
            severity = 2
            condition = "WATCH"
            failure_mode = f"Early {pd_type}"
            fault_code = FaultCode.PARTIAL_DISCHARGE_ACTIVE.value
            mechanism_tags.append(MechanismTag.INSULATION_DEGRADATION.value)
            confidence = 0.80
            health_score = 75.0
            evidence.append(f"Aktivitas PD tahap awal termonitor ({pulse_mag:.0f} pC)")
            recommendations.append("Catat tren magnitudo dan korelasi terhadap kelembaban udara")

        if not recommendations:
            recommendations.append("Insulasi stator/kabel dalam kondisi prima tanpa aktivitas peluahan parsial signifikan")

        return {
            "equipment": equipment,
            "domain": "Partial Discharge",
            "condition": condition,
            "health_score": round(health_score, 1),
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "metrics": {
                "pulse_magnitude_pc": pulse_mag,
                "nqn": nqn,
                "pd_type": pd_type,
                "phase_clustering_deg": phase_clustering
            }
        }


class TribologyAgent(BaseSpecialistAgent):
    """
    Evaluates Lube Oil Condition & Wear Debris Analysis:
    Viscosity (ASTM D445), TAN, Water ppm, Wear Metals Fe/Cu/Al, ISO 4406 Cleanliness.
    """
    def __init__(self):
        super().__init__("Tribology")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {str(key).lower(): value for key, value in (data or {}).items()}
        invalid_fields = []

        def _get(*keys, numeric=True):
            for key in keys:
                value = normalized.get(key)
                if value is None or str(value).strip() == "":
                    continue
                if not numeric:
                    return str(value).strip()
                try:
                    number = float(value)
                except (TypeError, ValueError, OverflowError):
                    invalid_fields.append(key)
                    continue
                if isinstance(value, bool) or not math.isfinite(number) or number < 0:
                    invalid_fields.append(key)
                    continue
                return number
            return None

        visc = _get("viscosity_40c", "viscosity")
        nominal_visc = _get("nominal_viscosity")
        tan = _get("tan")
        water_ppm = _get("water_ppm", "water")
        fe = _get("fe_ppm", "fe")
        cu = _get("cu_ppm", "cu")
        iso_code = _get("iso_cleanliness", numeric=False)
        measurements = {
            "viscosity_40c": visc, "tan": tan, "water_ppm": water_ppm,
            "fe_ppm": fe, "cu_ppm": cu, "iso_cleanliness": iso_code,
        }
        observed = [key for key, value in measurements.items() if value is not None]
        missing = [key for key, value in measurements.items() if value is None]
        visc_dev = (
            abs(visc - nominal_visc) / nominal_visc * 100.0
            if visc is not None and nominal_visc is not None and nominal_visc > 0 else None
        )
        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal Lubrication"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.94
        health_score = 95.0

        if fe is not None and fe >= 80.0:
            severity = 4
            condition = "CRITICAL"
            failure_mode = "Severe Ferrous Bearing / Gear Wear Degradation"
            fault_code = FaultCode.BEARING_WEAR.value
            mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            confidence = 0.95
            health_score = 30.0
            evidence.append(f"Konsentrasi partikel keausan besi (Fe) sangat tinggi ({fe:.1f} ppm > 80 ppm)")
            recommendations.append("Inspeksi fisik elemen bearing/gearbox, flushing oli, dan ganti filter cartridge")
        elif fe is not None and fe >= 40.0:
            severity = max(severity, 3)
            condition = "ALERT"
            failure_mode = "Active Bearing Sliding / Fatigue Wear"
            fault_code = FaultCode.BEARING_WEAR.value
            mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            confidence = 0.88
            health_score = min(health_score, 55.0)
            evidence.append(f"Konsentrasi Fe meningkat ({fe:.1f} ppm Alert)")
            recommendations.append("Lakukan re-sampling oli dan periksa magnetic plug")

        if water_ppm is not None and water_ppm >= 500.0:
            severity = max(severity, 3)
            condition = "CRITICAL" if severity >= 4 else "ALERT"
            evidence.append(f"Kontaminasi air tinggi ({water_ppm:.0f} ppm > 500 ppm ASTM D6304)")
            recommendations.append("Periksa seal pendingin oli / oil cooler dan lakukan dehidrasi oli (centrifuge/vacuum)")
            health_score = min(health_score, 50.0)

        if tan is not None and tan >= 0.8:
            severity = max(severity, 3)
            condition = "CRITICAL" if severity >= 4 else "ALERT"
            evidence.append(f"Angka asam total (TAN) tinggi ({tan:.2f} mg KOH/g), oli mengalami oksidasi parah")
            recommendations.append("Jadwalkan penggantian oli pelumas (oil replacement)")
            health_score = min(health_score, 55.0)

        limitations = [
            "ISO cleanliness, Cu, dan viskositas belum memiliki aturan diagnosis di agen ini."
        ]
        if missing:
            limitations.append("Parameter belum diukur: " + ", ".join(missing) + ".")
        if invalid_fields:
            limitations.append("Nilai tidak valid diabaikan: " + ", ".join(invalid_fields) + ".")
        has_evaluated_data = any(value is not None for value in (fe, water_ppm, tan))
        if severity == 1 and (missing or not has_evaluated_data):
            condition = "UNKNOWN"
            severity = 0
            health_score = None
            confidence = 0.0
            failure_mode = "Insufficient measurement data"
            fault_code = FaultCode.UNKNOWN.value
        elif missing:
            # Coverage reduces confidence without changing measured alarm thresholds.
            confidence = round(confidence * len(observed) / len(measurements), 3)
        if condition == "UNKNOWN" or missing:
            recommendations.append("Lengkapi data pengukuran sebelum menyimpulkan kondisi pelumas secara menyeluruh.")
        elif not recommendations:
            recommendations.append("Fe, kadar air, dan TAN terukur berada di bawah ambang alarm; parameter lainnya belum dievaluasi.")

        return {
            "equipment": equipment,
            "domain": "Tribology",
            "condition": condition,
            "health_score": round(health_score, 1) if health_score is not None else None,
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "next_data_needed": missing,
            "data_quality": {
                "status": "insufficient_data" if condition == "UNKNOWN" else "partial" if missing or invalid_fields else "valid",
                "observed_fields": observed,
                "invalid_fields": invalid_fields,
                "limitations": limitations,
            },
            "metrics": {
                "viscosity_40c": visc,
                "viscosity_dev_pct": round(visc_dev, 1) if visc_dev is not None else None,
                "tan_mgkoh_g": tan,
                "water_ppm": water_ppm,
                "fe_ppm": fe,
                "cu_ppm": cu,
                "iso_cleanliness": iso_code
            }
        }


class ThermalAgent(BaseSpecialistAgent):
    """
    Evaluates Thermography & RTD Temperature Monitoring:
    Hotspot Delta-T, Bearing Temperature, Winding Temperature, Phase Thermal Imbalance.
    """
    def __init__(self):
        super().__init__("Thermal")

    def evaluate(self, equipment: str, data: Dict[str, Any]) -> Dict[str, Any]:
        insufficient = self._insufficient_if_empty(equipment, data, {
            "bearing_temp", "temp", "winding_temp", "ambient_temp", "delta_t_phase", "hotspot_temp",
        })
        if insufficient:
            return insufficient
        bearing_temp = float(data.get("bearing_temp", data.get("temp", 62.0)))
        winding_temp = float(data.get("winding_temp", 75.0))
        ambient_temp = float(data.get("ambient_temp", 32.0))
        delta_t_phase = float(data.get("delta_t_phase", 1.5))
        hotspot_temp = float(data.get("hotspot_temp", bearing_temp))

        delta_t_ambient = bearing_temp - ambient_temp
        evidence = []
        recommendations = []
        severity = 1
        condition = "HEALTHY"
        failure_mode = "Normal Thermal State"
        fault_code = FaultCode.NORMAL.value
        mechanism_tags = []
        confidence = 0.93
        health_score = 96.0

        if bearing_temp >= 95.0 or delta_t_ambient >= 60.0:
            severity = 4
            condition = "CRITICAL"
            failure_mode = "Severe Bearing Overheating / Inadequate Lubrication"
            fault_code = FaultCode.BEARING_OVERHEAT.value
            mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            confidence = 0.95
            health_score = 30.0
            evidence.append(f"Suhu bearing sangat tinggi ({bearing_temp:.1f}°C, Delta-T {delta_t_ambient:.1f}°C)")
            recommendations.append("Inspeksi pasokan pelumas segera dan verifikasi getaran bearing")
        elif bearing_temp >= 80.0 or delta_t_phase >= 15.0:
            severity = 3
            condition = "ALERT"
            failure_mode = "Thermal Hotspot / Loose Electrical Connection" if delta_t_phase >= 15.0 else "Bearing Thermal Elevation"
            if delta_t_phase >= 15.0:
                fault_code = FaultCode.ELECTRICAL_HOTSPOT.value
                mechanism_tags.append(MechanismTag.THERMAL_ELECTRICAL.value)
                if bearing_temp >= 80.0:
                    mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            else:
                fault_code = FaultCode.BEARING_OVERHEAT.value
                mechanism_tags.append(MechanismTag.BEARING_DEGRADATION.value)
            confidence = 0.89
            health_score = 58.0
            if delta_t_phase >= 15.0:
                evidence.append(f"Perbedaan suhu antar fasa tinggi (Delta-T {delta_t_phase:.1f}°C > 15°C)")
                recommendations.append("Lakukan inspeksi thermovision pada terminal busbar dan tightening baut kabel")
            else:
                evidence.append(f"Suhu bearing meningkat ({bearing_temp:.1f}°C)")
                recommendations.append("Periksa kuantitas dan interval regreasing pelumas")
        elif bearing_temp >= 70.0:
            severity = 2
            condition = "WATCH"
            health_score = 78.0
            evidence.append(f"Suhu bearing termonitor ({bearing_temp:.1f}°C)")

        if not recommendations:
            recommendations.append("Profil temperatur peralatan dan gradien suhu dalam batas normal aman")

        return {
            "equipment": equipment,
            "domain": "Thermal",
            "condition": condition,
            "health_score": round(health_score, 1),
            "failure_mode": failure_mode,
            "fault_code": fault_code,
            "mechanism_tags": mechanism_tags,
            "severity": severity,
            "confidence": confidence,
            "evidence": evidence,
            "recommendation": recommendations,
            "metrics": {
                "bearing_temp_c": bearing_temp,
                "winding_temp_c": winding_temp,
                "delta_t_ambient_c": round(delta_t_ambient, 1),
                "delta_t_phase_c": delta_t_phase,
                "hotspot_temp_c": hotspot_temp
            }
        }
