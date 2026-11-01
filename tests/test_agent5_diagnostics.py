from agents.agent5_orchestrator import Agent5_Orchestrator
from core.report_builder import _diagnostic_badge


def test_intercalation_pseudocapacitive_has_priority_and_is_not_inconsistent():
    summary = {
        "lin_kk_valid": True,
        "lin_kk_rmse_pct": 0.8,
        "regime_drt": "diffusion_dominated",
        "regime_gsf": "pseudocapacitive",
        "I_crit": 0.2,
        "kphi_mean": 1.2,
        "R_ct": 25.0,
        "esc_G2_flags": [],
    }
    summary.update(
        Agent5_Orchestrator._regime_assessment(
            summary["regime_drt"], summary["regime_gsf"]
        )
    )
    rules = Agent5_Orchestrator._interpret(summary)

    assert summary["diagnostic"] == "intercalation_pseudocapacitive"
    assert summary["drt_gsf_inconsistent"] is False
    assert any("pseudocapacitância de intercalação" in rule for rule in rules)
    assert not any("divergem" in rule or "inconsistência" in rule for rule in rules)

    badge = _diagnostic_badge(summary)
    assert "Intercalation Pseudocapacitive" in badge
    assert "observáveis complementares" in badge
