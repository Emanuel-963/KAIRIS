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
  if command -v apt-get >/dev/null 2>&1; then
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

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python setup_kairis.py "$@"
echo "KAIRIS configurado. Execute scripts/start_kairis.sh"
