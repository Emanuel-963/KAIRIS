from scripts.run_retrospective_baseline_comparison import (
    aggregate_records,
    aggregate_sensitivity,
)


def _row(family, lin_status, lin_a, drt_status, drt_a, k_lin=True, b_lin=True, kp=1, bp=1):
    return {
        "family": family,
        "source_type": "synthetic",
        "lin_kk_status": lin_status,
        "lin_kk_agreement": lin_a,
        "drt_primary_status": drt_status,
        "drt_peak_count_agreement": drt_a,
        "kairis_lin_kk_valid": k_lin,
        "baseline_lin_kk_valid": b_lin if lin_status == "completed" else None,
        "kairis_drt_peak_count": kp,
        "baseline_drt_peak_count": bp if drt_status == "completed" else None,
    }


def test_aggregate_retains_failures_and_builds_matrices():
    rows = [
        _row("A", "completed", True, "completed", True),
        _row("A", "completed", False, "completed", False, True, False, 2, 1),
        _row("B", "failed", None, "failed", None),
    ]
    result = aggregate_records(rows)
    assert result["sample_count"] == 3
    assert result["lin_kk_failed"] == 1
    assert result["lin_kk_agreement_fraction"] == 0.5
    assert result["drt_primary_failed"] == 1
    assert result["drt_peak_agreement_fraction"] == 0.5
    assert result["lin_kk_matrix"]["kairis_True|baseline_False"] == 1
    assert result["drt_peak_count_matrix"]["kairis_2|baseline_1"] == 1
    assert result["families"]["B"]["lin_kk_failed"] == 1


def test_sensitivity_summary_retains_condition_failures():
    records = [
        {
            "sample_id": "A",
            "independent_drt": {
                "real_lambda_-1": {"status": "completed", "result": {"peak_count": 1, "normalized_complex_rmse_pct": 0.2}},
                "imaginary_lambda_-1": {"status": "completed", "result": {"peak_count": 2, "normalized_complex_rmse_pct": 0.4}},
            },
        },
        {
            "sample_id": "B",
            "independent_drt": {
                "real_lambda_-1": {"status": "completed", "result": {"peak_count": 2, "normalized_complex_rmse_pct": 0.6}},
                "imaginary_lambda_-1": {"status": "failed", "result": None, "error": "did not converge"},
            },
        },
    ]
    result = aggregate_sensitivity(records, "real_lambda_-1")
    assert result["real_lambda_-1"]["peak_count_agreement_with_primary_fraction"] == 1.0
    assert result["imaginary_lambda_-1"]["completed"] == 1
    assert result["imaginary_lambda_-1"]["failed"] == 1
    assert result["imaginary_lambda_-1"]["failures"][0]["sample_id"] == "B"
