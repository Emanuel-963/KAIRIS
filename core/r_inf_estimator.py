"""Secondary high-frequency extrapolation for the KAIRIS R_inf endpoint."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.optimize import least_squares


def _tail_model(omega: np.ndarray, r_inf: float, amplitude: float, exponent: float) -> np.ndarray:
    """Asymptotic capacitive CPE tail: R_inf + A*(j*omega)^(-n)."""
    return r_inf + amplitude * (1j * omega) ** (-exponent)


def extrapolate_r_inf(
    frequency: np.ndarray,
    real: np.ndarray,
    imag: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Estimate R_inf from nested high-frequency windows as a secondary analysis.

    The reported interval is the range across nested fitting windows. It is a
    sensitivity interval, not a confidence interval and not a replacement for
    direct observation of a high-frequency plateau.
    """
    if not bool(config.get("r_inf_extrapolation_enabled", True)):
        return {
            "R_inf_extrapolation_status": "disabled",
            "R_inf_extrapolated": None,
            "R_inf_extrapolation_interval": None,
            "R_inf_extrapolation_reasons": ["disabled_by_config"],
        }
    frequency = np.asarray(frequency, dtype=float)
    z = np.asarray(real, dtype=float) + 1j * np.asarray(imag, dtype=float)
    valid = np.isfinite(frequency) & (frequency > 0) & np.isfinite(z.real) & np.isfinite(z.imag)
    frequency, z = frequency[valid], z[valid]
    order = np.argsort(frequency)[::-1]
    frequency, z = frequency[order], z[order]
    maximum_points = int(config.get("r_inf_extrapolation_points", 20))
    minimum_points = int(config.get("r_inf_extrapolation_min_points", 12))
    maximum_rmse = float(config.get("r_inf_extrapolation_max_rmse_fraction", 0.03))
    maximum_spread = float(
        config.get("r_inf_extrapolation_max_window_spread_fraction", 0.20)
    )
    reasons: list[str] = []
    if z.size < minimum_points:
        reasons.append("insufficient_points_for_extrapolation")
    if z.size and z[0].imag > 0:
        reasons.append("inductive_high_frequency_edge_not_supported")
    if reasons:
        return {
            "R_inf_extrapolation_status": "abstained",
            "R_inf_extrapolated": None,
            "R_inf_extrapolation_interval": None,
            "R_inf_extrapolation_reasons": reasons,
        }

    largest = min(maximum_points, z.size)
    candidates = sorted(
        {
            minimum_points,
            max(minimum_points, round((minimum_points + largest) / 2)),
            largest,
        }
    )
    fits: list[dict[str, float]] = []
    for count in candidates:
        local_f = frequency[:count]
        local_z = z[:count]
        omega = 2.0 * np.pi * local_f
        scale = max(float(np.median(np.abs(local_z))), np.finfo(float).eps)
        initial_r = max(0.0, min(float(np.min(local_z.real)), float(local_z.real[0])))
        initial_n = 0.8
        tail = (1j * omega[0]) ** (-initial_n)
        initial_a = max(
            np.finfo(float).eps,
            float(abs(local_z[0] - initial_r) / max(abs(tail), np.finfo(float).eps)),
        )

        def residual(parameters: np.ndarray) -> np.ndarray:
            prediction = _tail_model(omega, *parameters)
            difference = (prediction - local_z) / scale
            return np.concatenate((difference.real, difference.imag))

        upper_r = max(float(np.max(local_z.real)) * 2.0, scale * 2.0, 1.0)
        result = least_squares(
            residual,
            x0=np.array([initial_r, initial_a, initial_n]),
            bounds=(np.array([0.0, 0.0, 0.30]), np.array([upper_r, np.inf, 1.20])),
            max_nfev=2000,
        )
        if not result.success or not np.all(np.isfinite(result.x)):
            continue
        prediction = _tail_model(omega, *result.x)
        rmse = float(np.sqrt(np.mean(np.abs(prediction - local_z) ** 2)) / scale)
        fits.append(
            {
                "points": float(count),
                "r_inf": float(result.x[0]),
                "amplitude": float(result.x[1]),
                "exponent": float(result.x[2]),
                "rmse_fraction": rmse,
            }
        )
    if len(fits) < 2:
        reasons.append("extrapolation_fit_failed")
        return {
            "R_inf_extrapolation_status": "abstained",
            "R_inf_extrapolated": None,
            "R_inf_extrapolation_interval": None,
            "R_inf_extrapolation_reasons": reasons,
        }
    primary = fits[-1]
    intercepts = [item["r_inf"] for item in fits]
    interval = [min(intercepts), max(intercepts)]
    denominator = max(abs(primary["r_inf"]), np.finfo(float).eps)
    spread = (interval[1] - interval[0]) / denominator
    if primary["rmse_fraction"] > maximum_rmse:
        reasons.append("extrapolation_residual_too_large")
    if spread > maximum_spread:
        reasons.append("extrapolation_window_instability")
    if primary["r_inf"] > float(z[0].real) * 1.20:
        reasons.append("extrapolated_intercept_exceeds_measured_edge")
    accepted = not reasons
    return {
        "R_inf_extrapolation_status": "accepted" if accepted else "abstained",
        "R_inf_extrapolated": primary["r_inf"] if accepted else None,
        "R_inf_extrapolation_candidate": primary["r_inf"],
        "R_inf_extrapolation_interval": interval,
        "R_inf_extrapolation_interval_type": "nested_window_sensitivity_range",
        "R_inf_extrapolation_exponent": primary["exponent"],
        "R_inf_extrapolation_rmse_fraction": primary["rmse_fraction"],
        "R_inf_extrapolation_window_spread_fraction": spread,
        "R_inf_extrapolation_reasons": reasons,
        "R_inf_extrapolation_fits": fits,
    }
