"""JSON Schema validation for the effective KAIRIS configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


DEFAULT_SCHEMA = Path(__file__).resolve().parents[1] / "config" / "protocol_schema.json"


def validate_config(config: dict[str, Any], schema_path: str | Path = DEFAULT_SCHEMA) -> None:
    """Raise a readable ValueError when effective configuration is invalid."""
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(config), key=lambda error: list(error.absolute_path))
    messages = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<raiz>"
        messages.append(f"{location}: {error.message}")
    if (
        isinstance(config.get("r_inf_extrapolation_min_points"), int)
        and isinstance(config.get("r_inf_extrapolation_points"), int)
        and config["r_inf_extrapolation_min_points"] > config["r_inf_extrapolation_points"]
    ):
        messages.append(
            "r_inf_extrapolation_min_points: deve ser menor ou igual a "
            "r_inf_extrapolation_points"
        )
    if not messages:
        return
    raise ValueError("Configuração KAIRIS inválida:\n- " + "\n- ".join(messages))
