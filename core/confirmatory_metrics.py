"""Frozen response mapping and classification metrics for KAIRIS validation."""

from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np

EVALUABLE_CLASSES = ("kinetic", "diffusive", "pseudocapacitive", "mixed")


def derive_kairis_response(summary: dict[str, Any]) -> str:
    """Map two KAIRIS observables to the frozen external-review vocabulary.

    Ambiguous or spectrally inadmissible combinations abstain. This mapping is
    deliberately narrower than the report's explanatory compatibility rules.
    """
    if summary.get("lin_kk_valid") is not True:
        return "undetermined"
    drt = str(summary.get("regime_drt", ""))
    gsf = str(summary.get("regime_gsf", ""))
    diagnostic = summary.get("diagnostic")
    if (
        drt == "diffusion_dominated"
        and gsf == "pseudocapacitive"
        and diagnostic == "intercalation_pseudocapacitive"
    ):
        return "pseudocapacitive"
    mapping = {
        ("kinetic_dominated", "resistive"): "kinetic",
        ("diffusion_dominated", "diffusive"): "diffusive",
        ("mixed", "mixed"): "mixed",
    }
    return mapping.get((drt, gsf), "undetermined")


def human_consensus(first: str | None, second: str | None) -> str | None:
    a = str(first or "").strip().casefold()
    b = str(second or "").strip().casefold()
    if a == b and a in EVALUABLE_CLASSES:
        return a
    return None


def classification_metrics(
    truth: list[str], prediction: list[str], classes: tuple[str, ...] = EVALUABLE_CLASSES
) -> dict[str, Any]:
    if len(truth) != len(prediction):
        raise ValueError("truth and prediction lengths differ")
    confusion = {actual: {predicted: 0 for predicted in (*classes, "undetermined")} for actual in classes}
    for actual, predicted in zip(truth, prediction):
        if actual not in classes:
            raise ValueError(f"unsupported truth class: {actual}")
        predicted_key = predicted if predicted in classes else "undetermined"
        confusion[actual][predicted_key] += 1

    per_class: dict[str, Any] = {}
    recalls: list[float] = []
    f1_values: list[float] = []
    for label in classes:
        tp = confusion[label][label]
        support = sum(confusion[label].values())
        predicted_count = sum(confusion[actual][label] for actual in classes)
        recall = tp / support if support else None
        precision = tp / predicted_count if predicted_count else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall > 0
            else (0.0 if support else None)
        )
        if recall is not None:
            recalls.append(recall)
        if f1 is not None:
            f1_values.append(f1)
        per_class[label] = {
            "support": support,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    abstentions = sum(value not in classes for value in prediction)
    return {
        "n": len(truth),
        "supported_class_count": sum(per_class[label]["support"] > 0 for label in classes),
        "balanced_accuracy_supported_classes": float(np.mean(recalls)) if recalls else None,
        "macro_f1_supported_classes": float(np.mean(f1_values)) if f1_values else None,
        "kairis_abstention_fraction": abstentions / len(truth) if truth else None,
        "truth_distribution": dict(Counter(truth)),
        "prediction_distribution": dict(Counter(prediction)),
        "per_class": per_class,
        "confusion_matrix": confusion,
    }


def grouped_bootstrap_intervals(
    rows: list[dict[str, str]], *, draws: int, seed: int
) -> dict[str, list[float] | None]:
    groups = sorted({row["bootstrap_group"] for row in rows})
    if not rows or not groups:
        return {"balanced_accuracy_supported_classes": None, "macro_f1_supported_classes": None}
    by_group = {group: [row for row in rows if row["bootstrap_group"] == group] for group in groups}
    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = {
        "balanced_accuracy_supported_classes": [],
        "macro_f1_supported_classes": [],
    }
    for _ in range(draws):
        sampled_groups = rng.choice(groups, size=len(groups), replace=True)
        sampled = [row for group in sampled_groups for row in by_group[str(group)]]
        metrics = classification_metrics(
            [row["truth"] for row in sampled], [row["prediction"] for row in sampled]
        )
        for key in values:
            value = metrics[key]
            if value is not None and np.isfinite(value):
                values[key].append(float(value))
    return {
        key: [float(x) for x in np.quantile(items, [0.025, 0.975])] if items else None
        for key, items in values.items()
    }
