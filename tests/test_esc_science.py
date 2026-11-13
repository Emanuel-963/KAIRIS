from __future__ import annotations

import numpy as np
import pytest

from agents.agent4_esc import Agent4_ESC
from core.esc_engine import (
    assess_reference,
    calculate_group,
    conventional_references,
    inverse_transform_esc,
    reference_sensitivity,
    reference_uncertainty_monte_carlo,
    transform_esc,
)


def _randles() -> tuple[np.ndarray, np.ndarray]:
    frequency = np.logspace(5, -2, 80)
    omega = 2.0 * np.pi * frequency
    rs, rct, capacitance = 4.0, 20.0, 2e-4
    z = rs + rct / (1.0 + 1j * omega * rct * capacitance)
    return frequency, z


def test_classical_transform_round_trip_and_scale_covariance():
    frequency, z = _randles()
    gamma = transform_esc(z, 20.0)

    assert inverse_transform_esc(gamma, 20.0) == pytest.approx(z)
    assert transform_esc(7.5 * z, 7.5 * 20.0) == pytest.approx(gamma)
    assert frequency.size == gamma.size


def test_positive_real_reference_maps_positive_real_impedance_inside_unit_disk():
    frequency, z = _randles()
    metrics = calculate_group(z, 4.0, frequency)

    assert metrics["passivity_applicable"] is True
    assert metrics["passive_point_fraction"] == 1.0
    assert metrics["passivity_violation_count"] == 0
    assert metrics["passivity_identity_error_max"] < 1e-12
    assert metrics["gamma_max"] <= 1.0 + 1e-12


def test_negative_resistance_is_outside_disk_and_complex_reference_disables_test():
    frequency = np.logspace(3, -1, 10)
    active_z = np.full(frequency.shape, -2.0 + 0.5j)
    active = calculate_group(active_z, 5.0, frequency)
    complex_reference = calculate_group(active_z, 5.0 + 1.0j, frequency)

    assert active["passivity_violation_count"] == frequency.size
    assert "outside_passive_unit_disk" in active["flags"]
    assert complex_reference["passivity_applicable"] is False
    assert complex_reference["passive_point_fraction"] is None


def test_trajectory_follows_frequency_without_reordering_returned_gamma():
    frequency = np.array([1e4, 1e3, 1e2, 1e1])
    z = np.array([0.2-0.1j, 0.5-0.5j, 2-0.3j, 5-0.1j])
    order = [1, 3, 0, 2]
    baseline = calculate_group(z, 1.0, frequency)
    shuffled = calculate_group(z[order], 1.0, frequency[order])
    for field in ("path_length", "tortuosity", "radial_total_variation", "unwrapped_phase_span_rad"):
        assert shuffled[field] == pytest.approx(baseline[field])
    assert shuffled["gamma"] == pytest.approx(baseline["gamma"][order])


def test_small_complex_reference_is_preserved_and_not_passivity_eligible():
    group = calculate_group(np.array([1e-8 - 2e-8j]), 1e-8 + 5e-9j)
    assert group["Z0"] == [1e-8, 5e-9]
    assert group["passivity_applicable"] is False
    assert group["passivity_identity_error_max"] is None


def test_tiny_scale_preserves_transform_and_singularity_margin():
    z = np.array([1 + 1j, -1.0])
    normal = calculate_group(z, 1.0)
    for scale in (1e-9, 1e-180):
        scaled = calculate_group(z * scale, scale)
        assert scaled["gamma"][0] == pytest.approx(normal["gamma"][0])
        assert scaled["singularity_count"] == 1
        assert scaled["singularity_margin_min"] == 0.0
        assert scaled["passivity_identity_error_max"] < 1e-12
    with pytest.raises(ValueError, match="Z0"):
        calculate_group(z, 0.0)


def test_integrated_esc_handles_absent_g2_and_keeps_other_groups(tmp_path):
    f, z = _randles()
    data = {"frequency": f, "real": z.real, "imag": z.imag}
    result = Agent4_ESC(data, 4.0, None, 20.0, 5.0, {}).run(tmp_path, "randles")
    assert result["G2"]["status"] == "abstained"
    assert len(result["G2_interpretation"]) == 1
    assert all(len(result[group]["points"]) == f.size for group in ("G1", "G3", "G4"))


def test_singularity_is_counted_and_near_singularity_causes_abstention():
    frequency = np.array([100.0, 10.0, 1.0, 0.1, 0.01])
    z = np.array([2.0, 1.0, -4.9999999, -5.0, 10.0], dtype=complex)
    decision = assess_reference(z, 5.0, frequency)

    assert decision["status"] == "abstained"
    assert decision["metrics"]["singularity_count"] == 1
    assert "near_transform_singularity" in decision["reasons"]


def test_log_frequency_centroid_is_stable_to_log_grid_density():
    def spectrum(frequency: np.ndarray) -> np.ndarray:
        omega = 2.0 * np.pi * frequency
        return 3.0 + 15.0 / (1.0 + 1j * omega * 15.0 * 1e-3)

    sparse_f = np.logspace(4, -2, 31)
    dense_f = np.logspace(4, -2, 301)
    sparse = calculate_group(spectrum(sparse_f), 3.0, sparse_f)
    dense = calculate_group(spectrum(dense_f), 3.0, dense_f)

    assert sparse["log_frequency_centroid"] == pytest.approx(
        dense["log_frequency_centroid"], abs=2e-3
    )


def test_reference_sensitivity_and_uncertainty_are_reproducible():
    frequency, z = _randles()
    sensitivity = reference_sensitivity(z, 4.0, frequency, np.array([0.5, 1.0, 2.0]))
    first = reference_uncertainty_monte_carlo(
        z, 4.0, frequency, relative_standard_uncertainty=0.1, draws=40, seed=17
    )
    second = reference_uncertainty_monte_carlo(
        z, 4.0, frequency, relative_standard_uncertainty=0.1, draws=40, seed=17
    )

    assert sensitivity["baseline_factor"] == 1.0
    assert len(sensitivity["rows"]) == 3
    assert first == second
    assert first["intervals"]["gamma_mean"]["q025"] <= first["intervals"]["gamma_mean"]["q975"]


def test_reference_uncertainty_policy_and_conventional_comparators():
    frequency, z = _randles()
    accepted = assess_reference(z, 4.0, frequency, reference_relative_uncertainty=0.1)
    abstained = assess_reference(z, 4.0, frequency, reference_relative_uncertainty=0.4)
    baselines = conventional_references(z, frequency)

    assert accepted["usable"] is True
    assert abstained["usable"] is False
    assert "reference_uncertainty_too_large" in abstained["reasons"]
    assert set(baselines) == {
        "fixed_50_ohm",
        "high_frequency_real_proxy",
        "median_magnitude",
        "geometric_mean_magnitude",
    }



