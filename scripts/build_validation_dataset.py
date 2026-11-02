"""Build the deterministic KAIRIS EIS validation and training corpus.

Synthetic spectra are generated locally from declared impedance elements.  The
optional public portion downloads the unmodified CC BY 4.0 files associated
with DOI 10.5281/zenodo.15422339.  Public downloads are never performed unless
``--download-public`` is passed explicitly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SEED = 20261101
VERSION = "1.0.0"
PUBLIC_RECORD = "15422339"
PUBLIC_DOI = "10.5281/zenodo.15422339"
PUBLIC_LICENSE = "CC BY 4.0"
PUBLIC_API = f"https://zenodo.org/api/records/{PUBLIC_RECORD}"
AUTOECM_DOI = "10.1149/1945-7111/acd8fb"
AUTOECM_LICENSE = "CC BY 4.0"
AUTOECM_DATA_URL = "https://raw.githubusercontent.com/BatteryDEV/AutoECM/main/data/test_data.csv"
AUTOECM_TRAIN_URL = "https://raw.githubusercontent.com/BatteryDEV/AutoECM/main/data/train_data.csv"
AUTOECM_LICENSE_URL = "https://raw.githubusercontent.com/BatteryDEV/AutoECM/main/data/LICENSE"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DESTINATION = ROOT / "data" / "validation" / "kairis_eis_validation_v1"


@dataclass(frozen=True)
class Family:
    slug: str
    process: str
    quality: str
    challenge: str


FAMILIES = (
    Family("randles_rc", "single ideal charge-transfer relaxation", "good", "baseline semicircle"),
    Family("zarc_cpe", "single depressed CPE relaxation", "good", "fractional non-Debye response"),
    Family("double_zarc", "two overlapping interfacial relaxations", "intermediate", "partially resolved time constants"),
    Family("triple_zarc", "three overlapping relaxations", "challenging", "ambiguous DRT peak separation"),
    Family("warburg_semi_infinite", "charge transfer with semi-infinite diffusion", "intermediate", "45 degree diffusion tail"),
    Family("finite_diffusion", "finite-length transmissive or reflective diffusion", "intermediate", "low-frequency diffusion boundary"),
    Family("gerischer", "coupled reaction-diffusion Gerischer response", "intermediate", "Gerischer versus Warburg curvature"),
    Family("porous_tlm", "distributed porous-electrode response", "challenging", "broad hierarchy of pore time scales"),
    Family("adsorption_inductive", "adsorption relaxation with an inductive loop", "warning", "positive imaginary low-frequency loop"),
    Family("lead_inductance", "high-frequency wiring inductance", "warning", "instrument lead artifact"),
    Family("nonstationary_drift", "low-frequency time drift", "warning", "linearity and stationarity violation"),
    Family("sparse_outliers", "sparse acquisition with isolated outliers", "poor", "local corruption and limited bandwidth"),
)

ELECTROLYTES = ("KCl", "H2SO4", "KOH", "NaCl", "LiNO3", "Na2SO4")


def atomic_write(path: Path, content: str | bytes) -> None:
    """Write one dataset artifact atomically in its destination directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = content.encode("utf-8") if isinstance(content, str) else content
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def zarc(w: np.ndarray, resistance: float, q: float, exponent: float) -> np.ndarray:
    return 1.0 / (1.0 / resistance + q * (1j * w) ** exponent)


def finite_warburg(w: np.ndarray, resistance: float, tau: float, boundary: str) -> np.ndarray:
    root = np.sqrt(1j * w * tau)
    tanh = np.ones_like(root)
    finite = np.real(root) < 20.0
    tanh[finite] = np.tanh(root[finite])
    tanh[np.abs(tanh) < 1e-12] = 1e-12
    return resistance * tanh / root if boundary == "short" else resistance / (root * tanh)


def gerischer(w: np.ndarray, resistance: float, tau: float) -> np.ndarray:
    return resistance / np.sqrt(1.0 + 1j * w * tau)


def distributed_pores(w: np.ndarray, resistance: float, tau: float) -> np.ndarray:
    weights = np.array([0.06, 0.10, 0.16, 0.22, 0.20, 0.15, 0.08, 0.03])
    scales = np.logspace(-2.0, 2.0, weights.size)
    return sum(
        resistance * weight / (1.0 + 1j * w * tau * scale)
        for weight, scale in zip(weights, scales)
    )


def model_impedance(family: str, variant: int, frequency: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    w = 2.0 * np.pi * frequency
    scale = 0.65 + 0.22 * variant
    rs = 0.18 * scale + 0.04 * variant
    parameters: dict[str, Any] = {"Rs_ohm": rs}
    if family == "randles_rc":
        rct, cdl = 4.0 * scale, 2e-3 / scale
        z = rs + rct / (1.0 + 1j * w * rct * cdl)
        parameters.update(Rct_ohm=rct, Cdl_F=cdl)
    elif family == "zarc_cpe":
        rct, q, exponent = 7.0 * scale, 5e-3 / scale, 0.96 - 0.055 * variant
        z = rs + zarc(w, rct, q, exponent)
        parameters.update(Rct_ohm=rct, Q=q, n=exponent)
    elif family == "double_zarc":
        tau_ratio = (5.0, 8.0, 15.0, 30.0, 70.0, 160.0)[variant]
        r1, r2 = 3.0 * scale, 6.0 * scale
        q1 = 1.0 / (r1 * 2 * np.pi * 500.0)
        q2 = tau_ratio / (r2 * 2 * np.pi * 500.0)
        z = rs + zarc(w, r1, q1, 0.90) + zarc(w, r2, q2, 0.78)
        parameters.update(
            R1_ohm=r1, R2_ohm=r2, Q1=q1, Q2=q2, n1=0.90, n2=0.78,
            tau_ratio=tau_ratio,
        )
    elif family == "triple_zarc":
        z = rs
        peaks = (2e4, 120.0, 0.18)
        resistances = (1.5 * scale, 4.0 * scale, 8.0 * scale)
        for index, (peak, resistance) in enumerate(zip(peaks, resistances), start=1):
            q = 1.0 / (resistance * 2 * np.pi * peak)
            z = z + zarc(w, resistance, q, 0.88 - 0.05 * index)
            parameters[f"R{index}_ohm"] = resistance
            parameters[f"Q{index}"] = q
            parameters[f"n{index}"] = 0.88 - 0.05 * index
    elif family == "warburg_semi_infinite":
        rct, q, sigma = 5.0 * scale, 4e-3 / scale, 1.2 * scale
        z = rs + zarc(w, rct, q, 0.88) + sigma / np.sqrt(1j * w)
        parameters.update(Rct_ohm=rct, Q=q, sigma=sigma)
    elif family == "finite_diffusion":
        boundary = "short" if variant % 2 == 0 else "open"
        rct, rw, tau = 4.0 * scale, 8.0 * scale, 0.4 * (3.0**variant)
        z = rs + zarc(w, rct, 5e-3 / scale, 0.86) + finite_warburg(w, rw, tau, boundary)
        parameters.update(Rct_ohm=rct, Rw_ohm=rw, tau_s=tau, boundary=boundary)
    elif family == "gerischer":
        rg, tau = 9.0 * scale, 0.04 * (4.0**variant)
        z = rs + zarc(w, 3.5 * scale, 4e-3 / scale, 0.87) + gerischer(w, rg, tau)
        parameters.update(Rg_ohm=rg, tau_s=tau)
    elif family == "porous_tlm":
        rp, tau = 14.0 * scale, 0.015 * (3.2**variant)
        z = rs + zarc(w, 2.0 * scale, 8e-4 / scale, 0.90) + distributed_pores(w, rp, tau)
        parameters.update(Rpore_ohm=rp, tau_s=tau)
    elif family == "adsorption_inductive":
        rct, rl, tau = 7.0 * scale, 2.0 * scale, 0.02 * (4.0**variant)
        inductive = rl * (1j * w * tau) / (1.0 + 1j * w * tau)
        z = rs + zarc(w, rct, 4e-3 / scale, 0.84) + inductive
        parameters.update(Rct_ohm=rct, RL_ohm=rl, tau_s=tau)
    elif family == "lead_inductance":
        inductance = (0.2 + 0.55 * variant) * 1e-6
        z = rs + 1j * w * inductance + zarc(w, 6.0 * scale, 3e-3 / scale, 0.90)
        parameters.update(L_H=inductance)
    elif family == "nonstationary_drift":
        z = rs + zarc(w, 9.0 * scale, 5e-3 / scale, 0.82) + finite_warburg(w, 5.0, 4.0, "short")
        ramp = np.linspace(0.0, 1.0, z.size) ** 1.7
        drift = (0.04 + 0.035 * variant) * np.max(np.abs(z))
        z = z + drift * ramp * (0.7 - 0.5j)
        parameters.update(drift_fraction=0.04 + 0.035 * variant)
    elif family == "sparse_outliers":
        z = rs + zarc(w, 8.0 * scale, 5e-3 / scale, 0.79) + distributed_pores(w, 5.0, 0.8)
        parameters.update(outlier_fraction=0.04 + 0.01 * variant)
    else:
        raise ValueError(f"Unknown family: {family}")
    return np.asarray(z, dtype=complex), parameters


def frequency_grid(family: str, variant: int) -> np.ndarray:
    if family == "sparse_outliers":
        return np.logspace(5, -1, 31 - 2 * (variant % 3))
    if variant == 4:
        return np.logspace(4, -1, 81)
    if variant == 5:
        return np.logspace(6, -3, 121)
    return np.logspace(5.5, -2, 101)


def add_noise(
    rng: np.random.Generator,
    z: np.ndarray,
    family: str,
    variant: int,
) -> tuple[np.ndarray, float]:
    relative = 0.0015 + 0.0012 * variant
    if family in {"nonstationary_drift", "sparse_outliers"}:
        relative *= 1.8
    scale = relative * np.maximum(np.abs(z), np.median(np.abs(z)) * 0.1)
    noisy = z + rng.normal(size=z.size) * scale + 1j * rng.normal(size=z.size) * scale
    if family == "sparse_outliers":
        count = max(1, round(z.size * (0.04 + 0.01 * variant)))
        candidates = np.arange(3, z.size - 3)
        indices = rng.choice(candidates, size=min(count, candidates.size), replace=False)
        noisy[indices] += (5.0 + variant) * scale[indices] * (1.0 + 0.7j)
    return noisy, relative


def render_spectrum(frequency: np.ndarray, impedance: np.ndarray, layout: int) -> tuple[str, str]:
    lines: list[str]
    if layout == 0:
        lines = ["Frequency (Hz);Z' (Ohm);Z'' (Ohm)"]
        lines += [f"{f:.12g};{z.real:.12g};{z.imag:.12g}" for f, z in zip(frequency, impedance)]
        return "csv", "\n".join(lines) + "\n"
    if layout == 1:
        lines = ["EC-Lab ASCII FILE", "Nb header lines : 3", "freq/Hz\tRe(Z)/Ohm\t-Im(Z)/Ohm"]
        lines += [f"{f:.12g}\t{z.real:.12g}\t{-z.imag:.12g}" for f, z in zip(frequency, impedance)]
        return "txt", "\n".join(lines) + "\n"
    if layout == 2:
        lines = ["Frequency_Hz,Real_Ohm,Imag_Ohm"]
        lines += [f"{f:.12g},{z.real:.12g},{z.imag:.12g}" for f, z in zip(frequency, impedance)]
        return "csv", "\n".join(lines) + "\n"
    lines = ["Frequency (Hz);Z' (Ohm);Z'' (Ohm)"]
    lines += [
        f"{f:.9E};{z.real:.9E};{z.imag:.9E}".replace(".", ",")
        for f, z in zip(frequency, impedance)
    ]
    return "txt", "\n".join(lines) + "\n"


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, stream.getvalue())


def generate_synthetic(destination: Path) -> list[dict[str, Any]]:
    synthetic = destination / "synthetic"
    rng = np.random.default_rng(SEED)
    rows: list[dict[str, Any]] = []
    for family_index, family in enumerate(FAMILIES, start=1):
        for variant in range(6):
            sample_id = f"SYN-{family_index:02d}-{variant + 1:02d}"
            electrolyte = ELECTROLYTES[(family_index + variant) % len(ELECTROLYTES)]
            frequency = frequency_grid(family.slug, variant)
            clean, parameters = model_impedance(family.slug, variant, frequency)
            measured, noise = add_noise(rng, clean, family.slug, variant)
            extension, content = render_spectrum(frequency, measured, variant % 4)
            filename = f"{sample_id}_{electrolyte}_{family.slug}.{extension}"
            path = synthetic / family.slug / filename
            atomic_write(path, content)
            rows.append(
                {
                    "sample_id": sample_id,
                    "relative_path": path.relative_to(destination).as_posix(),
                    "source_type": "synthetic",
                    "dataset_role": "development_validation",
                    "family": family.slug,
                    "process_description": family.process,
                    "quality_class": family.quality,
                    "intended_challenge": family.challenge,
                    "electrolyte_token": electrolyte,
                    "point_count": frequency.size,
                    "frequency_min_hz": float(frequency.min()),
                    "frequency_max_hz": float(frequency.max()),
                    "noise_relative": noise,
                    "generator_parameters_json": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
                    "doi": "",
                    "license": "KAIRIS synthetic test data; project license",
                    "sha256": sha256(path),
                }
            )
    return rows


def download_zenodo(destination: Path) -> list[dict[str, Any]]:
    """Download and verify the 54 unmodified public cell spectra."""
    with urllib.request.urlopen(PUBLIC_API, timeout=60) as response:
        record = json.load(response)
    license_id = record.get("metadata", {}).get("license", {}).get("id")
    if license_id != "cc-by-4.0":
        raise RuntimeError(f"Unexpected public dataset license: {license_id!r}")
    rows: list[dict[str, Any]] = []
    files = sorted(
        (item for item in record["files"] if item["key"].lower().endswith(".csv")),
        key=lambda item: item["key"],
    )
    if len(files) != 54:
        raise RuntimeError(f"Expected 54 public CSV files; Zenodo reported {len(files)}")
    public = destination / "public" / f"zenodo_{PUBLIC_RECORD}_nmc811_30soc"
    for item in files:
        path = public / item["key"]
        if not path.is_file():
            with urllib.request.urlopen(item["links"]["self"], timeout=60) as response:
                atomic_write(path, response.read())
        expected_md5 = item["checksum"].split(":", 1)[1]
        actual_md5 = hashlib.md5(path.read_bytes()).hexdigest()  # nosec - repository checksum verification
        if actual_md5 != expected_md5:
            raise RuntimeError(f"Checksum mismatch for {item['key']}")
        rows.append(
            {
                "sample_id": f"PUB-ZENODO-{Path(item['key']).stem}",
                "relative_path": path.relative_to(destination).as_posix(),
                "source_type": "experimental_public",
                "dataset_role": "external_holdout",
                "family": "nmc811_21700_cell",
                "process_description": "NMC811 21700 cell at 30% state of charge",
                "quality_class": "experimental_unlabeled",
                "intended_challenge": "between-cell experimental variability",
                "electrolyte_token": "unknown_proprietary_cell",
                "point_count": 44,
                "frequency_min_hz": 0.05,
                "frequency_max_hz": 10000.0,
                "noise_relative": "",
                "generator_parameters_json": "",
                "doi": PUBLIC_DOI,
                "license": PUBLIC_LICENSE,
                "sha256": sha256(path),
            }
        )
    atomic_write(destination / "public" / f"zenodo_{PUBLIC_RECORD}_metadata.json", json.dumps(record, ensure_ascii=False, indent=2))
    return rows


def _download_if_missing(url: str, path: Path) -> None:
    if path.is_file():
        return
    request = urllib.request.Request(url, headers={"User-Agent": "KAIRIS-validation-builder"})
    with urllib.request.urlopen(request, timeout=120) as response:
        atomic_write(path, response.read())


def _parse_autoecm_values(raw: str, complex_values: bool = False) -> np.ndarray:
    values = raw.strip().strip("[]")
    tokens = [token.strip().replace(" ", "") for token in values.split(",") if token.strip()]
    converter = complex if complex_values else float
    return np.asarray([converter(token) for token in tokens])


def download_autoecm(destination: Path) -> list[dict[str, Any]]:
    """Download AutoECM data and expose disjoint train and test subsets."""
    root = destination / "public" / "autoecm_ccby4"
    raw_path = root / "test_data.csv"
    train_path = root / "train_data.csv"
    license_path = root / "LICENSE"
    _download_if_missing(AUTOECM_DATA_URL, raw_path)
    _download_if_missing(AUTOECM_TRAIN_URL, train_path)
    _download_if_missing(AUTOECM_LICENSE_URL, license_path)
    selected: dict[str, int] = {}
    rows: list[dict[str, Any]] = []
    with raw_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for source_row in reader:
            circuit = source_row["Circuit"]
            occurrence = selected.get(circuit, 0)
            if occurrence >= 3:
                continue
            frequency = _parse_autoecm_values(source_row["freq"])
            impedance = _parse_autoecm_values(source_row["Z"], complex_values=True)
            if frequency.size != impedance.size:
                raise RuntimeError(f"AutoECM row {source_row.get('', '?')} has mismatched arrays")
            selected[circuit] = occurrence + 1
            slug = re.sub(r"[^A-Za-z0-9]+", "-", circuit).strip("-")
            sample_id = f"PUB-AUTOECM-{slug}-{occurrence + 1:02d}"
            path = root / "converted" / circuit / f"{sample_id}.csv"
            _, content = render_spectrum(frequency, impedance, 2)
            atomic_write(path, content)
            rows.append(
                {
                    "sample_id": sample_id,
                    "relative_path": path.relative_to(destination).as_posix(),
                    "source_type": "synthetic_publication",
                    "dataset_role": "published_benchmark_holdout",
                    "family": f"autoecm_{circuit}",
                    "process_description": f"AutoECM labeled synthetic equivalent-circuit spectrum: {circuit}",
                    "quality_class": "publication_labeled",
                    "intended_challenge": "equivalent-circuit class diversity",
                    "electrolyte_token": "not_applicable_synthetic",
                    "point_count": frequency.size,
                    "frequency_min_hz": float(frequency.min()),
                    "frequency_max_hz": float(frequency.max()),
                    "noise_relative": "as_published",
                    "generator_parameters_json": source_row["Parameters"],
                    "doi": AUTOECM_DOI,
                    "license": AUTOECM_LICENSE,
                    "sha256": sha256(path),
                }
            )
    if len(selected) != 9 or len(rows) != 27:
        raise RuntimeError(f"Expected 9 AutoECM classes and 27 spectra; got {len(selected)} and {len(rows)}")
    selected_train: dict[str, int] = {}
    with train_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for source_row in reader:
            circuit = source_row["Circuit"]
            occurrence = selected_train.get(circuit, 0)
            if occurrence >= 5:
                continue
            frequency = _parse_autoecm_values(source_row["freq"])
            impedance = _parse_autoecm_values(source_row["Z"], complex_values=True)
            if frequency.size != impedance.size:
                raise RuntimeError(f"AutoECM training row has mismatched arrays for {circuit}")
            selected_train[circuit] = occurrence + 1
            slug = re.sub(r"[^A-Za-z0-9]+", "-", circuit).strip("-")
            sample_id = f"PUB-AUTOECM-TRAIN-{slug}-{occurrence + 1:02d}"
            path = root / "converted" / "train" / circuit / f"{sample_id}.csv"
            _, content = render_spectrum(frequency, impedance, 2)
            atomic_write(path, content)
            rows.append(
                {
                    "sample_id": sample_id,
                    "relative_path": path.relative_to(destination).as_posix(),
                    "source_type": "synthetic_publication",
                    "dataset_role": "training_benchmark",
                    "family": f"autoecm_{circuit}",
                    "process_description": f"AutoECM training spectrum labeled by equivalent circuit: {circuit}",
                    "quality_class": "publication_labeled",
                    "intended_challenge": "equivalent-circuit class diversity",
                    "electrolyte_token": "not_applicable_synthetic",
                    "point_count": frequency.size,
                    "frequency_min_hz": float(frequency.min()),
                    "frequency_max_hz": float(frequency.max()),
                    "noise_relative": "as_published",
                    "generator_parameters_json": source_row["Parameters"],
                    "doi": AUTOECM_DOI,
                    "license": AUTOECM_LICENSE,
                    "sha256": sha256(path),
                }
            )
    if len(selected_train) != 9 or sum(row["dataset_role"] == "training_benchmark" for row in rows) != 45:
        raise RuntimeError("Expected 45 AutoECM training spectra across nine classes")
    source_metadata = {
        "title": "Machine Learning Benchmarks for the Classification of Equivalent Circuit Models from Electrochemical Impedance Spectra",
        "doi": AUTOECM_DOI,
        "repository": "https://github.com/BatteryDEV/AutoECM",
        "license": AUTOECM_LICENSE,
        "source_files": {
            "train_data.csv": sha256(train_path),
            "test_data.csv": sha256(raw_path),
        },
        "selection": {
            "training": "first five rows of each of nine classes in train_data.csv",
            "holdout": "first three rows of each of nine classes in test_data.csv",
        },
    }
    atomic_write(root / "source_metadata.json", json.dumps(source_metadata, ensure_ascii=False, indent=2) + "\n")
    return rows


def download_public(destination: Path) -> list[dict[str, Any]]:
    return download_zenodo(destination) + download_autoecm(destination)


MANIFEST_FIELDS = [
    "sample_id", "relative_path", "source_type", "dataset_role", "family",
    "process_description", "quality_class", "intended_challenge", "electrolyte_token",
    "point_count", "frequency_min_hz", "frequency_max_hz", "noise_relative",
    "generator_parameters_json", "doi", "license", "sha256",
]


def existing_public_rows(destination: Path) -> list[dict[str, Any]]:
    path = destination / "public_manifest.csv"
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> int:
    parser = argparse.ArgumentParser(description="Constrói o corpus EIS de validação do KAIRIS")
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument(
        "--download-public",
        action="store_true",
        help="baixar explicitamente os 54 CSV experimentais CC BY 4.0 do Zenodo",
    )
    args = parser.parse_args()
    destination = args.destination.resolve()
    synthetic_rows = generate_synthetic(destination)
    public_rows = download_public(destination) if args.download_public else existing_public_rows(destination)
    write_csv(destination / "synthetic_truth.csv", synthetic_rows, MANIFEST_FIELDS)
    if public_rows:
        write_csv(destination / "public_manifest.csv", public_rows, MANIFEST_FIELDS)
    all_rows = synthetic_rows + public_rows
    write_csv(destination / "dataset_manifest.csv", all_rows, MANIFEST_FIELDS)
    metadata = {
        "name": "KAIRIS EIS Validation Corpus",
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_seed": SEED,
        "synthetic_spectra": len(synthetic_rows),
        "public_experimental_spectra": sum(row["source_type"] == "experimental_public" for row in public_rows),
        "published_synthetic_spectra": sum(row["source_type"] == "synthetic_publication" for row in public_rows),
        "total_spectra": len(all_rows),
        "public_source_doi": PUBLIC_DOI,
        "public_source_license": PUBLIC_LICENSE,
        "autoecm_source_doi": AUTOECM_DOI,
        "autoecm_source_license": AUTOECM_LICENSE,
    }
    atomic_write(destination / "dataset_metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
