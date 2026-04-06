# Test comparatif des moteurs vocaux (Windows / Google / Whisper)

Objectif : mesurer rapidement **ce qui marche le mieux** sur ton PC (27/12/2025) entre :
- Windows Speech Recognition (SAPI, offline)
- Google Speech Recognition (online via `SpeechRecognition`)
- Whisper (local via `faster-whisper`)

Le script de bench est : [bench_voice_engines.py](bench_voice_engines.py)

## Pré-requis (déjà présents dans ton environnement)

Le workspace utilise Python 3.12, et on voit installés :
- `pywin32` (Windows SAPI)
- `SpeechRecognition` + `PyAudio`
- `faster-whisper`

## Lancer le bench

Depuis la racine du projet :

- Bench des 3 moteurs :
  - `C:/Users/arnau/AppData/Local/Programs/Python/Python312/python.exe bench_voice_engines.py --engine all`

- Bench Whisper uniquement (modèle tiny recommandé) :
  - `C:/Users/arnau/AppData/Local/Programs/Python/Python312/python.exe bench_voice_engines.py --engine whisper --whisper-model tiny`

- Bench Windows SAPI uniquement :
  - `C:/Users/arnau/AppData/Local/Programs/Python/Python312/python.exe bench_voice_engines.py --engine windows`

- Bench Google uniquement (nécessite Internet) :
  - `C:/Users/arnau/AppData/Local/Programs/Python/Python312/python.exe bench_voice_engines.py --engine google`

## Phrases testées

Par défaut, le script te fait prononcer une liste de commandes type `OK ... OK`.

Tu peux fournir ta propre liste (1 commande par ligne) :
- `C:/Users/arnau/AppData/Local/Programs/Python/Python312/python.exe bench_voice_engines.py --phrases data/phrases_test.txt`

## Résultats

Le script affiche un résumé :
- % de match exact (après normalisation)
- similarité moyenne (approx)
- latence moyenne
- erreurs/timeouts

Et sauvegarde un JSON dans :
- `data/voice_engine_bench_YYYYMMDD_HHMMSS.json`

## Lecture rapide (reco)

- Si **Windows SAPI** a un bon taux + faible latence : c’est généralement le meilleur choix sur Windows (offline).
- Si **Google** gagne mais te gêne (internet, quota, latence variable) : bon en fallback.
- Si **Whisper** est stable mais lent : tester `tiny` + éventuellement GPU plus tard.
