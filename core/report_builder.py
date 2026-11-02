"""Build KAIRIS metrics files and a single-file interactive HTML report."""

from __future__ import annotations

import html
import json
import math
from urllib.request import urlopen
from datetime import datetime
from pathlib import Path
from typing import Any

from core.artifact_io import atomic_write_bytes, atomic_write_text
from core.branding import FULL_NAME
from core.runtime_paths import workspace_root


D3_CDN_URL = "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"
D3_CACHE_PATH = workspace_root() / "web" / "static" / "d3.min.js"


def to_jsonable(value: Any) -> Any:
    """Recursively convert numerical containers to strict JSON values."""
    if isinstance(value, complex):
        return [float(value.real), float(value.imag)]
    if hasattr(value, "tolist"):
        return to_jsonable(value.tolist())
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if hasattr(value, "item"):
        return to_jsonable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def save_json(path: str | Path, payload: dict[str, Any]) -> Path:
    destination = Path(path)
    atomic_write_text(
        destination,
        json.dumps(to_jsonable(payload), ensure_ascii=False, indent=2, allow_nan=False),
    )
    return destination


def _d3_script(config: dict[str, Any]) -> str:
    """Return a CDN tag or an inline, locally cached D3 bundle."""
    if not bool(config.get("report_d3_inline", False)):
        return f'<script src="{D3_CDN_URL}"></script>'
    if not D3_CACHE_PATH.is_file():
        try:
            with urlopen(D3_CDN_URL, timeout=30) as response:
                bundle = response.read()
        except Exception as error:
            raise RuntimeError(
                "report_d3_inline está ativo, mas não foi possível baixar D3.js. "
                "Verifique a rede ou coloque o bundle em web/static/d3.min.js."
            ) from error
        atomic_write_bytes(D3_CACHE_PATH, bundle)
    source = D3_CACHE_PATH.read_text(encoding="utf-8").replace("</script", "<\\/script")
    return f"<script>{source}</script>"


def _table(mapping: dict[str, Any]) -> str:
    rows = []
    for key, value in mapping.items():
        if isinstance(value, float):
            rendered = f"{value:.6g}"
        elif isinstance(value, (dict, list, tuple)):
            rendered = json.dumps(to_jsonable(value), ensure_ascii=False)
        else:
            rendered = str(value)
        rows.append(f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(rendered)}</td></tr>")
    return "<table>" + "".join(rows) + "</table>"


def _diagnostic_badge(summary: dict[str, Any]) -> str:
    """Render a prominent synthesis label for recognized KAIRIS diagnostics."""
    if summary.get("diagnostic") != "intercalation_pseudocapacitive":
        return ""
    tooltip = (
        "DRT descreve dominância difusiva no domínio temporal; GSF descreve "
        "comportamento pseudocapacitivo no campo espectral global. Os módulos "
        "resolvem observáveis complementares, portanto este padrão não é marcado "
        "como inconsistência."
    )
    escaped = html.escape(tooltip, quote=True)
    return (
        '<span class="diagnostic-badge" tabindex="0" '
        f'data-tooltip="{escaped}" title="{escaped}">'
        "Intercalation Pseudocapacitive</span>"
    )


def _r_inf_badge(summary: dict[str, Any]) -> str:
    """Render an explicit warning when KAIRIS abstains from reporting R_inf."""
    if summary.get("R_inf_status") != "abstained":
        return ""
    tooltip = (
        "A região de alta frequência não atingiu os critérios configurados de fase "
        "e platô de Re(Z). O valor bruto permanece na proveniência, mas R∞ não é "
        "reportado como quantitativamente confiável."
    )
    escaped = html.escape(tooltip, quote=True)
    return (
        '<span class="diagnostic-badge warning-badge" tabindex="0" '
        f'data-tooltip="{escaped}" title="{escaped}">R∞ Abstained</span>'
    )


def _r_inf_extrapolation_badge(summary: dict[str, Any]) -> str:
    if summary.get("R_inf_extrapolation_status") != "accepted":
        return ""
    tooltip = (
        "Estimativa secundária pelo modelo assintótico R∞ + A(jω)^−n, aceita por "
        "resíduo e estabilidade entre janelas. Não substitui a observação direta, "
        "não é usada no ESC G4 e seu intervalo representa sensibilidade à janela."
    )
    escaped = html.escape(tooltip, quote=True)
    return (
        '<span class="diagnostic-badge secondary-badge" tabindex="0" '
        f'data-tooltip="{escaped}" title="{escaped}">R∞ Extrapolated · Secondary</span>'
    )


def _inline_svg(path: str | Path) -> str:
    """Read a Matplotlib SVG as inline markup, without external file links."""
    content = Path(path).read_text(encoding="utf-8")
    start = content.find("<svg")
    return content[start:] if start >= 0 else ""


def _safe_inline_json(payload: Any) -> str:
    """Serialize JSON safely inside a script element."""
    return (
        json.dumps(to_jsonable(payload), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def _chart_payload(outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    a1, a2, a3, a4 = (outputs[key] for key in ("agent1", "agent2", "agent3", "agent4"))
    z_data = a1["Z_data"]
    eis = [
        {
            "frequency": float(frequency),
            "real": float(real),
            "imag": float(imag),
            "smoothness_pass": bool(passed),
        }
        for frequency, real, imag, passed in zip(
            z_data["frequency"], z_data["real"], z_data["imag"], z_data["smoothness_pass"]
        )
    ]
    lin_kk = [
        {
            "frequency": float(frequency),
            "measured_real": float(measured_real),
            "measured_imag": float(measured_imag),
            "fit_real": float(fit_real),
            "fit_imag": float(fit_imag),
            "residual_pct": float(residual_pct),
            "pass": bool(passed),
        }
        for frequency, measured_real, measured_imag, fit_real, fit_imag, residual_pct, passed in zip(
            z_data["frequency"],
            z_data["real"],
            z_data["imag"],
            z_data["lin_kk_fit_real"],
            z_data["lin_kk_fit_imag"],
            z_data["lin_kk_residual_magnitude_pct"],
            z_data["lin_kk_pass"],
        )
    ]
    drt = [
        {
            "tau": float(tau),
            "gamma": float(gamma),
            "frequency": float(1.0 / (2.0 * math.pi * tau)),
        }
        for tau, gamma in zip(a2["tau"], a2["gamma"])
    ]
    q_map = [
        {
            "frequency": float(frequency),
            "x": float(x_value),
            "y": float(y_value),
            "q": float(q_value),
            "alpha": None if alpha is None or not math.isfinite(float(alpha)) else float(alpha),
        }
        for frequency, x_value, y_value, q_value, alpha in zip(
            a3["frequency"], a3["x_n"], a3["y_n"], a3["q"], a3["alpha"]
        )
    ]
    return {
        "eis": eis,
        "lin_kk": lin_kk,
        "drt": drt,
        "drt_peaks": a2["peaks"],
        "q_map": q_map,
        "esc": {group: a4[group]["points"] for group in ("G1", "G2", "G3", "G4")},
    }


def build_html_report(
    destination: str | Path,
    sample_name: str,
    config: dict[str, Any],
    outputs: dict[str, dict[str, Any]],
    summary: dict[str, Any],
    interpretations: list[str],
    llm_text: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> Path:
    """Create one HTML file with inline data, SVGs, CSS and JavaScript.

    D3 itself is loaded from its CDN as requested. No chart data, image or style
    file is referenced externally.
    """
    a1, a2, a3, a4 = (outputs[key] for key in ("agent1", "agent2", "agent3", "agent4"))
    agent1_metrics = {key: value for key, value in a1.items() if key not in {"Z_data", "figures"}}
    agent2_metrics = {key: value for key, value in a2.items() if key not in {"tau", "gamma", "figures"}}
    agent3_metrics = {
        key: value
        for key, value in a3.items()
        if key not in {"frequency", "x_n", "y_n", "q", "alpha", "kphi", "gradient", "figures"}
    }
    agent4_metrics = {
        group: {key: value for key, value in a4[group].items() if key != "points"}
        for group in ("G1", "G2", "G3", "G4")
    }
    agent4_metrics["G2_interpretation"] = a4["G2_interpretation"]
    static_svgs = "".join(
        f'<figure class="static-svg">{_inline_svg(path)}<figcaption>{html.escape(Path(path).stem)}</figcaption></figure>'
        for path in a3.get("figures", [])
        if Path(path).is_file() and Path(path).suffix.lower() == ".svg"
    )
    rules_html = "".join(f"<li>{html.escape(text)}</li>" for text in interpretations)
    llm_html = (
        f"<h3>Interpretação estendida</h3><p>{html.escape(llm_text)}</p>"
        if llm_text
        else "<p><em>Interpretação por LLM não utilizada; síntese determinística ativa.</em></p>"
    )
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    chart_json = _safe_inline_json(_chart_payload(outputs))
    d3_script = _d3_script(config)
    provenance_html = _table(provenance or {})
    diagnostic_badge = (
        _diagnostic_badge(summary)
        + _r_inf_badge(summary)
        + _r_inf_extrapolation_badge(summary)
    )

    document = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(FULL_NAME)} — {html.escape(sample_name)}</title>
{d3_script}
<style>
:root{{--ink:#172126;--muted:#5d7078;--accent:#11647a;--panel:#fff;--page:#eef3f4}}
*{{box-sizing:border-box}}body{{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;background:var(--page);color:var(--ink)}}
main{{max-width:1280px;margin:auto;padding:24px}}header,section{{background:var(--panel);border-radius:12px;padding:22px;margin-bottom:18px;box-shadow:0 2px 10px #00000012}}
h1,h2{{color:var(--accent)}}h3{{margin-bottom:8px}}.lede{{color:var(--muted)}}
table{{border-collapse:collapse;width:100%;margin:12px 0 20px}}th,td{{border:1px solid #d8e1e5;padding:8px;text-align:left;vertical-align:top}}th{{width:28%;background:#edf6f7}}
.chart-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:18px}}.chart-card{{border:1px solid #d8e1e5;border-radius:10px;padding:10px;min-width:0}}
.chart{{width:100%;min-height:390px}}.chart svg{{display:block;width:100%;height:auto}}.axis text{{fill:#40535b}}.axis path,.axis line{{stroke:#8799a0}}.series-line{{fill:none;stroke:#176d83;stroke-width:2}}
.point{{stroke:#fff;stroke-width:.7;cursor:crosshair}}.zoom-hint{{color:var(--muted);font-size:.82rem;margin:2px 8px 8px}}.tooltip{{position:fixed;display:none;z-index:20;pointer-events:none;background:#14272e;color:#fff;padding:8px 10px;border-radius:6px;font-size:12px;line-height:1.45;box-shadow:0 3px 14px #0005}}
.static-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}}.static-svg{{margin:0;border:1px solid #d8e1e5;border-radius:10px;padding:8px}}.static-svg svg{{max-width:100%;height:auto}}figcaption{{text-align:center;color:var(--muted);font-size:.9rem}}
.diagnostic-badge{{position:relative;display:inline-block;margin-left:.55rem;padding:.32rem .62rem;border-radius:999px;background:#6a3db8;color:#fff;font-size:.78rem;vertical-align:middle;cursor:help;letter-spacing:.01em}}
.warning-badge{{background:#a13d2d}}
.secondary-badge{{background:#276b55}}
.diagnostic-badge:hover::after,.diagnostic-badge:focus::after{{content:attr(data-tooltip);position:absolute;z-index:30;left:0;top:calc(100% + .5rem);width:min(420px,75vw);padding:.65rem .75rem;border-radius:7px;background:#14272e;color:#fff;font-size:.78rem;font-weight:400;line-height:1.4;box-shadow:0 3px 14px #0005}}
@media(max-width:600px){{main{{padding:10px}}.chart-grid{{grid-template-columns:1fr}}.chart-card{{padding:4px}}}}
</style></head><body><main>
<header><h1>Relatório KAIRIS: {html.escape(sample_name)}</h1><p class="lede"><strong>{html.escape(FULL_NAME)}</strong><br>Gerado em {html.escape(generated)} · análise EIS sem circuito equivalente.</p></header>
<section><h2>1. EIS bruto e Spectral Smoothness (local residue)</h2>
<p><strong>Nota:</strong> Spectral Smoothness é um indicador de suavidade por resíduo local; não é uma validação integral de Kramers-Kronig.</p>{_table(agent1_metrics)}
<div class="chart-grid"><article class="chart-card"><h3>Nyquist</h3><p class="zoom-hint">Role para zoom; arraste para navegar.</p><div id="nyquist" class="chart"></div></article>
<article class="chart-card"><h3>Bode — módulo</h3><div id="bode-magnitude" class="chart"></div></article>
<article class="chart-card"><h3>Bode — fase</h3><div id="bode-phase" class="chart"></div></article></div></section>
<section><h2>1.1 Validação linear Kramers-Kronig (Lin-KK)</h2>
<p>O teste Lin-KK reproduz o espectro com uma base compatível com Kramers-Kronig formada por R₀, elementos RC log-distribuídos e indutância serial. A aprovação usa μ, RMSE normalizado e a fração de pontos acima dos limites configurados; ela indica compatibilidade com Lin-KK, mas não substitui controle experimental de linearidade, estabilidade e causalidade.</p>
<div class="chart-grid"><article class="chart-card"><h3>Nyquist ajustado por Lin-KK</h3><div id="lin-kk-fit" class="chart"></div></article>
<article class="chart-card"><h3>Resíduo normalizado Lin-KK</h3><div id="lin-kk-residual" class="chart"></div></article></div></section>
<section><h2>2. Distribuição de Tempos de Relaxação</h2>{_table(agent2_metrics)}<div class="chart-card"><h3>Espectro DRT</h3><div id="drt" class="chart"></div></div></section>
<section><h2>3. Golden Spectral Field</h2>{_table(agent3_metrics)}
<div class="chart-card"><h3>Mapa q interativo</h3><div id="q-map" class="chart"></div></div>
<h3>Métricas estáticas</h3><div class="static-grid">{static_svgs}</div></section>
<section><h2>4. Diagrama de Emanuel-Smith</h2>{_table(agent4_metrics)}<div class="chart-grid">
{''.join(f'<article class="chart-card"><h3>ESC {group}</h3><p class="zoom-hint">Role para zoom; arraste para navegar.</p><div id="esc-{group.lower()}" class="chart"></div></article>' for group in ('G1','G2','G3','G4'))}
</div></section>
<section><h2>5. Síntese integrada {diagnostic_badge}</h2>{_table(summary)}<h3>Interpretação por regras</h3><ul>{rules_html}</ul>{llm_html}</section>
<section><h2>Parâmetros KAIRIS</h2>{_table(config)}</section>
<footer><details><summary>Proveniência da execução</summary>{provenance_html}</details></footer>
</main><div id="tooltip" class="tooltip"></div>
<script id="kairis-chart-data" type="application/json">{chart_json}</script>
<script>
"use strict";
const KAIRIS = JSON.parse(document.getElementById("kairis-chart-data").textContent);
const tooltip = d3.select("#tooltip");
const fmt = d3.format(".5~g");
let chartSerial = 0;
function showTip(event, markup) {{ tooltip.style("display","block").html(markup).style("left",`${{event.clientX+14}}px`).style("top",`${{event.clientY+14}}px`); }}
function hideTip() {{ tooltip.style("display","none"); }}
function extentPad(values, fraction=0.07) {{ const e=d3.extent(values); const span=(e[1]-e[0])||Math.abs(e[0])||1; return [e[0]-span*fraction,e[1]+span*fraction]; }}
function xyChart(selector, rawData, options) {{
  const data=rawData.filter(d=>Number.isFinite(options.x(d))&&Number.isFinite(options.y(d)));
  const host=document.querySelector(selector); const width=Math.max(420,host.clientWidth||700),height=410;
  const margin={{top:22,right:25,bottom:58,left:72}},innerW=width-margin.left-margin.right,innerH=height-margin.top-margin.bottom;
  const svg=d3.select(selector).append("svg").attr("viewBox",`0 0 ${{width}} ${{height}}`).attr("role","img").attr("aria-label",options.aria||"");
  const root=svg.append("g").attr("transform",`translate(${{margin.left}},${{margin.top}})`);
  const xValues=data.map(options.x).concat(options.unitCircle?[-1,1]:[]),yValues=data.map(options.y).concat(options.unitCircle?[-1,1]:[]);
  const x0=options.xLog?d3.scaleLog().domain(d3.extent(xValues)).nice():d3.scaleLinear().domain(extentPad(xValues)).nice();
  const y0=options.yLog?d3.scaleLog().domain(d3.extent(yValues)).nice():d3.scaleLinear().domain(extentPad(yValues)).nice();
  x0.range([0,innerW]); y0.range([innerH,0]);
  const clipId=`clip-kairis-${{++chartSerial}}`; svg.append("defs").append("clipPath").attr("id",clipId).append("rect").attr("width",innerW).attr("height",innerH);
  const xAxis=root.append("g").attr("class","axis").attr("transform",`translate(0,${{innerH}})`).call(d3.axisBottom(x0).ticks(6,"~g"));
  const yAxis=root.append("g").attr("class","axis").call(d3.axisLeft(y0).ticks(6,"~g"));
  root.append("text").attr("x",innerW/2).attr("y",innerH+46).attr("text-anchor","middle").text(options.xLabel);
  root.append("text").attr("transform","rotate(-90)").attr("x",-innerH/2).attr("y",-54).attr("text-anchor","middle").text(options.yLabel);
  const plot=root.append("g").attr("clip-path",`url(#${{clipId}})`);
  let x=x0,y=y0;
  let reference=null;
  if(options.unitCircle) {{ const circleData=d3.range(0,361).map(deg=>{{const r=deg*Math.PI/180;return {{x:Math.cos(r),y:Math.sin(r)}};}}); reference=plot.append("path").datum(circleData).attr("fill","none").attr("stroke","#7d8c91").attr("stroke-dasharray","5 4"); reference.attr("d",d3.line().x(d=>x(d.x)).y(d=>y(d.y))); }}
  const line=plot.append("path").datum(data).attr("class","series-line").attr("d",d3.line().defined(d=>Number.isFinite(options.x(d))&&Number.isFinite(options.y(d))).x(d=>x(options.x(d))).y(d=>y(options.y(d))));
  const color=options.color||(()=>"#176d83");
  const points=plot.selectAll("circle.point").data(data).join("circle").attr("class","point").attr("r",options.radius||3.6).attr("fill",color).attr("cx",d=>x(options.x(d))).attr("cy",d=>y(options.y(d))).on("pointermove",(event,d)=>showTip(event,options.tip(d))).on("pointerleave",hideTip);
  if(options.zoom) {{
    root.insert("rect",":first-child").attr("width",innerW).attr("height",innerH).attr("fill","transparent").attr("pointer-events","all");
    root.style("cursor","grab").call(d3.zoom().scaleExtent([0.7,20]).extent([[0,0],[innerW,innerH]]).on("zoom",event=>{{
      x=event.transform.rescaleX(x0); y=event.transform.rescaleY(y0); xAxis.call(d3.axisBottom(x).ticks(6,"~g")); yAxis.call(d3.axisLeft(y).ticks(6,"~g"));
      line.attr("d",d3.line().x(d=>x(options.x(d))).y(d=>y(options.y(d)))); points.attr("cx",d=>x(options.x(d))).attr("cy",d=>y(options.y(d)));
      if(reference) reference.attr("d",d3.line().x(d=>x(d.x)).y(d=>y(d.y)));
    }})).on("dblclick.zoom",null);
  }}
  return {{svg,root,plot,x,y,data}};
}}
const frequencyTip=d=>`<strong>f:</strong> ${{fmt(d.frequency)}} Hz`;
xyChart("#nyquist",KAIRIS.eis,{{x:d=>d.real,y:d=>-d.imag,xLabel:"Re(Z) / Ω",yLabel:"−Im(Z) / Ω",zoom:true,aria:"Nyquist interativo",color:d=>d.smoothness_pass?"#238b45":"#cb181d",tip:d=>`${{frequencyTip(d)}}<br>Re(Z): ${{fmt(d.real)}} Ω<br>−Im(Z): ${{fmt(-d.imag)}} Ω<br>Spectral Smoothness: ${{d.smoothness_pass?"aprovado":"reprovado"}}`}});
xyChart("#lin-kk-fit",KAIRIS.lin_kk,{{x:d=>d.fit_real,y:d=>-d.fit_imag,xLabel:"Re(Z ajuste) / Ω",yLabel:"−Im(Z ajuste) / Ω",aria:"Ajuste Nyquist Lin-KK",color:d=>d.pass?"#238b45":"#cb181d",tip:d=>`${{frequencyTip(d)}}<br>Re medido: ${{fmt(d.measured_real)}} Ω<br>−Im medido: ${{fmt(-d.measured_imag)}} Ω<br>Re ajustado: ${{fmt(d.fit_real)}} Ω<br>−Im ajustado: ${{fmt(-d.fit_imag)}} Ω<br>Resíduo: ${{fmt(d.residual_pct)}}%`}});
xyChart("#lin-kk-residual",KAIRIS.lin_kk.slice().sort((a,b)=>a.frequency-b.frequency),{{x:d=>d.frequency,y:d=>d.residual_pct,xLog:true,xLabel:"f / Hz",yLabel:"Resíduo normalizado / %",aria:"Resíduos Lin-KK",color:d=>d.pass?"#238b45":"#cb181d",tip:d=>`${{frequencyTip(d)}}<br>Resíduo: ${{fmt(d.residual_pct)}}%<br>Lin-KK: ${{d.pass?"aprovado":"reprovado"}}`}});
const bode=KAIRIS.eis.map(d=>({{...d,magnitude:Math.hypot(d.real,d.imag),phase:Math.atan2(d.imag,d.real)*180/Math.PI}})).sort((a,b)=>a.frequency-b.frequency);
xyChart("#bode-magnitude",bode,{{x:d=>d.frequency,y:d=>d.magnitude,xLog:true,yLog:true,xLabel:"f / Hz",yLabel:"|Z| / Ω",aria:"Bode módulo interativo",tip:d=>`${{frequencyTip(d)}}<br>|Z|: ${{fmt(d.magnitude)}} Ω`}});
xyChart("#bode-phase",bode,{{x:d=>d.frequency,y:d=>d.phase,xLog:true,xLabel:"f / Hz",yLabel:"Fase / °",aria:"Bode fase interativo",tip:d=>`${{frequencyTip(d)}}<br>Fase: ${{fmt(d.phase)}}°`}});
const drtChart=xyChart("#drt",KAIRIS.drt,{{x:d=>d.tau,y:d=>d.gamma,xLog:true,xLabel:"τ / s",yLabel:"γ(ln τ) / Ω",aria:"Espectro DRT interativo",tip:d=>`${{frequencyTip(d)}}<br>τ: ${{fmt(d.tau)}} s<br>γ: ${{fmt(d.gamma)}} Ω`}});
drtChart.plot.selectAll("circle.peak").data(KAIRIS.drt_peaks).join("circle").attr("class","peak").attr("r",6).attr("fill","#d7301f").attr("stroke","#fff").attr("cx",d=>drtChart.x(d.tau)).attr("cy",d=>drtChart.y(d.gamma_max)).on("pointermove",(event,d)=>showTip(event,`<strong>Pico DRT</strong><br>f: ${{fmt(d.f_char)}} Hz<br>τ: ${{fmt(d.tau)}} s<br>γ_max: ${{fmt(d.gamma_max)}} Ω<br>Área: ${{fmt(d.area)}} Ω`)).on("pointerleave",hideTip);
const alphaValues=KAIRIS.q_map.map(d=>d.alpha).filter(Number.isFinite); const alphaExtent=d3.extent(alphaValues); const qDomain=alphaExtent[0]===alphaExtent[1]?[alphaExtent[0]-1,alphaExtent[1]+1]:alphaExtent; const qColor=d3.scaleSequential(d3.interpolateTurbo).domain(qDomain);
xyChart("#q-map",KAIRIS.q_map,{{x:d=>d.x,y:d=>d.y,xLabel:"xₙ",yLabel:"yₙ",aria:"Mapa q interativo",radius:4.2,color:d=>Number.isFinite(d.alpha)?qColor(d.alpha):"#777",tip:d=>`${{frequencyTip(d)}}<br>xₙ: ${{fmt(d.x)}}<br>yₙ: ${{fmt(d.y)}}<br>q: ${{fmt(d.q)}}<br>α: ${{Number.isFinite(d.alpha)?fmt(d.alpha):"n/d"}}`}});
for(const group of ["G1","G2","G3","G4"]) {{ const points=KAIRIS.esc[group]; if(!points.length) {{ d3.select(`#esc-${{group.toLowerCase()}}`).append("p").attr("class","lede").text("KAIRIS absteve este grupo: impedância de referência sem confiabilidade suficiente."); continue; }} const color=d3.scaleSequential(d3.interpolateViridis).domain(d3.extent(points,d=>Math.log10(d.frequency))); xyChart(`#esc-${{group.toLowerCase()}}`,points,{{x:d=>d.real,y:d=>d.imag,xLabel:"Re(Γ)",yLabel:"Im(Γ)",zoom:true,unitCircle:true,aria:`ESC ${{group}} interativo`,color:d=>color(Math.log10(d.frequency)),tip:d=>`${{frequencyTip(d)}}<br>Re(Γ): ${{fmt(d.real)}}<br>Im(Γ): ${{fmt(d.imag)}}<br>|Γ|: ${{fmt(d.magnitude)}}`}}); }}
</script></body></html>"""
    path = Path(destination)
    return atomic_write_text(path, document)
