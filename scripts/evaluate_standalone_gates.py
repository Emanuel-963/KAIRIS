"""Execute frozen H3-H6 gates for standalone GSF and ESC over the EIS corpus."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from agents.agent4_esc import Agent4_ESC  # noqa: E402
from core.artifact_io import atomic_write_text  # noqa: E402
from core.config_loader import load_config  # noqa: E402
from core.eis_loader import load_btlab  # noqa: E402
from core.gsf_engine import calculate_gsf  # noqa: E402
from core.report_builder import to_jsonable  # noqa: E402


DEFAULT_CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"
DEFAULT_CONFIG = PROJECT / "config" / "protocol_config.json"
DEFAULT_ACCEPTANCE = PROJECT / "config" / "standalone_validation_acceptance_v1.json"
DEFAULT_OUTPUT = PROJECT / "output" / "standalone_validation_v1"
DEFAULT_GSF_CHECKOUT = PROJECT.parent / "kairis-gsf-standalone"
DEFAULT_ESC_CHECKOUT = PROJECT.parent / "kairis-esc-standalone"
ARRAY_KEYS = ("x_n", "y_n", "q", "alpha", "kphi", "gradient")


def _manifest_rows(path: Path, limit: int | None = None) -> tuple[list[dict[str, str]], int]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        all_rows = list(csv.DictReader(stream))
    return (all_rows[:limit] if limit else all_rows), len(all_rows)


def _git(checkout: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=True,
    )
    return result.stdout.strip()


def verify_checkout(checkout: Path, expected_commit: str, module: str) -> dict[str, Any]:
    """Reject a missing, modified or non-frozen standalone checkout."""
    script = checkout / f"standalone_{module}.py"
    if not script.is_file():
        raise RuntimeError(
            f"Checkout {module.upper()} ausente ou incompleto: {checkout}. "
            f"Use --{module}-checkout para indicar a branch congelada."
        )
    observed = _git(checkout, "rev-parse", "HEAD")
    if observed != expected_commit:
        raise RuntimeError(
            f"Commit {module.upper()} incorreto: esperado {expected_commit}, observado {observed}."
        )
    dirty = _git(checkout, "status", "--porcelain")
    if dirty:
        raise RuntimeError(f"Checkout {module.upper()} possui alterações locais: {checkout}")
    return {"path": str(checkout.resolve()), "commit": observed, "clean": True}


def _run_worker(
    mode: str,
    checkout: Path,
    corpus: Path,
    manifest: Path,
    config: Path,
    acceptance: Path,
    output: Path,
    limit: int | None,
) -> Path:
    command = [
        sys.executable,
        str(PROJECT / "scripts" / "standalone_validation_worker.py"),
        "--mode",
        mode,
        "--corpus",
        str(corpus),
        "--manifest",
        str(manifest),
        "--config",
        str(config),
        "--acceptance",
        str(acceptance),
        "--output",
        str(output),
    ]
    if limit:
        command.extend(("--limit", str(limit)))
    result = subprocess.run(
        command,
        cwd=checkout,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=3600,
    )
    if result.returncode not in (0, 2):
        raise RuntimeError(
            f"Worker {mode.upper()} falhou com código {result.returncode}:\n{result.stderr}"
        )
    return output / f"{mode}_worker_results.json"


def _array(value: Any) -> np.ndarray:
    return np.asarray([np.nan if item is None else item for item in value], dtype=float)


def numeric_equivalent(
    observed: Any, expected: Any, rtol: float, atol: float
) -> tuple[bool, float]:
    """Compare shape, NaN locations and finite values under frozen tolerances."""
    left = _array(observed) if isinstance(observed, list) else np.asarray(observed, dtype=float)
    right = np.asarray(expected, dtype=float)
    if left.shape != right.shape or not np.array_equal(np.isnan(left), np.isnan(right)):
        return False, math.inf
    finite = np.isfinite(left) & np.isfinite(right)
    if not np.any(finite):
        return True, 0.0
    scale = np.maximum(np.abs(right[finite]), atol)
    maximum = float(np.max(np.abs(left[finite] - right[finite]) / scale))
    return bool(np.allclose(left, right, rtol=rtol, atol=atol, equal_nan=True)), maximum


def _gsf_result(
    record: dict[str, Any], source: Path, config: dict[str, Any], rtol: float, atol: float
) -> dict[str, Any]:
    if record.get("status") != "complete":
        return {
            "sample_id": record["sample_id"],
            "complete": False,
            "equivalent": False,
            "scale_invariant": False,
            "artifact_complete": False,
            "error": record.get("error", "worker incomplete"),
        }
    standalone = json.loads(Path(record["metrics_path"]).read_text(encoding="utf-8"))
    spectrum = load_btlab(source, config)
    integrated = calculate_gsf(
        spectrum["frequency"], spectrum["real"], spectrum["imag"], config
    )
    comparisons = [
        numeric_equivalent(standalone[key], integrated[key], rtol, atol) for key in ARRAY_KEYS
    ]
    scalar_pairs = (
        (standalone["I_crit"], integrated["I_crit"]),
        (standalone["f_Icrit"], integrated["f_Icrit"]),
    )
    scalar_ok = all(np.isclose(a, b, rtol=rtol, atol=atol) for a, b in scalar_pairs)
    equivalent = (
        all(item[0] for item in comparisons)
        and scalar_ok
        and standalone["regime_gsf"] == integrated["regime_gsf"]
    )
    errors = [item[1] for item in comparisons if math.isfinite(item[1])]
    return {
        "sample_id": record["sample_id"],
        "complete": True,
        "equivalent": bool(equivalent),
        "equivalence_max_relative_error": max(errors, default=0.0),
        "scale_invariant": bool(record["scale_invariant"]),
        "scale_max_tolerance_ratio": record.get("scale_max_tolerance_ratio"),
        "artifact_complete": bool(record["artifact_complete"]),
    }


def _esc_result(
    record: dict[str, Any], source: Path, config: dict[str, Any], acceptance: dict[str, Any]
) -> dict[str, Any]:
    tolerances = acceptance["numeric_tolerances"]
    rtol, atol = float(tolerances["relative"]), float(tolerances["absolute"])
    inverse_limit = float(tolerances["esc_inverse_relative_error_max"])
    singularity = float(tolerances["esc_inverse_singularity_cutoff"])
    passivity_tolerance = float(tolerances["esc_passivity_magnitude_tolerance"])
    if record.get("status") != "complete":
        return {
            "sample_id": record["sample_id"],
            "complete": False,
            "equivalent": False,
            "inverse_consistent": False,
            "passivity_applicable": False,
            "passivity_bound": False,
            "artifact_complete": False,
            "error": record.get("error", "worker incomplete"),
        }

    standalone = json.loads(Path(record["metrics_path"]).read_text(encoding="utf-8"))
    spectrum = load_btlab(source, config)
    z_data = {
        "frequency": spectrum["frequency"],
        "real": spectrum["real"],
        "imag": spectrum["imag"],
    }
    real_ref = complex(*record["references"]["NOMINAL_REAL"])
    complex_ref = complex(*record["references"]["NOMINAL_COMPLEX"])
    integrated = Agent4_ESC(z_data, real_ref, complex_ref, None, None, config).run(
        PROJECT / "output", record["sample_id"]
    )
    group_pairs = (
        (standalone["groups"]["NOMINAL_REAL"], integrated["G1"]),
        (standalone["groups"]["NOMINAL_COMPLEX"], integrated["G2"]),
    )
    equivalent = True
    comparison_errors: list[float] = []
    for observed, expected in group_pairs:
        for key in ("centroid", "lf_point", "gamma_mean"):
            matches, error = numeric_equivalent(observed[key], expected[key], rtol, atol)
            equivalent = equivalent and matches
            if math.isfinite(error):
                comparison_errors.append(error)
        observed_points = observed["points"]
        expected_points = expected["points"]
        if len(observed_points) != len(expected_points):
            equivalent = False
        else:
            for coordinate in ("frequency", "real", "imag", "magnitude"):
                matches, error = numeric_equivalent(
                    [point[coordinate] for point in observed_points],
                    [point[coordinate] for point in expected_points],
                    rtol,
                    atol,
                )
                equivalent = equivalent and matches
                if math.isfinite(error):
                    comparison_errors.append(error)
        equivalent = equivalent and observed["flags"] == expected["flags"]

    real_group = standalone["groups"]["NOMINAL_REAL"]
    points = real_group["points"]
    gamma = np.asarray([complex(point["real"], point["imag"]) for point in points])
    frequency = np.asarray([point["frequency"] for point in points])
    order = np.argsort(spectrum["frequency"])[::-1]
    expected_frequency = spectrum["frequency"][order]
    impedance = spectrum["real"][order] + 1j * spectrum["imag"][order]
    frequency_matches = len(frequency) == len(expected_frequency) and np.allclose(
        frequency, expected_frequency, rtol=rtol, atol=atol
    )
    denominator = 1.0 - gamma
    eligible_inverse = np.abs(denominator) >= singularity
    if frequency_matches and np.any(eligible_inverse):
        reconstructed = real_ref * (1.0 + gamma[eligible_inverse]) / denominator[eligible_inverse]
        inverse_errors = np.abs(reconstructed - impedance[eligible_inverse]) / np.maximum(
            np.abs(impedance[eligible_inverse]), np.finfo(float).eps
        )
        inverse_max = float(np.max(inverse_errors))
        inverse_consistent = inverse_max <= inverse_limit
    else:
        inverse_max, inverse_consistent = math.inf, False

    eligible_passivity = spectrum["real"][order] >= -atol
    passivity_applicable = bool(frequency_matches and np.any(eligible_passivity))
    passivity_max = (
        float(np.max(np.abs(gamma[eligible_passivity]))) if passivity_applicable else math.nan
    )
    passivity_bound = passivity_applicable and passivity_max <= 1.0 + passivity_tolerance
    return {
        "sample_id": record["sample_id"],
        "complete": True,
        "equivalent": bool(equivalent),
        "equivalence_max_relative_error": max(comparison_errors, default=0.0),
        "inverse_consistent": bool(inverse_consistent),
        "inverse_max_relative_error": inverse_max,
        "passivity_applicable": passivity_applicable,
        "passivity_bound": bool(passivity_bound),
        "passivity_max_gamma": passivity_max,
        "artifact_complete": bool(record["artifact_complete"]),
    }


def _fraction(records: list[dict[str, Any]], key: str, applicable: str | None = None) -> float:
    selected = [record for record in records if applicable is None or record.get(applicable) is True]
    return sum(record.get(key) is True for record in selected) / len(selected) if selected else 0.0


def evaluate_records(
    rows: list[dict[str, str]],
    corpus: Path,
    config: dict[str, Any],
    acceptance: dict[str, Any],
    gsf_worker: dict[str, Any],
    esc_worker: dict[str, Any],
) -> tuple[dict[str, float], dict[str, bool], list[dict[str, Any]]]:
    """Evaluate worker artifacts against integrated engines and frozen gates."""
    gsf_by_id = {item["sample_id"]: item for item in gsf_worker["records"]}
    esc_by_id = {item["sample_id"]: item for item in esc_worker["records"]}
    tolerances = acceptance["numeric_tolerances"]
    gsf_results, esc_results, samples = [], [], []
    for row in rows:
        sample, source = row["sample_id"], corpus / row["relative_path"]
        gsf = _gsf_result(
            gsf_by_id.get(sample, {"sample_id": sample, "status": "missing"}),
            source,
            config,
            float(tolerances["relative"]),
            float(tolerances["absolute"]),
        )
        esc = _esc_result(
            esc_by_id.get(sample, {"sample_id": sample, "status": "missing"}),
            source,
            config,
            acceptance,
        )
        gsf_results.append(gsf)
        esc_results.append(esc)
        samples.append({"sample_id": sample, "gsf": gsf, "esc": esc})

    completion = sum(
        gsf["complete"] and esc["complete"] for gsf, esc in zip(gsf_results, esc_results)
    ) / len(rows) if rows else 0.0
    measured = {
        "supported_input_completion_fraction": completion,
        "gsf_equivalence_fraction": _fraction(gsf_results, "equivalent"),
        "gsf_scale_invariance_fraction": _fraction(gsf_results, "scale_invariant"),
        "gsf_artifact_completeness_fraction": _fraction(gsf_results, "artifact_complete"),
        "esc_equivalence_fraction": _fraction(esc_results, "equivalent"),
        "esc_inverse_consistency_fraction": _fraction(esc_results, "inverse_consistent"),
        "esc_passivity_bound_fraction": _fraction(
            esc_results, "passivity_bound", "passivity_applicable"
        ),
        "esc_artifact_completeness_fraction": _fraction(esc_results, "artifact_complete"),
    }
    gates = {
        key.removesuffix("_min"): measured[key.removesuffix("_min")] >= float(value)
        for key, value in acceptance["gates"].items()
    }
    return measured, gates, samples


def _html_report(payload: dict[str, Any]) -> str:
    gate_rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{payload['measured'][name]:.6f}</td>"
        f"<td>{'PASS' if passed else 'FAIL'}</td></tr>"
        for name, passed in payload["gates"].items()
    )
    failed_rows = []
    for sample in payload["sample_results"]:
        failures = [
            f"GSF {key}" for key in ("complete", "equivalent", "scale_invariant", "artifact_complete")
            if sample["gsf"].get(key) is not True
        ]
        failures.extend(
            f"ESC {key}" for key in ("complete", "equivalent", "inverse_consistent", "artifact_complete")
            if sample["esc"].get(key) is not True
        )
        if sample["esc"].get("passivity_applicable") and not sample["esc"].get("passivity_bound"):
            failures.append("ESC passivity_bound")
        if failures:
            failed_rows.append(
                f"<tr><td>{html.escape(sample['sample_id'])}</td><td>{html.escape(', '.join(failures))}</td></tr>"
            )
    scope = "corpus completo" if payload["full_corpus"] else "subconjunto de smoke test"
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>KAIRIS H3–H6 gates</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;background:#eef3f4;color:#172126}}main{{max-width:1100px;margin:auto;padding:24px}}section{{background:white;padding:20px;margin:16px 0;border-radius:10px}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #d8e1e5;padding:8px;text-align:left}}.pass{{color:#176b45}}.fail{{color:#a12d2d}}</style></head><body><main>
<h1>KAIRIS — validação automática H3–H6</h1><p>Escopo: {scope}. Amostras: {payload['samples_evaluated']} de {payload['samples_in_manifest']}.</p>
<section><h2 class="{'pass' if payload['all_gates_pass'] else 'fail'}">Resultado: {'APROVADO' if payload['all_gates_pass'] else 'REPROVADO'}</h2>
<table><thead><tr><th>Gate</th><th>Medido</th><th>Estado</th></tr></thead><tbody>{gate_rows}</tbody></table></section>
<section><h2>Falhas por amostra</h2><table><thead><tr><th>Amostra</th><th>Falhas</th></tr></thead><tbody>{''.join(failed_rows) or '<tr><td colspan="2">Nenhuma</td></tr>'}</tbody></table></section>
<section><h2>Proveniência</h2><pre>{html.escape(json.dumps(payload['provenance'], ensure_ascii=False, indent=2))}</pre></section>
</main></body></html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--acceptance", type=Path, default=DEFAULT_ACCEPTANCE)
    parser.add_argument("--gsf-checkout", type=Path, default=DEFAULT_GSF_CHECKOUT)
    parser.add_argument("--esc-checkout", type=Path, default=DEFAULT_ESC_CHECKOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, help="Smoke test; não substitui o corpus completo")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--enforce", action="store_true", help="retornar código 2 se algum gate falhar")
    args = parser.parse_args()

    corpus, config_path = args.corpus.resolve(), args.config.resolve()
    acceptance_path, output = args.acceptance.resolve(), args.output.resolve()
    report_path = output / "standalone_gate_report.json"
    if report_path.exists() and not args.overwrite:
        parser.error(f"relatório já existe: {report_path}; use --overwrite conscientemente")
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    branch_info = acceptance["branches"]
    checkouts = {
        "gsf": verify_checkout(
            args.gsf_checkout.resolve(), branch_info["gsf"]["commit"], "gsf"
        ),
        "esc": verify_checkout(
            args.esc_checkout.resolve(), branch_info["esc"]["commit"], "esc"
        ),
    }
    manifest = corpus / "dataset_manifest.csv"
    rows, total = _manifest_rows(manifest, args.limit)
    if not rows:
        parser.error("manifesto sem amostras")
    output.mkdir(parents=True, exist_ok=True)
    gsf_path = _run_worker(
        "gsf", args.gsf_checkout.resolve(), corpus, manifest, config_path,
        acceptance_path, output / "gsf", args.limit,
    )
    esc_path = _run_worker(
        "esc", args.esc_checkout.resolve(), corpus, manifest, config_path,
        acceptance_path, output / "esc", args.limit,
    )
    gsf_worker = json.loads(gsf_path.read_text(encoding="utf-8"))
    esc_worker = json.loads(esc_path.read_text(encoding="utf-8"))
    config = load_config(config_path)
    measured, gates, samples = evaluate_records(
        rows, corpus, config, acceptance, gsf_worker, esc_worker
    )
    payload = {
        "format": "KAIRIS-standalone-gate-report-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_plan_tag": "validation-plan-v1.0",
        "confirmatory": False,
        "full_corpus": args.limit is None and len(rows) == total,
        "samples_evaluated": len(rows),
        "samples_in_manifest": total,
        "measured": measured,
        "thresholds": acceptance["gates"],
        "gates": gates,
        "all_gates_pass": all(gates.values()),
        "sample_results": samples,
        "provenance": {
            "integrated_commit": _git(PROJECT, "rev-parse", "HEAD"),
            "standalone_checkouts": checkouts,
            "python": sys.version,
            "platform": platform.platform(),
            "corpus": str(corpus),
            "config": str(config_path),
            "acceptance": str(acceptance_path),
        },
    }
    atomic_write_text(
        report_path,
        json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    atomic_write_text(output / "standalone_gate_report.html", _html_report(payload))
    print(json.dumps({key: payload[key] for key in ("full_corpus", "samples_evaluated", "gates", "all_gates_pass")}, ensure_ascii=False, indent=2))
    return 2 if args.enforce and not payload["all_gates_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
