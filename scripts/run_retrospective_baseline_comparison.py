#!/usr/bin/env python3
"""Compare KAIRIS with independent Lin-KK and DRT baselines retrospectively."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from html import escape
import json
from pathlib import Path
import statistics
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.artifact_io import atomic_write_text  # noqa: E402
from core.config_loader import load_config  # noqa: E402
from core.eis_loader import load_btlab  # noqa: E402
from core.independent_baselines import (  # noqa: E402
    run_impedance_lin_kk,
    run_pyimpspec_tr_nnls,
)
from scripts.run_independent_baseline_smoke import assert_synthetic_only  # noqa: E402

DEFAULT_CORPUS = ROOT / "data" / "validation" / "kairis_eis_validation_v1"
DEFAULT_KAIRIS_OUTPUT = ROOT / "output" / "validation_corpus"
DEFAULT_OUTPUT = ROOT / "output" / "independent_baselines_v1"
DEFAULT_SCHEMA = ROOT / "config" / "baseline_comparison_schema_v1.json"


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _condition_key(mode: str, lambda_value: float) -> str:
    return f"{mode}_lambda_{lambda_value:g}"


def _conditions(schema: dict[str, Any], primary_only: bool) -> list[dict[str, Any]]:
    primary = schema["drt"]["primary_condition"]
    return [primary] if primary_only else [primary, *schema["drt"]["sensitivity_conditions"]]


def _baseline_call(callable_: Any, *args: Any, **kwargs: Any) -> dict[str, Any]:
    try:
        return {"status": "completed", "result": callable_(*args, **kwargs), "error": ""}
    except Exception as exc:  # failures are retained as scientific outcomes
        return {
            "status": "failed",
            "result": None,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_case(
    manifest_row: dict[str, str],
    corpus: Path,
    kairis_output: Path,
    config: dict[str, Any],
    schema: dict[str, Any],
    primary_only: bool,
) -> dict[str, Any]:
    sample_id = manifest_row["sample_id"]
    source = corpus / manifest_row["relative_path"]
    metrics_path = kairis_output / "metrics" / f"{sample_id}_metrics.json"
    if not metrics_path.is_file():
        raise FileNotFoundError(f"KAIRIS metrics missing for {sample_id}: {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    eis = load_btlab(source, config)
    lin_kk = _baseline_call(
        run_impedance_lin_kk,
        eis["frequency"],
        eis["real"],
        eis["imag"],
        config,
    )
    drt: dict[str, Any] = {}
    for condition in _conditions(schema, primary_only):
        mode = str(condition["mode"])
        lambda_value = float(condition["lambda_value"])
        drt[_condition_key(mode, lambda_value)] = _baseline_call(
            run_pyimpspec_tr_nnls,
            eis["frequency"],
            eis["real"],
            eis["imag"],
            mode=mode,
            lambda_value=lambda_value,
            peak_threshold_fraction=float(schema["drt"]["peak_threshold_fraction"]),
        )
    return {
        "comparison_schema_version": schema["schema_version"],
        "sample_id": sample_id,
        "source_type": manifest_row["source_type"],
        "family": manifest_row["family"],
        "relative_path": manifest_row["relative_path"],
        "kairis": {
            "lin_kk_valid": metrics.get("summary", {}).get("lin_kk_valid"),
            "lin_kk_rmse_pct": metrics.get("summary", {}).get("lin_kk_rmse_pct"),
            "drt_peak_count": metrics.get("summary", {}).get("n_drt_peaks"),
            "regime_drt": metrics.get("summary", {}).get("regime_drt"),
            "regime_gsf": metrics.get("summary", {}).get("regime_gsf"),
        },
        "independent_lin_kk": lin_kk,
        "independent_drt": drt,
    }


def compact_record(record: dict[str, Any], primary_key: str) -> dict[str, Any]:
    lin = record["independent_lin_kk"]
    primary = record["independent_drt"].get(primary_key, {"status": "not_run"})
    lin_result = lin.get("result") or {}
    drt_result = primary.get("result") or {}
    kairis_lin = record["kairis"].get("lin_kk_valid")
    kairis_peaks = record["kairis"].get("drt_peak_count")
    baseline_lin = lin_result.get("pass") if lin["status"] == "completed" else None
    baseline_peaks = (
        drt_result.get("peak_count") if primary.get("status") == "completed" else None
    )
    return {
        "sample_id": record["sample_id"],
        "source_type": record["source_type"],
        "family": record["family"],
        "lin_kk_status": lin["status"],
        "kairis_lin_kk_valid": kairis_lin,
        "baseline_lin_kk_valid": baseline_lin,
        "lin_kk_agreement": (
            bool(kairis_lin) == bool(baseline_lin)
            if kairis_lin is not None and baseline_lin is not None
            else None
        ),
        "baseline_lin_kk_rmse_pct": lin_result.get("normalized_complex_rmse_pct"),
        "drt_primary_status": primary.get("status"),
        "kairis_drt_peak_count": kairis_peaks,
        "baseline_drt_peak_count": baseline_peaks,
        "drt_peak_count_agreement": (
            int(kairis_peaks) == int(baseline_peaks)
            if kairis_peaks is not None and baseline_peaks is not None
            else None
        ),
        "baseline_drt_rmse_pct": drt_result.get("normalized_complex_rmse_pct"),
        "baseline_drt_lambda": drt_result.get("lambda_effective"),
        "regime_drt": record["kairis"].get("regime_drt"),
        "regime_gsf": record["kairis"].get("regime_gsf"),
        "lin_kk_error": lin.get("error", ""),
        "drt_error": primary.get("error", ""),
    }


def aggregate_records(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lin_matrix: Counter[str] = Counter()
    drt_matrix: Counter[str] = Counter()
    families: dict[str, Counter[str]] = defaultdict(Counter)
    sources: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for group in (families[row["family"]], sources[row["source_type"]]):
            group["total"] += 1
            if row["lin_kk_status"] != "completed":
                group["lin_kk_failed"] += 1
            elif row["lin_kk_agreement"]:
                group["lin_kk_agreed"] += 1
            if row["drt_primary_status"] != "completed":
                group["drt_failed"] += 1
            elif row["drt_peak_count_agreement"]:
                group["drt_peak_agreed"] += 1
        if row["baseline_lin_kk_valid"] is not None:
            key = f"kairis_{bool(row['kairis_lin_kk_valid'])}|baseline_{bool(row['baseline_lin_kk_valid'])}"
            lin_matrix[key] += 1
        if row["baseline_drt_peak_count"] is not None:
            key = f"kairis_{row['kairis_drt_peak_count']}|baseline_{row['baseline_drt_peak_count']}"
            drt_matrix[key] += 1
    lin_completed = sum(row["lin_kk_status"] == "completed" for row in rows)
    drt_completed = sum(row["drt_primary_status"] == "completed" for row in rows)
    return {
        "sample_count": len(rows),
        "lin_kk_completed": lin_completed,
        "lin_kk_failed": len(rows) - lin_completed,
        "lin_kk_agreement_count": sum(row["lin_kk_agreement"] is True for row in rows),
        "lin_kk_agreement_fraction": (
            sum(row["lin_kk_agreement"] is True for row in rows) / lin_completed
            if lin_completed else 0.0
        ),
        "drt_primary_completed": drt_completed,
        "drt_primary_failed": len(rows) - drt_completed,
        "drt_peak_agreement_count": sum(
            row["drt_peak_count_agreement"] is True for row in rows
        ),
        "drt_peak_agreement_fraction": (
            sum(row["drt_peak_count_agreement"] is True for row in rows) / drt_completed
            if drt_completed else 0.0
        ),
        "lin_kk_matrix": dict(sorted(lin_matrix.items())),
        "drt_peak_count_matrix": dict(sorted(drt_matrix.items())),
        "families": {name: dict(value) for name, value in sorted(families.items())},
        "source_types": {name: dict(value) for name, value in sorted(sources.items())},
    }


def aggregate_sensitivity(
    records: list[dict[str, Any]], primary_key: str
) -> dict[str, dict[str, Any]]:
    """Summarize every frozen TR-NNLS condition without discarding failures."""
    keys = sorted({key for record in records for key in record["independent_drt"]})
    primary_counts = {
        record["sample_id"]: (record["independent_drt"].get(primary_key, {}).get("result") or {}).get(
            "peak_count"
        )
        for record in records
    }
    summary: dict[str, dict[str, Any]] = {}
    for key in keys:
        completed: list[tuple[dict[str, Any], dict[str, Any]]] = []
        failures: list[dict[str, str]] = []
        peak_distribution: Counter[str] = Counter()
        matches = 0
        comparable = 0
        for record in records:
            outcome = record["independent_drt"].get(key, {"status": "not_run"})
            if outcome.get("status") != "completed":
                failures.append(
                    {"sample_id": record["sample_id"], "error": outcome.get("error", "not run")}
                )
                continue
            result = outcome["result"]
            completed.append((record, result))
            peak_distribution[str(result["peak_count"])] += 1
            primary_count = primary_counts.get(record["sample_id"])
            if primary_count is not None:
                comparable += 1
                matches += int(result["peak_count"] == primary_count)
        rmses = [result["normalized_complex_rmse_pct"] for _, result in completed]
        summary[key] = {
            "completed": len(completed),
            "failed": len(records) - len(completed),
            "median_normalized_complex_rmse_pct": statistics.median(rmses) if rmses else None,
            "peak_count_agreement_with_primary_fraction": matches / comparable if comparable else None,
            "peak_count_distribution": dict(sorted(peak_distribution.items(), key=lambda item: int(item[0]))),
            "failures": failures,
        }
    return summary


def _csv_text(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    from io import StringIO

    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _fraction(count: int, total: int) -> str:
    return f"{100 * count / total:.1f}%" if total else "—"


def html_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    family_rows = []
    for family, item in summary["families"].items():
        total = item["total"]
        family_rows.append(
            "<tr>"
            f"<td>{escape(family)}</td><td>{total}</td>"
            f"<td>{item.get('lin_kk_agreed', 0)} ({_fraction(item.get('lin_kk_agreed', 0), total)})</td>"
            f"<td>{item.get('lin_kk_failed', 0)}</td>"
            f"<td>{item.get('drt_peak_agreed', 0)} ({_fraction(item.get('drt_peak_agreed', 0), total)})</td>"
            f"<td>{item.get('drt_failed', 0)}</td></tr>"
        )
    lin_rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{value}</td></tr>"
        for key, value in summary["lin_kk_matrix"].items()
    )
    drt_rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{value}</td></tr>"
        for key, value in summary["drt_peak_count_matrix"].items()
    )
    sensitivity_rows = "".join(
        "<tr>"
        f"<td>{escape(key)}</td><td>{item['completed']}</td><td>{item['failed']}</td>"
        f"<td>{item['median_normalized_complex_rmse_pct']:.3f}%</td>"
        f"<td>{item['peak_count_agreement_with_primary_fraction']:.1%}</td></tr>"
        for key, item in payload["sensitivity"].items()
    )
    failure_items = "".join(
        f"<li><strong>{escape(key)}</strong> — {escape(item['sample_id'])}: {escape(item['error'])}</li>"
        for key, condition in payload["sensitivity"].items()
        for item in condition["failures"]
    ) or "<li>Nenhuma falha numérica.</li>"
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>KAIRIS — comparação retrospectiva independente</title>
<style>body{{font:15px system-ui;margin:2rem auto;max-width:1200px;padding:0 1rem;color:#17202a}}h1,h2{{color:#16324f}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem}}.card{{padding:1rem;border:1px solid #ccd6df;border-radius:10px;background:#f7fafc}}.value{{font-size:1.7rem;font-weight:700}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}th,td{{border:1px solid #d9e1e8;padding:.45rem;text-align:left}}th{{background:#eaf1f7}}.matrices{{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}}.note{{padding:1rem;background:#fff7df;border-left:4px solid #d59b00}}@media(max-width:750px){{.matrices{{grid-template-columns:1fr}}}}</style></head>
<body><h1>KAIRIS — comparação retrospectiva independente</h1>
<p class="note">Análise exploratória retrospectiva. Não inclui o conjunto confirmatório externo de 42 casos e não altera os endpoints pré-registrados.</p>
<div class="cards"><div class="card"><div>Amostras</div><div class="value">{summary['sample_count']}</div></div>
<div class="card"><div>Concordância Lin-KK</div><div class="value">{summary['lin_kk_agreement_fraction']:.1%}</div></div>
<div class="card"><div>Concordância de picos DRT</div><div class="value">{summary['drt_peak_agreement_fraction']:.1%}</div></div>
<div class="card"><div>Falhas Lin-KK / DRT</div><div class="value">{summary['lin_kk_failed']} / {summary['drt_primary_failed']}</div></div></div>
<h2>Resultados por família</h2><table><thead><tr><th>Família</th><th>n</th><th>Lin-KK concordante</th><th>Falhas Lin-KK</th><th>Picos DRT concordantes</th><th>Falhas DRT</th></tr></thead><tbody>{''.join(family_rows)}</tbody></table>
<div class="matrices"><section><h2>Matriz Lin-KK</h2><table><tr><th>Célula</th><th>n</th></tr>{lin_rows}</table></section><section><h2>Matriz de contagem de picos DRT</h2><table><tr><th>Célula</th><th>n</th></tr>{drt_rows}</table></section></div>
<h2>Análises de sensibilidade DRT</h2><table><tr><th>Condição</th><th>Concluídas</th><th>Falhas</th><th>RMSE mediana</th><th>Picos iguais ao primário</th></tr>{sensitivity_rows}</table>
<details><summary>Falhas numéricas retidas</summary><ul>{failure_items}</ul></details>
<details><summary>Metadados e resumo JSON</summary><pre>{escape(json.dumps(payload, ensure_ascii=False, indent=2))}</pre></details>
</body></html>"""


def execute(
    corpus: Path,
    kairis_output: Path,
    output: Path,
    config_path: Path,
    schema_path: Path,
    *,
    limit: int | None = None,
    overwrite: bool = False,
    primary_only: bool = False,
) -> dict[str, Any]:
    assert_synthetic_only(corpus)
    config = load_config(config_path)
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = _read_csv(corpus / "dataset_manifest.csv")
    if limit is not None:
        manifest = manifest[:limit]
    records_dir = output / "records"
    records: list[dict[str, Any]] = []
    for index, row in enumerate(manifest, start=1):
        record_path = records_dir / f"{row['sample_id']}.json"
        if record_path.is_file() and not overwrite:
            record = json.loads(record_path.read_text(encoding="utf-8"))
            state = "reused"
        else:
            record = run_case(
                row, corpus, kairis_output, config, schema, primary_only
            )
            atomic_write_text(
                record_path, json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            )
            state = "completed"
        records.append(record)
        print(f"[{index}/{len(manifest)}] {row['sample_id']}: {state}", flush=True)

    primary = schema["drt"]["primary_condition"]
    primary_key = _condition_key(str(primary["mode"]), float(primary["lambda_value"]))
    compact = [compact_record(record, primary_key) for record in records]
    summary = aggregate_records(compact)
    sensitivity = aggregate_sensitivity(records, primary_key)
    payload = {
        "format": "KAIRIS-independent-baseline-retrospective-v1",
        "confirmatory": False,
        "external_confirmatory_executed": False,
        "comparison_schema": schema,
        "corpus": str(corpus.resolve()),
        "kairis_artifacts": str(kairis_output.resolve()),
        "primary_drt_condition_key": primary_key,
        "summary": summary,
        "sensitivity": sensitivity,
    }
    atomic_write_text(
        output / "comparison_summary.json",
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(output / "comparison_records.csv", _csv_text(compact))
    atomic_write_text(output / "comparison_report.html", html_report(payload))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--kairis-output", type=Path, default=DEFAULT_KAIRIS_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--config", type=Path, default=ROOT / "config" / "protocol_config.json")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--primary-only", action="store_true", help="execute only the frozen primary DRT condition"
    )
    args = parser.parse_args()
    result = execute(
        args.corpus.resolve(), args.kairis_output.resolve(), args.output.resolve(),
        args.config.resolve(), args.schema.resolve(), limit=args.limit,
        overwrite=args.overwrite, primary_only=args.primary_only,
    )
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
