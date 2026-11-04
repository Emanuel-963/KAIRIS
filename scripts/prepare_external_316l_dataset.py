"""Prepare the frozen KAIRIS 316L external cohort without analysing it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_write_text  # noqa: E402


DEFAULT_ROOT = PROJECT / "data" / "external_confirmatory" / "316l_passivity_osf_xrav8"
EXPECTED_SOURCE_SHA256 = (
    "01c85092b46a68a832124d7327157b6327a0d440ea3b66ba277694432edfb8b3"
)
MAGNITUDE_PATTERN = re.compile(r"^log_Z_f(?P<frequency>.+)$")
PHASE_PATTERN = re.compile(r"^Phase_Angle(?:_Z)?_f(?P<frequency>.+)$")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _spectral_columns(columns: list[str]) -> list[tuple[float, str, str]]:
    magnitude: dict[float, str] = {}
    phase: dict[float, str] = {}
    for column in columns:
        mag_match = MAGNITUDE_PATTERN.match(column)
        phase_match = PHASE_PATTERN.match(column)
        if mag_match:
            magnitude[float(mag_match.group("frequency"))] = column
        elif phase_match:
            phase[float(phase_match.group("frequency"))] = column
    if not magnitude or set(magnitude) != set(phase):
        raise ValueError("Magnitude and phase frequency columns do not match.")
    return [
        (frequency, magnitude[frequency], phase[frequency])
        for frequency in sorted(magnitude, reverse=True)
    ]


def _blind_id(sample: str, seed: str) -> str:
    token = hashlib.sha256(f"{seed}\0{sample}".encode("utf-8")).hexdigest()[:12]
    return f"EXT316L-{token.upper()}"


def prepare_dataset(
    source: Path,
    destination: Path,
    coordinator_mapping: Path,
    *,
    seed: str = "20261104",
    expected_sha256: str | None = EXPECTED_SOURCE_SHA256,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Convert wide Bode rows into blinded, long-form KAIRIS EIS files.

    The source stores ``log10(|Z|)`` and the positive magnitude of the
    capacitive phase angle. Therefore ``-Im(Z) = |Z| sin(phase)``. This is a
    deterministic representation conversion, not a scientific analysis.
    """
    source = Path(source)
    destination = Path(destination)
    coordinator_mapping = Path(coordinator_mapping)
    if not source.is_file():
        raise FileNotFoundError(source)
    actual_hash = _sha256(source)
    if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
        raise ValueError(
            f"Source SHA-256 mismatch: expected {expected_sha256}, got {actual_hash}."
        )
    existing = list(destination.glob("*.csv")) if destination.exists() else []
    if existing and not overwrite:
        raise FileExistsError(
            f"{destination} already contains prepared spectra; use --overwrite explicitly."
        )

    frame = pd.read_csv(source)
    required = {"Sample", "Subgroup"}
    if not required.issubset(frame.columns):
        raise ValueError("Source must contain Sample and Subgroup columns.")
    if frame["Sample"].duplicated().any():
        raise ValueError("Source sample identifiers must be unique.")
    spectral_columns = _spectral_columns([str(value) for value in frame.columns])
    destination.mkdir(parents=True, exist_ok=True)

    blind_manifest: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    for source_row, (_, row) in enumerate(frame.iterrows(), start=1):
        sample = str(row["Sample"])
        subgroup = str(row["Subgroup"])
        case_id = _blind_id(sample, seed)
        spectrum_rows: list[dict[str, Any]] = []
        for frequency, magnitude_column, phase_column in spectral_columns:
            log_magnitude = float(row[magnitude_column])
            phase_degrees = float(row[phase_column])
            if not all(math.isfinite(value) for value in (log_magnitude, phase_degrees)):
                raise ValueError(f"Non-finite value in source sample {sample}.")
            magnitude = 10.0**log_magnitude
            phase_radians = math.radians(phase_degrees)
            spectrum_rows.append(
                {
                    "freq/Hz": format(frequency, ".12g"),
                    "Re(Z)/Ohm": format(magnitude * math.cos(phase_radians), ".15g"),
                    "-Im(Z)/Ohm": format(magnitude * math.sin(phase_radians), ".15g"),
                }
            )
        spectrum_path = destination / f"{case_id}.csv"
        atomic_write_text(
            spectrum_path,
            _csv_text(spectrum_rows, ["freq/Hz", "Re(Z)/Ohm", "-Im(Z)/Ohm"]),
        )
        blind_manifest.append(
            {
                "case_id": case_id,
                "relative_path": spectrum_path.name,
                "sha256": _sha256(spectrum_path),
                "point_count": len(spectrum_rows),
                "frequency_min_hz": min(value[0] for value in spectral_columns),
                "frequency_max_hz": max(value[0] for value in spectral_columns),
            }
        )
        mapping.append(
            {
                "case_id": case_id,
                "source_row": source_row,
                "source_sample": sample,
                "source_subgroup": subgroup,
            }
        )

    blind_manifest.sort(key=lambda item: item["case_id"])
    mapping.sort(key=lambda item: item["case_id"])
    atomic_write_text(
        destination / "blind_manifest.csv",
        _csv_text(
            blind_manifest,
            [
                "case_id",
                "relative_path",
                "sha256",
                "point_count",
                "frequency_min_hz",
                "frequency_max_hz",
            ],
        ),
    )
    atomic_write_text(
        coordinator_mapping,
        _csv_text(
            mapping,
            ["case_id", "source_row", "source_sample", "source_subgroup"],
        ),
    )
    summary = {
        "format": "KAIRIS-external-cohort-preparation-v1",
        "source_sha256": actual_hash,
        "seed": seed,
        "sample_count": len(blind_manifest),
        "points_per_sample": len(spectral_columns),
        "frequency_min_hz": min(value[0] for value in spectral_columns),
        "frequency_max_hz": max(value[0] for value in spectral_columns),
        "phase_convention": "source positive capacitive angle; output is -Im(Z)",
        "scientific_analysis_performed": False,
    }
    atomic_write_text(
        destination / "preparation_summary.json",
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_ROOT / "raw" / "input_data.csv",
        help="Canonical wide Bode CSV downloaded from OSF.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ROOT / "prepared_blind",
        help="Destination for blinded long-form spectra.",
    )
    parser.add_argument(
        "--mapping",
        type=Path,
        default=DEFAULT_ROOT / "coordinator" / "blinding_key.csv",
        help="Coordinator-only case-to-subgroup mapping.",
    )
    parser.add_argument("--seed", default="20261104")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    summary = prepare_dataset(
        args.source,
        args.output,
        args.mapping,
        seed=args.seed,
        overwrite=args.overwrite,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
