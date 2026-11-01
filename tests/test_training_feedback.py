from __future__ import annotations

import json

import pytest

from core.training_feedback import TrainingFeedbackStore


def _metrics(llm_text="Interpretação originalmente aprovada."):
    return {
        "sample": "sample-a",
        "provenance": {"input_sha256": "abc123", "kairis_git_commit": "deadbeef"},
        "summary": {"R_ct": 10.5, "regime_drt": "mixed"},
        "interpretation_rules": ["Regime misto."],
        "llm_interpretation": llm_text,
    }


def test_feedback_rebuilds_dataset_and_latest_review_supersedes_previous(tmp_path):
    store = TrainingFeedbackStore(tmp_path)
    store.review(_metrics(), "approved")

    lines = store.dataset_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["messages"][-1]["content"] == "Interpretação originalmente aprovada."

    store.review(_metrics(), "corrected", "Interpretação corrigida por pesquisador.")
    lines = store.dataset_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["messages"][-1]["content"] == "Interpretação corrigida por pesquisador."
    assert store.stats()["corrected"] == 1
    assert store.stats()["dataset_examples"] == 1

    examples = store.prompt_examples(limit=3, max_chars=5000)
    assert examples[0]["reviewed_answer"] == "Interpretação corrigida por pesquisador."
    assert not list((tmp_path / "training").glob("*.tmp"))


def test_rejection_removes_sample_from_dataset_but_keeps_audit_history(tmp_path):
    store = TrainingFeedbackStore(tmp_path)
    store.review(_metrics(), "approved")
    store.review(_metrics(), "rejected", notes="Extrapolou os dados.")

    assert store.dataset_path.read_text(encoding="utf-8") == ""
    assert len(store.records()) == 2
    assert store.stats()["rejected"] == 1
    assert store.stats()["dataset_examples"] == 0


def test_approval_requires_an_llm_answer_and_correction_requires_text(tmp_path):
    store = TrainingFeedbackStore(tmp_path)
    with pytest.raises(ValueError, match="interpretação da LLM"):
        store.review(_metrics(llm_text=None), "approved")
    with pytest.raises(ValueError, match="correção textual"):
        store.review(_metrics(), "corrected")
