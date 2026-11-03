from pathlib import Path

from core.config_loader import load_config
from standalone_gsf import analyze_file


PROJECT = Path(__file__).resolve().parents[1]


def test_standalone_gsf_reads_raw_eis_and_writes_metrics(tmp_path):
    config = load_config(PROJECT / "config" / "protocol_config.json")
    destination = analyze_file(
        PROJECT / "tests" / "fixtures" / "synthetic_btlab.txt",
        tmp_path,
        config,
        "standalone_sample",
    )

    assert destination.is_file()
    assert (tmp_path / "figures" / "standalone_sample" / "alpha_vs_f.svg").is_file()
    assert '"analysis": "GSF standalone"' in destination.read_text(encoding="utf-8")
