from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from core.config_loader import load_config
from core.eis_loader import load_btlab


PROJECT = Path(__file__).resolve().parents[1]
CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"


def test_validation_corpus_has_declared_scale_sources_and_integrity():
    with (CORPUS / "dataset_manifest.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 198
    assert sum(row["source_type"] == "synthetic" for row in rows) == 72
    assert sum(row["source_type"] == "experimental_public" for row in rows) == 54
    assert sum(row["source_type"] == "synthetic_publication" for row in rows) == 72
    assert sum(row["dataset_role"] == "training_benchmark" for row in rows) == 45
    assert sum(row["dataset_role"] == "published_benchmark_holdout" for row in rows) == 27
    assert len({row["family"] for row in rows if row["source_type"] == "synthetic"}) == 12

    for row in rows:
        path = CORPUS / row["relative_path"]
        assert path.is_file()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"]


def test_every_validation_spectrum_is_loadable_by_kairis():
    config = load_config(PROJECT / "config" / "protocol_config.json")
    with (CORPUS / "dataset_manifest.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    for row in rows:
        spectrum = load_btlab(CORPUS / row["relative_path"], config)
        assert len(spectrum["frequency"]) == int(row["point_count"]), row["sample_id"]

