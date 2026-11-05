from __future__ import annotations

import json
from pathlib import Path

from core.confirmatory_metrics import (
    classification_metrics,
    derive_kairis_response,
    grouped_bootstrap_intervals,
    human_consensus,
)
from scripts.analyze_external_confirmation import evaluate_integrity


def test_frozen_kairis_response_mapping_abstains_on_ambiguous_combinations():
    base = {"lin_kk_valid": True, "diagnostic": None}
    assert derive_kairis_response({**base, "regime_drt": "kinetic_dominated", "regime_gsf": "resistive"}) == "kinetic"
    assert derive_kairis_response({**base, "regime_drt": "diffusion_dominated", "regime_gsf": "diffusive"}) == "diffusive"
    assert derive_kairis_response({**base, "regime_drt": "mixed", "regime_gsf": "mixed"}) == "mixed"
    assert derive_kairis_response({**base, "regime_drt": "kinetic_dominated", "regime_gsf": "pseudocapacitive"}) == "undetermined"
    assert derive_kairis_response({**base, "lin_kk_valid": False, "regime_drt": "mixed", "regime_gsf": "mixed"}) == "undetermined"


def test_intercalation_pattern_maps_to_pseudocapacitive():
    assert derive_kairis_response(
        {
            "lin_kk_valid": True,
            "regime_drt": "diffusion_dominated",
            "regime_gsf": "pseudocapacitive",
            "diagnostic": "intercalation_pseudocapacitive",
        }
    ) == "pseudocapacitive"


def test_human_consensus_and_abstention_scoring_are_explicit():
    assert human_consensus("kinetic", "kinetic") == "kinetic"
    assert human_consensus("kinetic", "mixed") is None
    assert human_consensus("undetermined", "undetermined") is None
    result = classification_metrics(
        ["kinetic", "diffusive", "mixed"],
        ["kinetic", "undetermined", "kinetic"],
    )
    assert result["n"] == 3
    assert result["kairis_abstention_fraction"] == 1 / 3
    assert result["confusion_matrix"]["diffusive"]["undetermined"] == 1
    assert result["balanced_accuracy_supported_classes"] == 1 / 3


def test_grouped_bootstrap_is_reproducible():
    rows = [
        {"truth": "kinetic", "prediction": "kinetic", "bootstrap_group": "A"},
        {"truth": "diffusive", "prediction": "undetermined", "bootstrap_group": "B"},
    ]
    first = grouped_bootstrap_intervals(rows, draws=50, seed=7)
    second = grouped_bootstrap_intervals(rows, draws=50, seed=7)
    assert first == second
    assert first["balanced_accuracy_supported_classes"] is not None


def test_integrity_gate_requires_complete_hashed_artifacts(tmp_path: Path):
    cohort = tmp_path / "cohort"
    prepared = cohort / "prepared_blind"
    prepared.mkdir(parents=True)
    (prepared / "blind_manifest.csv").write_text(
        "case_id,relative_path,sha256\nCASE-1,CASE-1.csv,abc\n", encoding="utf-8"
    )
    output = tmp_path / "output"
    (output / "metrics").mkdir(parents=True)
    (output / "reports").mkdir()
    (output / "external_run_manifest.json").write_text(
        json.dumps({"cases": [{"case_id": "CASE-1", "status": "completed"}]}),
        encoding="utf-8",
    )
    (output / "metrics" / "CASE-1_metrics.json").write_text(
        json.dumps({"provenance": {"input_sha256": "abc"}}), encoding="utf-8"
    )
    (output / "reports" / "CASE-1_report.html").write_text("ok", encoding="utf-8")

    result = evaluate_integrity(output, cohort)

    assert result["passed"] is True
    assert result["observed"]["pipeline_completion_fraction"] == 1.0
