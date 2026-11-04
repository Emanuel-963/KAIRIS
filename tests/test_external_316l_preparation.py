from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from core.eis_loader import load_btlab
from scripts.prepare_external_316l_dataset import prepare_dataset


def test_prepare_external_316l_converts_bode_and_blinds_labels(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text(
        "Sample,Subgroup,log_Z_f1.0E+00,log_Z_f1.0E+01,"
        "Phase_Angle_f1.0E+00,Phase_Angle_Z_f1.0E+01\n"
        "sample-secret,group-secret,1,1,90,0\n",
        encoding="utf-8",
    )
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "prepared"
    mapping = tmp_path / "coordinator" / "key.csv"

    summary = prepare_dataset(
        source,
        destination,
        mapping,
        expected_sha256=source_hash,
    )

    spectra = list(destination.glob("EXT316L-*.csv"))
    assert len(spectra) == 1
    assert "secret" not in spectra[0].name
    loaded = load_btlab(spectra[0], {"btlab_decimal": "."})
    assert np.allclose(loaded["frequency"], [10.0, 1.0])
    assert np.allclose(loaded["real"], [10.0, 0.0], atol=1e-12)
    assert np.allclose(loaded["imag"], [0.0, -10.0], atol=1e-12)
    assert summary["sample_count"] == 1
    assert summary["scientific_analysis_performed"] is False
    assert "group-secret" in mapping.read_text(encoding="utf-8")
    assert "group-secret" not in (destination / "blind_manifest.csv").read_text(
        encoding="utf-8"
    )


def test_prepare_external_316l_rejects_wrong_source_hash(tmp_path: Path):
    source = tmp_path / "source.csv"
    source.write_text("Sample,Subgroup\na,b\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        prepare_dataset(
            source,
            tmp_path / "prepared",
            tmp_path / "mapping.csv",
            expected_sha256="0" * 64,
        )
