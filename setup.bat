@echo off
setlocal
cd /d "%~dp0"

echo [1/2] Creating the private Python environment...
py -3 -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
if not errorlevel 1 (
    set "PY_LAUNCHER=py -3"
) else (
    python -c "import sys; assert sys.version_info >= (3,11)" >nul 2>nul
    if errorlevel 1 goto :error
    set "PY_LAUNCHER=python"
)

if not exist ".venv\Scripts\python.exe" %PY_LAUNCHER% -m venv .venv
if errorlevel 1 goto :error

echo [2/2] Installing required Python modules...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Offline mode is ready. Ollama is optional.
echo For local AI, install Ollama and run: ollama pull qwen2.5:3b

echo.
echo Setup complete. Double-click start_filepilot.bat to launch the app.
pause
exit /b 0

:error
echo.
echo Setup failed. Confirm that Python 3.11 or newer is installed and try again.
pause
exit /b 1
