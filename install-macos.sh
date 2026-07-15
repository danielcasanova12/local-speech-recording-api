#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 nao encontrado. Instale Python 3.11+ e tente novamente."
  exit 1
fi

if command -v brew >/dev/null 2>&1; then
  echo "Instalando dependencias nativas via Homebrew..."
  brew install portaudio libsndfile
else
  echo "Homebrew nao encontrado."
  echo "Instale manualmente PortAudio e libsndfile, ou instale o Homebrew: https://brew.sh"
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Instalacao concluida."
echo "Para iniciar a API, execute: ./start_api.sh"
echo "No macOS, conceda permissao de microfone ao Terminal/Python quando solicitado."
