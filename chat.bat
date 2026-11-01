@echo off
rem Starts an interactive chat with the agent. Sets up .venv on first use.
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Setting up .venv ...
    python -m venv .venv || exit /b 1
    .venv\Scripts\python -m pip install -q -r requirements.txt || exit /b 1
)

if not exist .env (
    echo No .env found. Copy .env.example to .env and put your API key in it.
    exit /b 1
)

.venv\Scripts\python -m agent
