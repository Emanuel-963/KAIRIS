"""Run the six Randles fixtures and record reproducible platform evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.artifact_io import atomic_write_text
from core.config_validator import validate_config
from core.report_builder import to_jsonable
from scripts.evaluate_validation_results import DEFAULT_ACCEPTANCE, evaluate
from scripts.run_release_validation import _release_identity, _sha256
from scripts.validate_eis_corpus import DEFAULT_CORPUS, audit_files, full_pipeline
from setup_kairis import total_memory_gb


def run(output: Path):
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Use a fresh output directory: {output}")
    commit, _ = _release_identity(require_tag=False)
    config_path = ROOT / "config" / "protocol_config.json"
    config = json.loads(config_path.read_bytes())
    validate_config(config)
    start = perf_counter()
    fixtures = [row for row in audit_files(DEFAULT_CORPUS, config)
                if row["source_type"] == "synthetic" and row["family"] == "randles_rc"]
    samples = {row["sample_id"] for row in fixtures}
    if len(fixtures) != 6 or len(samples) != 6 or any(row["file_status"] != "valid" for row in fixtures):
        raise ValueError("Expected six distinct Randles fixtures with verified input hashes")
    runs = full_pipeline(DEFAULT_CORPUS, output, config, fixtures, overwrite=False, limit=None)
    evaluation = evaluate(
        DEFAULT_CORPUS, output, json.loads(DEFAULT_ACCEPTANCE.read_bytes()),
        commit, sample_ids=samples,
    )
    packages = {}
    for sample in sorted(samples):
        path = output / "metrics" / f"{sample}_metrics.json"
        if path.is_file():
            origin = json.loads(path.read_bytes())["provenance"]
            packages = origin["package_versions"]
            if any(origin["effective_config"].get(key) is not False for key in (
                "llm_enabled", "llm_memory_enabled", "supervised_learning_enabled",
            )):
                raise ValueError(f"Optional LLM feature was enabled for {sample}")
    final_commit, _ = _release_identity(require_tag=False)
    if final_commit != commit:
        raise ValueError("Git commit changed during the portability check")
    evidence = {
        "format": "KAIRIS-portability-smoke-v1",
        "scope": "six retrospective Randles fixtures",
        "git_commit": commit,
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "python": sys.version,
        "physical_ram_gib": round(total_memory_gb(), 2),
        "package_versions": packages,
        "config_sha256": _sha256(config_path),
        "corpus_manifest_sha256": _sha256(DEFAULT_CORPUS / "dataset_manifest.csv"),
        "elapsed_seconds": round(perf_counter() - start, 3),
        "passed": evaluation["all_development_gates_pass"]
        and len(runs) == len(samples)
        and all(row["pipeline_status"] == "completed" for row in runs),
        "cases": [
            {key: row[key] for key in ("sample_id", "pipeline_status", "error")}
            for row in runs
        ],
        "gates": evaluation["gates"],
        "measured": evaluation["measured"],
    }
    serialized = json.dumps(to_jsonable(evidence), indent=2, allow_nan=False) + "\n"
    atomic_write_text(output / "portability_evidence.json", serialized)
    print(serialized)
    return 0 if evidence["passed"] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return run(args.output.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
