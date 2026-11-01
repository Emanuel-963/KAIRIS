#!/usr/bin/env sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then
  echo "Ambiente não encontrado. Execute scripts/setup_kairis.sh primeiro." >&2
  exit 1
fi
exec .venv/bin/python web_app.py "$@"
