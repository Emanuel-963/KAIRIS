"""Emanuel-Smith Chart transform and reflection metrics."""

from __future__ import annotations

from typing import Any

import numpy as np


def as_complex_reference(value: Any) -> complex:
    if isinstance(value, dict):
        return complex(float(value.get("real", 0.0)), float(value.get("imag", 0.0)))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return complex(float(value[0]), float(value[1]))
    return complex(value)


def transform_esc(z: np.ndarray, z0: Any) -> np.ndarray:
    reference = as_complex_reference(z0)
    denominator = z + reference
    safe = np.abs(denominator) > np.finfo(float).eps
    gamma = np.full(z.shape, np.nan + 1j * np.nan, dtype=complex)
    gamma[safe] = (z[safe] - reference) / denominator[safe]
    return gamma


def calculate_group(z: np.ndarray, z0: Any) -> dict[str, Any]:
    gamma = transform_esc(z, z0)
    finite = np.isfinite(gamma.real) & np.isfinite(gamma.imag)
    if not np.any(finite):
        raise ValueError("Transformação ESC singular para todos os pontos")
    values = gamma[finite]
    centroid = [float(np.mean(values.real)), float(np.mean(values.imag))]
    low_frequency_point = values[-1]
    flags: list[str] = []
    if centroid[0] > 0.3 and centroid[1] < 0:
        flags.append("capacitive_high_Z")
    if low_frequency_point.real > 0.8:
        flags.append("diffusion_dominated")
    reference = as_complex_reference(z0)
    return {
        "Z0": float(reference.real) if np.isclose(reference.imag, 0.0) else [float(reference.real), float(reference.imag)],
        "centroid": centroid,
        "gamma_mean": float(np.mean(np.abs(values))),
        "lf_point": [float(low_frequency_point.real), float(low_frequency_point.imag)],
        "flags": flags,
        "gamma": gamma,
    }

