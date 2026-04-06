@echo off
REM Build de l'exécutable PFPADEL
echo ========================================
echo    Build PFPADEL - Executable Windows
echo ========================================
echo.

REM Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe
    pause
    exit /b 1
)

REM Lancer le build
python build_exe.py

echo.
echo ========================================
echo Build termine !
echo Executable : dist\NanoApp_Stat.exe
echo ========================================
pause
