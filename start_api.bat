
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo Ambiente virtual nao encontrado. Execute install.bat primeiro.
  exit /b 1
)

call .venv\Scripts\activate.bat
uvicorn app.main:app --host 127.0.0.1 --port 9000 --reload
