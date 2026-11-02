#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"

confirm() {
  printf '%s [s/N] ' "$1"
  read -r answer
  case "$answer" in s|S|sim|SIM|y|Y|yes|YES) return 0 ;; *) return 1 ;; esac
}

if ! command -v python3 >/dev/null 2>&1; then
  confirm "Python não encontrado. Deseja instalá-lo pelo gerenciador do sistema?" || {
    echo "Python 3.10+ é necessário." >&2; exit 1;
  }
  if [ "$(uname -s)" = "Darwin" ]; then
    if command -v brew >/dev/null 2>&1; then
      brew install python@3.12
    else
      echo "Homebrew não encontrado. Instale Python 3.10+ por https://www.python.org/downloads/macos/ ou instale o Homebrew e repita." >&2
      exit 1
    fi
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed python python-pip
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper install -y python3 python3-pip python3-venv
  else
    echo "Gerenciador não reconhecido; instale Python 3.10+ manualmente." >&2; exit 1
  fi
fi

if ! python3 -m venv .venv; then
  echo "Não foi possível criar o ambiente virtual. No Linux, instale o pacote python3-venv; no macOS, use uma distribuição Python com venv." >&2
  exit 1
fi
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
kairis-setup "$@"
echo "KAIRIS configurado. Execute scripts/start_kairis.sh"
