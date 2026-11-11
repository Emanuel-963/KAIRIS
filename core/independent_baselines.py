"""Optional independent scientific baselines used to validate KAIRIS.

The imports are intentionally lazy: normal KAIRIS execution does not require
``impedance`` or ``pyimpspec``. These adapters standardize sign conventions,
metrics and JSON-serializable outputs for the preregistered comparisons.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import redirect_stdout
from importlib import metadata
from io import StringIO
from typing import Any

import numpy as np


def prepare_eis_arrays(
    frequency: Any, real: Any, imag: Any
) -> tuple[np.ndarray, np.ndarray]:
    """Return finite EIS vectors sorted from high to low frequency."""
    f = np.asarray(frequency, dtype=float).reshape(-1)
    re = np.asarray(real, dtype=float).reshape(-1)
    im = np.asarray(imag, dtype=float).reshape(-1)
    if not (f.size == re.size == im.size):
        raise ValueError("frequency, real and imag must have the same length")
    keep = np.isfinite(f) & np.isfinite(re) & np.isfinite(im) & (f > 0)
    f = f[keep]
    z = (re[keep] + 1j * im[keep]).astype(complex)
    if f.size < 3:
        raise ValueError("at least three finite positive-frequency points are required")
    order = np.argsort(f)[::-1]
    return f[order], z[order]


def _normalized_errors(z: np.ndarray, fitted: np.ndarray) -> tuple[np.ndarray, float]:
    scale = np.maximum(np.abs(z), np.finfo(float).eps)
    pointwise_pct = 100.0 * np.abs(z - fitted) / scale
    denominator = max(float(np.mean(np.abs(z) ** 2)), np.finfo(float).eps)
    rmse_pct = 100.0 * float(np.sqrt(np.mean(np.abs(z - fitted) ** 2) / denominator))
    return pointwise_pct, rmse_pct


def _trapz_compatible(y: np.ndarray, x: np.ndarray) -> float:
    """Use the NumPy 1.x API while tolerating releases that removed its alias."""
    trapz = getattr(np, "trapz", None)
    if trapz is not None:
        return float(trapz(y, x=x))
    return float(np.sum((y[1:] + y[:-1]) * np.diff(x) * 0.5))


def _package_version(distribution: str) -> str:
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError:
        return "injected-test-double"


def run_impedance_lin_kk(
    frequency: Any,
    real: Any,
    imag: Any,
    config: dict[str, Any],
    *,
    solver: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run impedance.py Lin-KK with KAIRIS-normalized comparison metrics."""
    f, z = prepare_eis_arrays(frequency, real, imag)
    compatibility_patch = False
    package_solver = solver is None
    if package_solver:
        try:
            from impedance.models.circuits.elements import circuit_elements
            from impedance.validation import linKK
        except ImportError as exc:
            raise RuntimeError(
                "independent Lin-KK requires requirements-validation.txt"
            ) from exc

        # impedance.py 1.7.1 builds an expression containing np.array but its
        # evaluation namespace omits np. Supplying it preserves package logic.
        compatibility_patch = True
        if "np" not in circuit_elements:
            circuit_elements["np"] = np
        solver = linKK

    cutoff = float(config.get("lin_kk_mu_cutoff", 0.85))
    max_m = int(config.get("lin_kk_max_rc_elements", 50))
    add_cap = bool(config.get("lin_kk_add_capacitance", False))
    call_kwargs = {
        "c": cutoff,
        "max_M": max_m,
        "fit_type": "complex",
        "add_cap": add_cap,
    }
    if package_solver:
        # impedance.py prints intermediate RC iterations unconditionally.
        # Keep batch output machine-readable without modifying its equations.
        with redirect_stdout(StringIO()):
            m, mu, fitted, residual_real, residual_imag = solver(f, z, **call_kwargs)
    else:
        m, mu, fitted, residual_real, residual_imag = solver(f, z, **call_kwargs)
    fitted = np.asarray(fitted, dtype=complex)
    if fitted.shape != z.shape:
        raise ValueError("impedance.py returned a fitted spectrum with an invalid shape")
    pointwise_pct, rmse_pct = _normalized_errors(z, fitted)
    point_threshold = float(config.get("lin_kk_point_threshold_pct", 5.0))
    max_failure = float(config.get("lin_kk_max_failure_pct", 10.0))
    rmse_threshold = float(config.get("lin_kk_rmse_threshold_pct", 5.0))
    failure_pct = 100.0 * float(np.mean(pointwise_pct > point_threshold))

    return {
        "implementation": "impedance.validation.linKK",
        "package_version": _package_version("impedance"),
        "parameters": {
            "c": cutoff,
            "max_M": max_m,
            "fit_type": "complex",
            "add_cap": add_cap,
        },
        "compatibility_patch_np_namespace": compatibility_patch,
        "rc_elements": int(m),
        "mu": float(mu),
        "normalized_complex_rmse_pct": rmse_pct,
        "failure_pct": failure_pct,
        "pass": bool(rmse_pct <= rmse_threshold and failure_pct <= max_failure),
        "frequency_hz": f.tolist(),
        "fit_real_ohm": fitted.real.tolist(),
        "fit_imag_ohm": fitted.imag.tolist(),
        "pointwise_residual_pct": pointwise_pct.tolist(),
        "native_residual_real": np.asarray(residual_real, dtype=float).tolist(),
        "native_residual_imag": np.asarray(residual_imag, dtype=float).tolist(),
    }


def run_pyimpspec_tr_nnls(
    frequency: Any,
    real: Any,
    imag: Any,
    *,
    mode: str = "real",
    lambda_value: float = -1.0,
    peak_threshold_fraction: float = 0.05,
    dataset_factory: Callable[..., Any] | None = None,
    solver: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run pyimpspec TR-NNLS and expose common reconstruction/peak metrics."""
    if mode not in {"real", "imaginary"}:
        raise ValueError("mode must be 'real' or 'imaginary'")
    if not 0.0 <= peak_threshold_fraction <= 1.0:
        raise ValueError("peak_threshold_fraction must be between 0 and 1")
    f, z = prepare_eis_arrays(frequency, real, imag)
    if dataset_factory is None or solver is None:
        try:
            from pyimpspec import DataSet
            from pyimpspec.analysis.drt import calculate_drt_tr_nnls
        except ImportError as exc:
            raise RuntimeError(
                "independent DRT requires requirements-validation.txt"
            ) from exc
        dataset_factory = dataset_factory or DataSet
        solver = solver or calculate_drt_tr_nnls

    dataset = dataset_factory(frequencies=f, impedances=z, label="KAIRIS baseline")
    result = solver(dataset, mode=mode, lambda_value=float(lambda_value))
    fitted = np.asarray(result.impedances, dtype=complex)
    if fitted.shape != z.shape:
        raise ValueError("pyimpspec returned a fitted spectrum with an invalid shape")
    pointwise_pct, rmse_pct = _normalized_errors(z, fitted)
    tau = np.asarray(result.time_constants, dtype=float)
    gamma = np.asarray(result.gammas, dtype=float)
    peak_tau, peak_gamma = result.get_peaks(threshold=float(peak_threshold_fraction))
    area = _trapz_compatible(gamma, np.log(tau)) if tau.size > 1 else 0.0

    return {
        "implementation": "pyimpspec.calculate_drt_tr_nnls",
        "package_version": _package_version("pyimpspec"),
        "parameters": {
            "mode": mode,
            "lambda_requested": float(lambda_value),
            "peak_threshold_fraction": float(peak_threshold_fraction),
        },
        "lambda_effective": float(result.lambda_value),
        "pseudo_chisqr": float(result.pseudo_chisqr),
        "normalized_complex_rmse_pct": rmse_pct,
        "integrated_area_log_tau_ohm": area,
        "peak_count": int(len(peak_tau)),
        "peaks": [
            {"tau_s": float(t), "gamma_ohm": float(g)}
            for t, g in zip(peak_tau, peak_gamma, strict=True)
        ],
        "frequency_hz": f.tolist(),
        "fit_real_ohm": fitted.real.tolist(),
        "fit_imag_ohm": fitted.imag.tolist(),
        "pointwise_residual_pct": pointwise_pct.tolist(),
        "tau_s": tau.tolist(),
        "gamma_ohm": gamma.tolist(),
    }
