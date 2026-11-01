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
    if not errors:
        return
    messages = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "<raiz>"
        messages.append(f"{location}: {error.message}")
    raise ValueError("Configuração KAIRIS inválida:\n- " + "\n- ".join(messages))
