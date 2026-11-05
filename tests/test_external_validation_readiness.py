from scripts.check_external_validation_readiness import evaluate_readiness


def test_external_cohort_is_technically_ready_but_administratively_locked():
    result = evaluate_readiness(check_git=False)
    gates = {item["name"]: item["passed"] for item in result["gates"]}
    assert gates["scientific_specification"] is True
    assert gates["canonical_source_hash"] is True
    assert gates["prepared_blind_manifest"] is True
    assert gates["reviewer_materials_specified"] is True
    assert gates["private_acceptances_and_conflicts"] is False
    assert gates["osf_registration"] is False
    assert result["ready_for_scientific_analysis"] is False
    assert result["analysis_lock"] == "locked"
