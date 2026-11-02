"""Build a blinded, randomized expert-review pack from KAIRIS release artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import io
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


PROJECT = Path(__file__).resolve().parents[1]
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))

from core.artifact_io import atomic_binary_writer, atomic_write_text  # noqa: E402


DEFAULT_CORPUS = PROJECT / "data" / "validation" / "kairis_eis_validation_v1"
DEFAULT_OUTPUT = PROJECT / "output" / "validation_release_05b85d1"
DEFAULT_DESTINATION = PROJECT / "output" / "blinded_review_pack_v1"
ANNOTATION_FIELDS = [
    "case_id",
    "spectrum_quality",
    "dominant_response",
    "estimated_process_count",
    "intercalation_pseudocapacitive",
    "confidence_1_to_5",
    "exclude_from_analysis",
    "exclusion_reason",
    "reviewer_comment",
]


def _csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _case_id(seed: str, sample_id: str) -> str:
    digest = hashlib.sha256(f"{seed}\0{sample_id}".encode("utf-8")).hexdigest()
    return f"KRS-{digest[:10].upper()}"


def _write_spectrum_csv(path: Path, data: dict[str, Any]) -> None:
    rows = [
        {"frequency_hz": f, "real_ohm": real, "imaginary_ohm": imag}
        for f, real, imag in zip(data["frequency"], data["real"], data["imag"])
    ]
    atomic_write_text(path, _csv_text(rows, ["frequency_hz", "real_ohm", "imaginary_ohm"]))


def _write_raw_figure(path: Path, data: dict[str, Any], case_id: str) -> None:
    frequency = np.asarray(data["frequency"], dtype=float)
    real = np.asarray(data["real"], dtype=float)
    imag = np.asarray(data["imag"], dtype=float)
    magnitude = np.hypot(real, imag)
    phase = np.degrees(np.arctan2(imag, real))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), constrained_layout=True)
    axes[0].plot(real, -imag, "o-", ms=2.5, lw=0.8)
    axes[0].set(xlabel="Z' (Ω)", ylabel="−Z'' (Ω)", title="Nyquist")
    axes[0].axis("equal")
    axes[1].loglog(frequency, magnitude, "o-", ms=2.5, lw=0.8)
    axes[1].set(xlabel="f (Hz)", ylabel="|Z| (Ω)", title="Bode magnitude")
    axes[2].semilogx(frequency, phase, "o-", ms=2.5, lw=0.8)
    axes[2].set(xlabel="f (Hz)", ylabel="Phase (°)", title="Bode phase")
    fig.suptitle(case_id)
    with atomic_binary_writer(path) as handle:
        fig.savefig(handle, format="svg", metadata={"Title": f"KAIRIS blinded case {case_id}"})
    plt.close(fig)


def build_pack(
    corpus: Path,
    output: Path,
    destination: Path,
    seed: str,
    figures: bool = True,
) -> dict[str, Any]:
    with (corpus / "dataset_manifest.csv").open("r", encoding="utf-8", newline="") as handle:
        manifest = list(csv.DictReader(handle))
    reviewer = destination / "reviewer"
    coordinator = destination / "coordinator_only"
    cases = reviewer / "cases"
    cases.mkdir(parents=True, exist_ok=True)
    coordinator.mkdir(parents=True, exist_ok=True)
    index_rows: list[dict[str, str]] = []
    key_rows: list[dict[str, Any]] = []
    for row in manifest:
        sample_id = row["sample_id"]
        metrics_path = output / "metrics" / f"{sample_id}_metrics.json"
        if not metrics_path.is_file():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        case_id = _case_id(seed, sample_id)
        data = metrics["agents"]["agent1"]["Z_data"]
        _write_spectrum_csv(cases / f"{case_id}.csv", data)
        if figures:
            _write_raw_figure(cases / f"{case_id}.svg", data, case_id)
        summary = metrics.get("summary", {})
        index_rows.append({"case_id": case_id})
        key_rows.append(
            {
                "case_id": case_id,
                "sample_id": sample_id,
                "relative_path": row["relative_path"],
                "source_type": row["source_type"],
                "family": row["family"],
                "regime_drt": summary.get("regime_drt"),
                "regime_gsf": summary.get("regime_gsf"),
                "diagnostic": summary.get("diagnostic"),
                "drt_gsf_inconsistent": summary.get("drt_gsf_inconsistent"),
            }
        )
    rng = random.Random(seed)
    rng.shuffle(index_rows)
    order = {row["case_id"]: index for index, row in enumerate(index_rows, start=1)}
    key_rows.sort(key=lambda row: order[row["case_id"]])
    annotations = [{field: (row["case_id"] if field == "case_id" else "") for field in ANNOTATION_FIELDS} for row in index_rows]
    atomic_write_text(reviewer / "annotation_form.csv", _csv_text(annotations, ANNOTATION_FIELDS))
    key_fields = list(key_rows[0]) if key_rows else ["case_id", "sample_id"]
    atomic_write_text(coordinator / "blinding_key.csv", _csv_text(key_rows, key_fields))

    links = "\n".join(
        f'<li><strong>{html.escape(row["case_id"])}</strong> — '
        f'<a href="cases/{row["case_id"]}.svg">figura</a> · '
        f'<a href="cases/{row["case_id"]}.csv">dados</a></li>'
        for row in index_rows
    )
    atomic_write_text(
        reviewer / "index.html",
        "<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>KAIRIS — revisão cega</title>"
        "<style>body{font:16px system-ui;max-width:900px;margin:2rem auto;padding:0 1rem}li{margin:.35rem}</style>"
        "<h1>KAIRIS — revisão cega de espectros</h1><p>Use apenas o identificador aleatório. "
        "As figuras contêm Nyquist e Bode calculados dos dados brutos, sem saídas dos agentes.</p><ol>"
        + links + "</ol></html>\n",
    )
    atomic_write_text(
        reviewer / "README.md",
        "# KAIRIS — instruções ao revisor cego\n\n"
        "Avalie cada caso sem consultar a pasta `coordinator_only` nem resultados do KAIRIS. "
        "Registre uma linha no `annotation_form.csv`.\n\n"
        "Valores permitidos:\n\n"
        "- `spectrum_quality`: `acceptable`, `questionable` ou `unusable`;\n"
        "- `dominant_response`: `kinetic`, `diffusive`, `pseudocapacitive`, `mixed`, `inductive` ou `undetermined`;\n"
        "- `estimated_process_count`: inteiro de 0 a 5, ou `undetermined`;\n"
        "- `intercalation_pseudocapacitive`: `yes`, `no` ou `uncertain`;\n"
        "- `confidence_1_to_5`: 1 (baixa) a 5 (alta);\n"
        "- `exclude_from_analysis`: `yes` ou `no`, sempre justificando exclusões.\n\n"
        "A ordem é aleatória, os nomes originais foram removidos e nenhum diagnóstico do pipeline é mostrado.\n",
    )
    pack_manifest = {
        "format": "KAIRIS-blinded-review-pack-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case_count": len(index_rows),
        "seed_sha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
        "figures_included": figures,
        "reviewer_content": "raw EIS only; no KAIRIS classifications",
        "separation_warning": "coordinator_only/blinding_key.csv must not be shared with reviewers",
    }
    atomic_write_text(
        destination / "pack_manifest.json",
        json.dumps(pack_manifest, ensure_ascii=False, indent=2) + "\n",
    )
    return pack_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--seed", default="KAIRIS-review-v1-2026")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()
    result = build_pack(
        args.corpus.resolve(), args.output.resolve(), args.destination.resolve(),
        args.seed, figures=not args.no_figures,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
