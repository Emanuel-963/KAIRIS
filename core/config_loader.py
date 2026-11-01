"""Configuration loading and environment overrides for KAIRIS."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _environment_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Valor booleano inválido: {value}")


def load_config(path: str | Path) -> dict[str, Any]:
    """Load KAIRIS JSON configuration with deployment-safe overrides."""
    config = json.loads(Path(path).read_text(encoding="utf-8"))
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
