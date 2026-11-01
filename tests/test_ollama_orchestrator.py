from __future__ import annotations

from agents.agent5_orchestrator import Agent5_Orchestrator


SUMMARY = {
    "regime_drt": "mixed",
    "regime_gsf": "pseudocapacitive",
    "I_crit": 0.2,
}
RULES = ["Consistência alta entre as classificações DRT e GSF."]


def _orchestrator(**config):
    defaults = {
        "llm_enabled": True,
        "llm_provider": "ollama",
        "llm_fallback_rules_only": True,
        "ollama_model": "llama3.2",
        "ollama_autostart": False,
    }
    defaults.update(config)
    return Agent5_Orchestrator({}, {}, {}, {}, defaults)


def test_ollama_uses_configured_local_model(monkeypatch):
    orchestrator = _orchestrator()
    calls = []

    def fake_json(url, payload=None, timeout=120):
        calls.append((url, payload, timeout))
        if url.endswith("/api/tags"):
            return {"models": [{"name": "qwen3:8b"}, {"name": "llama3.2:latest"}]}
        return {"response": "Interpretação local fundamentada."}

    monkeypatch.setattr(orchestrator, "_ollama_json", fake_json)

    result = orchestrator._optional_llm(SUMMARY, RULES)

    assert result == "Interpretação local fundamentada."
    assert calls[1][1]["model"] == "llama3.2:latest"
    assert calls[1][1]["stream"] is False
    assert calls[1][1]["think"] is False
    assert calls[1][1]["options"]["num_ctx"] == 4096
    assert calls[1][1]["options"]["num_predict"] == 256
    assert orchestrator.llm_status == {
        "enabled": True,
        "provider": "ollama",
        "model": "llama3.2:latest",
        "status": "used",
    }


def test_ollama_failure_falls_back_to_rules(monkeypatch):
    orchestrator = _orchestrator()

    def unavailable(*args, **kwargs):
        raise ConnectionError("serviço local indisponível")

    monkeypatch.setattr(orchestrator, "_ollama_json", unavailable)

    assert orchestrator._optional_llm(SUMMARY, RULES) is None
    assert orchestrator.llm_status["provider"] == "ollama"
    assert orchestrator.llm_status["status"] == "unavailable"


def test_prompt_contains_bounded_persistent_memory():
    memory = [{"sample": "anterior", "llm_interpretation": "Conclusão anterior."}]

    prompt = _orchestrator()._llm_prompt(SUMMARY, RULES, memory)

    assert "Memória KAIRIS de execuções anteriores" in prompt
    assert "Conclusão anterior" in prompt
    assert "não altere as métricas atuais" in prompt


def test_prompt_prioritizes_human_reviewed_examples():
    examples = [{"summary": {"R_ct": 12}, "reviewed_answer": "Resposta validada."}]

    prompt = _orchestrator()._llm_prompt(SUMMARY, RULES, [], examples)

    assert "Exemplos revisados por pesquisadores" in prompt
    assert "Resposta validada" in prompt
    assert "não copie números de outras amostras" in prompt
