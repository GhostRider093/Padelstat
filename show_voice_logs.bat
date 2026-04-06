@echo off
chcp 65001 > nul
echo ================================================================================
echo 📋 VISUALISEUR DE LOGS VOCAUX - PADEL STAT
echo ================================================================================
echo.
echo Options disponibles:
echo   1. Afficher les 10 dernières commandes
echo   2. Afficher les 20 dernières commandes
echo   3. Afficher tous les logs
echo   4. Rechercher un mot
echo   5. Effacer les logs (backup auto)
echo   6. Ouvrir le fichier de log
echo   0. Quitter
echo.
echo ================================================================================

:menu
echo.
set /p choice="Votre choix (0-6): "

if "%choice%"=="1" (
    python show_voice_logs.py -n 10
    goto menu
)

if "%choice%"=="2" (
    python show_voice_logs.py -n 20
    goto menu
)

if "%choice%"=="3" (
    python show_voice_logs.py
    goto menu
)

if "%choice%"=="4" (
    set /p search="Mot à rechercher: "
    python show_voice_logs.py -s "%search%"
    goto menu
)

if "%choice%"=="5" (
    python show_voice_logs.py -c
    goto menu
)

if "%choice%"=="6" (
    if exist "data\voice_commands.log" (
        notepad "data\voice_commands.log"
    ) else (
        echo ❌ Fichier de log non trouvé
    )
    goto menu
)

if "%choice%"=="0" (
    echo Au revoir!
    exit /b 0
)

echo ❌ Choix invalide
goto menu
