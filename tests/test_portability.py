from __future__ import annotations

import json

from core.config_loader import load_config
from run_pipeline import sample_identifier
from setup_kairis import compatible_installed_model, memory_profile, recommended_model


def test_nested_samples_receive_distinct_identifiers(tmp_path):
    first = tmp_path / "cell_a" / "spectrum.txt"
    second = tmp_path / "cell_b" / "spectrum.txt"

    assert sample_identifier(first, tmp_path) == "cell_a__spectrum"
    assert sample_identifier(second, tmp_path) == "cell_b__spectrum"


def test_flat_sample_keeps_legacy_name(tmp_path):
    assert sample_identifier(tmp_path / "spectrum.txt", tmp_path) == "spectrum"


def test_environment_can_disable_llm_for_containers(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"llm_enabled": True}), encoding="utf-8")
    monkeypatch.setenv("KAIRIS_LLM_ENABLED", "false")

    assert load_config(path)["llm_enabled"] is False


def test_memory_profiles_choose_lightweight_models():
    config = {
        "ollama_model_profiles": {
            "ram_4gb": "small:1b",
            "ram_8gb": "balanced:4b",
            "ram_16gb_plus": "balanced:4b",
        }
    }

    assert memory_profile(4.0) == "ram_4gb"
    assert memory_profile(8.0) == "ram_8gb"
    assert memory_profile(16.0) == "ram_16gb_plus"
    assert recommended_model(config, 4.0) == "small:1b"
    assert recommended_model(config, 8.0) == "balanced:4b"


def test_installed_model_selection_respects_low_memory():
    models = ["large:8b", "gemma3:1b", "gemma3:4b"]

    assert compatible_installed_model(models, 4.0) == "gemma3:1b"
    assert compatible_installed_model(models, 8.0) == "gemma3:4b"
    assert compatible_installed_model(["large:8b"], 4.0) is None
