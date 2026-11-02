from __future__ import annotations

import numpy as np

from agents.agent4_esc import Agent4_ESC
from core.drt_solver import assess_r_inf_quality
from scripts.run_robustness_benchmark import zarc_from_tau


CONFIG = {
    "r_inf_quality_enabled": True,
    "r_inf_hf_points": 8,
    "r_inf_max_phase_deg": 7.0,
    "r_inf_max_relative_span": 0.1,
}


def _triple_zarc(frequency: np.ndarray) -> np.ndarray:
    omega = 2.0 * np.pi * frequency
    return (
        0.2
        + zarc_from_tau(omega, 1.5, 1.0 / (2.0 * np.pi * 2e4), 0.83)
        + zarc_from_tau(omega, 4.0, 1.0 / (2.0 * np.pi * 120.0), 0.78)
        + zarc_from_tau(omega, 8.0, 1.0 / (2.0 * np.pi * 0.18), 0.73)
    )


def test_r_inf_abstains_when_high_frequency_window_has_not_plateaued():
    frequency = np.logspace(6, -2, 101)
    impedance = _triple_zarc(frequency)
    result = assess_r_inf_quality(frequency, impedance.real, impedance.imag, CONFIG)
    assert result["R_inf_status"] == "abstained"
    assert result["R_inf_accepted"] is None
    assert "high_frequency_phase_not_near_zero" in result["R_inf_abstention_reasons"]


def test_r_inf_is_accepted_after_sufficient_high_frequency_extension():
    frequency = np.logspace(np.log10(3e6), -2, 101)
    impedance = _triple_zarc(frequency)
    result = assess_r_inf_quality(frequency, impedance.real, impedance.imag, CONFIG)
    assert result["R_inf_status"] == "accepted"
    assert result["R_inf_accepted"] is not None
    assert result["R_inf_hf_phase_deg"] < 7.0
    assert result["R_inf_hf_real_span_fraction"] < 0.1


def test_esc_g4_is_explicitly_abstained_for_missing_reference(tmp_path):
    z_data = {"frequency": [1000.0, 100.0], "real": [1.0, 2.0], "imag": [-0.1, -0.3]}
    result = Agent4_ESC(z_data, 1.0, [1.0, -0.1], 1.5, None, {}).run(tmp_path, "sample")
    assert result["G4"]["status"] == "abstained"
    assert result["G4"]["points"] == []
    assert result["G4"]["flags"] == ["reference_abstained"]
