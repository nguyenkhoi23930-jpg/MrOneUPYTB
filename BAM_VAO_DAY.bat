@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo   MrOneUPYTB - install / run
echo ========================================
if not exist "client_secret.json" (
  echo.
  echo MISSING client_secret.json
  echo Put client_secret.json next to app.py then run again.
  echo.
  pause
  exit /b 1
)
python --version >nul 2>&1
if errorlevel 1 (
  echo PYTHON NOT FOUND. Install Python 3.10+ and tick Add to PATH.
  pause
  exit /b 1
)
python -m pip install -r requirements.txt
echo.
echo Starting app...
python app.py
pause
