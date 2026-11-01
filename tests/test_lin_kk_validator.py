from __future__ import annotations

import numpy as np
import pytest

from core.lin_kk_validator import validate_lin_kk


def test_lin_kk_accepts_an_ideal_rc_spectrum():
    frequency = np.logspace(5, -2, 60)
    omega = 2.0 * np.pi * frequency
    impedance = 5.0 + 100.0 / (1.0 + 1j * omega * 0.01)

    result = validate_lin_kk(frequency, impedance.real, impedance.imag, {})

    assert result["valid"] is True
    assert result["converged"] is True
    assert result["M"] >= 3
    assert result["rmse_pct"] <= 5.0
    assert result["failure_pct"] <= 10.0
    assert len(result["fit_real"]) == len(frequency)


def test_lin_kk_rejects_too_few_points():
    frequency = np.logspace(3, 1, 5)
    impedance = np.full(5, 10.0 - 1.0j)

    with pytest.raises(ValueError, match="ao menos 10 pontos"):
        validate_lin_kk(frequency, impedance.real, impedance.imag, {})
