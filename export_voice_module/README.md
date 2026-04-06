# Export module vocal — `padel_voice`

Ce dossier est **autonome**: vous pouvez le copier dans une autre application et importer le package `padel_voice`.

## Contenu

- `padel_voice/command_parser.py` : parsing + validation des commandes (sans dépendances audio)
- `padel_voice/voice_commander.py` : reconnaissance mains-libres (Windows SAPI → SpeechRecognition/Google → Whisper optionnel)
- `padel_voice/voice_batch_recorder.py` : mode push-to-talk (PTT) (enregistre WAV + transcrit via SpeechRecognition/Google)
- `padel_voice/voice_logger.py` : logging debug dans `data/voice_commands.log`

## Dépendances

### Parsing uniquement

Aucune dépendance externe.

### Mains-libres (Windows SAPI)

- `pywin32`

### Fallback SpeechRecognition (Google)

- `SpeechRecognition`
- `pyaudio`

### Push-to-talk (PTT)

- `SpeechRecognition`
- `pyaudio`

### Whisper (optionnel)

- `faster-whisper`
- `webrtcvad`
- `pyaudio`

## Installation rapide (dans une autre app)

Option A — copier le dossier `padel_voice/` dans votre projet, puis:

```python
from padel_voice import CommandParser
```

Option B — ajouter `export_voice_module/` au `PYTHONPATH`.

## Exemple 1 — Hands-free: écouter et parser

Voir `example_cli_handsfree.py`.

## Exemple 2 — Push-to-talk (PTT)

Voir `example_cli_ptt.py`.

## Notes importantes

- Le callback de `VoiceCommander` renvoie du texte. À vous de faire: parse → validate → action.
- Le module n’a **aucune dépendance UI** (Tkinter/PyQt/etc.).
- SpeechRecognition/Google a besoin d’internet.
