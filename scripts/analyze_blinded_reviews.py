"""Analyze two independent KAIRIS blinded-review forms with agreement statistics."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.report_builder import to_jsonable  # noqa: E402

CATEGORICAL_FIELDS = [
    "spectrum_quality",
    "dominant_response",
    "intercalation_pseudocapacitive",
    "exclude_from_analysis",
]
ORDINAL_FIELDS = ["estimated_process_count", "confidence_1_to_5"]
ABSTENTION_VALUES = {"", "undetermined", "uncertain", "na", "n/a"}


def _read_form(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        if not case_id:
            continue
        if case_id in result:
            raise ValueError(f"case_id duplicado em {path}: {case_id}")
        result[case_id] = {key: str(value or "").strip().casefold() for key, value in row.items()}
    return result


def cohen_kappa(first: list[str], second: list[str]) -> float | None:
    if len(first) != len(second) or not first:
        return None
    categories = sorted(set(first) | set(second))
    observed = sum(a == b for a, b in zip(first, second)) / len(first)
    count_a, count_b = Counter(first), Counter(second)
    expected = sum(count_a[c] * count_b[c] for c in categories) / len(first) ** 2
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else None
    return (observed - expected) / (1.0 - expected)


def weighted_kappa(first: list[int], second: list[int]) -> float | None:
    """Quadratic weighted Cohen kappa for paired ordinal ratings."""
    if len(first) != len(second) or not first:
        return None
    categories = sorted(set(first) | set(second))
    if len(categories) == 1:
        return 1.0
    index = {value: position for position, value in enumerate(categories)}
    size = len(categories)
    observed = np.zeros((size, size), dtype=float)
    for a, b in zip(first, second):
        observed[index[a], index[b]] += 1.0
    observed /= observed.sum()
    marginal_a = observed.sum(axis=1)
    marginal_b = observed.sum(axis=0)
    expected = np.outer(marginal_a, marginal_b)
    positions = np.arange(size, dtype=float)
    weights = ((positions[:, None] - positions[None, :]) / (size - 1)) ** 2
    denominator = float(np.sum(weights * expected))
    if denominator <= np.finfo(float).eps:
        return 1.0
    return 1.0 - float(np.sum(weights * observed)) / denominator


def _bootstrap_interval(
    first: list[Any],
    second: list[Any],
    statistic: Callable[[list[Any], list[Any]], float | None],
    rng: np.random.Generator,
    draws: int,
) -> list[float] | None:
    if not first:
        return None
    values: list[float] = []
    for _ in range(draws):
        indices = rng.integers(0, len(first), size=len(first))
        value = statistic([first[i] for i in indices], [second[i] for i in indices])
        if value is not None and math.isfinite(value):
            values.append(float(value))
    if not values:
        return None
    return [float(value) for value in np.quantile(values, [0.025, 0.975])]


def analyze_reviews(
    reviewer_a: dict[str, dict[str, str]],
    reviewer_b: dict[str, dict[str, str]],
    seed: int = 20261102,
    bootstrap_draws: int = 2000,
) -> dict[str, Any]:
    common = sorted(set(reviewer_a) & set(reviewer_b))
    only_a = sorted(set(reviewer_a) - set(reviewer_b))
    only_b = sorted(set(reviewer_b) - set(reviewer_a))
    rng = np.random.default_rng(seed)
    fields: dict[str, Any] = {}
    disagreements: list[dict[str, str]] = []
    for field in CATEGORICAL_FIELDS:
        pairs = [
            (case, reviewer_a[case].get(field, ""), reviewer_b[case].get(field, ""))
            for case in common
            if reviewer_a[case].get(field, "") and reviewer_b[case].get(field, "")
        ]
        first = [item[1] for item in pairs]
        second = [item[2] for item in pairs]
        kappa = cohen_kappa(first, second)
        for case, a, b in pairs:
            if a != b:
                disagreements.append({"case_id": case, "field": field, "reviewer_a": a, "reviewer_b": b})
        fields[field] = {
            "paired_count": len(pairs),
            "percent_agreement": 100.0 * sum(a == b for a, b in zip(first, second)) / len(pairs)
            if pairs
            else None,
            "cohen_kappa": kappa,
            "cohen_kappa_ci95_bootstrap": _bootstrap_interval(
                first, second, cohen_kappa, rng, bootstrap_draws
            ),
            "reviewer_a_abstention_fraction": sum(
                reviewer_a[case].get(field, "") in ABSTENTION_VALUES for case in common
            )
            / len(common)
            if common
            else None,
            "reviewer_b_abstention_fraction": sum(
                reviewer_b[case].get(field, "") in ABSTENTION_VALUES for case in common
            )
            / len(common)
            if common
            else None,
        }
    for field in ORDINAL_FIELDS:
        pairs: list[tuple[str, int, int]] = []
        for case in common:
            try:
                a = int(reviewer_a[case].get(field, ""))
                b = int(reviewer_b[case].get(field, ""))
            except ValueError:
                continue
            pairs.append((case, a, b))
        first = [item[1] for item in pairs]
        second = [item[2] for item in pairs]
        kappa = weighted_kappa(first, second)
        for case, a, b in pairs:
            if a != b:
                disagreements.append(
                    {"case_id": case, "field": field, "reviewer_a": str(a), "reviewer_b": str(b)}
                )
        fields[field] = {
            "paired_numeric_count": len(pairs),
            "percent_exact_agreement": 100.0
            * sum(a == b for a, b in zip(first, second))
            / len(pairs)
            if pairs
            else None,
            "quadratic_weighted_kappa": kappa,
            "quadratic_weighted_kappa_ci95_bootstrap": _bootstrap_interval(
                first, second, weighted_kappa, rng, bootstrap_draws
            ),
            "reviewer_a_abstention_fraction": sum(
                reviewer_a[case].get(field, "") in ABSTENTION_VALUES for case in common
            )
            / len(common)
            if common
            else None,
            "reviewer_b_abstention_fraction": sum(
                reviewer_b[case].get(field, "") in ABSTENTION_VALUES for case in common
            )
            / len(common)
            if common
            else None,
        }
    return {
        "format": "KAIRIS-blinded-review-agreement-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_a_cases": len(reviewer_a),
        "reviewer_b_cases": len(reviewer_b),
        "paired_cases": len(common),
        "only_reviewer_a": only_a,
        "only_reviewer_b": only_b,
        "bootstrap": {"seed": seed, "draws": bootstrap_draws, "confidence_level": 0.95},
        "fields": fields,
        "disagreements": disagreements,
    }


def write_outputs(result: dict[str, Any], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        destination / "review_agreement.json",
        json.dumps(to_jsonable(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    stream = io.StringIO(newline="")
    columns = ["case_id", "field", "reviewer_a", "reviewer_b"]
    writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(result["disagreements"])
    atomic_write_text(destination / "review_disagreements.csv", stream.getvalue())
    lines = [
        "# KAIRIS — concordância da revisão cega",
        "",
        f"Casos pareados: {result['paired_cases']}",
        "",
        "| Campo | n | Concordância | Kappa | IC 95% bootstrap |",
        "|---|---:|---:|---:|---:|",
    ]
    for field, values in result["fields"].items():
        count = values.get("paired_count", values.get("paired_numeric_count"))
        agreement = values.get("percent_agreement", values.get("percent_exact_agreement"))
        kappa = values.get("cohen_kappa", values.get("quadratic_weighted_kappa"))
        interval = values.get(
            "cohen_kappa_ci95_bootstrap",
            values.get("quadratic_weighted_kappa_ci95_bootstrap"),
        )
        interval_text = (
            f"[{interval[0]:.3f}, {interval[1]:.3f}]" if interval else "indisponível"
        )
        lines.append(
            f"| {field} | {count} | {agreement:.1f}% | {kappa:.3f} | {interval_text} |"
            if agreement is not None and kappa is not None
            else f"| {field} | {count} | indisponível | indisponível | {interval_text} |"
        )
    lines += [
        "",
        "Resultados `undetermined`, `uncertain` e ausentes são reportados como "
        "abstenções; não são convertidos automaticamente em erro.",
        "",
    ]
    atomic_write_text(destination / "review_agreement_summary.md", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("--destination", type=Path, default=PROJECT / "output" / "review_agreement_v1")
    parser.add_argument("--seed", type=int, default=20261102)
    parser.add_argument("--bootstrap-draws", type=int, default=2000)
    args = parser.parse_args()
    if args.bootstrap_draws < 1:
        parser.error("--bootstrap-draws deve ser pelo menos 1")
    result = analyze_reviews(
        _read_form(args.reviewer_a),
        _read_form(args.reviewer_b),
        seed=args.seed,
        bootstrap_draws=args.bootstrap_draws,
    )
    write_outputs(result, args.destination.resolve())
    print(json.dumps(to_jsonable(result["fields"]), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
