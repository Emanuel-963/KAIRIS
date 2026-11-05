"""Run the registered 42-case KAIRIS external validation exactly once."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.config_loader import load_config  # noqa: E402
from core.config_validator import validate_config  # noqa: E402
from run_pipeline import configure_logging, ensure_output_structure, run_sample  # noqa: E402
from scripts.check_external_validation_readiness import (  # noqa: E402
    DEFAULT_PLAN,
    DEFAULT_ROOT,
    evaluate_readiness,
)


def execute_external_validation(
    plan_path: Path,
    cohort_root: Path,
    protocol_config_path: Path,
    output: Path,
) -> dict[str, Any]:
    readiness = evaluate_readiness(plan_path, cohort_root, check_git=True)
    if not readiness["ready_for_scientific_analysis"]:
        failed = [gate["name"] for gate in readiness["gates"] if not gate["passed"]]
        raise RuntimeError(
            "External analysis remains locked. Failed gates: " + ", ".join(failed)
        )
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(f"External output must be new and empty: {output}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    config = load_config(protocol_config_path)
    config.update(
        {
            "llm_enabled": False,
            "llm_memory_enabled": False,
            "supervised_learning_enabled": False,
        }
    )
    validate_config(config)
    ensure_output_structure(output)
    configure_logging(output)
    manifest_path = cohort_root / "prepared_blind" / "blind_manifest.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    if len(manifest) != int(plan["cohort"]["case_count"]):
        raise RuntimeError("Prepared manifest count differs from the frozen plan.")

    started_at = datetime.now(timezone.utc).isoformat()
    cases: list[dict[str, Any]] = []
    for row in manifest:
        case_id = row["case_id"]
        source = cohort_root / "prepared_blind" / row["relative_path"]
        try:
            run_sample(source, output, config, sample_name=case_id)
            cases.append({"case_id": case_id, "status": "completed", "error": None})
        except Exception as error:  # failure is an endpoint and must remain explicit
            cases.append(
                {"case_id": case_id, "status": "failed", "error": f"{type(error).__name__}: {error}"}
            )
    completed = sum(case["status"] == "completed" for case in cases)
    result = {
        "format": "KAIRIS-external-validation-run-v1",
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "cases_expected": len(manifest),
        "cases_completed": completed,
        "cases_failed": len(cases) - completed,
        "llm_enabled": False,
        "llm_memory_enabled": False,
        "supervised_learning_enabled": False,
        "results_reused": False,
        "cases": cases,
    }
    atomic_write_text(
        output / "external_run_manifest.json",
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--cohort-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--config", type=Path, default=PROJECT / "config" / "protocol_config.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute_external_validation(
        args.plan.resolve(), args.cohort_root.resolve(), args.config.resolve(),
        args.output.resolve(),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["cases_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
