"""Golden Spectral Field calculations defined by KAIRIS."""

from __future__ import annotations

from typing import Any

import numpy as np


def calculate_gsf(
    frequency: np.ndarray,
    real: np.ndarray,
    imag: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    frequency = np.asarray(frequency, dtype=float)
    real = np.asarray(real, dtype=float)
    imag_abs = np.abs(np.asarray(imag, dtype=float))
    valid = np.isfinite(frequency + real + imag_abs) & (frequency > 0)
    frequency, real, imag_abs = frequency[valid], real[valid], imag_abs[valid]
    # α is defined along increasing frequency so capacitive/diffusive decay is
    # represented by the negative ranges used by the KAIRIS classifier.
    order = np.argsort(frequency)
    frequency, real, imag_abs = frequency[order], real[order], imag_abs[order]
    if frequency.size < 3:
        raise ValueError("GSF requer ao menos três pontos EIS válidos")

    real_max = float(np.max(real))
    real_scale = real_max if real_max > np.finfo(float).eps else max(float(np.max(np.abs(real))), np.finfo(float).eps)
    imag_scale = max(float(np.max(imag_abs)), np.finfo(float).eps)
    x_n = real / real_scale
    y_n = imag_abs / imag_scale
    q = np.sqrt(x_n**2 + y_n**2)
    q = np.maximum(q, np.finfo(float).eps)
    phi = float(config.get("gsf_phi", 1.618033988749895))

    window = max(1, int(config.get("gsf_window_alpha", 3)))
    if window > 1:
        half = window // 2
        smooth_log_q = np.array(
            [
                np.mean(np.log(q[max(0, i - half) : min(q.size, i + half + 1)]))
                for i in range(q.size)
            ]
        )
        q_for_alpha = np.exp(smooth_log_q)
    else:
        q_for_alpha = q
    alpha = np.full(q.size, np.nan)
    alpha[1:] = np.log(q_for_alpha[1:] / q_for_alpha[:-1]) / np.log(phi)

    gradient = np.full(q.size, np.nan)
    log_frequency = np.log(frequency)
    for index in range(1, q.size - 1):
        denominator = log_frequency[index + 1] - log_frequency[index - 1]
        if not np.isclose(denominator, 0.0) and np.isfinite(alpha[index - 1 : index + 2]).all():
            gradient[index] = (alpha[index + 1] - alpha[index - 1]) / denominator
    finite_alpha = alpha[np.isfinite(alpha)]
    finite_gradient_indices = np.flatnonzero(np.isfinite(gradient))
    if finite_alpha.size == 0:
        raise ValueError("Não foi possível calcular α para o GSF")
    if finite_gradient_indices.size:
        critical_index = int(
            finite_gradient_indices[np.argmax(np.abs(gradient[finite_gradient_indices]))]
        )
        i_crit = float(abs(gradient[critical_index]))
        f_icrit = float(frequency[critical_index])
    else:
        i_crit, f_icrit = 0.0, float(frequency[0])

    alpha_mean = float(np.mean(finite_alpha))
    if alpha_mean > -0.1:
        regime = "resistive"
    elif alpha_mean >= -0.5:
        regime = "pseudocapacitive"
    elif alpha_mean >= -1.0:
        regime = "mixed"
    else:
        regime = "diffusive"
    kphi = q * phi
    return {
        "frequency": frequency,
        "x_n": x_n,
        "y_n": y_n,
        "q": q,
        "alpha": alpha,
        "kphi": kphi,
        "gradient": gradient,
        "alpha_mean": alpha_mean,
        "alpha_std": float(np.std(finite_alpha)),
        "alpha_min": float(np.min(finite_alpha)),
        "alpha_max": float(np.max(finite_alpha)),
        "kphi_mean": float(np.mean(kphi)),
        "kphi_std": float(np.std(kphi)),
        "I_crit": i_crit,
        "f_Icrit": f_icrit,
        "regime_gsf": regime,
        "n_points_valid": int(frequency.size),
    }

