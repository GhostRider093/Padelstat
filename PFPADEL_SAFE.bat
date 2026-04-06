@echo off
REM Lanceur PFPADEL/NanoApp Stat en mode SAFE (sans video / vocal / IA)
echo ========================================
echo    PFPADEL - Demarrage SAFE MODE
echo ========================================
echo.

set NANOAPPSTAT_SAFE_MODE=1

if exist "PFPADEL.exe" (
    echo Lancement de PFPADEL.exe --safe...
    start "" /b PFPADEL.exe --safe
    exit /b 0
)

if exist "NanoApp_Stat.exe" (
    echo Lancement de NanoApp_Stat.exe --safe...
    start "" /b NanoApp_Stat.exe --safe
    exit /b 0
)

if exist "dist\NanoApp_Stat.exe" (
    echo Lancement de dist\NanoApp_Stat.exe --safe...
    start "" /b dist\NanoApp_Stat.exe --safe
    exit /b 0
)

REM Fallback Python (mode dev)
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Exe introuvable et Python non installe.
    pause
    exit /b 1
)

echo Lancement de l'application en Python --safe...
python main.py --safe

if errorlevel 1 (
    echo.
    echo [ERREUR] L'application s'est terminee avec une erreur
    pause
)
