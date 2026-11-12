"""Apply the frozen KAIRIS confirmatory mapping after reviews and outputs lock."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.confirmatory_metrics import (  # noqa: E402
    classification_metrics,
    derive_kairis_response,
    grouped_bootstrap_intervals,
    human_consensus,
)
from core.report_builder import to_jsonable  # noqa: E402


def _rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id or case_id in indexed:
            raise ValueError(f"Missing or duplicate case_id in {path}: {case_id!r}")
        indexed[case_id] = row
    return indexed


def evaluate_integrity(output: Path, cohort_root: Path) -> dict[str, Any]:
    with (cohort_root / "prepared_blind" / "blind_manifest.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        source_rows = list(csv.DictReader(handle))
    expected = {row["case_id"]: row for row in source_rows}
    run_path = output / "external_run_manifest.json"
    run = json.loads(run_path.read_text(encoding="utf-8")) if run_path.is_file() else {}
    run_cases = {row.get("case_id"): row for row in run.get("cases", []) if row.get("case_id")}
    completed = [case_id for case_id, row in run_cases.items() if row.get("status") == "completed"]
    silent = sorted(set(expected) - set(run_cases))
    partial_count = 0
    artifact_ok = 0
    hash_ok = 0
    provenance_ok = 0
    for case_id in completed:
        metrics_path = output / "metrics" / f"{case_id}_metrics.json"
        report_path = output / "reports" / f"{case_id}_report.html"
        metrics_exists, report_exists = metrics_path.is_file(), report_path.is_file()
        if metrics_exists != report_exists:
            partial_count += 1
        if not (metrics_exists and report_exists):
            continue
        artifact_ok += 1
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        provenance = metrics.get("provenance") or {}
        if provenance:
            provenance_ok += 1
        if provenance.get("input_sha256") == expected.get(case_id, {}).get("sha256"):
            hash_ok += 1
    expected_count = len(expected)
    completed_count = len(completed)
    fraction = lambda numerator, denominator: numerator / denominator if denominator else 0.0
    observed = {
        "all_cases_accounted_fraction": fraction(len(set(expected) & set(run_cases)), expected_count),
        "pipeline_completion_fraction": fraction(completed_count, expected_count),
        "completed_case_artifact_fraction": fraction(artifact_ok, completed_count),
        "completed_case_input_hash_match_fraction": fraction(hash_ok, completed_count),
        "completed_case_provenance_fraction": fraction(provenance_ok, completed_count),
        "partial_artifact_count": partial_count,
        "silent_failure_count": len(silent),
    }
    thresholds = {
        "all_cases_accounted_fraction": 1.0,
        "pipeline_completion_fraction": 1.0,
        "completed_case_artifact_fraction": 1.0,
        "completed_case_input_hash_match_fraction": 1.0,
        "completed_case_provenance_fraction": 1.0,
        "partial_artifact_count": 0,
        "silent_failure_count": 0,
    }
    passed = all(
        observed[key] >= value if key.endswith("fraction") else observed[key] <= value
        for key, value in thresholds.items()
    )
    return {
        "passed": passed,
        "observed": observed,
        "thresholds": thresholds,
        "completed_cases": completed_count,
        "failed_cases": sorted(case_id for case_id, row in run_cases.items() if row.get("status") == "failed"),
        "silent_case_ids": silent,
    }


def analyze(
    output: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    mapping_path: Path,
    cohort_root: Path,
    *,
    draws: int = 2000,
    seed: int = 20261105,
) -> dict[str, Any]:
    reviewer_a = _rows(reviewer_a_path)
    reviewer_b = _rows(reviewer_b_path)
    mapping = _rows(mapping_path)
    expected = set(mapping)
    if set(reviewer_a) != expected or set(reviewer_b) != expected:
        raise ValueError("Both reviewer forms must contain exactly the mapped external cases.")

    comparison_rows: list[dict[str, str]] = []
    no_human_consensus: list[str] = []
    missing_outputs: list[str] = []
    for case_id in sorted(expected):
        consensus = human_consensus(
            reviewer_a[case_id].get("dominant_response"),
            reviewer_b[case_id].get("dominant_response"),
        )
        if consensus is None:
            no_human_consensus.append(case_id)
            continue
        metrics_path = output / "metrics" / f"{case_id}_metrics.json"
        if not metrics_path.is_file():
            missing_outputs.append(case_id)
            # Eligibility is defined by human consensus. A missing response
            # is scored as an abstention and recorded separately for audit.
            prediction = "undetermined"
        else:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            prediction = derive_kairis_response(metrics["summary"])
        comparison_rows.append(
            {
                "case_id": case_id,
                "truth": consensus,
                "prediction": prediction,
                "bootstrap_group": str(mapping[case_id]["source_subgroup"]),
            }
        )
    primary = classification_metrics(
        [row["truth"] for row in comparison_rows],
        [row["prediction"] for row in comparison_rows],
    )
    primary["grouped_bootstrap_ci95"] = grouped_bootstrap_intervals(
        comparison_rows, draws=draws, seed=seed
    )
    return {
        "format": "KAIRIS-external-confirmatory-analysis-v1",
        "P1_integrity": evaluate_integrity(output, cohort_root),
        "P2_dominant_response_agreement": primary,
        "case_accounting": {
            "mapped_cases": len(expected),
            "primary_denominator": len(comparison_rows),
            "human_no_consensus_count": len(no_human_consensus),
            "missing_kairis_output_count": len(missing_outputs),
            "human_no_consensus_case_ids": no_human_consensus,
            "missing_kairis_output_case_ids": missing_outputs,
        },
        "bootstrap": {"group": "source_subgroup", "draws": draws, "seed": seed},
        "comparison_rows": comparison_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="Locked KAIRIS external-run output")
    parser.add_argument("--reviewer-a", type=Path, required=True)
    parser.add_argument("--reviewer-b", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True, help="Private coordinator blinding key")
    parser.add_argument(
        "--cohort-root", type=Path,
        default=PROJECT / "data" / "external_confirmatory" / "316l_passivity_osf_xrav8",
    )
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20261105)
    args = parser.parse_args()
    result = analyze(
        args.output.resolve(), args.reviewer_a.resolve(), args.reviewer_b.resolve(),
        args.mapping.resolve(), args.cohort_root.resolve(),
        draws=args.bootstrap_draws, seed=args.seed,
    )
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        destination / "external_confirmatory_analysis.json",
        json.dumps(to_jsonable(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    print(json.dumps(to_jsonable(result), ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
