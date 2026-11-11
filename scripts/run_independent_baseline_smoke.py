#!/usr/bin/env python3
"""Run locked independent baselines on KAIRIS synthetic fixtures only."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.config_loader import load_config  # noqa: E402
from core.eis_loader import load_btlab  # noqa: E402
from core.independent_baselines import (  # noqa: E402
    run_impedance_lin_kk,
    run_pyimpspec_tr_nnls,
)

DEFAULT_CORPUS = ROOT / "data" / "validation" / "kairis_eis_validation_v1"
EXTERNAL_ROOT = (ROOT / "data" / "external_confirmatory").resolve()


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def assert_synthetic_only(corpus: Path) -> None:
    """Hard guard against premature execution of the external cohort."""
    resolved = corpus.resolve()
    if _is_relative_to(resolved, EXTERNAL_ROOT):
        raise RuntimeError("external confirmatory cohort is locked; synthetic smoke only")


def _rows(corpus: Path, family: str, limit: int) -> list[dict[str, str]]:
    with (corpus / "dataset_manifest.csv").open(encoding="utf-8", newline="") as handle:
        candidates = [
            row
            for row in csv.DictReader(handle)
            if row.get("source_type") == "synthetic" and row.get("family") == family
        ]
    return candidates[:limit] if limit > 0 else candidates


def run_smoke(
    corpus: Path,
    output: Path,
    config_path: Path,
    family: str,
    limit: int,
    drt_modes: list[str],
    lambda_values: list[float],
) -> dict[str, Any]:
    assert_synthetic_only(corpus)
    config = load_config(config_path)
    records: list[dict[str, Any]] = []
    for row in _rows(corpus, family, limit):
        source = corpus / row["relative_path"]
        eis = load_btlab(source, config)
        record: dict[str, Any] = {
            "sample_id": row["sample_id"],
            "family": row["family"],
            "relative_path": row["relative_path"],
            "lin_kk": run_impedance_lin_kk(
                eis["frequency"], eis["real"], eis["imag"], config
            ),
            "drt": {},
        }
        for mode in drt_modes:
            for requested_lambda in lambda_values:
                key = f"{mode}_lambda_{requested_lambda:g}"
                record["drt"][key] = run_pyimpspec_tr_nnls(
                    eis["frequency"],
                    eis["real"],
                    eis["imag"],
                    mode=mode,
                    lambda_value=requested_lambda,
                    peak_threshold_fraction=float(
                        config.get("drt_peak_prominence_fraction", 0.05)
                    ),
                )
        records.append(record)

    summary = {
        "scope": "synthetic_smoke_only",
        "external_confirmatory_executed": False,
        "comparison_schema_version": "1.0",
        "family": family,
        "sample_count": len(records),
        "primary_drt_condition": "real_lambda_-1",
        "sensitivity_drt_conditions": [
            f"{mode}_lambda_{value:g}"
            for mode in drt_modes
            for value in lambda_values
            if not (mode == "real" and value == -1.0)
        ],
        "records": records,
    }
    atomic_write_text(output, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute independent Lin-KK/DRT baselines on synthetic KAIRIS fixtures."
    )
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "output" / "baseline_smoke_v1.json"
    )
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config" / "protocol_config.json"
    )
    parser.add_argument("--family", default="randles_rc")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument(
        "--drt-mode", action="append", choices=("real", "imaginary"), dest="modes"
    )
    parser.add_argument(
        "--lambda-value", action="append", type=float, dest="lambdas"
    )
    args = parser.parse_args()
    result = run_smoke(
        args.corpus,
        args.output,
        args.config,
        args.family,
        args.limit,
        args.modes or ["real"],
        args.lambdas or [-1.0],
    )
    print(
        f"KAIRIS baseline smoke: {result['sample_count']} synthetic samples; "
        f"output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
