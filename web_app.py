"""Local browser dashboard for running and inspecting KAIRIS."""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import subprocess
import sys
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "data" / "input"
DEFAULT_OUTPUT = PROJECT_DIR / "output"
DEFAULT_CONFIG = PROJECT_DIR / "config" / "protocol_config.json"
STATUS_PATTERN = re.compile(
    r"AGENT_STATUS sample=(?P<sample>\S+) agent=(?P<agent>[1-5]) "
    r"state=(?P<state>running|complete|failed) label=(?P<label>\S+)"
)
SUPPORTED_INPUT_SUFFIXES = {".txt", ".csv"}


class PipelineManager:
    """Own one KAIRIS subprocess and expose its observable local state."""

    def __init__(self, input_dir: Path, output_dir: Path, config_path: Path = DEFAULT_CONFIG) -> None:
        self.input_dir = input_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.config_path = config_path.resolve()
        self.input_dir.mkdir(parents=True, exist_ok=True)
        for child in ("metrics", "figures", "reports"):
            (self.output_dir / child).mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._stream: Any = None
        self._mode: str | None = None
        self._started_at: datetime | None = None
        self._last_exit_code: int | None = None
        self._log_offset = 0

    @property
    def pipeline_log(self) -> Path:
        return self.output_dir / "pipeline.log"

    def _refresh(self) -> None:
        if self._process is None:
            return
        code = self._process.poll()
        if code is None:
            return
        self._last_exit_code = code
        self._process = None
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def start(self, mode: str) -> dict[str, Any]:
        if mode not in {"once", "watch"}:
            raise ValueError("Modo inválido")
        with self._lock:
            self._refresh()
            if self._process is not None:
                raise RuntimeError("Já existe uma execução KAIRIS ativa")
            self._started_at = datetime.now().astimezone()
            self._last_exit_code = None
            self._mode = mode
            self._log_offset = self.pipeline_log.stat().st_size if self.pipeline_log.exists() else 0
            runner_log = self.output_dir / "web_runner.log"
            self._stream = runner_log.open("a", encoding="utf-8")
            command = [
                sys.executable,
                str(PROJECT_DIR / "run_pipeline.py"),
                "--input",
                str(self.input_dir),
                "--output",
                str(self.output_dir),
                "--config",
                str(self.config_path),
            ]
            if mode == "watch":
                command.append("--watch")
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            self._process = subprocess.Popen(
                command,
                cwd=PROJECT_DIR,
                stdout=self._stream,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=creationflags,
            )
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            if self._process is not None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=3)
                self._last_exit_code = self._process.returncode
                self._process = None
                if self._stream is not None:
                    self._stream.close()
                    self._stream = None
            return self.status()

    def shutdown(self) -> None:
        try:
            self.stop()
        except Exception:
            pass

    def _run_log(self) -> str:
        if not self.pipeline_log.exists():
            return ""
        with self.pipeline_log.open("rb") as handle:
            handle.seek(min(self._log_offset, self.pipeline_log.stat().st_size))
            return handle.read().decode("utf-8", errors="replace")

    def _progress(self, log_text: str) -> list[dict[str, Any]]:
        samples: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for match in STATUS_PATTERN.finditer(log_text):
            sample = match.group("sample")
            if sample not in samples:
                samples[sample] = {"sample": sample, "agents": {}}
                order.append(sample)
            samples[sample]["agents"][match.group("agent")] = {
                "state": match.group("state"),
                "label": match.group("label"),
            }
        return [samples[sample] for sample in order]

    def _input_files(self) -> list[dict[str, Any]]:
        return [
            {
                "name": str(path.relative_to(self.input_dir)),
                "size": path.stat().st_size,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
            }
            for path in sorted(
                (
                    item
                    for item in self.input_dir.rglob("*")
                    if item.is_file() and item.suffix.lower() in SUPPORTED_INPUT_SUFFIXES
                ),
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
        ]

    def _reports(self) -> list[dict[str, Any]]:
        reports = []
        for path in sorted((self.output_dir / "reports").glob("*_report.html"), key=lambda item: item.stat().st_mtime, reverse=True):
            sample = path.name.removesuffix("_report.html")
            summary = None
            metrics_path = self.output_dir / "metrics" / f"{sample}_metrics.json"
            if metrics_path.is_file():
                try:
                    summary = json.loads(metrics_path.read_text(encoding="utf-8")).get("summary")
                except (OSError, json.JSONDecodeError):
                    summary = None
            reports.append(
                {
                    "name": path.name,
                    "sample": sample,
                    "size": path.stat().st_size,
                    "modified": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
                    "url": f"/reports/{path.name}",
                    "summary": summary,
                }
            )
        return reports

    def status(self) -> dict[str, Any]:
        with self._lock:
            self._refresh()
            log_text = self._run_log()
            lines = log_text.splitlines()
            return {
                "running": self._process is not None,
                "mode": self._mode,
                "pid": self._process.pid if self._process is not None else None,
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "exit_code": self._last_exit_code,
                "progress": self._progress(log_text),
                "log": "\n".join(lines[-250:]),
                "input_files": self._input_files(),
                "reports": self._reports(),
            }


def unique_destination(directory: Path, original_name: str) -> Path:
    safe_name = secure_filename(original_name)
    if not safe_name or Path(safe_name).suffix.lower() not in SUPPORTED_INPUT_SUFFIXES:
        raise ValueError(f"Arquivo inválido: {original_name}")
    candidate = directory / safe_name
    counter = 1
    while candidate.exists():
        candidate = directory / f"{Path(safe_name).stem}_{counter}{Path(safe_name).suffix}"
        counter += 1
    return candidate


def create_app(
    input_dir: Path = DEFAULT_INPUT,
    output_dir: Path = DEFAULT_OUTPUT,
    config_path: Path = DEFAULT_CONFIG,
) -> Flask:
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    app.config["MAX_CONTENT_LENGTH"] = 256 * 1024 * 1024
    manager = PipelineManager(input_dir, output_dir, config_path)
    app.extensions["kairis_manager"] = manager
    atexit.register(manager.shutdown)

    @app.get("/")
    def dashboard() -> str:
        return render_template("index.html")

    @app.get("/health")
    def health() -> Any:
        return jsonify({"status": "ok", "service": "KAIRIS"})

    @app.errorhandler(413)
    def upload_too_large(_error: Any) -> Any:
        return jsonify({"error": "Upload excede o limite local de 256 MB"}), 413

    @app.get("/api/status")
    def api_status() -> Any:
        return jsonify(manager.status())

    @app.post("/api/upload")
    def api_upload() -> Any:
        files = request.files.getlist("files")
        if not files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400
        saved = []
        errors = []
        for uploaded in files:
            temporary: Path | None = None
            try:
                destination = unique_destination(manager.input_dir, uploaded.filename or "")
                temporary = destination.with_suffix(destination.suffix + ".uploading")
                uploaded.save(temporary)
                temporary.replace(destination)
                saved.append(destination.name)
            except (OSError, ValueError) as error:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
                errors.append(str(error))
        code = 200 if saved else 400
        return jsonify({"saved": saved, "errors": errors, "status": manager.status()}), code

    @app.post("/api/run")
    def api_run() -> Any:
        try:
            return jsonify(manager.start("once"))
        except RuntimeError as error:
            return jsonify({"error": str(error)}), 409

    @app.post("/api/watch/start")
    def api_watch_start() -> Any:
        try:
            return jsonify(manager.start("watch"))
        except RuntimeError as error:
            return jsonify({"error": str(error)}), 409

    @app.post("/api/stop")
    def api_stop() -> Any:
        return jsonify(manager.stop())

    @app.get("/reports/<path:filename>")
    def report(filename: str) -> Any:
        return send_from_directory(manager.output_dir / "reports", filename)

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description="Painel web local KAIRIS")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Diretório BT-Lab de entrada")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Diretório de resultados")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="Configuração JSON do KAIRIS")
    parser.add_argument("--host", default="127.0.0.1", help="Endereço local do servidor")
    parser.add_argument("--port", type=int, default=8000, help="Porta HTTP")
    parser.add_argument("--no-open", action="store_true", help="Não abrir o navegador automaticamente")
    args = parser.parse_args()
    app = create_app(
        Path(args.input).expanduser(),
        Path(args.output).expanduser(),
        Path(args.config).expanduser(),
    )
    url = f"http://{args.host}:{args.port}"
    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Painel KAIRIS disponível em {url}")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False, threaded=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

