"""Configuration loading and environment overrides for KAIRIS."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.runtime_paths import PACKAGE_ROOT, local_config_path


def _merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value


def _environment_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Valor booleano inválido: {value}")


def load_config(path: str | Path) -> dict[str, Any]:
    """Load KAIRIS JSON configuration with deployment-safe overrides."""
    config_path = Path(path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    local_paths = [config_path.with_name("local_config.json")]
    workspace_local = local_config_path()
    packaged_default = (PACKAGE_ROOT / "config" / "protocol_config.json").resolve()
    if config_path.resolve() == packaged_default and workspace_local not in local_paths:
        local_paths.append(workspace_local)
    if config_path.name == "protocol_config.json":
        for local_path in local_paths:
            if not local_path.is_file():
                continue
            local = json.loads(local_path.read_text(encoding="utf-8"))
            if not isinstance(local, dict):
                raise ValueError(f"Configuração local inválida: {local_path}")
            _merge(config, local)
    overrides = {
        "KAIRIS_OLLAMA_URL": "ollama_base_url",
        "KAIRIS_OLLAMA_MODEL": "ollama_model",
    }
    for environment_name, config_name in overrides.items():
        value = os.getenv(environment_name)
        if value:
            config[config_name] = value
    enabled = os.getenv("KAIRIS_LLM_ENABLED")
    if enabled is not None:
        config["llm_enabled"] = _environment_bool(enabled)
    return config
