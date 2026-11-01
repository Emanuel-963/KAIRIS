from __future__ import annotations

import json
import shutil
import subprocess

import pytest

import update_kairis
from core.config_loader import load_config


def _git(path, *arguments):
    return subprocess.run(
        ["git", *arguments],
        cwd=path,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def test_local_config_overrides_defaults_without_modifying_versioned_file(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    base = config_dir / "protocol_config.json"
    base.write_text(json.dumps({"llm_enabled": True, "new_default": 42}), encoding="utf-8")
    (config_dir / "local_config.json").write_text(
        json.dumps({"llm_enabled": False}), encoding="utf-8"
    )

    config = load_config(base)

    assert config == {"llm_enabled": False, "new_default": 42}
    assert json.loads(base.read_text(encoding="utf-8"))["llm_enabled"] is True


@pytest.mark.skipif(shutil.which("git") is None, reason="Git não instalado")
def test_updater_fast_forwards_clean_checkout_and_refuses_dirty_one(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    checkout = tmp_path / "checkout"
    _git(tmp_path, "init", "--bare", str(remote))
    _git(tmp_path, "clone", str(remote), str(seed))
    _git(seed, "checkout", "-b", "main")
    _git(seed, "config", "user.name", "KAIRIS Test")
    _git(seed, "config", "user.email", "kairis-test@local")
    (seed / "version.txt").write_text("one", encoding="utf-8")
    _git(seed, "add", "version.txt")
    _git(seed, "commit", "-m", "first")
    _git(seed, "push", "-u", "origin", "main")
    _git(tmp_path, "clone", "--branch", "main", str(remote), str(checkout))

    config_dir = checkout / "config"
    config_dir.mkdir()
    config = config_dir / "protocol_config.json"
    config.write_text(
        json.dumps(
            {
                "auto_update_enabled": True,
                "auto_update_remote": "origin",
                "auto_update_branch": "main",
                "auto_update_install_dependencies": False,
            }
        ),
        encoding="utf-8",
    )
    status = checkout / "update_status.json"
    monkeypatch.setattr(update_kairis, "PROJECT_DIR", checkout)

    (seed / "version.txt").write_text("two", encoding="utf-8")
    _git(seed, "add", "version.txt")
    _git(seed, "commit", "-m", "second")
    _git(seed, "push")

    assert update_kairis.update(config, status, install_dependencies=False) == 0
    assert (checkout / "version.txt").read_text(encoding="utf-8") == "two"
    assert json.loads(status.read_text(encoding="utf-8"))["state"] == "updated"

    (checkout / "version.txt").write_text("local edit", encoding="utf-8")
    assert update_kairis.update(config, status, install_dependencies=False) == 0
    assert json.loads(status.read_text(encoding="utf-8"))["state"] == "local_changes"
