"""Audit the KAIRIS EIS corpus and optionally run all five agents."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
from core.eis_loader import load_btlab  # noqa: E402
import run_pipeline  # noqa: E402


DEFAULT_CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(corpus: Path) -> list[dict[str, str]]:
    with (corpus / "dataset_manifest.csv").open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def audit_files(corpus: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in read_manifest(corpus):
        path = corpus / item["relative_path"]
        status = "valid"
        error = ""
        points = 0
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            if file_sha256(path) != item["sha256"]:
                raise ValueError("SHA-256 differs from manifest")
            spectrum = load_btlab(path, config)
            points = len(spectrum["frequency"])
            if points != int(item["point_count"]):
                raise ValueError(f"point count {points} differs from manifest {item['point_count']}")
        except Exception as exc:
            status = "invalid"
            error = f"{type(exc).__name__}: {exc}"
        rows.append(
            {
                "sample_id": item["sample_id"],
                "relative_path": item["relative_path"],
                "source_type": item["source_type"],
                "family": item["family"],
                "file_status": status,
                "loaded_points": points,
                "error": error,
            }
        )
    return rows


def full_pipeline(
    corpus: Path,
    output: Path,
    config: dict[str, Any],
    audit: list[dict[str, Any]],
    overwrite: bool,
    limit: int | None,
) -> list[dict[str, Any]]:
    run_pipeline.ensure_output_structure(output)
    run_pipeline.configure_logging(output)
    effective = dict(config)
    effective["llm_enabled"] = False
    selected = [row for row in audit if row["file_status"] == "valid"]
    if limit is not None:
        selected = selected[:limit]
    results: list[dict[str, Any]] = []
    for index, row in enumerate(selected, start=1):
        path = corpus / row["relative_path"]
        sample = row["sample_id"]
        metrics_path = output / "metrics" / f"{sample}_metrics.json"
        try:
            if metrics_path.is_file() and not overwrite:
                final = {"metrics": str(metrics_path)}
                state = "reused"
            else:
                final = run_pipeline.run_sample(path, output, effective, sample)
                state = "completed"
            metrics = json.loads(Path(final["metrics"]).read_text(encoding="utf-8"))
            rules = metrics.get("interpretation_rules", [])
            summary = metrics.get("summary", {})
            disagreement = bool(summary.get("drt_gsf_inconsistent")) if "drt_gsf_inconsistent" in summary else any(
                "diverg" in str(message).casefold() for message in rules
            )
            results.append(
                {
                    "sample_id": sample,
                    "source_type": row["source_type"],
                    "family": row["family"],
                    "pipeline_status": state,
                    "all_five_agents_completed": True,
                    "lin_kk_valid": summary.get("lin_kk_valid"),
                    "drt_gsf_agreement": not disagreement,
                    "report": final.get("report", str(output / "reports" / f"{sample}_report.html")),
                    "error": "",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "sample_id": sample,
                    "source_type": row["source_type"],
                    "family": row["family"],
                    "pipeline_status": "failed",
                    "all_five_agents_completed": False,
                    "lin_kk_valid": None,
                    "drt_gsf_agreement": None,
                    "report": "",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        print(f"[{index}/{len(selected)}] {sample}: {results[-1]['pipeline_status']}")
    return results


def csv_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita o corpus EIS e executa opcionalmente o KAIRIS completo")
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--config", type=Path, default=PROJECT / "config" / "protocol_config.json")
    parser.add_argument("--output", type=Path, default=PROJECT / "output" / "validation_corpus")
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help=(
            "Diretório dos manifestos da execução; o padrão histórico é "
            "<corpus>/validation_evidence"
        ),
    )
    parser.add_argument("--full-pipeline", action="store_true", help="executar Agentes 1 a 5 em cada espectro")
    parser.add_argument("--overwrite", action="store_true", help="reprocessar resultados existentes")
    parser.add_argument("--limit", type=int, help="limitar o número de espectros para smoke test")
    args = parser.parse_args()

    corpus = args.corpus.resolve()
    output = args.output.resolve()
    config = load_config(args.config)
    validate_config(config, Path(args.config).with_name("protocol_schema.json"))
    audit = audit_files(corpus, config)
    pipeline_rows = full_pipeline(corpus, output, config, audit, args.overwrite, args.limit) if args.full_pipeline else []
    invalid = sum(row["file_status"] != "valid" for row in audit)
    failures = sum(row["pipeline_status"] == "failed" for row in pipeline_rows)
    disagreements = sum(row.get("drt_gsf_agreement") is False for row in pipeline_rows)
    summary = {
        "format": "KAIRIS-validation-evidence-v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "corpus": str(corpus),
        "files_total": len(audit),
        "files_valid": len(audit) - invalid,
        "files_invalid": invalid,
        "pipeline_requested": bool(args.full_pipeline),
        "pipeline_samples": len(pipeline_rows),
        "pipeline_completed": len(pipeline_rows) - failures,
        "pipeline_failed": failures,
        "drt_gsf_disagreements_with_report": disagreements,
        "llm_enabled": False,
    }
    evidence = (
        args.evidence_dir.resolve()
        if args.evidence_dir is not None
        else corpus / "validation_evidence"
    )
    atomic_write_text(
        evidence / "last_run_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(evidence / "file_audit.csv", csv_text(audit))
    if pipeline_rows:
        atomic_write_text(evidence / "pipeline_results.csv", csv_text(pipeline_rows))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if invalid or failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
