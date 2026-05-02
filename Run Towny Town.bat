@echo off
title Towny Town
cd /d "%~dp0"

echo Starting Towny Town...
python -m pip install -r requirements.txt -q 2>nul
python main.py
if errorlevel 1 (
    echo.
    echo If you see "python is not recognized", install Python from https://www.python.org/downloads/
    echo and check "Add python.exe to PATH" during setup.
    pause
)
