@echo off
cd /d "%~dp0"
if not exist "build\web\index.html" (
    echo No web build found. Run build_web.bat first.
    pause
    exit /b 1
)
cd build\web
echo Serving Towny Town at http://localhost:8000/
echo Press Ctrl+C to stop.
start "" "http://localhost:8000/"
py -m http.server 8000
