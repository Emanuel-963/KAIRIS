"""Non-negative Tikhonov DRT solver with automatic L-curve selection."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import lsq_linear
from scipy.signal import find_peaks


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    """Integrate with NumPy 1.x ``trapz`` and support versions that removed it."""
    trapz = getattr(np, "trapz", None)
    if trapz is not None:
        return float(trapz(y, x))
    # NumPy 2.4+ removed the legacy alias. Keep the same trapezoidal formula
    # without requiring the NumPy 2-only ``trapezoid`` name.
    return float(np.sum((y[1:] + y[:-1]) * np.diff(x) * 0.5))


def _second_difference(size: int) -> np.ndarray:
    if size < 3:
        return np.eye(size)
    operator = np.zeros((size - 2, size), dtype=float)
    rows = np.arange(size - 2)
    operator[rows, rows] = 1.0
    operator[rows, rows + 1] = -2.0
    operator[rows, rows + 2] = 1.0
    return operator


def _lcurve_index(residuals: np.ndarray, roughness: np.ndarray) -> int:
    """Choose the point of maximum discrete curvature in log-log space."""
    x = np.log(np.maximum(residuals, np.finfo(float).tiny))
    y = np.log(np.maximum(roughness, np.finfo(float).tiny))
    curvature = np.zeros_like(x)
    for i in range(1, len(x) - 1):
        a = np.array([x[i] - x[i - 1], y[i] - y[i - 1]])
        b = np.array([x[i + 1] - x[i], y[i + 1] - y[i]])
        c = np.array([x[i + 1] - x[i - 1], y[i + 1] - y[i - 1]])
        denominator = np.linalg.norm(a) * np.linalg.norm(b) * np.linalg.norm(c)
        if denominator > 0:
            curvature[i] = abs(a[0] * b[1] - a[1] * b[0]) / denominator
    if np.allclose(curvature, 0):
        return len(x) // 2
    return int(np.nanargmax(curvature))


def solve_drt(
    frequency: np.ndarray,
    real: np.ndarray,
    imag: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Solve the DRT in log-time coordinates with non-negative bounds."""
    frequency = np.asarray(frequency, dtype=float)
    order = np.argsort(frequency)[::-1]
    frequency = frequency[order]
    z = np.asarray(real, dtype=float)[order] + 1j * np.asarray(imag, dtype=float)[order]
    omega = 2.0 * np.pi * frequency
    n_tau = int(config.get("drt_n_tau_points", 100))
    tau_min = 1.0 / (2.0 * np.pi * np.max(frequency))
    tau_max = 1.0 / (2.0 * np.pi * np.min(frequency))
    tau = np.logspace(np.log10(tau_min), np.log10(tau_max), n_tau)
    log_tau = np.log(tau)
    dlog_tau = np.gradient(log_tau)

    r_inf = float(np.real(z[0]))
    target = z - r_inf
    kernel = 1.0 / (1.0 + 1j * omega[:, None] * tau[None, :])
    weighted_kernel = kernel * dlog_tau[None, :]
    matrix = np.vstack((weighted_kernel.real, weighted_kernel.imag))
    vector = np.concatenate((target.real, target.imag))
    operator = _second_difference(n_tau)

    lambdas = np.logspace(-8, 2, 25)
    solutions: list[np.ndarray] = []
    residuals: list[float] = []
    roughness: list[float] = []
    for regularization in lambdas:
        augmented_matrix = np.vstack((matrix, np.sqrt(regularization) * operator))
        augmented_vector = np.concatenate((vector, np.zeros(operator.shape[0])))
        result = lsq_linear(
            augmented_matrix,
            augmented_vector,
            bounds=(0.0, np.inf),
            method="trf",
            lsmr_tol="auto",
            max_iter=500,
        )
        gamma = np.maximum(result.x, 0.0)
        solutions.append(gamma)
        residuals.append(float(np.linalg.norm(matrix @ gamma - vector)))
        roughness.append(float(np.linalg.norm(operator @ gamma)))

    selected = _lcurve_index(np.asarray(residuals), np.asarray(roughness))
    gamma = solutions[selected]
    regularization = float(lambdas[selected])

    prominence = float(config.get("drt_peak_prominence_fraction", 0.05)) * float(
        np.max(gamma)
    )
    peak_indices, _ = find_peaks(gamma, prominence=max(prominence, 0.0))
    peak_indices = peak_indices[np.argsort(tau[peak_indices])]
    minima, _ = find_peaks(-gamma)
    peaks: list[dict[str, float | int]] = []
    for peak_index in peak_indices:
        left_candidates = minima[minima < peak_index]
        right_candidates = minima[minima > peak_index]
        left = int(left_candidates[-1]) if left_candidates.size else 0
        right = int(right_candidates[0]) if right_candidates.size else n_tau - 1
        if right <= left:
            left, right = max(0, peak_index - 1), min(n_tau - 1, peak_index + 1)
        area = _trapz(gamma[left : right + 1], log_tau[left : right + 1])
        peaks.append(
            {
                "index": int(peak_index),
                "left_index": left,
                "right_index": right,
                "tau": float(tau[peak_index]),
                "gamma_max": float(gamma[peak_index]),
                "area": max(area, 0.0),
                "f_char": float(1.0 / (2.0 * np.pi * tau[peak_index])),
            }
        )

    if peaks:
        first_peak = peaks[0]
        r_ct = max(float(first_peak["area"]), np.finfo(float).eps)
        tau_first = float(first_peak["tau"])
    else:
        peak_index = int(np.argmax(gamma))
        r_ct = max(_trapz(gamma, log_tau), np.finfo(float).eps)
        tau_first = float(tau[peak_index])

    f_eq = 1.0 / (2.0 * np.pi * tau_first)
    f_eq_index = int(np.argmin(np.abs(np.log(frequency) - np.log(f_eq))))
    warburg_index = int(np.argmin(np.abs(z.real - np.abs(z.imag))))
    f_w = float(frequency[warburg_index])
    z_w = complex(z[warburg_index])

    total_area = max(_trapz(gamma, log_tau), np.finfo(float).eps)
    tail_mask = tau > 1.0
    tail_area = (
        _trapz(gamma[tail_mask], log_tau[tail_mask])
        if np.count_nonzero(tail_mask) >= 2
        else 0.0
    )
    main_index = int(np.argmax(gamma))
    main_tau = float(tau[main_index])
    tail_fraction = tail_area / total_area
    if main_tau < 0.01 and tail_fraction < 0.25:
        regime = "kinetic_dominated"
    elif main_tau > 1.0 or tail_fraction > 0.60:
        regime = "diffusion_dominated"
    else:
        regime = "mixed"

    return {
        "frequency": frequency,
        "z": z,
        "tau": tau,
        "gamma": gamma,
        "R_inf": r_inf,
        "peaks": peaks,
        "lambda_regularization": regularization,
        "Z0_G1": r_ct,
        "Z0_G2": float(abs(z_w)),
        "Z0_G2_complex": [float(z_w.real), float(z_w.imag)],
        "Z0_G3": float(abs(z[f_eq_index])),
        "Z0_G4": r_inf,
        "f_W": f_w,
        "tau_W": float(1.0 / (2.0 * np.pi * f_w)),
        "f_eq": float(f_eq),
        "regime": regime,
        "fit_residual": float(residuals[selected]),
    }

