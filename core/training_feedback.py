"""Human-reviewed learning records and automatic KAIRIS dataset generation."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from core.artifact_io import atomic_write_text


VERDICTS = {"approved", "corrected", "rejected"}


class TrainingFeedbackStore:
    """Persist an audit trail and rebuild a supervised JSONL dataset per review."""

    def __init__(self, output_dir: str | Path) -> None:
        root = Path(output_dir) / "training"
        self.feedback_path = root / "feedback.json"
        self.dataset_path = root / "dataset.jsonl"
        self._lock = threading.RLock()

    def records(self) -> list[dict[str, Any]]:
        if not self.feedback_path.is_file():
            return []
        try:
            payload = json.loads(self.feedback_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        records = payload.get("records", []) if isinstance(payload, dict) else []
        return [record for record in records if isinstance(record, dict)]

    @staticmethod
    def _key(record: dict[str, Any]) -> tuple[str, str]:
        return str(record.get("sample", "")), str(record.get("input_sha256", ""))

    def latest(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {self._key(record): record for record in self.records()}

    def review(
        self,
        metrics: dict[str, Any],
        verdict: str,
        correction: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        verdict = verdict.strip().lower()
        correction = correction.strip()
        notes = notes.strip()
        if verdict not in VERDICTS:
            raise ValueError("Avaliação deve ser approved, corrected ou rejected.")
        original = str(metrics.get("llm_interpretation") or "").strip()
        if verdict == "approved" and not original:
            raise ValueError("Não há interpretação da LLM para aprovar nesta amostra.")
        if verdict == "corrected" and not correction:
            raise ValueError("Uma correção textual é obrigatória para avaliações corrected.")

        provenance = metrics.get("provenance", {})
        record = {
            "review_id": uuid.uuid4().hex,
            "reviewed_at": datetime.now().astimezone().isoformat(),
            "sample": str(metrics.get("sample", "")),
            "input_sha256": str(provenance.get("input_sha256", "")),
            "kairis_git_commit": provenance.get("kairis_git_commit"),
            "verdict": verdict,
            "summary": metrics.get("summary", {}),
            "interpretation_rules": metrics.get("interpretation_rules", []),
            "original_llm_interpretation": original or None,
            "corrected_interpretation": correction or None,
            "notes": notes or None,
        }
        with self._lock:
            records = self.records()
            records.append(record)
            atomic_write_text(
                self.feedback_path,
                json.dumps(
                    {"format": "KAIRIS-feedback-v1", "records": records},
                    ensure_ascii=False,
                    indent=2,
                    allow_nan=False,
                )
                + "\n",
            )
            self._rebuild_dataset(records)
        return record

    @staticmethod
    def _target(record: dict[str, Any]) -> str | None:
        if record.get("verdict") == "corrected":
            return str(record.get("corrected_interpretation") or "").strip() or None
        if record.get("verdict") == "approved":
            return str(record.get("original_llm_interpretation") or "").strip() or None
        return None

    @staticmethod
    def _user_prompt(record: dict[str, Any]) -> str:
        return (
            "Métricas KAIRIS:\n"
            + json.dumps(record.get("summary", {}), ensure_ascii=False, indent=2)
            + "\n\nInterpretação determinística:\n"
            + "\n".join(
                f"- {rule}" for rule in record.get("interpretation_rules", [])
            )
        )

    def _rebuild_dataset(self, records: list[dict[str, Any]]) -> int:
        latest = {self._key(record): record for record in records}
        lines = []
        for record in sorted(latest.values(), key=lambda item: str(item.get("reviewed_at", ""))):
            target = self._target(record)
            if not target:
                continue
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Você é o orquestrador científico do KAIRIS. Interprete somente "
                            "as métricas fornecidas, sem inventar mecanismos não medidos."
                        ),
                    },
                    {"role": "user", "content": self._user_prompt(record)},
                    {"role": "assistant", "content": target},
                ],
                "metadata": {
                    "sample": record.get("sample"),
                    "input_sha256": record.get("input_sha256"),
                    "verdict": record.get("verdict"),
                    "review_id": record.get("review_id"),
                },
            }
            lines.append(json.dumps(example, ensure_ascii=False, allow_nan=False))
        content = "\n".join(lines) + ("\n" if lines else "")
        atomic_write_text(self.dataset_path, content)
        return len(lines)

    def prompt_examples(self, limit: int, max_chars: int) -> list[dict[str, Any]]:
        examples: list[dict[str, Any]] = []
        used = 0
        current = sorted(
            self.latest().values(), key=lambda item: str(item.get("reviewed_at", ""))
        )
        for record in reversed(current):
            target = self._target(record)
            if not target:
                continue
            example = {
                "summary": record.get("summary", {}),
                "interpretation_rules": record.get("interpretation_rules", []),
                "reviewed_answer": target,
            }
            size = len(json.dumps(example, ensure_ascii=False, separators=(",", ":")))
            if len(examples) >= max(0, limit) or (examples and used + size > max_chars):
                break
            if size > max_chars and not examples:
                continue
            examples.append(example)
            used += size
        examples.reverse()
        return examples

    def stats(self) -> dict[str, Any]:
        records = self.records()
        latest = list({self._key(record): record for record in records}.values())
        counts = {verdict: 0 for verdict in VERDICTS}
        for record in latest:
            verdict = record.get("verdict")
            if verdict in counts:
                counts[verdict] += 1
        return {
            "total_reviews": len(records),
            "current_reviews": len(latest),
            "approved": counts["approved"],
            "corrected": counts["corrected"],
            "rejected": counts["rejected"],
            "dataset_examples": counts["approved"] + counts["corrected"],
            "feedback_path": str(self.feedback_path.resolve()),
            "dataset_path": str(self.dataset_path.resolve()),
        }
