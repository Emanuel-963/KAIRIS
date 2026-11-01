"""Interactive cross-platform setup assistant for KAIRIS."""

from __future__ import annotations

import argparse
import ctypes
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from core.artifact_io import atomic_write_text


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = PROJECT_DIR / "config" / "protocol_config.json"
DEPENDENCIES = ("numpy", "scipy", "pandas", "matplotlib", "flask", "watchdog")
MODEL_ALTERNATIVES = {
    "ram_4gb": ("gemma3:1b", "qwen3:1.7b", "llama3.2:1b"),
    "ram_8gb": (
        "qwen3:4b-instruct-2507-q4_K_M",
        "gemma3:4b",
        "qwen3:1.7b",
        "gemma3:1b",
    ),
    "ram_16gb_plus": (
        "qwen3:4b-instruct-2507-q4_K_M",
        "gemma3:4b",
        "qwen3:1.7b",
        "gemma3:1b",
    ),
}


def total_memory_gb() -> float:
    """Return installed physical memory without third-party dependencies."""
    if os.name == "nt":
        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise OSError("Não foi possível consultar a memória do Windows.")
        return status.total_physical / 1024**3

    if Path("/proc/meminfo").is_file():
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return float(line.split()[1]) * 1024 / 1024**3
    if sys.platform == "darwin":
        value = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True)
        return int(value.strip()) / 1024**3
    pages = os.sysconf("SC_PHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    return pages * page_size / 1024**3


def memory_profile(memory_gb: float) -> str:
    if memory_gb < 6:
        return "ram_4gb"
    if memory_gb < 12:
        return "ram_8gb"
    return "ram_16gb_plus"


def recommended_model(config: dict[str, Any], memory_gb: float) -> str:
    profiles = config.get("ollama_model_profiles", {})
    defaults = {
        "ram_4gb": "gemma3:1b",
        "ram_8gb": "qwen3:4b-instruct-2507-q4_K_M",
        "ram_16gb_plus": "qwen3:4b-instruct-2507-q4_K_M",
    }
    profile = memory_profile(memory_gb)
    return str(profiles.get(profile, defaults[profile]))


def compatible_installed_model(models: list[str], memory_gb: float) -> str | None:
    """Choose a known instruction model that fits the detected RAM profile."""
    for candidate in MODEL_ALTERNATIVES[memory_profile(memory_gb)]:
        if candidate in models:
            return candidate
    return None


def ask(question: str, default: bool = False, assume_yes: bool = False) -> bool:
    """Ask before every material download or installation."""
    if assume_yes:
        return True
    suffix = "[S/n]" if default else "[s/N]"
    answer = input(f"{question} {suffix} ").strip().lower()
    if not answer:
        return default
    return answer in {"s", "sim", "y", "yes"}


def missing_dependencies() -> list[str]:
    return [name for name in DEPENDENCIES if importlib.util.find_spec(name) is None]


def find_ollama() -> str | None:
    """Locate Ollama, including a fresh Windows installation not yet on PATH."""
    executable = shutil.which("ollama")
    if executable:
        return executable
    candidates = []
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Ollama" / "ollama.exe")
    candidates.extend((Path("/usr/local/bin/ollama"), Path("/usr/bin/ollama")))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def ollama_models(executable: str | None = None) -> list[str]:
    executable = executable or find_ollama()
    if not executable:
        return []
    try:
        output = subprocess.check_output(
            [executable, "list"], stderr=subprocess.STDOUT, text=True, timeout=20
        )
    except (OSError, subprocess.SubprocessError):
        return []
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return [line.split()[0] for line in lines[1:] if line.split()]


def install_ollama() -> None:
    """Install Ollama using the platform's standard supported route."""
    system = platform.system()
    if system == "Windows":
        if not shutil.which("winget"):
            raise RuntimeError("winget não foi encontrado; instale o Ollama manualmente.")
        subprocess.run(
            [
                "winget", "install", "--id", "Ollama.Ollama", "--exact",
                "--accept-package-agreements", "--accept-source-agreements",
            ],
            check=True,
        )
        return
    if system == "Darwin" and shutil.which("brew"):
        subprocess.run(["brew", "install", "--cask", "ollama"], check=True)
        return
    if system == "Linux":
        with tempfile.TemporaryDirectory(prefix="kairis_ollama_") as temporary:
            installer = Path(temporary) / "install_ollama.sh"
            urllib.request.urlretrieve("https://ollama.com/install.sh", installer)
            subprocess.run(["sh", str(installer)], check=True)
        return
    raise RuntimeError("Instalação automática do Ollama indisponível neste sistema.")


def configure_ollama(
    config: dict[str, Any], memory_gb: float, assume_yes: bool, requested_model: str | None
) -> None:
    recommendation = requested_model or recommended_model(config, memory_gb)
    print(f"Perfil de memória: {memory_profile(memory_gb)}")
    print(f"Modelo recomendado: {recommendation}")

    executable = find_ollama()
    if not executable:
        if ask("Ollama não encontrado. Deseja baixá-lo e instalá-lo?", assume_yes=assume_yes):
            install_ollama()
            executable = find_ollama()
            if not executable:
                raise RuntimeError("Ollama foi instalado, mas o executável ainda não foi localizado.")
        else:
            config["llm_enabled"] = False
            print("Ollama não instalado; o KAIRIS usará somente regras determinísticas.")
            return

    models = ollama_models(executable)
    selected = recommendation
    if recommendation not in models:
        if ask(
            f"O modelo {recommendation} não está instalado. Deseja baixá-lo?",
            assume_yes=assume_yes,
        ):
            subprocess.run([executable or "ollama", "pull", recommendation], check=True)
            models = ollama_models(executable)
        elif compatible_installed_model(models, memory_gb):
            selected = compatible_installed_model(models, memory_gb) or recommendation
            print(f"Usando o modelo local já disponível: {selected}")
        else:
            config["llm_enabled"] = False
            print("Nenhum modelo local compatível foi selecionado; interpretação por regras mantida.")
            return

    config["llm_provider"] = "ollama"
    config["ollama_model"] = selected
    config["llm_enabled"] = selected in models
    print(f"Ollama configurado com o modelo: {selected}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Assistente de configuração do KAIRIS")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--check", action="store_true", help="Somente verificar pré-requisitos")
    parser.add_argument("--yes", action="store_true", help="Confirmar opções de instalação solicitadas")
    parser.add_argument("--model", help="Modelo Ollama preferido")
    parser.add_argument("--skip-ollama", action="store_true", help="Não oferecer Ollama ou modelos")
    args = parser.parse_args()

    if sys.version_info < (3, 10):
        print("Python 3.10 ou superior é necessário.", file=sys.stderr)
        return 2
    memory_gb = total_memory_gb()
    missing = missing_dependencies()
    print(f"Sistema: {platform.system()} {platform.release()}")
    print(f"Python: {platform.python_version()}")
    print(f"Memória física: {memory_gb:.1f} GB")
    print("Dependências Python: " + ("OK" if not missing else ", ".join(missing)))
    print("Ollama: " + (find_ollama() or "não encontrado"))
    if args.check:
        return 0 if not missing else 1

    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if args.skip_ollama:
        config["llm_enabled"] = False
    else:
        configure_ollama(config, memory_gb, args.yes, args.model)
    atomic_write_text(config_path, json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    print(f"Configuração salva em {config_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
