from __future__ import annotations

import numpy as np
import pytest

from scripts.run_robustness_benchmark import (
    _wilson_interval,
    add_complex_noise,
    zarc_from_tau,
)


def test_zarc_parameterization_places_imaginary_peak_at_requested_tau():
    tau = 0.02
    frequency = np.logspace(5, -3, 20001)
    omega = 2.0 * np.pi * frequency
    impedance = zarc_from_tau(omega, resistance=5.0, tau_s=tau, exponent=0.77)
    observed_tau = 1.0 / omega[np.argmax(-impedance.imag)]
    assert observed_tau == pytest.approx(tau, rel=0.002)


def test_noise_is_reproducible_and_zero_level_preserves_signal():
    impedance = np.array([1.0 - 1.0j, 2.0 - 0.5j])
    assert np.array_equal(
        add_complex_noise(impedance, 0.0, np.random.default_rng(1)), impedance
    )
    first = add_complex_noise(impedance, 0.01, np.random.default_rng(42))
    second = add_complex_noise(impedance, 0.01, np.random.default_rng(42))
    assert np.array_equal(first, second)
    assert not np.array_equal(first, impedance)


def test_wilson_interval_contains_observed_proportion():
    low, high = _wilson_interval(8, 10)
    assert low < 0.8 < high
    assert 0.0 <= low <= high <= 1.0
