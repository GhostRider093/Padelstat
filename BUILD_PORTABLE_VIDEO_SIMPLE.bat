@echo off
REM Build de la version portable video simple PFPADEL
echo ========================================
echo   Build PFPADEL - Video Simple
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe
    pause
    exit /b 1
)

python build_exe.py --portable-video-simple
if errorlevel 1 (
    echo [ERREUR] Echec du build exe video simple
    pause
    exit /b 1
)

python build_portable.py --portable-video-simple
if errorlevel 1 (
    echo [ERREUR] Echec du packaging video simple
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build termine !
echo Archive : dist\PFPADEL_Portable_Video_Simple.zip
echo ========================================
pause
