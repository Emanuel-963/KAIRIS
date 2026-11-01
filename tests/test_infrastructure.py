from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pytest

import core.report_builder as report_builder
import run_pipeline
from core.artifact_io import atomic_text_writer
from core.config_validator import validate_config
from core.memory_store import KairisMemoryStore
from core.report_builder import save_json
from core.runtime_control import read_llm_enabled, write_llm_enabled


PROJECT_DIR = Path(__file__).resolve().parents[1]


def test_atomic_writer_preserves_previous_file_on_failure(tmp_path):
    destination = tmp_path / "artifact.json"
    destination.write_text("previous", encoding="utf-8")

    with pytest.raises(RuntimeError):
        with atomic_text_writer(destination) as handle:
            handle.write("partial")
            raise RuntimeError("interrupted")

    assert destination.read_text(encoding="utf-8") == "previous"
    assert not (tmp_path / "artifact.json.tmp").exists()


def test_save_json_is_atomic_and_strict(tmp_path):
    destination = tmp_path / "metrics.json"
    save_json(destination, {"value": 2.0})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"value": 2.0}
    assert not (tmp_path / "metrics.json.tmp").exists()


def test_current_config_satisfies_schema():
    config = json.loads((PROJECT_DIR / "config" / "protocol_config.json").read_text(encoding="utf-8"))
    validate_config(config)


def test_schema_reports_missing_and_out_of_range_values():
    config = json.loads((PROJECT_DIR / "config" / "protocol_config.json").read_text(encoding="utf-8"))
    del config["protocol_name"]
    config["ollama_temperature"] = 3.0

    with pytest.raises(ValueError) as error:
        validate_config(config)

    message = str(error.value)
    assert "protocol_name" in message
    assert "ollama_temperature" in message


def test_existing_consolidated_result_is_skipped_without_overwrite(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (output_dir / "metrics").mkdir(parents=True)
    sample = input_dir / "sample.txt"
    sample.write_text("input", encoding="utf-8")
    (output_dir / "metrics" / "sample_metrics.json").write_text("{}", encoding="utf-8")
    calls = []
    monkeypatch.setattr(run_pipeline, "run_sample", lambda *args, **kwargs: calls.append(args))

    assert run_pipeline.process_file(sample, input_dir, output_dir, {}, overwrite=False)
    assert calls == []
    assert run_pipeline.process_file(sample, input_dir, output_dir, {}, overwrite=True)
    assert len(calls) == 1


def test_runtime_llm_control_is_atomic_and_applied_per_sample(tmp_path, monkeypatch):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    (output_dir / "metrics").mkdir(parents=True)
    sample = input_dir / "sample.txt"
    sample.write_text("input", encoding="utf-8")
    control = output_dir / "runtime_control.json"
    write_llm_enabled(control, True)
    calls = []
    monkeypatch.setattr(run_pipeline, "run_sample", lambda *args, **kwargs: calls.append(args))

    assert read_llm_enabled(control, False) is True
    assert run_pipeline.process_file(sample, input_dir, output_dir, {"llm_enabled": False}, llm_control_path=control)
    assert calls[0][2]["llm_enabled"] is True
    assert not (output_dir / "runtime_control.json.tmp").exists()


def test_memory_keeps_complete_history_but_bounds_prompt_context(tmp_path):
    store = KairisMemoryStore(tmp_path / "memory" / "kairis_memory.json")
    for index in range(5):
        store.append({"sample": f"sample-{index}", "conclusion": "x" * 40})

    assert len(store.records()) == 5
    prompt_records = store.prompt_records(limit=2, max_chars=500)
    assert [record["sample"] for record in prompt_records] == ["sample-3", "sample-4"]
    assert not (tmp_path / "memory" / "kairis_memory.json.tmp").exists()


def test_d3_inline_downloads_once_and_uses_atomic_cache(tmp_path, monkeypatch):
    cache = tmp_path / "d3.min.js"
    downloads = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"window.d3={version:'test'};"

    def fake_urlopen(url, timeout):
        downloads.append((url, timeout))
        return Response()

    monkeypatch.setattr(report_builder, "D3_CACHE_PATH", cache)
    monkeypatch.setattr(report_builder, "urlopen", fake_urlopen)

    first = report_builder._d3_script({"report_d3_inline": True})
    second = report_builder._d3_script({"report_d3_inline": True})

    assert "window.d3" in first
    assert "window.d3" in second
    assert "src=" not in first
    assert len(downloads) == 1
    assert cache.is_file()
    assert not (tmp_path / "d3.min.js.tmp").exists()


def test_provenance_in_consolidated_metrics(tmp_path):
    fixture = PROJECT_DIR / "tests" / "fixtures" / "synthetic_btlab.txt"
    source = tmp_path / "synthetic_btlab.txt"
    shutil.copy2(fixture, source)
    output = tmp_path / "output"
    run_pipeline.ensure_output_structure(output)
    config = json.loads((PROJECT_DIR / "config" / "protocol_config.json").read_text(encoding="utf-8"))
    config["llm_enabled"] = False
    run_pipeline.run_sample(source, output, config, "synthetic_btlab")
    metrics_path = output / "metrics" / "synthetic_btlab_metrics.json"
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    provenance = metrics["provenance"]

    assert provenance["input_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    datetime.fromisoformat(provenance["execution_timestamp"])
    assert set(provenance["package_versions"]) == {"numpy", "scipy", "pandas", "matplotlib"}
    assert provenance["kairis_git_commit"]
    assert "llm_api_key_env" not in provenance["effective_config"]
    assert metrics["memory"]["enabled"] is True
    memory = json.loads((output / "memory" / "kairis_memory.json").read_text(encoding="utf-8"))
    assert memory["records"][0]["sample"] == "synthetic_btlab"
    report = (output / "reports" / "synthetic_btlab_report.html").read_text(encoding="utf-8")
    assert "Proveniência da execução" in report
    assert provenance["input_sha256"] in report
    assert not list(output.rglob("*.tmp"))
