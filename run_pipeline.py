"""KAIRIS command-line entry point.

Usage: python run_pipeline.py --input data/input --output output [--watch]
"""

from __future__ import annotations

import argparse
import logging
import queue
import re
import sys
import time
from pathlib import Path
from typing import Any

from agents.agent1_eis_reader import Agent1_EIS
from agents.agent2_drt import Agent2_DRT
from agents.agent3_gsf import Agent3_GSF
from agents.agent4_esc import Agent4_ESC
from agents.agent5_orchestrator import Agent5_Orchestrator
from core.config_loader import load_config
from core.config_validator import validate_config
from core.runtime_control import read_llm_enabled


LOGGER = logging.getLogger("kairis")
SUPPORTED_INPUT_SUFFIXES = {".txt", ".csv"}


def configure_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    LOGGER.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    console = logging.StreamHandler(sys.stdout); console.setFormatter(formatter)
    file_handler = logging.FileHandler(output_dir / "pipeline.log", encoding="utf-8"); file_handler.setFormatter(formatter)
    LOGGER.addHandler(console); LOGGER.addHandler(file_handler)


def ensure_output_structure(output_dir: Path) -> None:
    for child in ("metrics", "figures", "reports"):
        (output_dir / child).mkdir(parents=True, exist_ok=True)


def run_stage(sample_name: str, agent: int, label: str, operation: Any) -> Any:
    """Run one KAIRIS stage while emitting machine-readable progress logs."""
    LOGGER.info("AGENT_STATUS sample=%s agent=%d state=running label=%s", sample_name, agent, label)
    try:
        result = operation()
    except Exception:
        LOGGER.exception("AGENT_STATUS sample=%s agent=%d state=failed label=%s", sample_name, agent, label)
        raise
    LOGGER.info("AGENT_STATUS sample=%s agent=%d state=complete label=%s", sample_name, agent, label)
    return result


def run_sample(
    filepath: str | Path,
    output_dir: str | Path,
    config: dict[str, Any],
    sample_name: str | None = None,
) -> dict[str, Any]:
    path = Path(filepath)
    output = Path(output_dir)
    sample_name = sample_name or path.stem
    LOGGER.info("Processando amostra: %s", sample_name)
    a1 = Agent1_EIS(path, config)
    out1 = run_stage(sample_name, 1, "EIS", lambda: a1.run(output, sample_name))
    if not out1["spectral_smooth"]:
        LOGGER.warning("%s: suavidade espectral insuficiente (resíduo local %.1f%%); análise continua", sample_name, out1["smoothness_residue_pct"])
    if not out1["lin_kk_valid"]:
        LOGGER.warning(
            "%s: validacao Lin-KK reprovada (RMSE %.2f%%; pontos reprovados %.1f%%; mu %.4g); analise continua",
            sample_name,
            out1["lin_kk_rmse_pct"],
            out1["lin_kk_failure_pct"],
            out1["lin_kk_mu"],
        )
    out2 = run_stage(sample_name, 2, "DRT", lambda: Agent2_DRT(out1["Z_data"], config, path.name).run(output, sample_name))
    out3 = run_stage(sample_name, 3, "GSF", lambda: Agent3_GSF(out1["Z_data"], config).run(output, sample_name))
    z0_g2 = out2.get("Z0_G2_complex", out2["Z0_G2"])
    out4 = run_stage(
        sample_name,
        4,
        "ESC",
        lambda: Agent4_ESC(out1["Z_data"], out2["Z0_G1"], z0_g2, out2["Z0_G3"], out2["Z0_G4"], config).run(output, sample_name),
    )
    final = run_stage(sample_name, 5, "Relatorio", lambda: Agent5_Orchestrator(out1, out2, out3, out4, config, source_path=path).run(output, sample_name))
    LOGGER.info("Amostra concluída: %s", sample_name)
    return final


def sample_identifier(path: Path, input_dir: Path) -> str:
    """Return a stable output name that preserves nested input identity."""
    try:
        relative = path.resolve().relative_to(input_dir.resolve()).with_suffix("")
    except ValueError:
        relative = Path(path.stem)
    raw = "__".join(relative.parts)
    identifier = re.sub(r"[^A-Za-z0-9._-]+", "_", raw).strip("._-")
    return identifier or "sample"


def process_file(
    path: Path,
    input_dir: Path,
    output_dir: Path,
    config: dict[str, Any],
    overwrite: bool = False,
    llm_control_path: Path | None = None,
) -> bool:
    sample_name = sample_identifier(path, input_dir)
    consolidated = output_dir / "metrics" / f"{sample_name}_metrics.json"
    if consolidated.is_file() and not overwrite:
        LOGGER.info("Amostra já processada, ignorada sem --overwrite: %s", sample_name)
        return True
    try:
        effective_config = dict(config)
        effective_config["llm_enabled"] = read_llm_enabled(
            llm_control_path, bool(config.get("llm_enabled", False))
        )
        LOGGER.info(
            "LLM %s para a amostra %s",
            "ativada" if effective_config["llm_enabled"] else "desativada",
            sample_name,
        )
        run_sample(path, output_dir, effective_config, sample_name)
        return True
    except Exception:
        LOGGER.exception("Falha na amostra %s; as demais amostras continuarão", path)
        return False


def process_existing(
    input_dir: Path,
    output_dir: Path,
    config: dict[str, Any],
    overwrite: bool = False,
    llm_control_path: Path | None = None,
) -> set[Path]:
    files = sorted(
        path.resolve()
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES
    )
    LOGGER.info("Encontrados %d arquivo(s) EIS", len(files))
    processed: set[Path] = set()
    for path in files:
        if process_file(path, input_dir, output_dir, config, overwrite, llm_control_path):
            processed.add(path)
    return processed


def watch_directory(
    input_dir: Path,
    output_dir: Path,
    config: dict[str, Any],
    processed: set[Path],
    overwrite: bool = False,
    llm_control_path: Path | None = None,
) -> None:
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError as error:
        raise RuntimeError("--watch requer a dependência watchdog (pip install -r requirements.txt)") from error

    pending: queue.Queue[Path] = queue.Queue()

    class Handler(FileSystemEventHandler):
        def _enqueue(self, raw_path: str) -> None:
            path = Path(raw_path)
            if path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES:
                pending.put(path.resolve())

        def on_created(self, event: Any) -> None:
            if not event.is_directory: self._enqueue(event.src_path)

        def on_modified(self, event: Any) -> None:
            if not event.is_directory: self._enqueue(event.src_path)

        def on_moved(self, event: Any) -> None:
            if not event.is_directory: self._enqueue(event.dest_path)

    observer = Observer(); observer.schedule(Handler(), str(input_dir), recursive=True); observer.start()
    LOGGER.info("Monitorando %s; pressione Ctrl+C para encerrar", input_dir)
    signatures: dict[Path, tuple[int, int]] = {}
    try:
        while True:
            try:
                path = pending.get(timeout=1.0)
            except queue.Empty:
                continue
            if not path.is_file():
                continue
            stat = path.stat(); signature = (stat.st_size, stat.st_mtime_ns)
            time.sleep(0.5)
            if not path.is_file():
                continue
            new_stat = path.stat(); stable_signature = (new_stat.st_size, new_stat.st_mtime_ns)
            if signature != stable_signature:
                pending.put(path); continue
            if signatures.get(path) == stable_signature and path in processed:
                continue
            signatures[path] = stable_signature
            if process_file(path, input_dir, output_dir, config, overwrite, llm_control_path):
                processed.add(path)
    except KeyboardInterrupt:
        LOGGER.info("Monitoramento encerrado pelo usuário")
    finally:
        observer.stop(); observer.join()


def main() -> int:
    from core.runtime_paths import default_config_path, workspace_root

    project_dir = workspace_root()
    parser = argparse.ArgumentParser(description="Pipeline científico KAIRIS")
    parser.add_argument(
        "--input",
        default=str(project_dir / "data" / "input"),
        help="Arquivo EIS .txt/.csv ou diretório contendo amostras",
    )
    parser.add_argument("--output", default=str(project_dir / "output"), help="Diretório de resultados")
    parser.add_argument("--config", default=str(default_config_path()), help="Arquivo JSON de configuração")
    parser.add_argument("--watch", action="store_true", help="Monitorar continuamente novos arquivos")
    llm_group = parser.add_mutually_exclusive_group()
    llm_group.add_argument("--llm", dest="llm_enabled", action="store_true", help="Ativar a interpretação por LLM nesta execução")
    llm_group.add_argument("--no-llm", dest="llm_enabled", action="store_false", help="Desativar a LLM e usar somente as regras")
    parser.set_defaults(llm_enabled=None)
    parser.add_argument(
        "--llm-control",
        type=Path,
        help="Arquivo de controle em tempo real; quando usado, é relido antes de cada amostra",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Reprocessar e substituir artefatos existentes; por padrão, amostras com JSON consolidado são ignoradas",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve(); output_dir = Path(args.output).expanduser().resolve()
    if not input_path.exists():
        if input_path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES:
            parser.error(f"arquivo de entrada não encontrado: {input_path}")
        input_path.mkdir(parents=True, exist_ok=True)
    ensure_output_structure(output_dir); configure_logging(output_dir)
    config = load_config(args.config)
    if args.llm_enabled is not None:
        config["llm_enabled"] = args.llm_enabled
    validate_config(config)
    llm_control_path = args.llm_control.expanduser().resolve() if args.llm_control else None
    if input_path.is_file():
        if input_path.suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
            parser.error("--input deve ser um arquivo .txt/.csv ou um diretório")
        if args.watch:
            parser.error("--watch requer que --input seja um diretório")
        process_file(
            input_path,
            input_path.parent,
            output_dir,
            config,
            args.overwrite,
            llm_control_path,
        )
    else:
        processed = process_existing(input_path, output_dir, config, args.overwrite, llm_control_path)
        if args.watch:
            watch_directory(input_path, output_dir, config, processed, args.overwrite, llm_control_path)
    if not args.watch:
        LOGGER.info("Pipeline concluído")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

