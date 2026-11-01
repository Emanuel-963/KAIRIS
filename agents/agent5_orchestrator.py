"""Agent 5: deterministic synthesis, optional LLM interpretation and reporting."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.report_builder import build_html_report, save_json
from core.memory_store import KairisMemoryStore
from core.training_feedback import TrainingFeedbackStore


class Agent5_Orchestrator:
    def __init__(self, agent1: dict[str, Any], agent2: dict[str, Any], agent3: dict[str, Any], agent4: dict[str, Any], config: dict[str, Any], source_path: str | Path | None = None):
        self.outputs = {"agent1": agent1, "agent2": agent2, "agent3": agent3, "agent4": agent4}
        self.config = config
        self.source_path = Path(source_path) if source_path else None
        self.llm_status: dict[str, Any] = {
            "enabled": bool(config.get("llm_enabled", False)),
            "provider": None,
            "model": None,
            "status": "not_attempted",
        }

    def run(self, output_dir: str | Path, sample_name: str) -> dict[str, Any]:
        a1, a2, a3, a4 = (self.outputs[key] for key in ("agent1", "agent2", "agent3", "agent4"))
        summary = {
            "smoothness_residue_pct": a1["smoothness_residue_pct"],
            "lin_kk_valid": a1["lin_kk_valid"],
            "lin_kk_rmse_pct": a1["lin_kk_rmse_pct"],
            "lin_kk_failure_pct": a1["lin_kk_failure_pct"],
            "morphology": a1["morphology_flag"],
            "n_drt_peaks": a2["n_peaks"],
            "R_inf": a2["R_inf"],
            "R_ct": a2["Z0_G1"],
            "regime_drt": a2["regime"],
            "alpha_mean": a3["alpha_mean"],
            "kphi_mean": a3["kphi_mean"],
            "I_crit": a3["I_crit"],
            "regime_gsf": a3["regime_gsf"],
            "esc_G2_lf": a4["G2"]["lf_point"],
            "esc_G2_flags": a4["G2"]["flags"],
        }
        summary.update(
            self._regime_assessment(summary["regime_drt"], summary["regime_gsf"])
        )
        interpretations = self._interpret(summary)
        provenance = self._provenance()
        memory_enabled = bool(self.config.get("llm_memory_enabled", True))
        memory_store = KairisMemoryStore(Path(output_dir) / "memory" / "kairis_memory.json")
        memory_records = (
            memory_store.prompt_records(
                int(self.config.get("llm_memory_recent_records", 8)),
                int(self.config.get("llm_memory_max_prompt_chars", 6000)),
            )
            if memory_enabled
            else []
        )
        training_store = TrainingFeedbackStore(output_dir)
        supervised_enabled = bool(self.config.get("supervised_learning_enabled", True))
        validated_examples = (
            training_store.prompt_examples(
                int(self.config.get("supervised_examples_in_prompt", 3)),
                int(self.config.get("supervised_examples_max_chars", 5000)),
            )
            if supervised_enabled
            else []
        )
        llm_text = self._optional_llm(
            summary, interpretations, memory_records, validated_examples
        )
        metrics_agents = {
            agent: {key: value for key, value in payload.items() if key != "figures"}
            for agent, payload in self.outputs.items()
        }
        memory_total = None
        if memory_enabled:
            memory_total = memory_store.append(
                {
                    "sample": sample_name,
                    "timestamp": provenance["execution_timestamp"],
                    "input_sha256": provenance["input_sha256"],
                    "summary": summary,
                    "interpretation_rules": interpretations,
                    "llm_interpretation": llm_text,
                }
            )
        memory_status = {
            "enabled": memory_enabled,
            "records_used": len(memory_records),
            "records_total": memory_total,
            "path": str(memory_store.path.resolve()) if memory_enabled else None,
        }
        training_status = training_store.stats()
        finetune_minimum = int(self.config.get("finetune_min_validated_examples", 50))
        training_status.update(
            {
                "enabled": supervised_enabled,
                "validated_examples_used": len(validated_examples),
                "finetune_min_validated_examples": finetune_minimum,
                "finetune_ready": training_status["dataset_examples"] >= finetune_minimum,
            }
        )
        metrics = {"sample": sample_name, "provenance": provenance, "summary": summary, "interpretation_rules": interpretations, "llm_interpretation": llm_text, "llm": self.llm_status, "memory": memory_status, "training": training_status, "agents": metrics_agents}
        metrics_path = Path(output_dir) / "metrics" / f"{sample_name}_metrics.json"
        report_path = Path(output_dir) / "reports" / f"{sample_name}_report.html"
        save_json(metrics_path, metrics)
        build_html_report(report_path, sample_name, self.config, self.outputs, summary, interpretations, llm_text, provenance)
        return {"metrics": str(metrics_path.resolve()), "report": str(report_path.resolve()), "summary": summary, "interpretation_rules": interpretations, "llm": self.llm_status, "memory": memory_status, "training": training_status}

    @staticmethod
    def _sanitized_config(config: dict[str, Any]) -> dict[str, Any]:
        """Copy effective configuration while removing secret-bearing keys."""
        sensitive_fragments = ("api_key", "apikey", "secret", "password", "token")

        def clean(value: Any) -> Any:
            if isinstance(value, dict):
                return {
                    key: clean(item)
                    for key, item in value.items()
                    if not any(fragment in key.casefold() for fragment in sensitive_fragments)
                }
            if isinstance(value, list):
                return [clean(item) for item in value]
            return copy.deepcopy(value)

        return clean(config)

    def _provenance(self) -> dict[str, Any]:
        """Build reproducibility metadata for the consolidated sample result."""
        source = self.source_path
        if source is None:
            recorded = self.outputs["agent1"].get("source_path")
            source = Path(recorded) if recorded else None
        if source is None or not source.is_file():
            raise ValueError("Arquivo de entrada indisponível para calcular a proveniência SHA-256.")
        digest = hashlib.sha256()
        with source.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        packages: dict[str, str] = {}
        for package in ("numpy", "scipy", "pandas", "matplotlib"):
            try:
                packages[package] = version(package)
            except PackageNotFoundError:
                packages[package] = "not-installed"
        git_commit = None
        git_dirty = None
        try:
            project_dir = Path(__file__).resolve().parents[1]
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=project_dir,
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
            git_dirty = bool(
                subprocess.check_output(
                    ["git", "status", "--porcelain", "--untracked-files=no"],
                    cwd=project_dir,
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                ).strip()
            )
        except (OSError, subprocess.SubprocessError):
            pass
        return {
            "input_file": str(source.resolve()),
            "input_sha256": digest.hexdigest(),
            "execution_timestamp": datetime.now().astimezone().isoformat(),
            "package_versions": packages,
            "kairis_git_commit": git_commit,
            "kairis_git_dirty": git_dirty,
            "effective_config": self._sanitized_config(self.config),
        }

    @staticmethod
    def _regime_assessment(regime_drt: str, regime_gsf: str) -> dict[str, Any]:
        """Resolve special two-observable patterns before generic agreement rules."""
        if regime_drt == "diffusion_dominated" and regime_gsf == "pseudocapacitive":
            return {
                "diagnostic": "intercalation_pseudocapacitive",
                "drt_gsf_inconsistent": False,
            }
        compatible = {
            "kinetic_dominated": {"resistive", "pseudocapacitive"},
            "diffusion_dominated": {"diffusive"},
            "mixed": {"mixed", "pseudocapacitive"},
        }
        return {
            "diagnostic": None,
            "drt_gsf_inconsistent": regime_gsf
            not in compatible.get(regime_drt, set()),
        }

    @staticmethod
    def _interpret(summary: dict[str, Any]) -> list[str]:
        messages: list[str] = []
        if summary["lin_kk_valid"]:
            messages.append(
                f"Espectro compatível com Lin-KK (RMSE normalizado {float(summary['lin_kk_rmse_pct']):.2f}%)."
            )
        else:
            messages.append(
                "Atenção: o espectro não satisfez os critérios configurados da validação Lin-KK."
            )
        drt = summary["regime_drt"]
        gsf = summary["regime_gsf"]
        if summary.get("diagnostic") == "intercalation_pseudocapacitive":
            messages.append(
                "O DRT identifica processo difusivo dominante no domínio temporal, "
                "enquanto o GSF classifica o campo espectral global como "
                "pseudocapacitivo. Esse padrão é consistente com pseudocapacitância "
                "de intercalação — mecanismo documentado em MXene e outros materiais "
                "lamelares — onde o transporte iônico é difusivo localmente mas o "
                "comportamento eletroquímico macroscópico é pseudocapacitivo. Não "
                "constitui divergência entre os módulos; constitui resolução de dois "
                "observáveis distintos."
            )
        elif not bool(summary.get("drt_gsf_inconsistent", True)):
            messages.append("Consistência alta entre as classificações DRT e GSF.")
        else:
            messages.append(f"Atenção: as classificações DRT ({drt}) e GSF ({gsf}) divergem.")
        instability = float(summary["I_crit"])
        if instability > 1.0:
            messages.append("Instabilidade espectral severa (I_crit > 1,0).")
        elif instability > 0.5:
            messages.append("Instabilidade espectral moderada (I_crit > 0,5).")
        else:
            messages.append("Não há instabilidade espectral moderada pelo limiar KAIRIS.")
        kphi = float(summary["kphi_mean"])
        if kphi > 1.5:
            messages.append("Campo espectral próximo ao estado áureo.")
        elif kphi < 1.0:
            messages.append("Campo espectral abaixo do limiar áureo.")
        else:
            messages.append("Campo espectral em faixa intermediária de kφ.")
        if float(summary["R_ct"]) > 5000 and gsf == "diffusive":
            messages.append("Possível passivação: R_ct elevado e regime GSF difusivo.")
        if "diffusion_dominated" in summary["esc_G2_flags"]:
            messages.append("O ESC G2 indica domínio difusivo no limite de baixa frequência.")
        return messages

    def _optional_llm(
        self,
        summary: dict[str, Any],
        rules: list[str],
        memory_records: list[dict[str, Any]] | None = None,
        validated_examples: list[dict[str, Any]] | None = None,
    ) -> str | None:
        if not bool(self.config.get("llm_enabled", False)):
            self.llm_status["status"] = "disabled"
            return None

        provider = str(self.config.get("llm_provider", "ollama")).strip().lower()
        if provider in {"ollama", "auto"}:
            try:
                return self._ollama_interpretation(
                    summary, rules, memory_records, validated_examples
                )
            except Exception as error:
                self.llm_status = {
                    "enabled": True,
                    "provider": "ollama",
                    "model": None,
                    "status": "unavailable",
                    "detail": str(error),
                }
                if provider == "ollama":
                    if self.config.get("llm_fallback_rules_only", True):
                        return None
                    raise

        if provider not in {"openai", "auto"}:
            self.llm_status.update({"provider": provider, "status": "unsupported_provider"})
            if self.config.get("llm_fallback_rules_only", True):
                return None
            raise ValueError(f"Provedor LLM não suportado: {provider}")

        key_name = str(self.config.get("llm_api_key_env", "OPENAI_API_KEY"))
        api_key = os.getenv(key_name)
        if not api_key:
            self.llm_status.update({"provider": "openai", "status": "missing_api_key"})
            return None
        try:
            from openai import OpenAI
            model = str(self.config.get("llm_model", "gpt-4o-mini"))
            response = OpenAI(api_key=api_key).responses.create(
                model=model,
                input=self._llm_prompt(
                    summary, rules, memory_records, validated_examples
                ),
            )
            text = response.output_text.strip()
            if not text:
                raise ValueError("A LLM retornou uma interpretação vazia.")
            self.llm_status = {
                "enabled": True,
                "provider": "openai",
                "model": model,
                "status": "used",
            }
            return text
        except Exception as error:
            self.llm_status.update({"provider": "openai", "status": "failed", "detail": str(error)})
            if self.config.get("llm_fallback_rules_only", True):
                return None
            raise

    @staticmethod
    def _llm_prompt(
        summary: dict[str, Any],
        rules: list[str],
        memory_records: list[dict[str, Any]] | None = None,
        validated_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        """Build the grounded KAIRIS interpretation prompt."""
        context_path = Path(__file__).resolve().parents[1] / "models" / "orchestrator_context.txt"
        context = context_path.read_text(encoding="utf-8")
        metrics = json.dumps(summary, ensure_ascii=False, indent=2)
        rule_text = "\n".join(f"- {rule}" for rule in rules)
        examples_text = ""
        if validated_examples:
            examples_text = (
                "\n\nExemplos revisados por pesquisadores (imite o rigor e o limite "
                "interpretativo, não copie números de outras amostras):\n"
                + json.dumps(validated_examples, ensure_ascii=False, indent=2)
            )
        memory_text = ""
        if memory_records:
            memory_text = (
                "\n\nMemória KAIRIS de execuções anteriores (use apenas para "
                "comparação contextual; não altere as métricas atuais):\n"
                + json.dumps(memory_records, ensure_ascii=False, indent=2)
            )
        return (
            f"{context}\n\nMétricas KAIRIS:\n{metrics}\n\n"
            f"Interpretação determinística:\n{rule_text}{examples_text}{memory_text}\n\n"
            "Produza um único parágrafo objetivo em português, sem extrapolar "
            "os dados e sem sugerir diagnóstico clínico ou mecanismo não medido."
        )

    def _ollama_interpretation(
        self,
        summary: dict[str, Any],
        rules: list[str],
        memory_records: list[dict[str, Any]] | None = None,
        validated_examples: list[dict[str, Any]] | None = None,
    ) -> str:
        """Use a running local Ollama service and an already installed model."""
        base_url = str(self.config.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
        timeout = float(self.config.get("ollama_timeout_seconds", 120))
        tags = self._ollama_tags(base_url, timeout)
        models = [
            str(item.get("name") or item.get("model"))
            for item in tags.get("models", [])
            if item.get("name") or item.get("model")
        ]
        if not models:
            raise RuntimeError("Ollama está acessível, mas não há modelos locais instalados.")

        preferred = str(self.config.get("ollama_model", "")).strip()
        model = self._select_ollama_model(preferred, models)
        payload = {
            "model": model,
            "prompt": self._llm_prompt(
                summary, rules, memory_records, validated_examples
            ),
            "stream": False,
            "think": bool(self.config.get("ollama_think", False)),
            "options": {
                "temperature": float(self.config.get("ollama_temperature", 0.1)),
                "num_ctx": int(self.config.get("ollama_context_tokens", 4096)),
                "num_predict": int(self.config.get("ollama_max_output_tokens", 256)),
            },
        }
        response = self._ollama_json(
            f"{base_url}/api/generate",
            payload=payload,
            timeout=timeout,
        )
        text = str(response.get("response", "")).strip()
        if not text:
            raise ValueError("Ollama retornou uma interpretação vazia.")
        self.llm_status = {
            "enabled": True,
            "provider": "ollama",
            "model": model,
            "status": "used",
        }
        return text

    def _ollama_tags(self, base_url: str, request_timeout: float) -> dict[str, Any]:
        """Read local models, starting the installed Ollama service if needed."""
        tags_url = f"{base_url}/api/tags"
        try:
            return self._ollama_json(tags_url, timeout=request_timeout)
        except (OSError, ConnectionError) as initial_error:
            if not bool(self.config.get("ollama_autostart", True)):
                raise initial_error

        executable = shutil.which("ollama")
        if not executable:
            raise RuntimeError("O executável local do Ollama não foi encontrado.")
        self._start_ollama_service(executable)
        startup_timeout = float(self.config.get("ollama_startup_timeout_seconds", 15))
        deadline = time.monotonic() + max(startup_timeout, 0.5)
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                return self._ollama_json(tags_url, timeout=min(request_timeout, 2.0))
            except (OSError, ConnectionError) as error:
                last_error = error
                time.sleep(0.25)
        raise RuntimeError(
            f"O serviço do Ollama não iniciou em {startup_timeout:g} segundos."
        ) from last_error

    @staticmethod
    def _start_ollama_service(executable: str) -> None:
        """Start Ollama silently as a detached local background service."""
        options: dict[str, Any] = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if os.name == "nt":
            options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        else:
            options["start_new_session"] = True
        subprocess.Popen([executable, "serve"], **options)

    def _select_ollama_model(self, preferred: str, available: list[str]) -> str:
        """Select the configured Ollama model, or fall back to a local model."""
        if preferred in available:
            return preferred
        if preferred:
            preferred_base = preferred.split(":", 1)[0]
            for model in available:
                if model.split(":", 1)[0] == preferred_base:
                    return model
        profiles = self.config.get("ollama_model_profiles", {})
        safe_candidates = list(profiles.values()) + [
            "gemma3:1b",
            "qwen3:1.7b",
            "gemma3:4b",
            "llama3.2:1b",
        ]
        for candidate in safe_candidates:
            if candidate in available:
                return candidate
        return available[0]

    @staticmethod
    def _ollama_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 120) -> dict[str, Any]:
        """Call the local Ollama JSON API without an extra Python dependency."""
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="GET" if body is None else "POST",
        )
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict):
            raise ValueError("Resposta JSON inválida do Ollama.")
        return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("agent1_json", "agent2_json", "agent3_json", "agent4_json"):
        parser.add_argument(name)
    parser.add_argument("--output", default="output")
    parser.add_argument("--config", default="config/protocol_config.json")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    payloads = [json.loads(Path(getattr(args, name)).read_text(encoding="utf-8")) for name in ("agent1_json", "agent2_json", "agent3_json", "agent4_json")]
    sample = Path(args.agent1_json).stem.replace("_agent1", "")
    source_path = payloads[0].get("source_path")
    result = Agent5_Orchestrator(*payloads, config, source_path=source_path).run(args.output, sample)
    # ASCII escaping keeps the standalone CLI portable to Windows consoles
    # still configured with a legacy code page.
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()

