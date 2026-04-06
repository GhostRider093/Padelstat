# Prompt — Module vocal padel (copier-coller dans un LLM)

> Ce prompt décrit le module `padel_voice` tel qu'il est implémenté dans `export_voice_module/padel_voice/`.
> Copiez-collez ce texte dans un LLM pour reproduire, adapter ou étendre le module dans une autre application.

---

## Contexte

Tu es un ingénieur Python senior. Je veux intégrer un module **vocal de statistiques padel** dans mon application de lecture vidéo. Ce module doit :

1. **Reconnaître la parole** (STT) en français
2. **Parser les commandes** prononcées en actions structurées
3. **Valider** les annotations avant de les ajouter
4. **Router** vers l'action applicative (annotation, contrôle vidéo, affichage stats)

---

## Architecture du package `padel_voice`

```
padel_voice/
├── __init__.py                  # Exports publics
├── command_parser.py            # Parseur + validateur (0 dépendances audio)
├── voice_commander.py           # STT mains-libres: SAPI → Google → Whisper optionnel
├── voice_commander_windows.py   # SAPI COM events (pywin32)
├── voice_batch_recorder.py      # Push-to-talk: WAV + transcription async
└── voice_logger.py              # Log vers data/voice_commands.log
```

---

## 1. CommandParser — Structure hiérarchique du résultat

### Champs produits par `parse(text) -> dict | None`

```python
{
  "action":      str | None,  # voir liste complète ci-dessous
  "joueur":      str | None,  # nom joueur (attaquant / gagnant / fautif)
  "defenseur":   str | None,  # uniquement pour faute_provoquee
  "type_point":  str | None,  # faute_directe | point_gagnant | faute_provoquee
  "zone_frappe": str | None,  # service | fond_de_court | volee | lob       — niveau 3
  "technique":   str | None,  # coup_droit | revers | balle_haute            — niveau 4
  "coup_final":  str | None,  # smash | bandeja | vibora                     — niveau 5
  "type_coup":   str | None,  # slug compat (ex: "volee_balle_haute_smash")
  "zone":        str | None,  # position terrain: filet | milieu | fond_terrain
  "diagonale":   str | None,  # parallele | croise
  "label":       str | None,  # coeur_bandeja | coeur_smash | coeur_vibora
  "raw_text":    str,         # texte normalisé
}
```

### Hiérarchie 5 niveaux (conforme SCHEMA_COUPS_HIERARCHIE.md)

```
TYPE_POINT      → JOUEUR(S)  → ZONE_FRAPPE    → TECHNIQUE    → COUP_FINAL
─────────────────────────────────────────────────────────────────────────
point_gagnant                  service          —              —
faute_directe                  lob              —              —
faute_provoquee                fond_de_court    coup_droit     —
                               volee            revers         —
                                                balle_haute    smash | bandeja | vibora
```

### Exemples de `type_coup` générés automatiquement

| Phrase vocale                                   | `type_coup`                  |
|-------------------------------------------------|------------------------------|
| `point gagnant Pierre service`                  | `service`                    |
| `point gagnant Thomas volée coup droit`         | `volee_coup_droit`           |
| `point gagnant Lucas fond de court revers`      | `fond_de_court_revers`       |
| `point gagnant Arnaud volée balle haute smash`  | `volee_balle_haute_smash`    |
| `faute directe Arnaud`                          | `None` (normal: pas de coup) |

---

## 2. Liste complète des actions vocales

### Annotations de points

| Exemple de commande                              | `action`      | Règle de validation                                  |
|--------------------------------------------------|---------------|------------------------------------------------------|
| `faute directe Arnaud`                           | nouveau_point | type_point + joueur (coup optionnel)                 |
| `point gagnant Pierre service`                   | nouveau_point | type_point + joueur + zone_frappe                    |
| `point gagnant Thomas volée coup droit`          | nouveau_point | + technique si zone = fond_de_court / volee          |
| `point gagnant Arnaud volée balle haute smash`   | nouveau_point | + coup_final si technique = balle_haute              |
| `faute provoquée Arnaud Thomas volée revers`     | nouveau_point | + defenseur                                          |

### Contrôle vidéo

| Commande vocale              | `action`        |
|------------------------------|-----------------|
| `pause` / `stop`             | pause           |
| `lecture` / `play`           | lecture         |
| `retour 2` / `-2`            | retour_2s       |
| `avance 2` / `+2`            | avance_2s       |
| `retour 10` / `-10`          | retour_10s      |
| `avance 10` / `+10`          | avance_10s      |
| `point précédent`            | point_precedent |
| `point suivant`              | point_suivant   |
| `vitesse lente` / `ralentir` | vitesse_lente   |
| `vitesse normale`            | vitesse_normale |
| `vitesse rapide` / `accélérer` | vitesse_rapide |
| `zoom avant`                 | zoom_in         |
| `zoom arrière`               | zoom_out        |

### Stats et affichages

| Commande vocale         | `action`     |
|-------------------------|--------------|
| `review vocal`          | review_vocal |
| `stats` / `statistiques` | stats       |

### Gestion

| Commande vocale              | `action`    |
|------------------------------|-------------|
| `annuler` / `supprimer`      | annuler     |
| `sauvegarder`                | sauvegarder |
| `rapport` / `générer rapport` | rapport    |

---

## 3. Validation stricte

```python
valid, msg = parser.validate_command(cmd)
# valid = True  → prêt à créer l'annotation
# valid = False → msg = "⚠️ CHAMPS MANQUANTS: ZONE DE FRAPPE | TECHNIQUE"
missing = parser.get_missing_fields(cmd)  # ["Zone de frappe", "Technique"]
```

---

## 4. Modes STT

### Push-to-talk (PTT) — recommandé

```python
from padel_voice import CommandParser, VoiceBatchRecorder

parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])
rec = VoiceBatchRecorder(data_dir="data")

def on_transcription(audio_text: str, ts: float) -> bool:
    cmd = parser.parse(audio_text)
    valid, _ = parser.validate_command(cmd) if cmd else (False, "")
    if valid:
        create_annotation(cmd, ts)  # votre logique métier
    return valid

rec.start_session("ma_video.mp4", create_annotation_callback=on_transcription)

# Appel à chaque appui sur la touche PTT:
rec.start_recording(video_timestamp=12.5)
# Appel au relâchement:
rec.stop_recording()   # transcription en background (thread)
```

### Mains-libres (continu)

```python
from padel_voice import VoiceCommander

vc = VoiceCommander(callback=lambda text: router(parser.parse(text)),
                    language="fr-FR", enable_whisper=False)
vc.start()
```

---

## 5. Routage complet dans l'application

```python
VIDEO_ACTIONS = {
    "pause", "lecture",
    "retour_2s", "avance_2s", "retour_10s", "avance_10s",
    "vitesse_lente", "vitesse_normale", "vitesse_rapide",
    "point_precedent", "point_suivant",
    "zoom_in", "zoom_out",
}

def router(cmd: dict | None):
    if not cmd:
        return
    action = cmd.get("action")
    valid, msg = parser.validate_command(cmd)

    if action in VIDEO_ACTIONS:
        apply_video_control(action)

    elif action == "review_vocal":
        show_review_panel()

    elif action == "stats":
        show_stats_overlay()

    elif action == "nouveau_point" and valid:
        create_annotation(
            type_point  = cmd["type_point"],
            joueur      = cmd["joueur"],
            defenseur   = cmd.get("defenseur"),
            zone_frappe = cmd.get("zone_frappe"),
            technique   = cmd.get("technique"),
            coup_final  = cmd.get("coup_final"),
            type_coup   = cmd.get("type_coup"),   # slug compat legacy
            timestamp   = current_video_position(),
        )

    elif action == "nouveau_point" and not valid:
        show_error_banner(msg)   # affiche les champs manquants

    elif action in ("annuler", "sauvegarder", "rapport"):
        handle_management(action)
```

---

## 6. Normalisation phonétique (variantes FR réelles)

Le normaliseur corrige les erreurs phonétiques collectées sur 58 transcriptions Google Speech :

| Transcription STT       | Normalisé           |
|-------------------------|---------------------|
| `faut directe Arnaud`   | `faute directe Arnaud` |
| `foot provoquer`        | `faute provoquée`   |
| `volets coup droit`     | `volée coup droit`  |
| `ball au smash`         | `balle haute smash` |
| `franco rover`          | `fond de court revers` |
| `ballotte`              | `balle haute`       |
| `l'aube`                | `lob`               |

---

## 7. Dépendances

| Feature                      | Package requis                   | Optionnel |
|------------------------------|----------------------------------|-----------|
| Parsing seul                 | *(aucune)*                       | —         |
| STT Windows SAPI             | `pywin32`                        | Oui       |
| STT Google (fallback)        | `SpeechRecognition`              | Oui       |
| PTT enregistrement           | `pyaudio` + `SpeechRecognition`  | Oui       |
| STT Whisper                  | `faster-whisper` + `webrtcvad`   | Oui       |

Le package s'importe sans erreur même si aucune des dépendances audio n'est installée.

---

## 8. Contraintes d'implémentation

- **Zéro dépendance UI** dans le package (pas Tkinter/PyQt)
- **Dépendances audio optionnelles** — erreur levée uniquement à l'utilisation, pas à l'import
- **Thread-safe** — STT et transcription PTT dans des threads séparés, non bloquants
- **Python ≥ 3.10**
- **Windows prioritaire** (SAPI COM), fallback Google (internet requis)
- **Fixes regex** dans le normaliseur: utilise `re.sub(r'\bfaut\b', ...)` pour éviter de corrompre "faute" en "fautee"
