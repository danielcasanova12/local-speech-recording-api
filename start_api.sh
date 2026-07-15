#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f ".venv/bin/activate" ]; then
  echo "Ambiente virtual nao encontrado. Execute ./install-linux.sh ou ./install-macos.sh primeiro."
  exit 1
fi

source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
