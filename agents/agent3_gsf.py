"""KAIRIS Agent 3: Golden Spectral Field metrics and static SVG figures."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.gsf_engine import calculate_gsf
from core.artifact_io import atomic_binary_writer
from core.report_builder import save_json


class Agent3_GSF:
    def __init__(self, z_data: dict[str, Any], config: dict[str, Any]):
        self.z_data = z_data
        self.config = config

    def run(self, output_dir: str | Path, sample_name: str) -> dict[str, Any]:
        result = calculate_gsf(
            np.asarray(self.z_data["frequency"]), np.asarray(self.z_data["real"]),
            np.asarray(self.z_data["imag"]), self.config,
        )
        figure_dir = Path(output_dir) / "figures" / sample_name
        figure_dir.mkdir(parents=True, exist_ok=True)
        paths = [figure_dir / name for name in ("alpha_vs_f.svg", "kphi_vs_f.svg", "gradient_s.svg")]
        logf = np.log10(result["frequency"])
        self._line_plot(logf, result["alpha"], "log₁₀(f / Hz)", "α", "Expoente local α", paths[0])
        self._line_plot(logf, result["kphi"], "log₁₀(f / Hz)", "kφ", "Fator espectral áureo", paths[1])
        self._line_plot(logf, result["gradient"], "log₁₀(f / Hz)", "S", "Gradiente espectral", paths[2])

        output = {key: value for key, value in result.items() if key not in {"frequency", "x_n", "y_n", "q", "alpha", "kphi", "gradient"}}
        output["figures"] = [str(path.resolve()) for path in paths]
        output.update({key: result[key] for key in ("frequency", "x_n", "y_n", "q", "alpha", "kphi", "gradient")})
        return output

    def _line_plot(self, x: np.ndarray, y: np.ndarray, xlabel: str, ylabel: str, title: str, path: Path) -> None:
        fig, axis = plt.subplots(figsize=(7, 4.5)); axis.plot(x, y, "o-", color="#6a51a3", ms=3)
        axis.set(xlabel=xlabel, ylabel=ylabel, title=title); axis.grid(alpha=.25); fig.tight_layout()
        try:
            with atomic_binary_writer(path) as handle:
                fig.savefig(handle, format="svg")
        finally:
            plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("input_json"); parser.add_argument("--output", default="output"); parser.add_argument("--config", default="config/protocol_config.json"); args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8")); agent1 = json.loads(Path(args.input_json).read_text(encoding="utf-8")); sample = Path(args.input_json).stem.replace("_agent1", "")
    save_json(Path(args.output) / "metrics" / f"{sample}_agent3.json", Agent3_GSF(agent1["Z_data"], config).run(args.output, sample))


if __name__ == "__main__":
    main()

