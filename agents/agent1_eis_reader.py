"""KAIRIS Agent 1: BT-Lab EIS ingestion and quality screening."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.eis_loader import classify_morphology, json_safe_z_data, load_btlab, validate_spectral_smoothness
from core.lin_kk_validator import validate_lin_kk
from core.report_builder import save_json


class Agent1_EIS:
    def __init__(self, filepath: str | Path, config: dict[str, Any]):
        self.filepath = Path(filepath)
        self.config = config

    def run(self, output_dir: str | Path, sample_name: str) -> dict[str, Any]:
        spectrum = load_btlab(self.filepath, self.config)
        frequency, real, imag = spectrum["frequency"], spectrum["real"], spectrum["imag"]
        # This local-residue indicator measures spectral smoothness; it is not
        # an integral Kramers-Kronig validation.
        quality = validate_spectral_smoothness(
            frequency,
            real,
            imag,
            float(self.config.get("smoothness_threshold_strict", 0.05)),
            float(self.config.get("smoothness_threshold_permissive", 0.15)),
        )
        lin_kk = validate_lin_kk(frequency, real, imag, self.config)
        z_data = {
            "frequency": frequency,
            "real": real,
            "imag": imag,
            "smoothness_residual": quality["residual"],
            "smoothness_pass": quality["smoothness_pass_strict"].astype(float),
            "lin_kk_fit_real": lin_kk["fit_real"],
            "lin_kk_fit_imag": lin_kk["fit_imag"],
            "lin_kk_residual_real": lin_kk["residual_real"],
            "lin_kk_residual_imag": lin_kk["residual_imag"],
            "lin_kk_residual_magnitude_pct": lin_kk["residual_magnitude_pct"],
            "lin_kk_pass": lin_kk["point_pass"].astype(float),
        }
        peak_index = int(np.argmax(np.abs(imag)))
        minimum_points = int(self.config.get("smoothness_min_points", 10))
        output = {
            "n_points": int(frequency.size),
            "n_smoothness_approved": int(np.count_nonzero(quality["smoothness_pass_strict"])),
            "smoothness_failures_strict": quality["smoothness_failures_strict"],
            "smoothness_failures_permissive": quality["smoothness_failures_permissive"],
            "smoothness_residue_pct": quality["smoothness_residue_pct"],
            "spectral_smooth": bool(
                np.count_nonzero(quality["smoothness_pass_permissive"]) >= minimum_points
                and quality["smoothness_failures_permissive"] / max(frequency.size, 1)
                <= float(self.config.get("smoothness_threshold_permissive", 0.15))
            ),
            "lin_kk_valid": lin_kk["valid"],
            "lin_kk_converged": lin_kk["converged"],
            "lin_kk_M": lin_kk["M"],
            "lin_kk_max_M_effective": lin_kk["max_M_effective"],
            "lin_kk_mu": lin_kk["mu"],
            "lin_kk_mu_cutoff": lin_kk["mu_cutoff"],
            "lin_kk_rmse_pct": lin_kk["rmse_pct"],
            "lin_kk_max_residual_pct": lin_kk["max_residual_pct"],
            "lin_kk_failure_pct": lin_kk["failure_pct"],
            "lin_kk_add_capacitance": lin_kk["add_capacitance"],
            "freq_range": [float(np.min(frequency)), float(np.max(frequency))],
            "Re_Z_min": float(np.min(real)),
            "Re_Z_max": float(np.max(real)),
            "Im_Z_max": float(np.max(np.abs(imag))),
            "f_ImZ_max": float(frequency[peak_index]),
            "morphology_flag": classify_morphology(real, imag),
            "source_file": self.filepath.name,
            "source_path": str(self.filepath.resolve()),
            "figures": [],
            "Z_data": z_data,
        }
        return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--output", default="output")
    parser.add_argument("--config", default="config/protocol_config.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    sample = Path(args.input).stem
    result = Agent1_EIS(args.input, config).run(args.output, sample)
    result["Z_data"] = json_safe_z_data(result["Z_data"])
    save_json(Path(args.output) / "metrics" / f"{sample}_agent1.json", result)


if __name__ == "__main__":
    main()

