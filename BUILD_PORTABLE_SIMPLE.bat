@echo off
REM Build de la version portable simple PFPADEL
echo ========================================
echo   Build PFPADEL - Portable Simple
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe
    pause
    exit /b 1
)

python build_exe.py --portable-simple
if errorlevel 1 (
    echo [ERREUR] Echec du build exe portable simple
    pause
    exit /b 1
)

python build_portable.py --portable-simple
if errorlevel 1 (
    echo [ERREUR] Echec du packaging portable simple
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build termine !
echo Archive : dist\PFPADEL_Portable_Simple.zip
echo ========================================
pause
