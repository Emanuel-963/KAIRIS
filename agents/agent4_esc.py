"""KAIRIS Agent 4: Emanuel-Smith Chart transformations for four DRT references."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.esc_engine import calculate_group
from core.report_builder import save_json


class Agent4_ESC:
    def __init__(
        self,
        z_data: dict[str, Any],
        z0_g1: Any,
        z0_g2: Any,
        z0_g3: Any,
        z0_g4: Any,
        config: dict[str, Any],
    ):
        self.z_data = z_data
        self.references = {"G1": z0_g1, "G2": z0_g2, "G3": z0_g3, "G4": z0_g4}
        self.config = config

    def run(self, output_dir: str | Path, sample_name: str) -> dict[str, Any]:
        frequency = np.asarray(self.z_data["frequency"], dtype=float)
        z = np.asarray(self.z_data["real"], dtype=float) + 1j * np.asarray(self.z_data["imag"], dtype=float)
        order = np.argsort(frequency)[::-1]
        frequency, z = frequency[order], z[order]
        output: dict[str, Any] = {}
        for group_name, reference in self.references.items():
            group = calculate_group(z, reference)
            output[group_name] = {key: value for key, value in group.items() if key != "gamma"}
            output[group_name]["points"] = [
                {
                    "frequency": float(freq),
                    "real": float(value.real),
                    "imag": float(value.imag),
                    "magnitude": float(abs(value)),
                }
                for freq, value in zip(frequency, group["gamma"])
                if np.isfinite(value.real) and np.isfinite(value.imag)
            ]

        g2 = output["G2"]
        interpretations = []
        if g2["lf_point"][0] > 0.8:
            interpretations.append("Difusão domina completamente em baixa frequência.")
        if g2["gamma_mean"] < 0.3:
            interpretations.append("Sistema próximo ao cruzamento difusivo em toda a faixa.")
        output["G2_interpretation"] = interpretations or ["Sem condição-limite de G2 detectada."]
        output["figures"] = []
        return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("agent1_json"); parser.add_argument("agent2_json")
    parser.add_argument("--output", default="output"); parser.add_argument("--config", default="config/protocol_config.json")
    args = parser.parse_args(); config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    a1 = json.loads(Path(args.agent1_json).read_text(encoding="utf-8")); a2 = json.loads(Path(args.agent2_json).read_text(encoding="utf-8"))
    sample = Path(args.agent1_json).stem.replace("_agent1", "")
    result = Agent4_ESC(a1["Z_data"], a2["Z0_G1"], a2.get("Z0_G2_complex", a2["Z0_G2"]), a2["Z0_G3"], a2["Z0_G4"], config).run(args.output, sample)
    save_json(Path(args.output) / "metrics" / f"{sample}_agent4.json", result)


if __name__ == "__main__":
    main()

