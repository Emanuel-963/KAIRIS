"""Small atomic runtime control shared by the KAIRIS dashboard and pipeline."""

from __future__ import annotations

import json
from pathlib import Path

from core.artifact_io import atomic_write_text


def read_llm_enabled(path: str | Path | None, default: bool) -> bool:
    if path is None:
        return bool(default)
    control = Path(path)
    if not control.is_file():
        return bool(default)
    try:
        value = json.loads(control.read_text(encoding="utf-8")).get("llm_enabled")
    except (OSError, json.JSONDecodeError, AttributeError):
        return bool(default)
    return value if isinstance(value, bool) else bool(default)


def write_llm_enabled(path: str | Path, enabled: bool) -> Path:
    destination = Path(path)
    atomic_write_text(
        destination,
        json.dumps({"llm_enabled": bool(enabled)}, indent=2) + "\n",
    )
    return destination
