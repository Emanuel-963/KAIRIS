from __future__ import annotations

import numpy as np
import pytest

from agents.agent4_esc import Agent4_ESC
from core.drt_solver import assess_r_inf_quality, solve_drt
from core.r_inf_estimator import extrapolate_r_inf
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


def test_secondary_extrapolation_recovers_simple_tail_without_replacing_primary():
    frequency = np.logspace(np.log10(1e4), -2, 101)
    omega = 2.0 * np.pi * frequency
    impedance = 0.2 + zarc_from_tau(omega, 8.0, 1e-2, 0.85)
    config = {
        "r_inf_extrapolation_enabled": True,
        "r_inf_extrapolation_points": 20,
        "r_inf_extrapolation_min_points": 12,
        "r_inf_extrapolation_max_rmse_fraction": 0.015,
        "r_inf_extrapolation_max_window_spread_fraction": 0.2,
    }
    result = extrapolate_r_inf(frequency, impedance.real, impedance.imag, config)
    assert result["R_inf_extrapolation_status"] == "accepted"
    assert result["R_inf_extrapolated"] == pytest.approx(0.2, rel=0.05)
    assert result["R_inf_extrapolation_interval_type"] == "nested_window_sensitivity_range"


def test_secondary_extrapolation_abstains_for_unstable_multitail_fit():
    frequency = np.logspace(6, -2, 101)
    impedance = _triple_zarc(frequency)
    config = {
        "r_inf_extrapolation_enabled": True,
        "r_inf_extrapolation_points": 20,
        "r_inf_extrapolation_min_points": 12,
        "r_inf_extrapolation_max_rmse_fraction": 0.015,
        "r_inf_extrapolation_max_window_spread_fraction": 0.2,
    }
    result = extrapolate_r_inf(frequency, impedance.real, impedance.imag, config)
    assert result["R_inf_extrapolation_status"] == "abstained"
    assert result["R_inf_extrapolated"] is None


def test_single_drt_peak_is_not_claimed_as_reliable_process_count():
    frequency = np.logspace(5, -2, 81)
    omega = 2.0 * np.pi * frequency
    impedance = 0.2 + zarc_from_tau(omega, 8.0, 1e-2, 0.90)
    config = {
        "drt_n_tau_points": 80,
        "drt_peak_prominence_fraction": 0.05,
        "drt_min_resolved_separation_decades": 1.3,
        "r_inf_quality_enabled": False,
        "r_inf_extrapolation_enabled": False,
    }
    result = solve_drt(frequency, impedance.real, impedance.imag, config)
    assert len(result["peaks"]) == 1
    assert result["drt_resolution_status"] == "indeterminate_single_peak"
    assert result["drt_peak_count_reliable"] is False
