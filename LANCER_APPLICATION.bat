@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul

rem ---------------------------------------------------------------------
rem  PADELSTAT - lancement avec le module vocal V2
rem
rem  Pour desactiver l'ecoute permanente (micro ouvert), mettre
rem  NANOAPPSTAT_VOICE_ECOUTE a 0. Le push-to-talk sur V continue de
rem  fonctionner sans elle.
rem ---------------------------------------------------------------------

set "NANOAPPSTAT_VOICE_V2=1"
set "NANOAPPSTAT_VOICE_ECOUTE=1"
set "HF_HUB_ENABLE_HF_TRANSFER=0"

rem Le HF_HOME systeme pointe vers F:, absent de cette machine. On ne le
rem contourne que si le lecteur n'est toujours pas la : une fois F:
rem rebranche, la configuration d'origine reprend la main.
if exist "F:\" (
  echo [INFO] Lecteur F: present - cache Hugging Face systeme conserve
) else (
  echo [INFO] Lecteur F: absent - cache Hugging Face redirige vers E:\hf-cache
  set "HF_HOME=E:\hf-cache"
)

if not exist "logs" mkdir "logs"

echo.
echo ==========================================================
echo   PADELSTAT - module vocal
echo ----------------------------------------------------------
echo   V maintenue        annoter (push-to-talk)
echo   ENTREE             valider une annotation proposee
echo   ECHAP              jeter la saisie en cours
echo   A                  afficher/masquer l'aide-memoire
echo ----------------------------------------------------------
echo   "OK STAT"          pause
echo   "reprise"          lecture
echo   "trois secondes"   avancer de 3 s
echo   "cinq secondes"    avancer de 5 s
echo   "recule trois secondes" / "recule cinq secondes"
echo ==========================================================
echo.

rem Tee-Object : la trace reste visible ET part dans un journal, pour
rem pouvoir diagnostiquer apres coup ce que le module a entendu.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "python -u main.py 2>&1 | Tee-Object -FilePath 'logs\vocal.log'"

echo.
echo Journal de la session : logs\vocal.log
echo.
pause
endlocal
