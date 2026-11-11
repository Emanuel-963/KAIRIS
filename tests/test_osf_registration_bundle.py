from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.build_osf_registration_bundle import PUBLIC_FILES, build_bundle


def test_osf_bundle_is_private_safe_and_manifested(tmp_path: Path):
    destination = tmp_path / "bundle.zip"
    result = build_bundle(destination, require_clean=False)

    assert destination.is_file()
    assert result["privacy"]["reviewer_identifiers_included"] is False
    with zipfile.ZipFile(destination) as archive:
        names = set(archive.namelist())
        assert set(PUBLIC_FILES).issubset(names)
        assert "BUNDLE_MANIFEST.json" in names
        assert "README_UPLOAD.md" in names
        assert not any("coordinator" in name.casefold() for name in names)
        assert not any("blinding_key" in name.casefold() for name in names)
        manifest = json.loads(archive.read("BUNDLE_MANIFEST.json"))
        assert manifest["analysis_code_commit"] == result["analysis_code_commit"]
        assert manifest["privacy"]["private_conflict_declarations_included"] is False

