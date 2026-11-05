"""Check every immutable and administrative gate before external KAIRIS analysis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = PROJECT / "config" / "external_validation_plan_v1.json"
DEFAULT_ROOT = PROJECT / "data" / "external_confirmatory" / "316l_passivity_osf_xrav8"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _gate(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _git(*args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["git", *args], cwd=PROJECT, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=False,
    )
    return result.returncode, result.stdout.strip()


def _private_signoff_complete(payload: dict[str, Any], roles: list[str]) -> bool:
    required = ("accepted_role", "conflict_declaration_received", "deadline_accepted")
    return all(
        isinstance(payload.get(role), dict)
        and all(payload[role].get(field) is True for field in required)
        for role in roles
    ) and bool(payload.get("review_deadline_iso8601")) and bool(
        payload.get("coordinator_approved_at_iso8601")
    )


def evaluate_readiness(
    plan_path: Path = DEFAULT_PLAN,
    cohort_root: Path = DEFAULT_ROOT,
    *,
    check_git: bool = True,
) -> dict[str, Any]:
    plan_path = Path(plan_path)
    cohort_root = Path(cohort_root)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    gates: list[dict[str, Any]] = []

    gates.append(_gate(
        "scientific_specification",
        plan.get("status") == "scientific_specification_complete_analysis_locked_pending_registration",
        str(plan.get("status")),
    ))
    source = cohort_root / "raw" / "input_data.csv"
    expected_source_hash = plan["cohort"]["source_sha256"]
    actual_source_hash = _sha256(source) if source.is_file() else None
    gates.append(_gate(
        "canonical_source_hash",
        actual_source_hash == expected_source_hash,
        f"expected={expected_source_hash}; actual={actual_source_hash}",
    ))

    prepared = cohort_root / "prepared_blind"
    manifest_path = prepared / "blind_manifest.csv"
    manifest: list[dict[str, str]] = []
    if manifest_path.is_file():
        with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
            manifest = list(csv.DictReader(handle))
    file_hashes_ok = bool(manifest)
    for row in manifest:
        candidate = prepared / row.get("relative_path", "")
        if not candidate.is_file() or _sha256(candidate) != row.get("sha256"):
            file_hashes_ok = False
            break
    gates.append(_gate(
        "prepared_blind_manifest",
        len(manifest) == int(plan["cohort"]["case_count"]) and file_hashes_ok,
        f"manifest_cases={len(manifest)}; hashes_ok={file_hashes_ok}",
    ))

    instruction_path = PROJECT / "paper" / "EXTERNAL_REVIEWER_INSTRUCTIONS_v1.md"
    gates.append(_gate(
        "reviewer_materials_specified", instruction_path.is_file(), str(instruction_path)
    ))

    signoff_path = PROJECT / plan["administrative_registration"]["private_signoff_file"]
    signoff: dict[str, Any] = {}
    if signoff_path.is_file():
        signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
    roles = list(plan["administrative_registration"]["required_acceptances"])
    gates.append(_gate(
        "private_acceptances_and_conflicts",
        _private_signoff_complete(signoff, roles),
        "complete" if signoff else f"missing private file: {signoff_path}",
    ))

    registration_path = PROJECT / plan["administrative_registration"]["public_registration_record"]
    registration: dict[str, Any] = {}
    if registration_path.is_file():
        registration = json.loads(registration_path.read_text(encoding="utf-8"))
    registration_complete = bool(registration.get("osf_registration_id")) and bool(
        registration.get("osf_registered_at")
    ) and registration.get("coordinator_verified_registered_package") is True
    gates.append(_gate(
        "osf_registration", registration_complete,
        str(registration.get("osf_registration_id") or f"missing record: {registration_path}"),
    ))

    identity_path = PROJECT / plan["execution"]["analysis_identity_source"]
    identity: dict[str, Any] = {}
    if identity_path.is_file():
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
    plan_hash = _sha256(plan_path)
    protocol_config = PROJECT / "config" / "protocol_config.json"
    identity_ok = bool(identity) and identity.get("external_plan_sha256") == plan_hash and (
        identity.get("protocol_config_sha256") == _sha256(protocol_config)
    ) and bool(identity.get("analysis_code_commit"))
    gates.append(_gate(
        "frozen_code_and_config_identity", identity_ok,
        str(identity_path) if identity else f"missing freeze record: {identity_path}",
    ))

    required_tag = plan["execution"]["required_tag"]
    tag_ok = False
    if check_git and identity.get("analysis_code_commit"):
        rc, tag_commit = _git("rev-list", "-n", "1", required_tag)
        tag_ok = rc == 0 and tag_commit == identity["analysis_code_commit"]
    gates.append(_gate(
        "immutable_git_tag", tag_ok if check_git else bool(identity.get("analysis_code_commit")),
        required_tag,
    ))

    clean = False
    if check_git:
        rc, status = _git("status", "--porcelain")
        clean = rc == 0 and status == ""
    gates.append(_gate(
        "clean_worktree", clean if check_git else True,
        "clean" if clean else ("not checked" if not check_git else "uncommitted changes present"),
    ))

    unlocked = registration.get("analysis_unlocked") is True
    gates.append(_gate(
        "coordinator_unlock_after_registration", unlocked,
        "unlocked" if unlocked else "locked",
    ))

    ready = all(item["passed"] for item in gates)
    return {
        "format": "KAIRIS-external-validation-readiness-v1",
        "ready_for_scientific_analysis": ready,
        "analysis_lock": "unlocked" if ready else "locked",
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--cohort-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--no-git-check", action="store_true")
    args = parser.parse_args()
    result = evaluate_readiness(
        args.plan.resolve(), args.cohort_root.resolve(), check_git=not args.no_git_check
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ready_for_scientific_analysis"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
