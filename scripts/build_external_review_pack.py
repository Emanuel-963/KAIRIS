"""Build the frozen raw-only review pack for the 42-case external cohort."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.eis_loader import load_btlab  # noqa: E402
from scripts.build_blinded_review_pack import (  # noqa: E402
    ANNOTATION_FIELDS,
    _csv_text,
    _write_raw_figure,
)

DEFAULT_PREPARED = (
    PROJECT / "data" / "external_confirmatory" / "316l_passivity_osf_xrav8"
    / "prepared_blind"
)
DEFAULT_DESTINATION = PROJECT / "output" / "external_review_pack_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_external_pack(
    prepared: Path,
    destination: Path,
    *,
    seed: str = "KAIRIS-external-review-v1-20261105",
) -> dict[str, Any]:
    manifest_path = prepared / "blind_manifest.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    if len(manifest) != 42:
        raise ValueError(f"Expected 42 external cases, found {len(manifest)}.")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Review-pack destination is not empty: {destination}")
    cases_dir = destination / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    case_ids: list[str] = []
    source_hashes: dict[str, str] = {}
    for row in manifest:
        case_id = row["case_id"]
        source = prepared / row["relative_path"]
        if _sha256(source) != row["sha256"]:
            raise ValueError(f"Prepared spectrum hash mismatch: {source}")
        target_csv = cases_dir / f"{case_id}.csv"
        atomic_write_text(target_csv, source.read_text(encoding="utf-8"))
        data = load_btlab(target_csv, {"btlab_decimal": "."})
        _write_raw_figure(cases_dir / f"{case_id}.svg", data, case_id)
        case_ids.append(case_id)
        source_hashes[case_id] = row["sha256"]

    random.Random(seed).shuffle(case_ids)
    blank_rows = [
        {field: case_id if field == "case_id" else "" for field in ANNOTATION_FIELDS}
        for case_id in case_ids
    ]
    form_text = _csv_text(blank_rows, ANNOTATION_FIELDS)
    atomic_write_text(destination / "reviewer_A_form.csv", form_text)
    atomic_write_text(destination / "reviewer_B_form.csv", form_text)
    atomic_write_text(
        destination / "README.md",
        (PROJECT / "paper" / "EXTERNAL_REVIEWER_INSTRUCTIONS_v1.md").read_text(
            encoding="utf-8"
        ),
    )
    index_lines = ["# KAIRIS external blinded cases", ""] + [
        f"{index}. [{case_id}](cases/{case_id}.svg) — [CSV](cases/{case_id}.csv)"
        for index, case_id in enumerate(case_ids, start=1)
    ]
    atomic_write_text(destination / "CASE_INDEX.md", "\n".join(index_lines) + "\n")
    result = {
        "format": "KAIRIS-external-blinded-review-pack-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(case_ids),
        "case_order": case_ids,
        "seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "source_hashes": source_hashes,
        "content": "raw converted EIS and raw Nyquist/Bode only; no source labels or KAIRIS outputs",
        "instructions_sha256": _sha256(PROJECT / "paper" / "EXTERNAL_REVIEWER_INSTRUCTIONS_v1.md"),
    }
    atomic_write_text(
        destination / "pack_manifest.json",
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", type=Path, default=DEFAULT_PREPARED)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--seed", default="KAIRIS-external-review-v1-20261105")
    args = parser.parse_args()
    result = build_external_pack(args.prepared.resolve(), args.destination.resolve(), seed=args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
