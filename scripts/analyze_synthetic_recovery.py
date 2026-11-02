"""Quantify retrospective KAIRIS recovery of identifiable synthetic parameters."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations, permutations
from pathlib import Path
from typing import Any

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.report_builder import to_jsonable  # noqa: E402


DEFAULT_CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"
DEFAULT_OUTPUT = PROJECT / "output" / "validation_release_05b85d1"
IDENTIFIABLE_FAMILIES = {"randles_rc", "zarc_cpe", "double_zarc", "triple_zarc"}


def expected_relaxation_times(family: str, parameters: dict[str, Any]) -> list[float]:
    """Return analytically defined RC/ZARC characteristic times in seconds."""
    if family == "randles_rc":
        return [float(parameters["Rct_ohm"]) * float(parameters["Cdl_F"])]
    if family == "zarc_cpe":
        exponent = float(parameters["n"])
        return [(float(parameters["Rct_ohm"]) * float(parameters["Q"])) ** (1.0 / exponent)]
    if family == "double_zarc":
        return [
            (float(parameters["R1_ohm"]) * float(parameters["Q1"]))
            ** (1.0 / float(parameters.get("n1", 0.90))),
            (float(parameters["R2_ohm"]) * float(parameters["Q2"]))
            ** (1.0 / float(parameters.get("n2", 0.78))),
        ]
    if family == "triple_zarc":
        return [
            (float(parameters[f"R{index}_ohm"]) * float(parameters[f"Q{index}"]))
            ** (1.0 / float(parameters.get(f"n{index}", 0.88 - 0.05 * index)))
            for index in range(1, 4)
        ]
    return []


def match_relaxation_times(expected: list[float], observed: list[float]) -> list[dict[str, float]]:
    """Find the one-to-one assignment with minimum total log10 time error."""
    expected = [float(value) for value in expected if float(value) > 0]
    observed = [float(value) for value in observed if float(value) > 0]
    count = min(len(expected), len(observed))
    if count == 0:
        return []
    best: tuple[float, tuple[int, ...], tuple[int, ...]] | None = None
    for expected_indices in combinations(range(len(expected)), count):
        for observed_indices in permutations(range(len(observed)), count):
            score = sum(
                abs(math.log10(observed[oi] / expected[ei]))
                for ei, oi in zip(expected_indices, observed_indices)
            )
            candidate = (score, expected_indices, observed_indices)
            if best is None or candidate[0] < best[0]:
                best = candidate
    assert best is not None
    return [
        {
            "expected_tau_s": expected[ei],
            "observed_tau_s": observed[oi],
            "absolute_log10_error": abs(math.log10(observed[oi] / expected[ei])),
        }
        for ei, oi in zip(best[1], best[2])
    ]


def _bootstrap_median_ci(values: list[float], seed: int, draws: int = 5000) -> list[float] | None:
    if not values:
        return None
    data = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    samples = rng.choice(data, size=(draws, data.size), replace=True)
    medians = np.median(samples, axis=1)
    return [float(value) for value in np.quantile(medians, [0.025, 0.975])]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def analyze(corpus: Path, output: Path, seed: int = 20261102) -> dict[str, Any]:
    truth = _read_csv(corpus / "synthetic_truth.csv")
    samples: list[dict[str, Any]] = []
    excluded: dict[str, int] = defaultdict(int)
    for row in truth:
        family = row["family"]
        if family not in IDENTIFIABLE_FAMILIES:
            excluded[family] += 1
            continue
        metrics_path = output / "metrics" / f"{row['sample_id']}_metrics.json"
        if not metrics_path.is_file():
            samples.append({"sample_id": row["sample_id"], "family": family, "missing": True})
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        agent2 = metrics.get("agents", {}).get("agent2", {})
        parameters = json.loads(row["generator_parameters_json"])
        expected = expected_relaxation_times(family, parameters)
        observed = [float(item["tau"]) for item in agent2.get("peaks", [])]
        matches = match_relaxation_times(expected, observed)
        errors = [item["absolute_log10_error"] for item in matches]
        expected_rs = float(parameters["Rs_ohm"])
        observed_r_inf = float(agent2["R_inf"])
        samples.append(
            {
                "sample_id": row["sample_id"],
                "family": family,
                "missing": False,
                "expected_process_count": len(expected),
                "observed_peak_count": len(observed),
                "peak_count_error": len(observed) - len(expected),
                "matched_fraction": len(matches) / len(expected),
                "r_inf_relative_error": abs(observed_r_inf - expected_rs) / abs(expected_rs),
                "median_log10_tau_error": statistics.median(errors) if errors else None,
                "worst_log10_tau_error": max(errors) if errors else None,
                "matches": matches,
            }
        )

    groups: dict[str, Any] = {}
    for family in sorted(IDENTIFIABLE_FAMILIES):
        rows = [item for item in samples if item["family"] == family and not item["missing"]]
        r_inf = [item["r_inf_relative_error"] for item in rows]
        tau = [item["median_log10_tau_error"] for item in rows if item["median_log10_tau_error"] is not None]
        groups[family] = {
            "sample_count": len(rows),
            "exact_peak_count_fraction": sum(item["peak_count_error"] == 0 for item in rows) / len(rows)
            if rows
            else 0.0,
            "mean_matched_fraction": statistics.mean(item["matched_fraction"] for item in rows)
            if rows
            else 0.0,
            "r_inf_relative_error_median": statistics.median(r_inf) if r_inf else None,
            "r_inf_relative_error_median_ci95_bootstrap": _bootstrap_median_ci(r_inf, seed + 11),
            "log10_tau_error_median": statistics.median(tau) if tau else None,
            "log10_tau_error_median_ci95_bootstrap": _bootstrap_median_ci(tau, seed + 29),
        }

    return {
        "format": "KAIRIS-synthetic-recovery-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "confirmatory": False,
        "analysis_scope": "retrospective development corpus",
        "matching_metric": "minimum one-to-one absolute log10(tau_observed/tau_expected)",
        "bootstrap": {"seed": seed, "draws": 5000, "confidence_level": 0.95},
        "identifiable_families": sorted(IDENTIFIABLE_FAMILIES),
        "excluded_from_parameter_recovery": dict(sorted(excluded.items())),
        "exclusion_rationale": (
            "Distributed, diffusion, inductive, drift and outlier families do not define a unique "
            "one-to-one DRT peak truth; they remain descriptive and enter blinded expert review."
        ),
        "family_summary": groups,
        "samples": samples,
    }


def write_outputs(result: dict[str, Any], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    serializable = to_jsonable(result)
    atomic_write_text(
        destination / "synthetic_recovery_report.json",
        json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    fields = [
        "sample_id", "family", "missing", "expected_process_count", "observed_peak_count",
        "peak_count_error", "matched_fraction", "r_inf_relative_error",
        "median_log10_tau_error", "worst_log10_tau_error",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for item in result["samples"]:
        writer.writerow({field: item.get(field) for field in fields})
    atomic_write_text(destination / "synthetic_recovery_samples.csv", stream.getvalue())
    lines = [
        "# KAIRIS — recuperação sintética retrospectiva",
        "",
        "> Análise de desenvolvimento, não confirmatória. Intervalos são IC 95% por bootstrap.",
        "",
        "| Família | n | picos exatos | processos pareados | mediana erro R∞ | mediana erro log10(τ) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for family, values in result["family_summary"].items():
        lines.append(
            f"| {family} | {values['sample_count']} | {values['exact_peak_count_fraction']:.1%} | "
            f"{values['mean_matched_fraction']:.1%} | "
            f"{values['r_inf_relative_error_median']:.4f} | "
            f"{values['log10_tau_error_median']:.4f} |"
        )
    lines += [
        "",
        "Famílias distribuídas, difusivas, indutivas, com deriva ou outliers foram excluídas da "
        "recuperação paramétrica porque não possuem verdade única de picos DRT.",
        "",
    ]
    atomic_write_text(destination / "synthetic_recovery_summary.md", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--seed", type=int, default=20261102)
    args = parser.parse_args()
    destination = args.destination or args.output / "evidence"
    result = analyze(args.corpus.resolve(), args.output.resolve(), args.seed)
    write_outputs(result, destination.resolve())
    print(json.dumps(to_jsonable(result["family_summary"]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
