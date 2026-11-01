from __future__ import annotations

import json

import numpy as np

from agents.agent1_eis_reader import Agent1_EIS
from core.eis_loader import load_btlab


def test_loads_tab_separated_decimal_comma_export(tmp_path):
    source = tmp_path / "tab_export.txt"
    source.write_text(
        "freq/Hz\tRe(Z)/Ohm\t-Im(Z)/Ohm\textra\n"
        "1,0000E+004\t5,0638E+000\t2,2875E+000\tx\n"
        "1,0000E+003\t6,0000E+000\t3,0000E+000\tx\n",
        encoding="latin-1",
    )

    result = load_btlab(source, {"btlab_decimal": ","})

    np.testing.assert_allclose(result["frequency"], [10000.0, 1000.0])
    np.testing.assert_allclose(result["real"], [5.0638, 6.0])
    np.testing.assert_allclose(result["imag"], [-2.2875, -3.0])


def test_loads_semicolon_export_with_omega_columns(tmp_path):
    source = tmp_path / "semicolon_export.txt"
    source.write_text(
        "Filename;Index;Frequency (Hz);-Z'' (Ω);Z (Ω);Z' (Ω)\n"
        "sample;0;1,0000E+004;2,2875E+000;5,5566E+000;5,0638E+000\n"
        ";1;1,0000E+003;3,0000E+000;6,7082E+000;6,0000E+000\n",
        encoding="utf-8",
    )

    result = load_btlab(source, {"btlab_decimal": ","})

    np.testing.assert_allclose(result["frequency"], [10000.0, 1000.0])
    np.testing.assert_allclose(result["real"], [5.0638, 6.0])
    np.testing.assert_allclose(result["imag"], [-2.2875, -3.0])


def test_loads_semicolon_csv_with_signed_imaginary_column(tmp_path):
    source = tmp_path / "hierarchical_porous.csv"
    source.write_text(
        "Frequency (Hz);Z' (Ohm);Z'' (Ohm)\n"
        "316227.766;0.4184665;-0.0012065\n"
        "281838.293;0.4203755;0.0022537\n",
        encoding="utf-8",
    )

    result = load_btlab(source, {"btlab_decimal": ","})

    np.testing.assert_allclose(result["frequency"], [316227.766, 281838.293])
    np.testing.assert_allclose(result["real"], [0.4184665, 0.4203755])
    np.testing.assert_allclose(result["imag"], [-0.0012065, 0.0022537])


def test_agent1_exposes_spectral_smoothness_names(tmp_path):
    source = tmp_path / "sample.txt"
    rows = ["freq/Hz\tRe(Z)/Ohm\t-Im(Z)/Ohm"]
    rows.extend(f"{10 ** (5 - index / 2):.8g}\t{5 + index / 10:.8g}\t{1 + index / 5:.8g}" for index in range(12))
    source.write_text("\n".join(rows), encoding="utf-8")
    config = {
        "btlab_decimal": ".",
        "smoothness_threshold_strict": 0.05,
        "smoothness_threshold_permissive": 0.15,
        "smoothness_min_points": 10,
    }

    result = Agent1_EIS(source, config).run(tmp_path, "sample")
    serialized = json.dumps(result, default=lambda value: value.tolist())

    assert "smoothness_residue_pct" in result
    assert "spectral_smooth" in result
    assert "smoothness_residual" in result["Z_data"]
    assert "lin_kk_valid" in result
    assert "lin_kk_residual_magnitude_pct" in result["Z_data"]
    assert "kk_failure_pct" not in serialized.casefold().replace("lin_kk_failure_pct", "")
    assert "kk_valid" not in serialized.casefold().replace("lin_kk_valid", "")
