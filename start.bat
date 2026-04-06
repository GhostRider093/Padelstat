@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo   PFPADEL - Demarrage de l'application
echo ========================================
echo.

if exist "vlc\libvlc.dll" (
  echo [INFO] Runtime VLC local detecte: vlc\
  set "VLC_DIR=%CD%\vlc"
) else if exist "dist\PFPADEL_Portable_Video_Simple\vlc\libvlc.dll" (
  echo [INFO] Runtime VLC detecte dans dist\PFPADEL_Portable_Video_Simple\vlc
  set "VLC_DIR=%CD%\dist\PFPADEL_Portable_Video_Simple\vlc"
)

if exist ".venv\Scripts\python.exe" (
  echo [INFO] Environnement virtuel detecte: .venv
  ".venv\Scripts\python.exe" main.py
  goto :end
)

where py >nul 2>nul
if %errorlevel%==0 (
  echo [INFO] Lancement via py -3
  py -3 main.py
  goto :end
)

echo [INFO] Lancement via python
python main.py

:end
if errorlevel 1 (
  echo.
  echo [ERREUR] Le lancement a echoue.
  echo Verifie Python et les dependances.
  pause
)
endlocal
