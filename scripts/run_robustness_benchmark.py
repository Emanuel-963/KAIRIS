"""Run controlled KAIRIS DRT robustness experiments and generate article-ready maps."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import math
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_binary_writer, atomic_write_text  # noqa: E402
from core.config_validator import validate_config  # noqa: E402
from core.drt_solver import assess_r_inf_quality, solve_drt  # noqa: E402
from core.r_inf_estimator import extrapolate_r_inf  # noqa: E402
from core.report_builder import to_jsonable  # noqa: E402
from scripts.analyze_synthetic_recovery import match_relaxation_times  # noqa: E402

DEFAULT_CONFIG = PROJECT / "config" / "protocol_config.json"
DEFAULT_DESTINATION = PROJECT / "output" / "robustness_benchmark_v1"
SEPARATION_DECADES = [0.20, 0.35, 0.50, 0.70, 1.00, 1.30, 1.70, 2.20, 3.00]
NOISE_LEVELS = [0.0, 0.001, 0.003, 0.01, 0.03, 0.05, 0.10]
FREQUENCY_MAX_LEVELS = [1e3, 3e3, 1e4, 3e4, 1e5, 3e5, 1e6, 3e6, 1e7, 3e7]
EXTRAPOLATION_FREQUENCY_MAX_LEVELS = [300.0, 1e3, 3e3, 1e4, 3e4, 1e5, 3e5]
Solver = Callable[[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]], dict[str, Any]]


def _provenance(config: dict[str, Any]) -> dict[str, Any]:
    sensitive = ("api_key", "apikey", "token", "password", "secret")

    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: clean(item)
                for key, item in value.items()
                if not any(fragment in key.casefold() for fragment in sensitive)
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        return copy.deepcopy(value)

    packages: dict[str, str] = {}
    for package in ("numpy", "scipy", "pandas", "matplotlib"):
        try:
            packages[package] = version(package)
        except PackageNotFoundError:
            packages[package] = "not-installed"
    git_commit = None
    git_dirty = None
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True,
            stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
        git_dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=PROJECT, text=True, stderr=subprocess.DEVNULL, timeout=5,
            ).strip()
        )
    except (OSError, subprocess.SubprocessError):
        pass
    script = Path(__file__).resolve()
    return {
        "execution_timestamp": datetime.now().astimezone().isoformat(),
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "package_versions": packages,
        "kairis_git_commit": git_commit,
        "kairis_git_dirty": git_dirty,
        "effective_config": clean(config),
    }


def zarc_from_tau(
    omega: np.ndarray, resistance: float, tau_s: float, exponent: float
) -> np.ndarray:
    """Return a ZARC whose -Im(Z) maximum is at omega=1/tau_s."""
    q = tau_s**exponent / resistance
    return 1.0 / (1.0 / resistance + q * (1j * omega) ** exponent)


def add_complex_noise(
    impedance: np.ndarray, relative_noise: float, rng: np.random.Generator
) -> np.ndarray:
    """Apply independent heteroscedastic Gaussian noise to Re(Z) and Im(Z)."""
    if relative_noise <= 0:
        return impedance.copy()
    scale = relative_noise * np.maximum(
        np.abs(impedance), np.median(np.abs(impedance)) * 0.1
    )
    return impedance + rng.normal(size=impedance.size) * scale + 1j * rng.normal(
        size=impedance.size
    ) * scale


def _wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> list[float]:
    if total <= 0:
        return [0.0, 0.0]
    proportion = successes / total
    denominator = 1.0 + z * z / total
    centre = (proportion + z * z / (2.0 * total)) / denominator
    half = z * math.sqrt(
        proportion * (1.0 - proportion) / total + z * z / (4.0 * total**2)
    ) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def _aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[float, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[float(record["level"])].append(record)
    summary: list[dict[str, Any]] = []
    for level, rows in sorted(grouped.items()):
        tau_errors = [float(row["median_log10_tau_error"]) for row in rows]
        rinf_errors = [float(row["r_inf_relative_error"]) for row in rows]
        recovered = sum(bool(row["recovered"]) for row in rows)
        exact = sum(bool(row["exact_peak_count"]) for row in rows)
        reliable = sum(bool(row["r_inf_reliable"]) for row in rows)
        extrapolated = sum(bool(row.get("r_inf_extrapolation_accepted")) for row in rows)
        extrapolation_errors = [
            float(row["r_inf_extrapolation_error"])
            for row in rows
            if row.get("r_inf_extrapolation_error") is not None
            and math.isfinite(float(row["r_inf_extrapolation_error"]))
        ]
        summary.append(
            {
                "level": level,
                "replicates": len(rows),
                "recovery_fraction": recovered / len(rows),
                "recovery_wilson_ci95": _wilson_interval(recovered, len(rows)),
                "exact_peak_count_fraction": exact / len(rows),
                "r_inf_reliable_fraction": reliable / len(rows),
                "r_inf_extrapolation_accepted_fraction": extrapolated / len(rows),
                "r_inf_extrapolation_error_median": statistics.median(extrapolation_errors)
                if extrapolation_errors
                else None,
                "tau_error_median": statistics.median(tau_errors),
                "tau_error_q25_q75": [
                    float(value) for value in np.quantile(tau_errors, [0.25, 0.75])
                ],
                "r_inf_error_median": statistics.median(rinf_errors),
                "r_inf_error_q25_q75": [
                    float(value) for value in np.quantile(rinf_errors, [0.25, 0.75])
                ],
            }
        )
    return summary


def run_benchmark(
    config: dict[str, Any],
    replicates: int = 5,
    seed: int = 20261102,
    solver: Solver = solve_drt,
) -> dict[str, Any]:
    """Execute the three pre-specified robustness experiments."""
    if replicates < 1:
        raise ValueError("replicates must be at least 1")
    started = time.perf_counter()
    rng = np.random.default_rng(seed)
    records: list[dict[str, Any]] = []
    tau_tolerance = 0.20
    frequency = np.logspace(6, -3, 121)
    omega = 2.0 * np.pi * frequency

    # Two equal-amplitude ZARCs with controlled log-time separation.
    centre_tau = 1e-2
    for separation in SEPARATION_DECADES:
        ratio = 10.0**separation
        expected = [centre_tau / math.sqrt(ratio), centre_tau * math.sqrt(ratio)]
        clean = 0.2 + zarc_from_tau(omega, 5.0, expected[0], 0.90) + zarc_from_tau(
            omega, 5.0, expected[1], 0.90
        )
        for replicate in range(replicates):
            impedance = add_complex_noise(clean, 0.003, rng)
            result = solver(frequency, impedance.real, impedance.imag, config)
            quality = assess_r_inf_quality(frequency, impedance.real, impedance.imag, config)
            observed = [float(peak["tau"]) for peak in result.get("peaks", [])]
            matches = match_relaxation_times(expected, observed)
            errors = [float(item["absolute_log10_error"]) for item in matches]
            records.append(
                {
                    "experiment": "process_separation",
                    "level": separation,
                    "replicate": replicate + 1,
                    "expected_processes": 2,
                    "observed_peaks": len(observed),
                    "recovered": len(matches) == 2
                    and max(errors, default=math.inf) <= tau_tolerance,
                    "exact_peak_count": len(observed) == 2,
                    "median_log10_tau_error": statistics.median(errors)
                    if errors
                    else math.inf,
                    "r_inf_relative_error": abs(float(result["R_inf"]) - 0.2) / 0.2,
                    "r_inf_reliable": quality["R_inf_reliable"],
                    "r_inf_quality_score": quality["R_inf_quality_score"],
                }
            )

    # One ZARC with increasing noise.
    expected_tau = 1e-2
    clean = 0.2 + zarc_from_tau(omega, 8.0, expected_tau, 0.85)
    for noise in NOISE_LEVELS:
        for replicate in range(replicates):
            impedance = add_complex_noise(clean, noise, rng)
            result = solver(frequency, impedance.real, impedance.imag, config)
            quality = assess_r_inf_quality(frequency, impedance.real, impedance.imag, config)
            observed = [float(peak["tau"]) for peak in result.get("peaks", [])]
            matches = match_relaxation_times([expected_tau], observed)
            error = float(matches[0]["absolute_log10_error"]) if matches else math.inf
            records.append(
                {
                    "experiment": "noise_sensitivity",
                    "level": noise,
                    "replicate": replicate + 1,
                    "expected_processes": 1,
                    "observed_peaks": len(observed),
                    "recovered": bool(matches) and error <= tau_tolerance,
                    "exact_peak_count": len(observed) == 1,
                    "median_log10_tau_error": error,
                    "r_inf_relative_error": abs(float(result["R_inf"]) - 0.2) / 0.2,
                    "r_inf_reliable": quality["R_inf_reliable"],
                    "r_inf_quality_score": quality["R_inf_quality_score"],
                }
            )

    # High-frequency truncation. The current solver defines R_inf as Re(Z[f_max]);
    # therefore the inverse solve cannot change this endpoint.
    for frequency_max in FREQUENCY_MAX_LEVELS:
        local_frequency = np.logspace(math.log10(frequency_max), -2, 101)
        local_omega = 2.0 * np.pi * local_frequency
        clean = (
            0.2
            + zarc_from_tau(local_omega, 1.5, 1.0 / (2.0 * np.pi * 2e4), 0.83)
            + zarc_from_tau(local_omega, 4.0, 1.0 / (2.0 * np.pi * 120.0), 0.78)
            + zarc_from_tau(local_omega, 8.0, 1.0 / (2.0 * np.pi * 0.18), 0.73)
        )
        for replicate in range(replicates):
            impedance = add_complex_noise(clean, 0.003, rng)
            observed_rinf = float(impedance.real[0])
            relative_error = abs(observed_rinf - 0.2) / 0.2
            quality = assess_r_inf_quality(
                local_frequency, impedance.real, impedance.imag, config
            )
            extrapolation = extrapolate_r_inf(
                local_frequency, impedance.real, impedance.imag, config
            )
            extrapolated_candidate = extrapolation.get("R_inf_extrapolation_candidate")
            records.append(
                {
                    "experiment": "high_frequency_truncation",
                    "level": frequency_max,
                    "replicate": replicate + 1,
                    "expected_processes": 3,
                    "observed_peaks": None,
                    "recovered": relative_error <= 0.05,
                    "exact_peak_count": False,
                    "median_log10_tau_error": 0.0,
                    "r_inf_relative_error": relative_error,
                    "r_inf_reliable": quality["R_inf_reliable"],
                    "r_inf_quality_score": quality["R_inf_quality_score"],
                    "r_inf_extrapolation_accepted": extrapolation["R_inf_extrapolation_status"]
                    == "accepted",
                    "r_inf_extrapolation_error": abs(extrapolated_candidate - 0.2) / 0.2
                    if extrapolated_candidate is not None
                    else None,
                }
            )

    # Secondary extrapolation on a single asymptotic CPE tail. This experiment
    # measures the method's own operating domain; it does not alter primary R_inf.
    for frequency_max in EXTRAPOLATION_FREQUENCY_MAX_LEVELS:
        local_frequency = np.logspace(math.log10(frequency_max), -2, 101)
        local_omega = 2.0 * np.pi * local_frequency
        clean = 0.2 + zarc_from_tau(local_omega, 8.0, 1e-2, 0.85)
        for replicate in range(replicates):
            impedance = add_complex_noise(clean, 0.003, rng)
            quality = assess_r_inf_quality(
                local_frequency, impedance.real, impedance.imag, config
            )
            extrapolation = extrapolate_r_inf(
                local_frequency, impedance.real, impedance.imag, config
            )
            candidate = extrapolation.get("R_inf_extrapolation_candidate")
            direct_error = abs(float(impedance.real[0]) - 0.2) / 0.2
            extrapolation_error = (
                abs(float(candidate) - 0.2) / 0.2 if candidate is not None else None
            )
            records.append(
                {
                    "experiment": "r_inf_extrapolation_single_zarc",
                    "level": frequency_max,
                    "replicate": replicate + 1,
                    "expected_processes": 1,
                    "observed_peaks": None,
                    "recovered": direct_error <= 0.05,
                    "exact_peak_count": False,
                    "median_log10_tau_error": 0.0,
                    "r_inf_relative_error": direct_error,
                    "r_inf_reliable": quality["R_inf_reliable"],
                    "r_inf_quality_score": quality["R_inf_quality_score"],
                    "r_inf_extrapolation_accepted": extrapolation["R_inf_extrapolation_status"]
                    == "accepted",
                    "r_inf_extrapolation_error": extrapolation_error,
                }
            )

    names = (
        "process_separation",
        "noise_sensitivity",
        "high_frequency_truncation",
        "r_inf_extrapolation_single_zarc",
    )
    summaries = {
        name: _aggregate([row for row in records if row["experiment"] == name])
        for name in names
    }
    truncation_rows = [
        row for row in records if row["experiment"] == "high_frequency_truncation"
    ]
    true_positive = sum(
        row["r_inf_reliable"] and row["r_inf_relative_error"] <= 0.05
        for row in truncation_rows
    )
    false_positive = sum(
        row["r_inf_reliable"] and row["r_inf_relative_error"] > 0.05
        for row in truncation_rows
    )
    true_negative = sum(
        not row["r_inf_reliable"] and row["r_inf_relative_error"] > 0.05
        for row in truncation_rows
    )
    false_negative = sum(
        not row["r_inf_reliable"] and row["r_inf_relative_error"] <= 0.05
        for row in truncation_rows
    )
    calibration = {
        "truth_definition": "absolute relative R_inf error <= 0.05",
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "sensitivity": true_positive / max(true_positive + false_negative, 1),
        "specificity": true_negative / max(true_negative + false_positive, 1),
        "positive_predictive_value": true_positive / max(true_positive + false_positive, 1),
        "negative_predictive_value": true_negative / max(true_negative + false_negative, 1),
    }
    extrapolation_rows = [
        row for row in records if row["experiment"] == "r_inf_extrapolation_single_zarc"
    ]
    extrapolation_tp = sum(
        row["r_inf_extrapolation_accepted"]
        and row["r_inf_extrapolation_error"] is not None
        and row["r_inf_extrapolation_error"] <= 0.05
        for row in extrapolation_rows
    )
    extrapolation_fp = sum(
        row["r_inf_extrapolation_accepted"]
        and row["r_inf_extrapolation_error"] is not None
        and row["r_inf_extrapolation_error"] > 0.05
        for row in extrapolation_rows
    )
    extrapolation_rejected = len(extrapolation_rows) - extrapolation_tp - extrapolation_fp
    extrapolation_calibration = {
        "truth_definition": "accepted extrapolation has absolute relative error <= 0.05",
        "accepted_accurate": extrapolation_tp,
        "accepted_inaccurate": extrapolation_fp,
        "rejected": extrapolation_rejected,
        "positive_predictive_value": extrapolation_tp
        / max(extrapolation_tp + extrapolation_fp, 1),
    }
    return {
        "format": "KAIRIS-robustness-benchmark-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confirmatory": False,
        "analysis_scope": "controlled retrospective sensitivity study",
        "seed": seed,
        "replicates_per_level": replicates,
        "tau_recovery_tolerance_log10_decades": tau_tolerance,
        "model": {
            "process_separation": "two equal-amplitude ZARCs; n=0.90; 0.3% noise",
            "noise_sensitivity": "one ZARC; n=0.85",
            "high_frequency_truncation": "three ZARCs at 20 kHz, 120 Hz and 0.18 Hz; 0.3% noise",
            "r_inf_extrapolation_single_zarc": "single ZARC; n=0.85; 0.3% noise",
        },
        "provenance": _provenance(config),
        "elapsed_seconds": time.perf_counter() - started,
        "summary": summaries,
        "r_inf_indicator_calibration": calibration,
        "r_inf_extrapolation_calibration": extrapolation_calibration,
        "records": records,
    }


def _write_figure(result: dict[str, Any], path: Path) -> None:
    summaries = result["summary"]
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.2), constrained_layout=True)
    separation = summaries["process_separation"]
    x = np.array([row["level"] for row in separation])
    y = np.array([row["recovery_fraction"] for row in separation])
    lower = np.array([row["recovery_wilson_ci95"][0] for row in separation])
    upper = np.array([row["recovery_wilson_ci95"][1] for row in separation])
    axes[0].plot(x, y, "o-", color="#1f77b4")
    exact = np.array([row["exact_peak_count_fraction"] for row in separation])
    axes[0].plot(x, exact, "s--", color="#756bb1", label="contagem exata")
    axes[0].fill_between(x, lower, upper, alpha=0.18, color="#1f77b4")
    axes[0].axhline(0.8, ls="--", lw=0.9, color="#666")
    axes[0].set(
        xlabel="Separação entre τ (décadas)", ylabel="Fração recuperada",
        ylim=(-0.03, 1.03), title="Resolução de dois processos",
    )
    axes[0].legend(frameon=False, fontsize=8)
    noise = summaries["noise_sensitivity"]
    x = np.array([row["level"] for row in noise])
    x_plot = np.where(x == 0, 1e-5, x)
    median = np.array([row["tau_error_median"] for row in noise])
    q25 = np.array([row["tau_error_q25_q75"][0] for row in noise])
    q75 = np.array([row["tau_error_q25_q75"][1] for row in noise])
    axes[1].plot(x_plot, median, "o-", color="#d95f02")
    axes[1].fill_between(x_plot, q25, q75, alpha=0.18, color="#d95f02")
    axes[1].axhline(
        result["tau_recovery_tolerance_log10_decades"], ls="--", lw=0.9, color="#666"
    )
    axes[1].set_xscale("log")
    axes[1].set(
        xlabel="Ruído relativo", ylabel="Erro |log10(τobs/τref)|",
        title="Sensibilidade de τ ao ruído",
    )
    truncation = summaries["high_frequency_truncation"]
    x = np.array([row["level"] for row in truncation])
    median = np.array([row["r_inf_error_median"] for row in truncation])
    q25 = np.array([row["r_inf_error_q25_q75"][0] for row in truncation])
    q75 = np.array([row["r_inf_error_q25_q75"][1] for row in truncation])
    axes[2].plot(x, median, "o-", color="#1b9e77")
    axes[2].fill_between(x, q25, q75, alpha=0.18, color="#1b9e77")
    axes[2].axhline(0.05, ls="--", lw=0.9, color="#666")
    axes[2].set_xscale("log")
    axes[2].set_yscale("log")
    axes[2].set(
        xlabel="Frequência máxima (Hz)", ylabel="Erro relativo de R∞",
        title="Truncamento em alta frequência",
    )
    reliability_axis = axes[2].twinx()
    reliability_axis.plot(
        x,
        [row["r_inf_reliable_fraction"] for row in truncation],
        "s--",
        color="#756bb1",
        label="R∞ aceito",
    )
    reliability_axis.set(ylabel="Fração aceita", ylim=(-0.03, 1.03))
    fig.suptitle("KAIRIS — benchmark retrospectivo de robustez")
    with atomic_binary_writer(path) as handle:
        fig.savefig(handle, format="svg", metadata={"Title": "KAIRIS robustness benchmark v1"})
    plt.close(fig)


def _write_extrapolation_figure(result: dict[str, Any], path: Path) -> None:
    rows = result["summary"]["r_inf_extrapolation_single_zarc"]
    x = np.array([row["level"] for row in rows])
    direct = np.array([row["r_inf_error_median"] for row in rows])
    extrapolated = np.array(
        [
            row["r_inf_extrapolation_error_median"]
            if row["r_inf_extrapolation_error_median"] is not None
            else np.nan
            for row in rows
        ]
    )
    accepted = np.array([row["r_inf_extrapolation_accepted_fraction"] for row in rows])
    fig, axis = plt.subplots(figsize=(7.6, 4.6), constrained_layout=True)
    axis.plot(x, direct, "o-", label="medição na borda", color="#1b9e77")
    axis.plot(x, extrapolated, "s-", label="extrapolação candidata", color="#d95f02")
    axis.axhline(0.05, ls="--", color="#666", lw=0.9, label="erro de 5%")
    axis.set_xscale("log")
    axis.set_yscale("log")
    axis.set(
        xlabel="Frequência máxima (Hz)",
        ylabel="Erro relativo mediano de R∞",
        title="KAIRIS — extrapolação secundária de R∞",
    )
    second = axis.twinx()
    second.plot(x, accepted, "^--", color="#756bb1", label="fração aceita")
    second.set(ylabel="Fração de extrapolações aceitas", ylim=(-0.03, 1.03))
    handles, labels = axis.get_legend_handles_labels()
    handles2, labels2 = second.get_legend_handles_labels()
    axis.legend(handles + handles2, labels + labels2, frameon=False, fontsize=8)
    with atomic_binary_writer(path) as handle:
        fig.savefig(
            handle,
            format="svg",
            metadata={"Title": "KAIRIS secondary R_inf extrapolation benchmark"},
        )
    plt.close(fig)


def write_outputs(result: dict[str, Any], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    serializable = to_jsonable(result)
    atomic_write_text(
        destination / "robustness_benchmark.json",
        json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    fields = [
        "experiment", "level", "replicate", "expected_processes", "observed_peaks",
        "recovered", "exact_peak_count", "median_log10_tau_error", "r_inf_relative_error",
        "r_inf_reliable", "r_inf_quality_score",
        "r_inf_extrapolation_accepted", "r_inf_extrapolation_error",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows({field: row.get(field) for field in fields} for row in result["records"])
    atomic_write_text(destination / "robustness_records.csv", stream.getvalue())
    _write_figure(result, destination / "robustness_maps.svg")
    _write_extrapolation_figure(result, destination / "r_inf_extrapolation_map.svg")
    separation = result["summary"]["process_separation"]
    stable = [row["level"] for row in separation if row["recovery_fraction"] >= 0.8]
    exact = [row["level"] for row in separation if row["exact_peak_count_fraction"] >= 0.8]
    truncation = result["summary"]["high_frequency_truncation"]
    adequate = [row["level"] for row in truncation if row["r_inf_error_median"] <= 0.05]
    noise = result["summary"]["noise_sensitivity"]
    robust_noise = [row["level"] for row in noise if row["recovery_fraction"] >= 0.8]
    calibration = result["r_inf_indicator_calibration"]
    extrapolation = result["r_inf_extrapolation_calibration"]
    lines = [
        "# KAIRIS — benchmark retrospectivo de robustez", "",
        "> Estudo de sensibilidade de desenvolvimento; não confirmatório.", "",
        f"- Réplicas por nível: {result['replicates_per_level']}",
        f"- Tempo de execução: {result['elapsed_seconds']:.1f} s",
        (f"- Menor separação testada com recuperação ≥80%: {min(stable):.2f} décadas"
         if stable else "- Nenhuma separação atingiu recuperação ≥80%."),
        (f"- Menor separação testada com contagem exata ≥80%: {min(exact):.2f} décadas"
         if exact else "- Nenhuma separação atingiu contagem exata ≥80%."),
        (f"- Maior ruído testado com recuperação ≥80%: {max(robust_noise):.1%}"
         if robust_noise else "- Nenhum nível de ruído atingiu recuperação ≥80%."),
        (f"- Menor fmax testado com erro mediano de R∞ ≤5%: {min(adequate):.0f} Hz"
         if adequate else "- Nenhum fmax atingiu erro mediano de R∞ ≤5%."),
        f"- Indicador R∞ — sensibilidade: {calibration['sensitivity']:.1%}",
        f"- Indicador R∞ — especificidade: {calibration['specificity']:.1%}",
        f"- Indicador R∞ — valor preditivo positivo: {calibration['positive_predictive_value']:.1%}",
        f"- Extrapolação secundária — valor preditivo positivo: {extrapolation['positive_predictive_value']:.1%}",
        f"- Extrapolação secundária — aceitações incorretas: {extrapolation['accepted_inaccurate']}",
        "",
        "Os limiares descrevem este modelo controlado e não devem ser generalizados "
        "para todos os sistemas eletroquímicos.", "",
    ]
    atomic_write_text(destination / "robustness_summary.md", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261102)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    validate_config(config)
    result = run_benchmark(config, replicates=args.replicates, seed=args.seed)
    write_outputs(result, args.destination.resolve())
    print(json.dumps(to_jsonable(result["summary"]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
