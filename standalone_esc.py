"""Independent command-line interface for the original KAIRIS ESC analysis."""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any

import numpy as np

from core.artifact_io import atomic_write_text
from core.config_loader import load_config
from core.config_validator import validate_config
from core.eis_loader import load_btlab
from core.esc_engine import as_complex_reference, calculate_group
from core.report_builder import save_json
from core.runtime_paths import default_config_path


SUPPORTED_SUFFIXES = {".csv", ".txt"}


def parse_reference(value: str) -> tuple[str, complex]:
    """Parse NAME=REAL or NAME=REAL,IMAG without inferring physical meaning."""
    if "=" not in value:
        raise argparse.ArgumentTypeError("use NOME=REAL ou NOME=REAL,IMAG")
    name, raw = value.split("=", 1)
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name.strip()).strip("_.")
    if not name:
        raise argparse.ArgumentTypeError("a referência precisa de um nome")
    try:
        parts = [float(part.strip()) for part in raw.split(",")]
    except ValueError as error:
        raise argparse.ArgumentTypeError("Z0 deve conter números válidos") from error
    if len(parts) == 1:
        reference = complex(parts[0], 0.0)
    elif len(parts) == 2:
        reference = complex(parts[0], parts[1])
    else:
        raise argparse.ArgumentTypeError("use no máximo as partes real e imaginária")
    if not np.isfinite(reference.real + reference.imag) or np.isclose(abs(reference), 0.0):
        raise argparse.ArgumentTypeError("Z0 deve ser finito e diferente de zero")
    return name, reference


def _sample_id(path: Path, root: Path) -> str:
    relative = path.relative_to(root) if root.is_dir() else Path(path.name)
    raw = "__".join(relative.with_suffix("").parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_.") or "spectrum"


def _html_report(sample: str, groups: dict[str, Any]) -> str:
    payload = json.dumps(groups, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    cards = "".join(
        f'<article><h2>{html.escape(name)}</h2><p>Z₀ = {html.escape(str(group["Z0"]))} Ω</p>'
        f'<div class="chart" id="chart-{index}"></div></article>'
        for index, (name, group) in enumerate(groups.items())
    )
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESC independente — {html.escape(sample)}</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>body{{font-family:Segoe UI,Arial,sans-serif;background:#eef3f4;color:#172126;margin:0}}main{{max-width:1200px;margin:auto;padding:24px}}header,article{{background:#fff;border-radius:12px;padding:20px;margin-bottom:18px}}.chart{{min-height:430px}}svg{{max-width:100%;height:auto}}.tip{{position:fixed;display:none;pointer-events:none;background:#14272e;color:#fff;padding:8px;border-radius:6px;font-size:12px}}</style>
</head><body><main><header><h1>Emanuel–Smith Chart (ESC)</h1><p>Análise independente · {html.escape(sample)} · role para zoom e arraste para navegar.</p></header>{cards}</main><div class="tip"></div>
<script id="esc-data" type="application/json">{payload}</script><script>
const groups=JSON.parse(document.getElementById('esc-data').textContent),tip=d3.select('.tip'),fmt=d3.format('.5g');
Object.entries(groups).forEach(([name,g],i)=>{{const data=g.points,w=620,h=410,m={{t:20,r:20,b:52,l:62}},svg=d3.select(`#chart-${{i}}`).append('svg').attr('viewBox',`0 0 ${{w}} ${{h}}`),plot=svg.append('g'),baseX=d3.scaleLinear().domain(d3.extent(data,d=>d.real)).nice().range([m.l,w-m.r]),baseY=d3.scaleLinear().domain(d3.extent(data,d=>d.imag)).nice().range([h-m.b,m.t]);const draw=(x,y)=>{{plot.selectAll('*').remove();plot.append('g').attr('transform',`translate(0,${{h-m.b}})`).call(d3.axisBottom(x));plot.append('g').attr('transform',`translate(${{m.l}},0)`).call(d3.axisLeft(y));plot.append('path').datum(data).attr('fill','none').attr('stroke','#176d83').attr('stroke-width',2).attr('d',d3.line().x(d=>x(d.real)).y(d=>y(d.imag)));plot.selectAll('circle').data(data).join('circle').attr('cx',d=>x(d.real)).attr('cy',d=>y(d.imag)).attr('r',3.5).attr('fill','#6a3db8').on('pointermove',(e,d)=>tip.style('display','block').style('left',`${{e.clientX+12}}px`).style('top',`${{e.clientY+12}}px`).html(`f: ${{fmt(d.frequency)}} Hz<br>Re(Γ): ${{fmt(d.real)}}<br>Im(Γ): ${{fmt(d.imag)}}<br>|Γ|: ${{fmt(d.magnitude)}}`)).on('pointerleave',()=>tip.style('display','none'));}};draw(baseX,baseY);svg.call(d3.zoom().scaleExtent([.5,20]).on('zoom',e=>draw(e.transform.rescaleX(baseX),e.transform.rescaleY(baseY))));}});
</script></body></html>"""


def analyze_file(
    input_path: Path,
    output_dir: Path,
    config: dict[str, Any],
    sample_name: str,
    references: dict[str, complex],
    overwrite: bool = False,
) -> tuple[Path, Path]:
    """Transform raw EIS with explicit named Z0 references."""
    metrics_path = output_dir / "metrics" / f"{sample_name}_esc.json"
    report_path = output_dir / "reports" / f"{sample_name}_esc.html"
    if metrics_path.exists() and report_path.exists() and not overwrite:
        return metrics_path, report_path
    spectrum = load_btlab(input_path, config)
    order = np.argsort(spectrum["frequency"])[::-1]
    frequency = spectrum["frequency"][order]
    impedance = spectrum["real"][order] + 1j * spectrum["imag"][order]
    groups: dict[str, Any] = {}
    for name, reference in references.items():
        calculated = calculate_group(impedance, reference)
        groups[name] = {key: value for key, value in calculated.items() if key != "gamma"}
        groups[name]["points"] = [
            {
                "frequency": float(freq),
                "real": float(gamma.real),
                "imag": float(gamma.imag),
                "magnitude": float(abs(gamma)),
            }
            for freq, gamma in zip(frequency, calculated["gamma"])
            if np.isfinite(gamma.real) and np.isfinite(gamma.imag)
        ]
    payload = {
        "analysis": "ESC standalone",
        "source_file": str(input_path.resolve()),
        "kairis_component": True,
        "reference_policy": "explicit_user_supplied",
        "groups": groups,
    }
    save_json(metrics_path, payload)
    atomic_write_text(report_path, _html_report(sample_name, groups))
    return metrics_path, report_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ESC independente: transforma EIS bruto usando referências Z0 explícitas."
    )
    parser.add_argument("input", help="Arquivo EIS .txt/.csv ou diretório")
    parser.add_argument(
        "--z0",
        action="append",
        required=True,
        type=parse_reference,
        metavar="NOME=REAL[,IMAG]",
        help="Referência nomeada; repita a opção para comparar vários Z0",
    )
    parser.add_argument("--output", default="output_esc")
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    references = dict(args.z0)
    if len(references) != len(args.z0):
        parser.error("os nomes fornecidos em --z0 devem ser únicos")
    source = Path(args.input).expanduser().resolve()
    if not source.exists():
        parser.error(f"entrada não encontrada: {source}")
    config = load_config(args.config)
    validate_config(config)
    output = Path(args.output).expanduser().resolve()
    root = source if source.is_dir() else source.parent
    files = (
        [source]
        if source.is_file()
        else sorted(path for path in source.rglob("*") if path.suffix.lower() in SUPPORTED_SUFFIXES)
    )
    if not files:
        parser.error("nenhum arquivo .txt ou .csv encontrado")
    for path in files:
        metrics, report = analyze_file(
            path, output, config, _sample_id(path, root), references, args.overwrite
        )
        print(f"{metrics}\n{report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
