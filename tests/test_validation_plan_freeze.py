import json
import hashlib
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    return json.loads((PROJECT / relative).read_text(encoding="utf-8"))


def test_integrated_acceptance_is_frozen_but_not_confirmatory():
    acceptance = _load("config/validation_acceptance_v1.json")

    assert acceptance["status"] == "frozen_retrospective_development_acceptance_v1"
    assert acceptance["frozen_at"] == "2026-11-03"
    assert "not prospective confirmatory claims" in acceptance["notes"][0]


def test_standalone_freeze_records_branches_and_numeric_gates():
    acceptance = _load("config/standalone_validation_acceptance_v1.json")

    assert acceptance["branches"]["gsf"]["name"] == "standalone/gsf"
    assert acceptance["branches"]["esc"]["name"] == "standalone/esc"
    assert len(acceptance["branches"]["gsf"]["commit"]) == 40
    assert len(acceptance["branches"]["esc"]["commit"]) == 40
    assert acceptance["numeric_tolerances"]["relative"] == 1e-10
    assert all(value == 1.0 for value in acceptance["gates"].values())


def test_validation_freeze_manifest_matches_file_bytes():
    manifest = _load("paper/validation_plan_manifest_v1.json")

    assert manifest["status"] == "publicly_frozen_retrospective_not_osf_preregistered"
    for relative, expected in manifest["sha256"].items():
        observed = hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest()
        assert observed == expected, relative
