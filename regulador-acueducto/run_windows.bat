@echo off
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo No se encontro uv. Instalalo con:
  echo   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
uv run app.py
pause
