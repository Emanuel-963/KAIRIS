"""Build a deterministic, privacy-safe OSF preregistration attachment bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
FREEZE_RECORD = PROJECT / "paper" / "EXTERNAL_VALIDATION_FREEZE_RECORD.json"
DEFAULT_OUTPUT = PROJECT / "output" / "osf_external_validation_bundle_v1.zip"

PUBLIC_FILES = [
    "paper/OSF_SECONDARY_DATA_PREREGISTRATION_DRAFT_v1.md",
    "paper/EXTERNAL_VALIDATION_ADDENDUM_v1.md",
    "paper/EXTERNAL_VALIDATION_FREEZE_RECORD.json",
    "paper/EXTERNAL_REVIEWER_INSTRUCTIONS_v1.md",
    "paper/REVIEWER_ROLES_AND_CONFLICTS_v1.md",
    "paper/DEVIATIONS_LOG_v1.md",
    "config/external_validation_plan_v1.json",
    "config/protocol_config.json",
    "data/external_confirmatory/316l_passivity_osf_xrav8/source_metadata.json",
    "data/external_confirmatory/316l_passivity_osf_xrav8/prepared_blind/preparation_summary.json",
    "data/external_confirmatory/316l_passivity_osf_xrav8/prepared_blind/blind_manifest.csv",
    "core/confirmatory_metrics.py",
    "scripts/analyze_blinded_reviews.py",
    "scripts/analyze_external_confirmation.py",
    "scripts/check_external_validation_readiness.py",
    "scripts/run_external_validation.py",
]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=PROJECT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
    )
    return result.stdout.strip()


def _validate_freeze() -> dict[str, Any]:
    freeze = json.loads(FREEZE_RECORD.read_text(encoding="utf-8"))
    tag_commit = _git("rev-list", "-n", "1", str(freeze["git_tag"]))
    if tag_commit != freeze["analysis_code_commit"]:
        raise RuntimeError("Frozen tag no longer points to the recorded analysis commit.")
    checks = {
        freeze["external_plan_path"]: freeze["external_plan_sha256"],
        freeze["protocol_config_path"]: freeze["protocol_config_sha256"],
        freeze["reviewer_instructions_path"]: freeze["reviewer_instructions_sha256"],
    }
    for relative, expected in checks.items():
        observed = _sha256(PROJECT / relative)
        if observed != expected:
            raise RuntimeError(
                f"Frozen file hash mismatch for {relative}: expected {expected}, got {observed}."
            )
    source = (
        PROJECT / "data" / "external_confirmatory" / "316l_passivity_osf_xrav8"
        / "raw" / "input_data.csv"
    )
    if _sha256(source) != freeze["source_sha256"]:
        raise RuntimeError("Canonical external source hash no longer matches the freeze record.")
    return freeze


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(2026, 11, 5, 23, 38, 14))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def build_bundle(destination: Path, *, require_clean: bool = True) -> dict[str, Any]:
    freeze = _validate_freeze()
    tracked_status = _git("status", "--porcelain", "--untracked-files=all")
    if require_clean and tracked_status:
        raise RuntimeError(
            "The OSF bundle requires a clean Git tree so every attached file has a committed identity."
        )
    payloads: dict[str, bytes] = {}
    for relative in PUBLIC_FILES:
        path = PROJECT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        lowered = relative.casefold()
        if "coordinator" in lowered or "signoff" in lowered or "blinding_key" in lowered:
            raise RuntimeError(f"Private-looking path cannot enter OSF bundle: {relative}")
        payloads[relative] = path.read_bytes()

    readme = (
        "# KAIRIS external-validation preregistration bundle\n\n"
        "This attachment set contains the frozen scientific plan, public metadata, "
        "de-identified reviewer materials and executable analysis definitions.\n\n"
        "It intentionally excludes reviewer identities, affiliations, ORCIDs, conflict "
        "declarations, the coordinator blinding key, KAIRIS outputs and the 42 converted "
        "case files. The public dataset is referenced by DOI and cryptographic hash.\n\n"
        f"Frozen analysis commit: `{freeze['analysis_code_commit']}`  \n"
        f"Frozen Git tag: `{freeze['git_tag']}`\n"
    ).encode("utf-8")
    payloads["README_UPLOAD.md"] = readme
    manifest = {
        "format": "KAIRIS-OSF-registration-bundle-v1",
        "analysis_code_commit": freeze["analysis_code_commit"],
        "analysis_git_tag": freeze["git_tag"],
        "bundle_builder_commit": _git("rev-parse", "HEAD"),
        "deterministic_zip_timestamp": "2026-11-05T23:38:14Z",
        "privacy": {
            "reviewer_identifiers_included": False,
            "private_conflict_declarations_included": False,
            "coordinator_blinding_key_included": False,
            "kairis_external_results_included": False,
        },
        "files": {
            name: {"bytes": len(content), "sha256": _sha256_bytes(content)}
            for name, content in sorted(payloads.items())
        },
    }
    payloads["BUNDLE_MANIFEST.json"] = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(file_descriptor)
    temporary = Path(temporary_name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name, content in sorted(payloads.items()):
                archive.writestr(_zip_info(name), content)
        with temporary.open("r+b") as handle:
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()

    return {
        **manifest,
        "bundle_path": str(destination.resolve()),
        "bundle_bytes": destination.stat().st_size,
        "bundle_sha256": _sha256(destination),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_bundle(args.output.resolve(), require_clean=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
