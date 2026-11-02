from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.analyze_synthetic_recovery import (
    expected_relaxation_times,
    match_relaxation_times,
)
from scripts.build_blinded_review_pack import build_pack


def test_expected_times_and_global_peak_assignment():
    expected = expected_relaxation_times(
        "double_zarc",
        {"R1_ohm": 2.0, "Q1": 0.05, "n1": 1.0, "R2_ohm": 5.0, "Q2": 0.2, "n2": 1.0},
    )
    assert expected == pytest.approx([0.1, 1.0])
    matches = match_relaxation_times(expected, [1.1, 0.09, 50.0])
    assert [item["observed_tau_s"] for item in matches] == pytest.approx([0.09, 1.1])
    assert max(item["absolute_log10_error"] for item in matches) < 0.05


def test_blinded_pack_does_not_expose_labels_to_reviewer(tmp_path: Path):
    corpus, output, destination = tmp_path / "corpus", tmp_path / "output", tmp_path / "pack"
    corpus.mkdir()
    (output / "metrics").mkdir(parents=True)
    row = {
        "sample_id": "SECRET-SAMPLE",
        "relative_path": "synthetic/secret_family.csv",
        "source_type": "synthetic",
        "family": "secret_family",
    }
    with (corpus / "dataset_manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    metrics = {
        "agents": {
            "agent1": {
                "Z_data": {
                    "frequency": [100.0, 10.0, 1.0],
                    "real": [1.0, 2.0, 3.0],
                    "imag": [-0.1, -0.5, -0.2],
                }
            }
        },
        "summary": {
            "regime_drt": "diffusion_dominated",
            "regime_gsf": "pseudocapacitive",
            "diagnostic": "intercalation_pseudocapacitive",
            "drt_gsf_inconsistent": False,
        },
    }
    (output / "metrics" / "SECRET-SAMPLE_metrics.json").write_text(
        json.dumps(metrics), encoding="utf-8"
    )
    result = build_pack(corpus, output, destination, "fixed-seed", figures=False)
    reviewer_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (destination / "reviewer").rglob("*")
        if path.is_file()
    )
    key_text = (destination / "coordinator_only" / "blinding_key.csv").read_text(encoding="utf-8")
    assert result["case_count"] == 1
    assert "SECRET-SAMPLE" not in reviewer_text
    assert "secret_family" not in reviewer_text
    assert "diffusion_dominated" not in reviewer_text
    assert "SECRET-SAMPLE" in key_text
    assert "intercalation_pseudocapacitive" in key_text
