@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================
echo  Build MrOneUPYTB.exe
echo ========================================
echo.

if not exist "client_secret.json" (
  echo WARNING: no client_secret.json in this folder.
  echo EXE will be built WITHOUT embedded secret.
  echo Put client_secret.json here then re-run to embed it.
  echo.
  set "ADD_SECRET="
) else (
  echo Found client_secret.json ? will EMBED into EXE.
  set "ADD_SECRET=--add-data client_secret.json;."
)

python -m pip install -r requirements.txt pyinstaller
echo.
pyinstaller --noconfirm --clean --onefile --windowed --name MrOneUPYTB --icon logo_mrone.ico --add-data "logo_mrone.png;." --add-data "logo_mrone.ico;." --add-data "VERSION;." %ADD_SECRET% app.py

echo.
if exist "dist\MrOneUPYTB.exe" (
  echo OK: dist\MrOneUPYTB.exe
  copy /Y dist\MrOneUPYTB.exe .
  echo.
  echo Share: send only MrOneUPYTB.exe if secret was embedded.
) else (
  echo BUILD FAILED
)
pause
