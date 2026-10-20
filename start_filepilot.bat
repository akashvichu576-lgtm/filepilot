@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo FilePilot is not installed yet. Running setup...
    call setup.bat
    if errorlevel 1 exit /b 1
)

echo Starting FilePilot...
".venv\Scripts\python.exe" -m streamlit run app.py

