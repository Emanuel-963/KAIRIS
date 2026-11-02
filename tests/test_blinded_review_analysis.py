from __future__ import annotations

import pytest

from scripts.analyze_blinded_reviews import analyze_reviews, cohen_kappa, weighted_kappa


def test_kappa_helpers_cover_perfect_and_partial_agreement():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    assert weighted_kappa([1, 2, 3, 4], [1, 2, 3, 4]) == 1.0
    assert weighted_kappa([1, 2, 3, 4], [1, 2, 4, 4]) < 1.0


def test_review_analysis_reports_abstentions_and_disagreements():
    reviewer_a = {
        "KRS-1": {
            "spectrum_quality": "acceptable",
            "dominant_response": "kinetic",
            "intercalation_pseudocapacitive": "no",
            "exclude_from_analysis": "no",
            "estimated_process_count": "1",
            "confidence_1_to_5": "4",
        },
        "KRS-2": {
            "spectrum_quality": "questionable",
            "dominant_response": "undetermined",
            "intercalation_pseudocapacitive": "uncertain",
            "exclude_from_analysis": "no",
            "estimated_process_count": "undetermined",
            "confidence_1_to_5": "2",
        },
    }
    reviewer_b = {
        "KRS-1": {
            "spectrum_quality": "acceptable",
            "dominant_response": "kinetic",
            "intercalation_pseudocapacitive": "no",
            "exclude_from_analysis": "no",
            "estimated_process_count": "1",
            "confidence_1_to_5": "5",
        },
        "KRS-2": {
            "spectrum_quality": "acceptable",
            "dominant_response": "mixed",
            "intercalation_pseudocapacitive": "uncertain",
            "exclude_from_analysis": "yes",
            "estimated_process_count": "2",
            "confidence_1_to_5": "2",
        },
    }
    result = analyze_reviews(reviewer_a, reviewer_b, seed=7, bootstrap_draws=100)
    assert result["paired_cases"] == 2
    assert result["fields"]["spectrum_quality"]["percent_agreement"] == pytest.approx(50.0)
    assert result["fields"]["dominant_response"]["reviewer_a_abstention_fraction"] == 0.5
    assert result["fields"]["estimated_process_count"]["paired_numeric_count"] == 1
    assert any(item["case_id"] == "KRS-2" for item in result["disagreements"])
