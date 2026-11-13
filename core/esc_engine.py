"""Electrochemical Spectral Cartography using a classical Smith transform.

The impedance-to-reflection-coefficient mapping is classical.  ESC contributes
electrochemical reference definitions, trajectory descriptors, uncertainty
handling and explicit abstention; it does not claim the bilinear map itself.
"""

from __future__ import annotations

from typing import Any

import numpy as np


DEFAULT_ABSTENTION_THRESHOLDS = {
    "min_points": 5,
    "min_frequency_decades": 1.0,
    "singularity_margin_min": 1e-6,
    "reference_relative_uncertainty_max": 0.25,
}


def as_complex_reference(value: Any) -> complex:
    if isinstance(value, dict):
        return complex(float(value.get("real", 0.0)), float(value.get("imag", 0.0)))
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return complex(float(value[0]), float(value[1]))
    return complex(value)


def transform_esc(z: np.ndarray, z0: Any) -> np.ndarray:
    # ESC uses the classical impedance-to-reflection-coefficient bilinear
    # transform. Originality is claimed only for the electrochemical reference
    # framework and its descriptors, not for the Smith mapping itself.
    reference = as_complex_reference(z0)
    if not np.isfinite(reference) or reference == 0:
        raise ValueError("Z0 deve ser finito e diferente de zero")
    impedance = np.asarray(z, dtype=complex)
    gamma = np.full(impedance.shape, np.nan + 1j * np.nan, dtype=complex)
    finite = np.isfinite(impedance)
    normalized_z, normalized_reference = _normalize_pair(impedance[finite], reference)
    denominator = normalized_z + normalized_reference
    safe = np.abs(denominator) > np.finfo(float).eps * (
        np.abs(normalized_z) + np.abs(normalized_reference)
    )
    gamma.flat[np.flatnonzero(finite)[safe]] = (
        normalized_z[safe] - normalized_reference[safe]
    ) / denominator[safe]
    return gamma


def inverse_transform_esc(gamma: np.ndarray, z0: Any) -> np.ndarray:
    """Invert the classical Smith transform away from ``gamma == 1``."""
    values = np.asarray(gamma, dtype=complex)
    reference = as_complex_reference(z0)
    denominator = 1.0 - values
    scale = np.maximum(1.0, np.abs(values))
    safe = np.abs(denominator) > np.finfo(float).eps * scale
    impedance = np.full(values.shape, np.nan + 1j * np.nan, dtype=complex)
    impedance[safe] = reference * (1.0 + values[safe]) / denominator[safe]
    return impedance


def _reference_is_positive_real(reference: complex) -> bool:
    return reference.imag == 0.0 and reference.real > 0.0


def _normalize_pair(z: np.ndarray, reference: complex) -> tuple[np.ndarray, np.ndarray]:
    """Scale by the largest component to keep the transform dimensionless."""
    scale = np.maximum(
        np.maximum(np.abs(z.real), np.abs(z.imag)),
        max(abs(reference.real), abs(reference.imag)),
    )
    # Scale components separately so division remains finite for subnormal scales.
    normalized_z = z.real / scale + 1j * (z.imag / scale)
    normalized_reference = reference.real / scale + 1j * (reference.imag / scale)
    return normalized_z, normalized_reference


def _singularity_margin(z: np.ndarray, reference: complex) -> np.ndarray:
    """Dimensionless distance from the pole ``Z == -Z0``."""
    normalized_z, normalized_reference = _normalize_pair(z, reference)
    return np.abs(normalized_z + normalized_reference) / (
        np.abs(normalized_z) + np.abs(normalized_reference)
    )


def _log_frequency_average(values: np.ndarray, frequency: np.ndarray) -> complex:
    """Average over log-frequency, reducing dependence on point density."""
    order = np.argsort(frequency)
    log_frequency = np.log(frequency[order])
    ordered = values[order]
    span = float(log_frequency[-1] - log_frequency[0])
    if span <= np.finfo(float).eps:
        return complex(np.mean(ordered))
    widths = np.diff(log_frequency)
    real = np.sum(0.5 * (ordered.real[1:] + ordered.real[:-1]) * widths) / span
    imag = np.sum(0.5 * (ordered.imag[1:] + ordered.imag[:-1]) * widths) / span
    return complex(real, imag)


def calculate_group(
    z: np.ndarray,
    z0: Any,
    frequency: np.ndarray | None = None,
    passivity_tolerance: float = 1e-10,
) -> dict[str, Any]:
    """Calculate frequency-resolved ESC descriptors for one reference.

    Passivity in the unit disk is assessed only for a positive real reference,
    because then ``1-|Gamma|^2 = 4*Z0*Re(Z)/|Z+Z0|^2``.  A complex reference
    remains a valid coordinate transform but does not retain that diagnostic.
    """
    impedance = np.asarray(z, dtype=complex)
    if impedance.ndim != 1:
        raise ValueError("ESC requer um vetor unidimensional de impedâncias")
    frequencies = None if frequency is None else np.asarray(frequency, dtype=float)
    if frequencies is not None:
        if frequencies.shape != impedance.shape:
            raise ValueError("frequency e z devem ter o mesmo formato")
        if np.any(~np.isfinite(frequencies)) or np.any(frequencies <= 0):
            raise ValueError("frequências ESC devem ser finitas e positivas")

    reference = as_complex_reference(z0)
    gamma = transform_esc(impedance, reference)
    finite = np.isfinite(gamma.real) & np.isfinite(gamma.imag)
    if not np.any(finite):
        raise ValueError("Transformação ESC singular para todos os pontos")
    values = gamma[finite]
    finite_impedance = impedance[finite]
    finite_frequency = frequencies[finite] if frequencies is not None else None
    centroid = [float(np.mean(values.real)), float(np.mean(values.imag))]
    if finite_frequency is None:
        low_frequency_point = values[-1]
        high_frequency_point = values[0]
        log_frequency_centroid = None
        frequency_span_decades = None
    else:
        # Keep gamma aligned with the input for plotting. Use a canonical
        # high-to-low trajectory, with coordinates breaking frequency ties.
        order = np.lexsort((values.imag, values.real, -finite_frequency))
        values = values[order]
        finite_impedance = finite_impedance[order]
        finite_frequency = finite_frequency[order]
        low_frequency_point = values[-1]
        high_frequency_point = values[0]
        weighted = _log_frequency_average(values, finite_frequency)
        log_frequency_centroid = [float(weighted.real), float(weighted.imag)]
        frequency_span_decades = float(
            np.log10(np.max(finite_frequency) / np.min(finite_frequency))
        )

    radii = np.abs(values)
    increments = np.abs(np.diff(values))
    path_length = float(np.sum(increments))
    displacement = float(abs(values[-1] - values[0]))
    tortuosity = path_length / max(displacement, np.finfo(float).eps)
    phase = np.unwrap(np.angle(values))
    finite_input = np.isfinite(impedance)
    margins = _singularity_margin(impedance[finite_input], reference)
    passivity_applicable = _reference_is_positive_real(reference)
    if passivity_applicable:
        inside = radii <= 1.0 + float(passivity_tolerance)
        passive_point_fraction = float(np.mean(inside))
        passivity_violation_count = int(np.count_nonzero(~inside))
        normalized_z, normalized_reference = _normalize_pair(finite_impedance, reference)
        passivity_identity_residual = np.abs(
            (1.0 - radii**2)
            - (4.0 * normalized_reference.real * normalized_z.real)
            / np.abs(normalized_z + normalized_reference) ** 2
        )
        passivity_identity_error_max = float(np.max(passivity_identity_residual))
    else:
        passive_point_fraction = None
        passivity_violation_count = None
        passivity_identity_error_max = None

    flags: list[str] = []
    if centroid[0] > 0.3 and centroid[1] < 0:
        flags.append("capacitive_high_Z")
    if low_frequency_point.real > 0.8:
        flags.append("diffusion_dominated")
    if passivity_applicable and passivity_violation_count:
        flags.append("outside_passive_unit_disk")
    if float(np.min(margins)) < DEFAULT_ABSTENTION_THRESHOLDS["singularity_margin_min"]:
        flags.append("near_transform_singularity")
    return {
        "Z0": float(reference.real) if reference.imag == 0.0 else [float(reference.real), float(reference.imag)],
        "centroid": centroid,
        "log_frequency_centroid": log_frequency_centroid,
        "gamma_mean": float(np.mean(radii)),
        "gamma_std": float(np.std(radii)),
        "gamma_min": float(np.min(radii)),
        "gamma_max": float(np.max(radii)),
        "path_length": path_length,
        "net_displacement": displacement,
        "tortuosity": float(tortuosity),
        "radial_total_variation": float(np.sum(np.abs(np.diff(radii)))),
        "unwrapped_phase_span_rad": float(np.ptp(phase)),
        "hf_point": [float(high_frequency_point.real), float(high_frequency_point.imag)],
        "lf_point": [float(low_frequency_point.real), float(low_frequency_point.imag)],
        "frequency_span_decades": frequency_span_decades,
        "n_points_total": int(impedance.size),
        "n_points_finite": int(values.size),
        "singularity_count": int(impedance.size - values.size),
        "singularity_margin_min": float(np.min(margins)),
        "passivity_applicable": passivity_applicable,
        "passive_point_fraction": passive_point_fraction,
        "passivity_violation_count": passivity_violation_count,
        "passivity_identity_error_max": passivity_identity_error_max,
        "flags": flags,
        "gamma": gamma,
    }


def assess_reference(
    z: np.ndarray,
    z0: Any,
    frequency: np.ndarray | None = None,
    reference_relative_uncertainty: float | None = None,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return an auditable usability/abstention decision for one reference."""
    limits = {**DEFAULT_ABSTENTION_THRESHOLDS, **(thresholds or {})}
    reasons: list[str] = []
    try:
        metrics = calculate_group(z, z0, frequency)
    except (TypeError, ValueError) as error:
        return {"status": "abstained", "usable": False, "reasons": [str(error)], "metrics": None}
    if metrics["n_points_finite"] < int(limits["min_points"]):
        reasons.append("insufficient_finite_points")
    span = metrics["frequency_span_decades"]
    if span is not None and span < float(limits["min_frequency_decades"]):
        reasons.append("insufficient_frequency_span")
    if metrics["singularity_margin_min"] < float(limits["singularity_margin_min"]):
        reasons.append("near_transform_singularity")
    if reference_relative_uncertainty is not None:
        if not np.isfinite(reference_relative_uncertainty) or reference_relative_uncertainty < 0:
            reasons.append("invalid_reference_uncertainty")
        elif reference_relative_uncertainty > float(
            limits["reference_relative_uncertainty_max"]
        ):
            reasons.append("reference_uncertainty_too_large")
    return {
        "status": "abstained" if reasons else "accepted",
        "usable": not reasons,
        "reasons": reasons,
        "metrics": metrics,
    }


def conventional_references(
    z: np.ndarray, frequency: np.ndarray | None = None
) -> dict[str, float]:
    """Return declared comparison references, not mechanistic substitutes.

    The high-frequency-real proxy is emitted only when frequency is supplied;
    otherwise the first finite point is labelled explicitly as an ordering-
    dependent baseline rather than being misrepresented as high frequency.
    """
    impedance = np.asarray(z, dtype=complex)
    mask = np.isfinite(impedance.real) & np.isfinite(impedance.imag)
    finite = impedance[mask]
    if finite.size == 0:
        raise ValueError("nenhuma impedância finita para referências convencionais")
    magnitudes = np.maximum(np.abs(finite), np.finfo(float).eps)
    references = {
        "fixed_50_ohm": 50.0,
        "median_magnitude": float(np.median(magnitudes)),
        "geometric_mean_magnitude": float(np.exp(np.mean(np.log(magnitudes)))),
    }
    if frequency is None:
        references["first_point_real_proxy"] = float(
            finite[0].real if finite[0].real > 0 else magnitudes[0]
        )
    else:
        frequencies = np.asarray(frequency, dtype=float)
        if frequencies.shape != impedance.shape:
            raise ValueError("frequency e z devem ter o mesmo formato")
        finite_frequency = frequencies[mask]
        if np.any(~np.isfinite(finite_frequency)) or np.any(finite_frequency <= 0):
            raise ValueError("frequências de referência devem ser finitas e positivas")
        high_frequency_index = int(np.argmax(finite_frequency))
        high_frequency_value = finite[high_frequency_index]
        references["high_frequency_real_proxy"] = float(
            high_frequency_value.real
            if high_frequency_value.real > 0
            else abs(high_frequency_value)
        )
    return references


def reference_sensitivity(
    z: np.ndarray,
    z0: Any,
    frequency: np.ndarray | None = None,
    factors: np.ndarray | None = None,
) -> dict[str, Any]:
    """Evaluate descriptor changes over pre-specified multiplicative Z0 factors."""
    reference = as_complex_reference(z0)
    tested = np.asarray(
        factors if factors is not None else [0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0],
        dtype=float,
    )
    if np.any(~np.isfinite(tested)) or np.any(tested <= 0):
        raise ValueError("fatores de sensibilidade devem ser positivos e finitos")
    rows = []
    for factor in tested:
        metrics = calculate_group(z, reference * float(factor), frequency)
        rows.append(
            {
                "factor": float(factor),
                "gamma_mean": metrics["gamma_mean"],
                "path_length": metrics["path_length"],
                "tortuosity": metrics["tortuosity"],
                "singularity_margin_min": metrics["singularity_margin_min"],
                "passive_point_fraction": metrics["passive_point_fraction"],
            }
        )
    baseline_index = int(np.argmin(np.abs(tested - 1.0)))
    baseline = rows[baseline_index]
    relative_ranges: dict[str, float] = {}
    for key in ("gamma_mean", "path_length", "tortuosity"):
        values = np.asarray([row[key] for row in rows], dtype=float)
        relative_ranges[key] = float(
            (np.max(values) - np.min(values))
            / max(abs(float(baseline[key])), np.finfo(float).eps)
        )
    return {
        "reference": [float(reference.real), float(reference.imag)],
        "rows": rows,
        "baseline_factor": float(tested[baseline_index]),
        "relative_ranges": relative_ranges,
    }


def reference_uncertainty_monte_carlo(
    z: np.ndarray,
    z0: Any,
    frequency: np.ndarray | None = None,
    relative_standard_uncertainty: float = 0.05,
    draws: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    """Propagate reference uncertainty into selected ESC descriptors.

    Positive real references are sampled lognormally so all draws remain
    positive. Complex references use independent Gaussian perturbations and are
    reported without a passivity interpretation.
    """
    reference = as_complex_reference(z0)
    uncertainty = float(relative_standard_uncertainty)
    if not np.isfinite(uncertainty) or uncertainty < 0:
        raise ValueError("incerteza relativa deve ser finita e não negativa")
    if draws < 20:
        raise ValueError("use ao menos 20 amostras de Monte Carlo")
    rng = np.random.default_rng(seed)
    if _reference_is_positive_real(reference):
        sigma_log = np.sqrt(np.log1p(uncertainty**2))
        sampled = reference.real * np.exp(
            rng.normal(-0.5 * sigma_log**2, sigma_log, size=draws)
        )
        references = sampled.astype(complex)
    else:
        scale = max(abs(reference), np.finfo(float).eps) * uncertainty
        references = reference + rng.normal(0.0, scale, draws) + 1j * rng.normal(
            0.0, scale, draws
        )
        references[references == 0] = reference
    descriptor_names = ("gamma_mean", "path_length", "tortuosity")
    samples = {name: [] for name in descriptor_names}
    for sampled_reference in references:
        metrics = calculate_group(z, sampled_reference, frequency)
        for name in descriptor_names:
            samples[name].append(float(metrics[name]))
    intervals = {}
    for name, values in samples.items():
        array = np.asarray(values)
        intervals[name] = {
            "median": float(np.median(array)),
            "q025": float(np.quantile(array, 0.025)),
            "q975": float(np.quantile(array, 0.975)),
        }
    return {
        "draws": int(draws),
        "seed": int(seed),
        "relative_standard_uncertainty": uncertainty,
        "reference_type": "positive_real" if _reference_is_positive_real(reference) else "complex",
        "intervals": intervals,
    }

