@echo off
echo ================================================
echo Installation de Whisper pour reconnaissance vocale
echo ================================================
echo.

echo Installation de faster-whisper...
pip install faster-whisper>=0.10.0

echo.
echo Installation de pyaudio...
pip install pyaudio>=0.2.14

echo.
echo Installation de webrtcvad...
pip install webrtcvad>=2.0.10

echo.
echo ================================================
echo Installation terminee !
echo ================================================
echo.
echo Whisper est maintenant pret a l'emploi.
echo Relancez l'application pour utiliser Whisper.
echo.
pause
