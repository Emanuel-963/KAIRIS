"""Internal worker executed inside a frozen standalone KAIRIS checkout."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def _rows(manifest: Path, limit: int | None) -> list[dict[str, str]]:
    with manifest.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return rows[:limit] if limit else rows


def _allclose(left: Any, right: Any, rtol: float, atol: float) -> tuple[bool, float]:
    import numpy as np

    first = np.asarray(left, dtype=float)
    second = np.asarray(right, dtype=float)
    if first.shape != second.shape or not np.array_equal(np.isnan(first), np.isnan(second)):
        return False, float("inf")
    finite = np.isfinite(first) & np.isfinite(second)
    if not np.any(finite):
        return True, 0.0
    allowed = atol + rtol * np.abs(first[finite])
    tolerance_ratio = np.max(np.abs(first[finite] - second[finite]) / allowed)
    return bool(np.allclose(first, second, rtol=rtol, atol=atol, equal_nan=True)), float(tolerance_ratio)


def _run_gsf(
    rows: list[dict[str, str]],
    corpus: Path,
    output: Path,
    config: dict[str, Any],
    acceptance: dict[str, Any],
) -> list[dict[str, Any]]:
    import numpy as np

    from core.eis_loader import load_btlab
    from core.gsf_engine import calculate_gsf
    from standalone_gsf import analyze_file

    tolerances = acceptance["numeric_tolerances"]
    rtol, atol = float(tolerances["relative"]), float(tolerances["absolute"])
    factors = acceptance["secondary_sensitivity"]["gsf_impedance_scale_factors"]
    keys = ("x_n", "y_n", "q", "alpha", "kphi", "gradient")
    records: list[dict[str, Any]] = []
    for row in rows:
        sample = row["sample_id"]
        source = corpus / row["relative_path"]
        try:
            metrics_path = analyze_file(source, output / "artifacts", config, sample, True)
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            spectrum = load_btlab(source, config)
            baseline = calculate_gsf(
                spectrum["frequency"], spectrum["real"], spectrum["imag"], config
            )
            factor_results = []
            maximum_error = 0.0
            for factor in factors:
                scaled = calculate_gsf(
                    spectrum["frequency"],
                    spectrum["real"] * float(factor),
                    spectrum["imag"] * float(factor),
                    config,
                )
                comparisons = [_allclose(baseline[key], scaled[key], rtol, atol) for key in keys]
                scalar_ok = bool(
                    np.isclose(baseline["I_crit"], scaled["I_crit"], rtol=rtol, atol=atol)
                    and np.isclose(baseline["f_Icrit"], scaled["f_Icrit"], rtol=rtol, atol=atol)
                    and baseline["regime_gsf"] == scaled["regime_gsf"]
                )
                finite_errors = [error for _, error in comparisons if np.isfinite(error)]
                maximum_error = max([maximum_error, *finite_errors])
                factor_results.append(
                    {
                        "factor": float(factor),
                        "pass": all(item[0] for item in comparisons) and scalar_ok,
                    }
                )
            figures = [Path(path) for path in metrics.get("figures", [])]
            records.append(
                {
                    "sample_id": sample,
                    "status": "complete",
                    "metrics_path": str(metrics_path),
                    "artifact_complete": metrics_path.is_file()
                    and len(figures) == 3
                    and all(path.is_file() for path in figures),
                    "scale_invariant": all(item["pass"] for item in factor_results),
                    "scale_max_tolerance_ratio": maximum_error,
                    "scale_factors": factor_results,
                }
            )
        except Exception as error:
            records.append(
                {"sample_id": sample, "status": "failed", "error": f"{type(error).__name__}: {error}"}
            )
    return records


def _run_esc(
    rows: list[dict[str, str]],
    corpus: Path,
    output: Path,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    import numpy as np

    from core.eis_loader import load_btlab
    from standalone_esc import analyze_file

    records: list[dict[str, Any]] = []
    for row in rows:
        sample = row["sample_id"]
        source = corpus / row["relative_path"]
        try:
            spectrum = load_btlab(source, config)
            impedance = spectrum["real"] + 1j * spectrum["imag"]
            nominal = float(np.median(np.abs(impedance[np.isfinite(impedance)])))
            if not np.isfinite(nominal) or nominal <= np.finfo(float).eps:
                raise ValueError("não foi possível definir a referência numérica de teste")
            references = {
                "NOMINAL_REAL": complex(nominal, 0.0),
                "NOMINAL_COMPLEX": complex(nominal, 0.1 * nominal),
            }
            metrics_path, report_path = analyze_file(
                source, output / "artifacts", config, sample, references, True
            )
            records.append(
                {
                    "sample_id": sample,
                    "status": "complete",
                    "metrics_path": str(metrics_path),
                    "report_path": str(report_path),
                    "artifact_complete": metrics_path.is_file() and report_path.is_file(),
                    "references": {
                        name: [float(value.real), float(value.imag)]
                        for name, value in references.items()
                    },
                }
            )
        except Exception as error:
            records.append(
                {"sample_id": sample, "status": "failed", "error": f"{type(error).__name__}: {error}"}
            )
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("gsf", "esc"), required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    # The worker is launched with cwd set to the frozen branch checkout. Putting
    # that checkout first ensures its standalone module and scientific core are used.
    sys.path.insert(0, str(Path.cwd().resolve()))
    from core.artifact_io import atomic_write_text
    from core.config_loader import load_config
    from core.report_builder import to_jsonable

    config = load_config(args.config.resolve())
    acceptance = json.loads(args.acceptance.read_text(encoding="utf-8"))
    rows = _rows(args.manifest.resolve(), args.limit)
    output = args.output.resolve()
    records = (
        _run_gsf(rows, args.corpus.resolve(), output, config, acceptance)
        if args.mode == "gsf"
        else _run_esc(rows, args.corpus.resolve(), output, config)
    )
    payload = {
        "format": f"KAIRIS-{args.mode}-standalone-worker-v1",
        "mode": args.mode,
        "checkout": str(Path.cwd().resolve()),
        "samples": len(rows),
        "records": records,
    }
    atomic_write_text(
        output / f"{args.mode}_worker_results.json",
        json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
    )
    return 0 if all(record["status"] == "complete" for record in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
