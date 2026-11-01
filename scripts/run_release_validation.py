"""Run a fresh, provenance-safe KAIRIS release validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402


def _git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=PROJECT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _release_identity(require_tag: bool) -> tuple[str, str | None]:
    status = _git("status", "--porcelain").stdout.strip()
    if status:
        raise RuntimeError(
            "A validação de release exige árvore Git limpa. Faça commit ou arquive "
            "as alterações antes de continuar."
        )
    commit = _git("rev-parse", "HEAD").stdout.strip()
    tag_result = _git("describe", "--tags", "--exact-match", "HEAD", check=False)
    tag = tag_result.stdout.strip() if tag_result.returncode == 0 else None
    if require_tag and not tag:
        raise RuntimeError("HEAD não possui uma tag exata; crie a tag da release primeiro.")
    return commit, tag


def _run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=PROJECT / "data" / "validation" / "kairis_eis_validation_v1",
    )
    parser.add_argument(
        "--config", type=Path, default=PROJECT / "config" / "protocol_config.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-tag", action="store_true")
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError(
            f"Saída não está vazia: {output}. Use um diretório novo; resultados "
            "de release nunca são reutilizados nem removidos automaticamente."
        )
    commit, tag = _release_identity(args.require_tag)
    output.mkdir(parents=True, exist_ok=True)
    evidence = output / "evidence"
    started = datetime.now(timezone.utc).isoformat()

    validate_command = [
        sys.executable,
        str(PROJECT / "scripts" / "validate_eis_corpus.py"),
        "--corpus",
        str(args.corpus.resolve()),
        "--config",
        str(args.config.resolve()),
        "--output",
        str(output),
        "--evidence-dir",
        str(evidence),
        "--full-pipeline",
    ]
    _run(validate_command)
    evaluation = evidence / "acceptance_report.json"
    _run(
        [
            sys.executable,
            str(PROJECT / "scripts" / "evaluate_validation_results.py"),
            "--corpus",
            str(args.corpus.resolve()),
            "--output",
            str(output),
            "--report",
            str(evaluation),
            "--enforce",
        ]
    )
    if _git("status", "--porcelain").stdout.strip():
        raise RuntimeError("A execução alterou a árvore Git; a evidência não é limpa.")

    manifest: dict[str, Any] = {
        "format": "KAIRIS-release-validation-run-v1",
        "started_at": started,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": commit,
        "git_tag": tag,
        "python": sys.version,
        "corpus": str(args.corpus.resolve()),
        "corpus_manifest_sha256": _sha256(
            args.corpus.resolve() / "dataset_manifest.csv"
        ),
        "config": str(args.config.resolve()),
        "config_sha256": _sha256(args.config.resolve()),
        "output": str(output),
        "llm_enabled": False,
        "results_reused": False,
        "acceptance_report": str(evaluation),
    }
    atomic_write_text(
        evidence / "release_run_manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
