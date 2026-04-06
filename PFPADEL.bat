@echo off
REM Lanceur PFPADEL (dev ou exe)
echo ========================================
echo    PFPADEL - Demarrage
echo ========================================
echo.

REM 1) Si un exe est present, le lancer directement (mode distribution)
if exist "PFPADEL.exe" (
    echo Lancement de PFPADEL.exe...
    start "" /b "PFPADEL.exe"
    exit /b 0
)

if exist "NanoApp_Stat.exe" (
    echo Lancement de NanoApp_Stat.exe...
    start "" /b "NanoApp_Stat.exe"
    exit /b 0
)

if exist "dist\NanoApp_Stat.exe" (
    echo Lancement de dist\NanoApp_Stat.exe...
    start "" /b "dist\NanoApp_Stat.exe"
    exit /b 0
)

REM 2) Sinon fallback Python (mode dev)
set "PYTHON_EXE=python"
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
    echo [INFO] Environnement virtuel detecte: %PYTHON_EXE%
)

"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Exe introuvable et Python non installe.
    echo - Pour distribution: copiez le dossier dist\PFPADEL_Portable sur l'autre PC.
    echo - Pour dev: installez Python depuis https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Vérifier les dépendances
echo Verification des dependances...
"%PYTHON_EXE%" -c "import vlc, cv2, PIL" >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances...
    "%PYTHON_EXE%" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERREUR] Installation des dependances echouee.
        pause
        exit /b 1
    )
)

REM Vérifier FFmpeg
if not exist "ffmpeg\ffmpeg.exe" (
    echo FFmpeg non trouve, telechargement automatique...
    "%PYTHON_EXE%" download_ffmpeg.py
    if errorlevel 1 (
        echo [ERREUR] Echec du telechargement de FFmpeg
        pause
        exit /b 1
    )
)

REM Lancer l'application
echo.
echo Lancement de PFPADEL (mode Python)...
echo.
"%PYTHON_EXE%" main.py

if errorlevel 1 (
    echo.
    echo [ERREUR] L'application s'est terminee avec une erreur
    pause
)
