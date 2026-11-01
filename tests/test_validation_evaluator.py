from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.evaluate_validation_results import evaluate


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path, dirty: bool = False) -> tuple[Path, Path, dict]:
    corpus = tmp_path / "corpus"
    output = tmp_path / "output"
    row = {
        "sample_id": "SYN-01-01",
        "relative_path": "synthetic/sample.csv",
        "source_type": "synthetic",
        "dataset_role": "development_validation",
        "family": "randles_rc",
        "process_description": "ideal",
        "quality_class": "good",
        "intended_challenge": "baseline",
        "electrolyte_token": "KCl",
        "point_count": "10",
        "frequency_min_hz": "1",
        "frequency_max_hz": "10",
        "noise_relative": "0",
        "generator_parameters_json": json.dumps(
            {"Rs_ohm": 1.0, "Rct_ohm": 4.0, "Cdl_F": 0.02}
        ),
        "doi": "",
        "license": "test",
        "sha256": "abc123",
    }
    _write_csv(corpus / "dataset_manifest.csv", [row])
    _write_csv(corpus / "synthetic_truth.csv", [row])
    (output / "metrics").mkdir(parents=True)
    (output / "reports").mkdir(parents=True)
    metrics = {
        "sample": row["sample_id"],
        "provenance": {
            "input_sha256": "abc123",
            "kairis_git_commit": "release-commit",
            "kairis_git_dirty": dirty,
        },
        "summary": {"lin_kk_valid": True},
        "interpretation_rules": ["Consistência alta entre DRT e GSF."],
        "agents": {
            "agent2": {
                "R_inf": 1.01,
                "n_peaks": 1,
                "peaks": [{"tau": 0.08}],
            }
        },
    }
    (output / "metrics" / "SYN-01-01_metrics.json").write_text(
        json.dumps(metrics), encoding="utf-8"
    )
    (output / "reports" / "SYN-01-01_report.html").write_text(
        "<html>KAIRIS</html>", encoding="utf-8"
    )
    acceptance = {
        "status": "test",
        "thresholds": {
            "artifact_completeness_fraction_min": 1.0,
            "input_hash_match_fraction_min": 1.0,
            "clean_provenance_fraction_min": 1.0,
            "current_commit_fraction_min": 1.0,
            "randles_lin_kk_pass_fraction_min": 1.0,
            "randles_single_peak_fraction_min": 1.0,
            "randles_r_inf_relative_error_median_max": 0.02,
            "randles_r_inf_relative_error_worst_max": 0.02,
            "randles_log10_tau_error_median_max": 0.01,
            "randles_log10_tau_error_worst_max": 0.01,
        },
    }
    return corpus, output, acceptance


def test_clean_release_artifacts_pass_development_gates(tmp_path):
    corpus, output, acceptance = _fixture(tmp_path)
    result = evaluate(corpus, output, acceptance, current_commit="release-commit")
    assert result["all_development_gates_pass"] is True
    assert result["measured"]["randles_r_inf_relative_error_worst"] == pytest.approx(0.01)


def test_dirty_provenance_is_an_explicit_failure(tmp_path):
    corpus, output, acceptance = _fixture(tmp_path, dirty=True)
    result = evaluate(corpus, output, acceptance, current_commit="release-commit")
    assert result["gates"]["clean_provenance"] is False
    assert result["all_development_gates_pass"] is False
