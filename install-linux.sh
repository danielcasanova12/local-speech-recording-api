#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 nao encontrado. Instale Python 3.11+ e tente novamente."
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  echo "Instalando dependencias nativas via apt..."
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-dev portaudio19-dev libsndfile1
elif command -v dnf >/dev/null 2>&1; then
  echo "Instalando dependencias nativas via dnf..."
  sudo dnf install -y python3-devel portaudio-devel libsndfile
elif command -v pacman >/dev/null 2>&1; then
  echo "Instalando dependencias nativas via pacman..."
  sudo pacman -S --needed python portaudio libsndfile
else
  echo "Gerenciador de pacotes nao detectado."
  echo "Instale manualmente: Python 3.11+, PortAudio e libsndfile."
fi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Instalacao concluida."
echo "Para iniciar a API, execute: ./start_api.sh"
