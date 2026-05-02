@echo off
cd /d "%~dp0"
echo Installing pygbag if needed...
py -m pip install "pygbag>=0.9" -q
echo.
echo Building Towny Town for web (output: build\web\)...
py -m pygbag --build --title "Towny Town" .
if errorlevel 1 (
    echo Build failed.
    pause
    exit /b 1
)
echo.
echo Done. Open build\web\index.html via a local server:
echo   Run: serve_web.bat
echo Or upload everything inside build\web\ to GitHub Pages / itch.io HTML.
pause
