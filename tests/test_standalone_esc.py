import json
from pathlib import Path

from core.config_loader import load_config
from standalone_esc import analyze_file, parse_reference


PROJECT = Path(__file__).resolve().parents[1]


def test_parse_real_and_complex_references():
    assert parse_reference("R_INF=12.4") == ("R_INF", complex(12.4, 0))
    assert parse_reference("peak=8.1,-0.2") == ("peak", complex(8.1, -0.2))


def test_standalone_esc_reads_raw_eis_and_writes_report(tmp_path):
    config = load_config(PROJECT / "config" / "protocol_config.json")
    metrics, report = analyze_file(
        PROJECT / "tests" / "fixtures" / "synthetic_btlab.txt",
        tmp_path,
        config,
        "standalone_sample",
        {"R_INF": complex(5.0, 0.0)},
    )

    payload = json.loads(metrics.read_text(encoding="utf-8"))
    assert payload["reference_policy"] == "explicit_user_supplied"
    assert payload["groups"]["R_INF"]["points"]
    assert report.is_file()
    assert "Emanuel–Smith Chart" in report.read_text(encoding="utf-8")
