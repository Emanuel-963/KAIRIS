"""KAIRIS Agent 2: non-negative DRT, peak extraction and ESC references."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.drt_solver import solve_drt
from core.report_builder import save_json


LOGGER = logging.getLogger("kairis")


def _normalized_token(value: str) -> str:
    """Normalize an electrolyte label for case-insensitive filename matching."""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def electrolyte_from_filename(filename: str, conductivities: dict[str, Any]) -> tuple[str, float] | None:
    """Return the best configured electrolyte match found in an input filename."""
    normalized_filename = _normalized_token(Path(filename).stem)
    candidates: list[tuple[int, str, float]] = []
    for name, raw_conductivity in conductivities.items():
        if name.casefold() == "default":
            continue
        aliases = {_normalized_token(name)}
        aliases.add(_normalized_token(re.split(r"[_\s-]+", name, maxsplit=1)[0]))
        matching_aliases = [alias for alias in aliases if alias and alias in normalized_filename]
        if matching_aliases:
            candidates.append((max(map(len, matching_aliases)), name, float(raw_conductivity)))
    if not candidates:
        return None
    _, name, conductivity = max(candidates, key=lambda item: item[0])
    return name, conductivity


class Agent2_DRT:
    def __init__(self, z_data: dict[str, Any], config: dict[str, Any], source_filename: str | None = None):
        self.z_data = z_data
        self.config = config
        self.source_filename = source_filename

    def run(self, output_dir: str | Path, sample_name: str) -> dict[str, Any]:
        result = solve_drt(
            np.asarray(self.z_data["frequency"]),
            np.asarray(self.z_data["real"]),
            np.asarray(self.z_data["imag"]),
            self.config,
        )
        source_filename = self.source_filename or sample_name
        r_inf_reliable = bool(result.get("R_inf_reliable", True))
        match = electrolyte_from_filename(
            source_filename,
            self.config.get("electrolyte_conductivity_S_per_m", {}),
        )
        z0_g4 = float(result["R_inf"])
        z0_g4_source = "R_inf_fallback"
        electrolyte = None
        if match is None:
            if r_inf_reliable:
                LOGGER.warning(
                    "%s: eletrolito nao identificado no nome %r; Z0_G4 usa R_inf=%.6g ohm",
                    sample_name, source_filename, z0_g4,
                )
            else:
                z0_g4 = None
                z0_g4_source = "abstained_unreliable_R_inf"
                LOGGER.warning(
                    "%s: eletrolito nao identificado e R_inf sem plato de alta frequencia; "
                    "KAIRIS abstém Z0_G4",
                    sample_name,
                )
        else:
            electrolyte, conductivity = match
            area_m2 = float(self.config.get("cell_area_cm2", 0.0)) * 1e-4
            distance_m = float(self.config.get("electrode_distance_mm", 0.0)) * 1e-3
            if conductivity > 0.0 and area_m2 > 0.0 and distance_m > 0.0:
                z0_g4 = distance_m / (conductivity * area_m2)
                z0_g4_source = "geometry_conductivity"
                LOGGER.info(
                    "%s: Z0_G4=%.6g ohm por L/(kappa*A), eletrolito=%s, kappa=%.6g S/m",
                    sample_name,
                    z0_g4,
                    electrolyte,
                    conductivity,
                )
            else:
                if r_inf_reliable:
                    LOGGER.warning(
                        "%s: geometria ou condutividade invalida para %s; Z0_G4 usa R_inf=%.6g ohm",
                        sample_name, electrolyte, z0_g4,
                    )
                else:
                    z0_g4 = None
                    z0_g4_source = "abstained_unreliable_R_inf"
                    LOGGER.warning(
                        "%s: geometria/condutividade invalida e R_inf sem plato; "
                        "KAIRIS abstém Z0_G4",
                        sample_name,
                    )
                electrolyte = None
        output = {
            "R_inf": result["R_inf"],
            "R_inf_accepted": result.get("R_inf_accepted", result["R_inf"]),
            "R_inf_reliable": r_inf_reliable,
            "R_inf_status": result.get("R_inf_status", "accepted"),
            "R_inf_quality_score": result.get("R_inf_quality_score", 1.0),
            "R_inf_hf_points_used": result.get("R_inf_hf_points_used"),
            "R_inf_hf_phase_deg": result.get("R_inf_hf_phase_deg"),
            "R_inf_hf_real_span_fraction": result.get("R_inf_hf_real_span_fraction"),
            "R_inf_abstention_reasons": result.get("R_inf_abstention_reasons", []),
            "n_peaks": len(result["peaks"]),
            "peaks": [{key: value for key, value in peak.items() if not key.endswith("index")} for peak in result["peaks"]],
            "Z0_G1": result["Z0_G1"],
            "Z0_G2": result["Z0_G2"],
            "Z0_G2_complex": result["Z0_G2_complex"],
            "Z0_G3": result["Z0_G3"],
            "Z0_G4": z0_g4,
            "Z0_G4_source": z0_g4_source,
            "Z0_G4_electrolyte": electrolyte,
            "Z0_G4_reliable": z0_g4 is not None,
            "f_W": result["f_W"],
            "tau_W": result["tau_W"],
            "f_eq": result["f_eq"],
            "regime": result["regime"],
            "lambda_regularization": result["lambda_regularization"],
            "fit_residual": result["fit_residual"],
            "figures": [],
            "tau": result["tau"],
            "gamma": result["gamma"],
        }
        return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", help="JSON do Agent 1")
    parser.add_argument("--output", default="output")
    parser.add_argument("--config", default="config/protocol_config.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    agent1 = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    sample = Path(args.input_json).stem.replace("_agent1", "")
    result = Agent2_DRT(agent1["Z_data"], config, agent1.get("source_file")).run(args.output, sample)
    save_json(Path(args.output) / "metrics" / f"{sample}_agent2.json", result)


if __name__ == "__main__":
    main()

