"""Linear Kramers-Kronig validation for KAIRIS EIS spectra.

This implements the Lin-KK model described by Schönleber et al. (2014):
an ohmic resistance, logarithmically distributed RC elements and a series
inductance. The fit is linear in all parameters and uses complex residuals.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _time_constants(frequency: np.ndarray, count: int) -> np.ndarray:
    tau_min = 1.0 / (2.0 * np.pi * np.max(frequency))
    tau_max = 1.0 / (2.0 * np.pi * np.min(frequency))
    return np.logspace(np.log10(tau_min), np.log10(tau_max), count)


def _mu(rc_resistances: np.ndarray) -> float:
    positive_mass = float(np.sum(np.abs(rc_resistances[rc_resistances >= 0.0])))
    negative_mass = float(np.sum(np.abs(rc_resistances[rc_resistances < 0.0])))
    if positive_mass <= np.finfo(float).eps:
        return float("-inf") if negative_mass > 0.0 else 1.0
    return 1.0 - negative_mass / positive_mass


def _fit_model(
    frequency: np.ndarray,
    impedance: np.ndarray,
    count: int,
    add_capacitance: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Fit one complex Lin-KK model and return its parameters and response."""
    omega = 2.0 * np.pi * frequency
    tau = _time_constants(frequency, count)
    magnitude = np.maximum(np.abs(impedance), np.finfo(float).eps)
    columns = count + (3 if add_capacitance else 2)
    real_matrix = np.zeros((frequency.size, columns), dtype=float)
    imag_matrix = np.zeros((frequency.size, columns), dtype=float)
    real_matrix[:, 0] = 1.0 / magnitude
    for index, tau_value in enumerate(tau, start=1):
        kernel = 1.0 / (1.0 + 1j * omega * tau_value)
        real_matrix[:, index] = kernel.real / magnitude
        imag_matrix[:, index] = kernel.imag / magnitude
    if add_capacitance:
        imag_matrix[:, -2] = -1.0 / (omega * magnitude)
    imag_matrix[:, -1] = omega / magnitude

    matrix = np.vstack((real_matrix, imag_matrix))
    target = np.concatenate((impedance.real / magnitude, impedance.imag / magnitude))
    parameters = np.linalg.lstsq(matrix, target, rcond=None)[0]

    fitted = np.full(frequency.shape, parameters[0], dtype=complex)
    for resistance, tau_value in zip(parameters[1 : count + 1], tau):
        fitted += resistance / (1.0 + 1j * omega * tau_value)
    if add_capacitance:
        fitted += -1j * parameters[-2] / omega
    fitted += 1j * omega * parameters[-1]
    return parameters, tau, fitted, _mu(parameters[1 : count + 1])


def validate_lin_kk(
    frequency: np.ndarray,
    real: np.ndarray,
    imag: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Run an actual Lin-KK compatibility test and quantify normalized errors.

    A passing result means the measured spectrum is reproducible by the
    Kramers-Kronig-compliant Lin-KK basis within the configured residual
    limits. It does not, by itself, prove good experimental practice.
    """
    frequency = np.asarray(frequency, dtype=float)
    impedance = np.asarray(real, dtype=float) + 1j * np.asarray(imag, dtype=float)
    minimum_points = int(config.get("lin_kk_min_points", 10))
    if frequency.size < minimum_points:
        raise ValueError(
            f"Lin-KK requer ao menos {minimum_points} pontos; foram recebidos {frequency.size}."
        )
    if np.any(~np.isfinite(frequency)) or np.any(frequency <= 0.0):
        raise ValueError("Lin-KK requer frequencias positivas e finitas.")
    if np.any(~np.isfinite(impedance.real)) or np.any(~np.isfinite(impedance.imag)):
        raise ValueError("Lin-KK requer impedancias finitas.")

    order = np.argsort(frequency)[::-1]
    frequency = frequency[order]
    impedance = impedance[order]
    cutoff = float(config.get("lin_kk_mu_cutoff", 0.85))
    add_capacitance = bool(config.get("lin_kk_add_capacitance", False))
    configured_max = max(3, int(config.get("lin_kk_max_rc_elements", 50)))
    extra_parameters = 3 if add_capacitance else 2
    # Keep the complex linear system overdetermined so a small spectrum cannot
    # obtain a trivial zero-residual fit from more parameters than observations.
    identifiable_max = max(3, 2 * frequency.size - extra_parameters - 1)
    max_elements = min(configured_max, identifiable_max)
    point_threshold_pct = float(config.get("lin_kk_point_threshold_pct", 5.0))
    max_failure_pct = float(config.get("lin_kk_max_failure_pct", 10.0))
    rmse_threshold_pct = float(config.get("lin_kk_rmse_threshold_pct", 5.0))

    selected: tuple[np.ndarray, np.ndarray, np.ndarray, float] | None = None
    element_count = 3
    for element_count in range(3, max_elements + 1):
        selected = _fit_model(frequency, impedance, element_count, add_capacitance)
        candidate_error = np.abs(impedance - selected[2]) / np.maximum(
            np.abs(impedance), np.finfo(float).eps
        )
        candidate_rmse_pct = 100.0 * float(np.sqrt(np.mean(candidate_error**2)))
        candidate_failure_pct = (
            100.0
            * float(np.count_nonzero(100.0 * candidate_error > point_threshold_pct))
            / frequency.size
        )
        # Standard Lin-KK uses mu to control over-fitting. KAIRIS also requires
        # the configured residual criteria before accepting the selected M.
        if (
            selected[3] <= cutoff
            and candidate_rmse_pct <= rmse_threshold_pct
            and candidate_failure_pct <= max_failure_pct
        ):
            break
    if selected is None:  # defensive; max_elements is constrained to at least 3
        raise RuntimeError("Lin-KK nao produziu um ajuste.")

    parameters, tau, fitted, mu = selected
    scale = np.maximum(np.abs(impedance), np.finfo(float).eps)
    normalized_error = (impedance - fitted) / scale
    residual_real = normalized_error.real
    residual_imag = normalized_error.imag
    residual_magnitude = np.abs(normalized_error)
    rmse_pct = 100.0 * float(np.sqrt(np.mean(residual_magnitude**2)))
    max_residual_pct = 100.0 * float(np.max(residual_magnitude))
    point_pass = 100.0 * residual_magnitude <= point_threshold_pct
    failure_pct = 100.0 * float(np.count_nonzero(~point_pass)) / frequency.size
    converged = bool(mu <= cutoff)

    return {
        "frequency": frequency,
        "fit_real": fitted.real,
        "fit_imag": fitted.imag,
        "residual_real": residual_real,
        "residual_imag": residual_imag,
        "residual_magnitude_pct": 100.0 * residual_magnitude,
        "point_pass": point_pass,
        "M": int(element_count),
        "max_M_effective": int(max_elements),
        "mu": float(mu),
        "mu_cutoff": cutoff,
        "converged": converged,
        "rmse_pct": rmse_pct,
        "max_residual_pct": max_residual_pct,
        "failure_pct": failure_pct,
        "valid": bool(
            converged
            and rmse_pct <= rmse_threshold_pct
            and failure_pct <= max_failure_pct
        ),
        "add_capacitance": add_capacitance,
        "tau": tau,
        "parameters": parameters,
    }
