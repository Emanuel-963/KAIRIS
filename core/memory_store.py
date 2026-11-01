"""Persistent, bounded-context memory for the KAIRIS orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.artifact_io import atomic_write_text


class KairisMemoryStore:
    """Keep every conclusion on disk and select a bounded recent prompt window."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def records(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        records = payload.get("records", []) if isinstance(payload, dict) else []
        return [record for record in records if isinstance(record, dict)]

    def prompt_records(self, limit: int, max_chars: int) -> list[dict[str, Any]]:
        """Return recent complete records without exceeding the configured budget."""
        selected: list[dict[str, Any]] = []
        used = 0
        for record in reversed(self.records()):
            if len(selected) >= max(0, limit):
                break
            size = len(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
            if selected and used + size > max_chars:
                break
            if size > max_chars and not selected:
                continue
            selected.append(record)
            used += size
        selected.reverse()
        return selected

    def append(self, record: dict[str, Any]) -> int:
        records = self.records()
        records.append(record)
        payload = {"format": "KAIRIS-memory-v1", "records": records}
        atomic_write_text(
            self.path,
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        )
        return len(records)
