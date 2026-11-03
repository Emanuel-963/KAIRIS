"""Independent command-line interface for the original KAIRIS GSF analysis."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from agents.agent3_gsf import Agent3_GSF
from core.config_loader import load_config
from core.config_validator import validate_config
from core.eis_loader import load_btlab
from core.report_builder import save_json
from core.runtime_paths import default_config_path


SUPPORTED_SUFFIXES = {".csv", ".txt"}


def _sample_id(path: Path, root: Path) -> str:
    relative = path.relative_to(root) if root.is_dir() else Path(path.name)
    raw = "__".join(relative.with_suffix("").parts)
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw).strip("_.") or "spectrum"


def analyze_file(
    input_path: Path,
    output_dir: Path,
    config: dict[str, Any],
    sample_name: str,
    overwrite: bool = False,
) -> Path:
    """Run GSF directly from a raw EIS file and return its metrics path."""
    destination = output_dir / "metrics" / f"{sample_name}_gsf.json"
    if destination.exists() and not overwrite:
        return destination
    spectrum = load_btlab(input_path, config)
    z_data = {
        "frequency": spectrum["frequency"],
        "real": spectrum["real"],
        "imag": spectrum["imag"],
    }
    result = Agent3_GSF(z_data, config).run(output_dir, sample_name)
    result.update(
        {
            "analysis": "GSF standalone",
            "source_file": str(input_path.resolve()),
            "kairis_component": True,
        }
    )
    save_json(destination, result)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GSF independente: calcula o Golden Spectral Field diretamente de EIS bruto."
    )
    parser.add_argument("input", help="Arquivo EIS .txt/.csv ou diretório")
    parser.add_argument("--output", default="output_gsf", help="Diretório dos resultados GSF")
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

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
        destination = analyze_file(path, output, config, _sample_id(path, root), args.overwrite)
        print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
