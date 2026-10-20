@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Run setup.bat first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m unittest discover -v
set "TEST_EXIT=%ERRORLEVEL%"
pause
exit /b %TEST_EXIT%
