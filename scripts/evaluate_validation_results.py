"""Evaluate KAIRIS release artifacts against explicit development gates."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.report_builder import to_jsonable  # noqa: E402


DEFAULT_CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"
DEFAULT_OUTPUT = PROJECT / "output" / "validation_corpus"
DEFAULT_ACCEPTANCE = PROJECT / "config" / "validation_acceptance_v1.json"


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=5,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _fraction(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _nearest_tau_error(peaks: list[dict[str, Any]], expected_tau: float) -> float:
    candidates = [float(peak["tau"]) for peak in peaks if float(peak.get("tau", 0)) > 0]
    if not candidates or expected_tau <= 0:
        return math.inf
    return min(abs(math.log10(value / expected_tau)) for value in candidates)


def evaluate(
    corpus: Path,
    output: Path,
    acceptance: dict[str, Any],
    current_commit: str | None = None,
) -> dict[str, Any]:
    """Return descriptive results and pass/fail development gates."""
    manifest = _csv_rows(corpus / "dataset_manifest.csv")
    truth = {
        row["sample_id"]: row for row in _csv_rows(corpus / "synthetic_truth.csv")
    }
    current_commit = current_commit if current_commit is not None else _git_commit()

    found = 0
    reports_found = 0
    hash_matches = 0
    clean_provenance = 0
    current_commit_matches = 0
    commit_counts: Counter[str] = Counter()
    source_stats: dict[str, Counter[str]] = defaultdict(Counter)
    randles: list[dict[str, Any]] = []
    missing: list[str] = []

    for row in manifest:
        sample = row["sample_id"]
        metrics_path = output / "metrics" / f"{sample}_metrics.json"
        report_path = output / "reports" / f"{sample}_report.html"
        if report_path.is_file():
            reports_found += 1
        if not metrics_path.is_file():
            missing.append(sample)
            continue
        found += 1
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        provenance = metrics.get("provenance", {})
        summary = metrics.get("summary", {})
        source = row["source_type"]
        source_stats[source]["total"] += 1
        if summary.get("lin_kk_valid") is True:
            source_stats[source]["lin_kk_valid"] += 1
        rules = metrics.get("interpretation_rules", [])
        disagreement = any("diverg" in str(item).casefold() for item in rules)
        if disagreement:
            source_stats[source]["drt_gsf_disagreement"] += 1

        if provenance.get("input_sha256") == row["sha256"]:
            hash_matches += 1
        if provenance.get("kairis_git_dirty") is False:
            clean_provenance += 1
        recorded_commit = str(provenance.get("kairis_git_commit") or "missing")
        commit_counts[recorded_commit] += 1
        if current_commit and recorded_commit == current_commit:
            current_commit_matches += 1

        truth_row = truth.get(sample)
        if row["family"] != "randles_rc" or truth_row is None:
            continue
        parameters = json.loads(truth_row["generator_parameters_json"])
        agent2 = metrics.get("agents", {}).get("agent2", {})
        expected_rs = float(parameters["Rs_ohm"])
        observed_r_inf = float(agent2["R_inf"])
        expected_tau = float(parameters["Rct_ohm"]) * float(parameters["Cdl_F"])
        randles.append(
            {
                "sample_id": sample,
                "lin_kk_valid": summary.get("lin_kk_valid") is True,
                "single_peak": int(agent2.get("n_peaks", 0)) == 1,
                "r_inf_relative_error": abs(observed_r_inf - expected_rs) / abs(expected_rs),
                "log10_tau_error": _nearest_tau_error(agent2.get("peaks", []), expected_tau),
            }
        )

    total = len(manifest)
    r_inf_errors = [item["r_inf_relative_error"] for item in randles]
    tau_errors = [item["log10_tau_error"] for item in randles]
    measured = {
        "artifact_completeness_fraction": _fraction(min(found, reports_found), total),
        "input_hash_match_fraction": _fraction(hash_matches, total),
        "clean_provenance_fraction": _fraction(clean_provenance, total),
        "current_commit_fraction": _fraction(current_commit_matches, total),
        "randles_lin_kk_pass_fraction": _fraction(
            sum(item["lin_kk_valid"] for item in randles), len(randles)
        ),
        "randles_single_peak_fraction": _fraction(
            sum(item["single_peak"] for item in randles), len(randles)
        ),
        "randles_r_inf_relative_error_median": statistics.median(r_inf_errors)
        if r_inf_errors
        else math.inf,
        "randles_r_inf_relative_error_worst": max(r_inf_errors, default=math.inf),
        "randles_log10_tau_error_median": statistics.median(tau_errors)
        if tau_errors
        else math.inf,
        "randles_log10_tau_error_worst": max(tau_errors, default=math.inf),
    }
    thresholds = acceptance["thresholds"]
    gates = {
        "artifact_completeness": measured["artifact_completeness_fraction"]
        >= thresholds["artifact_completeness_fraction_min"],
        "input_hash_match": measured["input_hash_match_fraction"]
        >= thresholds["input_hash_match_fraction_min"],
        "clean_provenance": measured["clean_provenance_fraction"]
        >= thresholds["clean_provenance_fraction_min"],
        "current_commit": measured["current_commit_fraction"]
        >= thresholds["current_commit_fraction_min"],
        "randles_lin_kk": measured["randles_lin_kk_pass_fraction"]
        >= thresholds["randles_lin_kk_pass_fraction_min"],
        "randles_single_peak": measured["randles_single_peak_fraction"]
        >= thresholds["randles_single_peak_fraction_min"],
        "randles_r_inf_median": measured["randles_r_inf_relative_error_median"]
        <= thresholds["randles_r_inf_relative_error_median_max"],
        "randles_r_inf_worst": measured["randles_r_inf_relative_error_worst"]
        <= thresholds["randles_r_inf_relative_error_worst_max"],
        "randles_tau_median": measured["randles_log10_tau_error_median"]
        <= thresholds["randles_log10_tau_error_median_max"],
        "randles_tau_worst": measured["randles_log10_tau_error_worst"]
        <= thresholds["randles_log10_tau_error_worst_max"],
    }
    return {
        "format": "KAIRIS-validation-evaluation-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "acceptance_status": acceptance.get("status"),
        "confirmatory": False,
        "corpus": str(corpus.resolve()),
        "output": str(output.resolve()),
        "current_git_commit": current_commit,
        "samples_expected": total,
        "metrics_found": found,
        "reports_found": reports_found,
        "missing_samples": missing,
        "recorded_commit_counts": dict(commit_counts),
        "source_descriptive": {
            source: dict(counts) for source, counts in sorted(source_stats.items())
        },
        "randles_reference_samples": randles,
        "measured": measured,
        "thresholds": thresholds,
        "gates": gates,
        "all_development_gates_pass": all(gates.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--acceptance", type=Path, default=DEFAULT_ACCEPTANCE)
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_OUTPUT / "evidence" / "acceptance_report.json",
    )
    parser.add_argument(
        "--enforce",
        action="store_true",
        help="retornar código 2 se algum critério de desenvolvimento falhar",
    )
    args = parser.parse_args()
    acceptance = json.loads(args.acceptance.read_text(encoding="utf-8"))
    result = evaluate(args.corpus.resolve(), args.output.resolve(), acceptance)
    serializable = to_jsonable(result)
    atomic_write_text(
        args.report.resolve(),
        json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    print(json.dumps(serializable, ensure_ascii=False, indent=2, allow_nan=False))
    return 2 if args.enforce and not result["all_development_gates_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
