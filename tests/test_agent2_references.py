from __future__ import annotations

import logging

import numpy as np
import pytest

from agents.agent2_drt import Agent2_DRT, electrolyte_from_filename


def _drt_result() -> dict:
    return {
        "R_inf": 7.5,
        "peaks": [],
        "Z0_G1": 2.0,
        "Z0_G2": 3.0,
        "Z0_G2_complex": [3.0, -1.0],
        "Z0_G3": 4.0,
        "Z0_G4": 7.5,
        "f_W": 10.0,
        "tau_W": 0.01,
        "f_eq": 100.0,
        "regime": "mixed",
        "lambda_regularization": 1e-3,
        "fit_residual": 0.1,
        "tau": np.array([1e-3, 1e-2]),
        "gamma": np.array([1.0, 0.5]),
    }


def _config() -> dict:
    return {
        "cell_area_cm2": 2.4544,
        "electrode_distance_mm": 0.75,
        "electrolyte_conductivity_S_per_m": {
            "H2SO4_1M": 24.0,
            "KCl_1M": 11.18,
            "KOH_1M": 27.0,
            "default": 10.0,
        },
    }


def test_electrolyte_match_is_case_insensitive_and_accepts_base_formula():
    table = _config()["electrolyte_conductivity_S_per_m"]

    assert electrolyte_from_filename("1 EIS GC2 h2So4 1A.txt", table) == ("H2SO4_1M", 24.0)
    assert electrolyte_from_filename("cell_KCL_1m_test.txt", table) == ("KCl_1M", 11.18)
    assert electrolyte_from_filename("unknown_sample.txt", table) is None


def test_agent2_uses_geometry_and_conductivity_for_g4(monkeypatch, tmp_path):
    monkeypatch.setattr("agents.agent2_drt.solve_drt", lambda *args, **kwargs: _drt_result())
    z_data = {"frequency": [1000.0, 100.0], "real": [7.5, 8.0], "imag": [-1.0, -2.0]}

    result = Agent2_DRT(z_data, _config(), "kcl_c1_fulltest.txt").run(tmp_path, "sample")

    expected = (0.75e-3) / (11.18 * 2.4544e-4)
    assert result["Z0_G4"] == pytest.approx(expected)
    assert result["Z0_G4_source"] == "geometry_conductivity"
    assert result["Z0_G4_electrolyte"] == "KCl_1M"


def test_agent2_falls_back_to_r_inf_and_logs(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr("agents.agent2_drt.solve_drt", lambda *args, **kwargs: _drt_result())
    z_data = {"frequency": [1000.0, 100.0], "real": [7.5, 8.0], "imag": [-1.0, -2.0]}

    with caplog.at_level(logging.WARNING, logger="kairis"):
        result = Agent2_DRT(z_data, _config(), "unidentified.txt").run(tmp_path, "sample")

    assert result["Z0_G4"] == 7.5
    assert result["Z0_G4_source"] == "R_inf_fallback"
    assert result["Z0_G4_electrolyte"] is None
    assert "Z0_G4 usa R_inf" in caplog.text


def test_agent2_abstains_g4_when_r_inf_is_unreliable(monkeypatch, tmp_path, caplog):
    drt = _drt_result()
    drt.update(
        {
            "R_inf_accepted": None,
            "R_inf_reliable": False,
            "R_inf_status": "abstained",
            "R_inf_quality_score": 0.0,
            "R_inf_abstention_reasons": ["high_frequency_real_part_not_plateaued"],
        }
    )
    monkeypatch.setattr("agents.agent2_drt.solve_drt", lambda *args, **kwargs: drt)
    z_data = {"frequency": [1000.0, 100.0], "real": [7.5, 8.0], "imag": [-1.0, -2.0]}

    with caplog.at_level(logging.WARNING, logger="kairis"):
        result = Agent2_DRT(z_data, _config(), "unidentified.txt").run(tmp_path, "sample")

    assert result["R_inf"] == 7.5
    assert result["R_inf_accepted"] is None
    assert result["Z0_G4"] is None
    assert result["Z0_G4_source"] == "abstained_unreliable_R_inf"
    assert result["Z0_G4_reliable"] is False
    assert "abstém Z0_G4" in caplog.text
