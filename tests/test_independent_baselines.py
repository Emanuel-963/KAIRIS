from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json

import numpy as np
import pytest

from core.independent_baselines import (
    prepare_eis_arrays,
    run_impedance_lin_kk,
    run_pyimpspec_tr_nnls,
)
from scripts.run_independent_baseline_smoke import assert_synthetic_only


def test_prepare_eis_arrays_filters_and_sorts_descending():
    f, z = prepare_eis_arrays([1.0, 100.0, -1.0, 10.0], [4, 1, 9, 2], [-4, -1, -9, -2])
    assert f.tolist() == [100.0, 10.0, 1.0]
    assert z.tolist() == [1 - 1j, 2 - 2j, 4 - 4j]


def test_lin_kk_adapter_uses_common_threshold_metrics():
    def fake_solver(f, z, **kwargs):
        fitted = z.copy()
        fitted[0] *= 1.2
        return 4, 0.8, fitted, np.zeros(len(z)), np.zeros(len(z))

    result = run_impedance_lin_kk(
        [100, 10, 1], [1, 2, 3], [-1, -2, -3],
        {"lin_kk_point_threshold_pct": 5, "lin_kk_max_failure_pct": 40,
         "lin_kk_rmse_threshold_pct": 20}, solver=fake_solver,
    )
    assert result["rc_elements"] == 4
    assert result["failure_pct"] == pytest.approx(100 / 3)
    assert result["pass"] is True


def test_drt_adapter_serializes_peaks_and_area():
    class FakeDataSet:
        def __init__(self, frequencies, impedances, label):
            self.frequencies = frequencies
            self.impedances = impedances

    def fake_solver(dataset, mode, lambda_value):
        return SimpleNamespace(
            impedances=dataset.impedances,
            time_constants=np.array([0.1, 1.0, 10.0]),
            gammas=np.array([0.0, 2.0, 0.0]),
            lambda_value=0.02,
            pseudo_chisqr=0.0,
            get_peaks=lambda threshold: (np.array([1.0]), np.array([2.0])),
        )

    result = run_pyimpspec_tr_nnls(
        [100, 10, 1], [1, 2, 3], [-1, -2, -3],
        dataset_factory=FakeDataSet, solver=fake_solver,
    )
    assert result["peak_count"] == 1
    assert result["peaks"] == [{"tau_s": 1.0, "gamma_ohm": 2.0}]
    assert result["normalized_complex_rmse_pct"] == 0.0
    assert result["integrated_area_log_tau_ohm"] > 0


def test_external_confirmatory_path_is_hard_blocked():
    project = Path(__file__).resolve().parents[1]
    with pytest.raises(RuntimeError, match="locked"):
        assert_synthetic_only(project / "data" / "external_confirmatory" / "cohort")


def test_frozen_schema_predates_external_execution():
    project = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (project / "config" / "baseline_comparison_schema_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["external_outputs_inspected_before_freeze"] is False
    assert schema["drt"]["primary_condition"] == {
        "mode": "real",
        "lambda_value": -1.0,
        "lambda_rule": "pyimpspec automatic suggestion",
    }
