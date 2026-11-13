"""Replay the integrated ESC candidate on archived KAIRIS G1–G4 references."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.agent5_orchestrator import Agent5_Orchestrator
from core.confirmatory_metrics import derive_kairis_response
from core.report_builder import build_html_report, save_json
from scripts.evaluate_standalone_gates import (
    DEFAULT_ACCEPTANCE, DEFAULT_CORPUS, _git, _manifest_rows, numeric_equivalent,
)

GROUPS = ("G1", "G2", "G3", "G4")
CANDIDATE_FILES = ("agents/agent4_esc.py", "core/esc_engine.py")
WORKER = """
import json
import sys
from pathlib import Path
from agents.agent4_esc import Agent4_ESC

results = {}
for sample, spectrum, refs, config in json.load(sys.stdin):
    try:
        results[sample] = {"agent4": Agent4_ESC(spectrum, *refs, config).run(Path.cwd(), sample)}
    except (ValueError, TypeError, KeyError) as error:
        results[sample] = {"error": f"{type(error).__name__}: {error}"}
json.dump(results, sys.stdout, allow_nan=False)
"""


def compare_group(old, new, rtol, atol):
    old_flags, new_flags = set(old["flags"]), set(new["flags"])
    differences = []
    for field in ("Z0", "centroid", "gamma_mean", "lf_point"):
        left, right = old[field], new[field]
        if left != right and not numeric_equivalent(left, right, rtol, atol)[0]:
            differences.append(field)
    for coordinate in ("frequency", "real", "imag", "magnitude"):
        left = [point[coordinate] for point in old["points"]]
        right = [point[coordinate] for point in new["points"]]
        if not numeric_equivalent(left, right, rtol, atol)[0]:
            differences.append(f"points.{coordinate}")
    return {
        "legacy_numeric_changes": differences,
        "flags_added": sorted(new_flags - old_flags),
        "flags_removed": sorted(old_flags - new_flags),
        "old_status": old.get("status", "complete"),
        "new_status": new.get("status", "complete"),
        "passivity_applicable": new.get("passivity_applicable"),
        "passivity_violations": new.get("passivity_violation_count"),
    }


def summarize(cases):
    completed = [case for case in cases if "error" not in case]
    groups = {}
    for group in GROUPS:
        rows = [case["groups"][group] for case in completed]
        groups[group] = {
            "numeric_changes": sum(bool(row["legacy_numeric_changes"]) for row in rows),
            "flags_added": dict(Counter(flag for row in rows for flag in row["flags_added"])),
            "flags_removed": dict(Counter(flag for row in rows for flag in row["flags_removed"])),
            "abstentions_before": sum(row["old_status"] == "abstained" for row in rows),
            "abstentions_after": sum(row["new_status"] == "abstained" for row in rows),
            "passivity_applicable": sum(row["passivity_applicable"] is True for row in rows),
        }
    return {
        "samples": len(cases),
        "errors": len(cases) - len(completed),
        "groups": groups,
        "g2_interpretation_changes": sum(case["g2_interpretation_changed"] for case in completed),
        "agent5_rule_changes": sum(case["agent5_rules_changed"] for case in completed),
        "response_changes": sum(case["response_before"] != case["response_after"] for case in completed),
        "response_abstentions_before": sum(case["response_before"] == "undetermined" for case in completed),
        "response_abstentions_after": sum(case["response_after"] == "undetermined" for case in completed),
    }


def run(checkout, archive, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Use um diretório de saída novo: {output}")
    manifest_path = DEFAULT_CORPUS / "dataset_manifest.csv"
    manifest, _ = _manifest_rows(manifest_path)
    if not manifest:
        raise ValueError("O manifesto retrospectivo está vazio")
    candidate = {
        "head": _git(checkout, "rev-parse", "HEAD"),
        "working_tree_dirty": bool(_git(checkout, "status", "--porcelain")),
        "files_sha256": {path: sha256((checkout / path).read_bytes()).hexdigest() for path in CANDIDATE_FILES},
    }
    records, inputs = {}, []
    for row in manifest:
        sample = row["sample_id"]
        source = (DEFAULT_CORPUS / row["relative_path"]).resolve()
        artifact = (archive / "metrics" / f"{sample}_metrics.json").resolve()
        if (row["dataset_role"] == "external_confirmatory"
            or not source.is_relative_to(DEFAULT_CORPUS)
            or not artifact.is_relative_to(archive / "metrics")):
            raise ValueError(f"Entrada fora do corpus retrospectivo: {sample}")
        raw = artifact.read_bytes()
        metrics = json.loads(raw)
        provenance = metrics["provenance"]
        if (sample != metrics["sample"]
            or provenance["input_sha256"] != row["sha256"]
            or sha256(source.read_bytes()).hexdigest() != row["sha256"]):
            raise ValueError(f"Arquivo arquivado não corresponde ao manifesto: {sample}")
        records[sample] = (metrics, sha256(raw).hexdigest())
        agents = metrics["agents"]
        a2 = agents["agent2"]
        refs = [a2["Z0_G1"], a2.get("Z0_G2_complex", a2["Z0_G2"]), a2["Z0_G3"], a2["Z0_G4"]]
        spectrum = {key: agents["agent1"]["Z_data"][key] for key in ("frequency", "real", "imag")}
        inputs.append((sample, spectrum, refs, provenance["effective_config"]))
    result = subprocess.run(
        [sys.executable, "-c", WORKER], cwd=checkout, input=json.dumps(inputs),
        capture_output=True, encoding="utf-8", check=True,
    )
    for path, expected in candidate["files_sha256"].items():
        if sha256((checkout / path).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Código candidato mudou durante a execução: {path}")
    new_results = json.loads(result.stdout)
    tolerances = json.loads(DEFAULT_ACCEPTANCE.read_bytes())["numeric_tolerances"]
    rtol, atol = tolerances["relative"], tolerances["absolute"]
    cases, previews = [], []
    for row in manifest:
        sample = row["sample_id"]
        metrics, artifact_hash = records[sample]
        case = {"sample_id": sample, "family": row["family"], "artifact_sha256": artifact_hash}
        cases.append(case)
        new = new_results[sample]
        if "error" in new:
            case["error"] = new["error"]
            continue
        old_agent = metrics["agents"]["agent4"]
        agent = new["agent4"]
        summary = metrics["summary"]
        updated = {**summary, "esc_G2_lf": agent["G2"]["lf_point"], "esc_G2_flags": agent["G2"]["flags"]}
        old_rules = Agent5_Orchestrator._interpret(summary)
        new_rules = Agent5_Orchestrator._interpret(updated)
        case.update({
            "groups": {group: compare_group(old_agent[group], agent[group], rtol, atol) for group in GROUPS},
            "g2_interpretation_changed": old_agent["G2_interpretation"] != agent["G2_interpretation"],
            "agent5_rules_changed": old_rules != new_rules,
            "response_before": derive_kairis_response(summary),
            "response_after": derive_kairis_response(updated),
        })
        previews.append((sample, metrics, agent, updated, new_rules, case))
    report = {
        "scope": "exploratory retrospective replay with fixed archived DRT references",
        "review_checkout": {
            "head": _git(ROOT, "rev-parse", "HEAD"),
            "working_tree_dirty": bool(_git(ROOT, "status", "--porcelain")),
        },
        "candidate": candidate,
        "baseline_archive": str(archive),
        "baseline_commits": sorted({item[0]["provenance"]["kairis_git_commit"] for item in records.values()}),
        "manifest_sha256": sha256(manifest_path.read_bytes()).hexdigest(),
        "legacy_numeric_tolerances": {"relative": rtol, "absolute": atol},
        "all": summarize(cases),
        "by_family": {
            family: summarize([case for case in cases if case["family"] == family])
            for family in sorted({case["family"] for case in cases})
        },
        "cases": cases,
    }
    if previews:
        sample, metrics, agent, summary, rules, _ = max(
            previews, key=lambda item: sum(len(g["flags_added"]) for g in item[-1]["groups"].values()),
        )
        config = {**metrics["provenance"]["effective_config"], "report_d3_inline": False}
        build_html_report(
            output / "preview_esc_candidate.html", f"{sample} — ESC candidato",
            config, {**metrics["agents"], "agent4": agent}, summary, rules,
            provenance={"scope": report["scope"], "candidate": candidate, "archive": metrics["provenance"]},
        )
        report["preview"] = {"sample_id": sample, "file": "preview_esc_candidate.html"}
    save_json(output / "esc_group_review.json", report)
    print(json.dumps(report["all"], indent=2))
    return int(report["all"]["errors"] > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--esc-checkout", required=True, type=Path)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    return run(args.esc_checkout.resolve(), args.archive.resolve(), args.output.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
