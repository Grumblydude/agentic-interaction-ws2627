@echo off
rem Checks the setup, installs what is missing, activates .venv and starts the chat.
setlocal
cd /d "%~dp0"

python -c "import sys; sys.exit(sys.version_info < (3, 11))" 2>nul
if errorlevel 1 (
    echo Python 3.11 or newer is required: https://www.python.org/downloads/
    exit /b 1
)

if not exist .venv\Scripts\activate.bat (
    echo Creating .venv ...
    python -m venv .venv || exit /b 1
)
call .venv\Scripts\activate.bat

python -m pip install -q --disable-pip-version-check -r requirements.txt || exit /b 1

if not exist .env (
    copy .env.example .env >nul
    echo Created .env from .env.example. Put your API key into .env and start again.
    exit /b 1
)

python -m agent
