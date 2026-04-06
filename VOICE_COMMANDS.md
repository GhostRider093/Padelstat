# 🎤 Commandes Vocales - NanoApp Stat

## 📋 Vue d'ensemble

Module de commandes vocales mains libres utilisant Whisper pour l'annotation de matchs de padel en temps réel, **sans interrompre la lecture vidéo**.

## ⚙️ Installation

```bash
pip install faster-whisper pyaudio webrtcvad
```

### Dépendances détaillées :
- **faster-whisper** : Modèle Whisper optimisé (4x plus rapide)
- **pyaudio** : Capture audio du microphone
- **webrtcvad** : Détection d'activité vocale (VAD)

### Notes Windows :
Si `pyaudio` pose problème, télécharger le wheel depuis :
https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## 🚀 Utilisation

### Activation
1. Cliquer sur le bouton **"🎤 COMMANDES VOCALES"** dans la sidebar
2. Autoriser l'accès au microphone si demandé
3. Le bouton devient vert : **"🎤 VOCAL ACTIF"**
4. Parler naturellement pendant que la vidéo tourne !

### Exemples de commandes

#### Annotation de points :
```
"Nouveau point faute directe Arnaud"
"Point gagnant smash Pierre"
"Faute provoquée vollée Thomas"
"Bandeja cœur Lucas"
```

#### Actions rapides :
```
"Annuler dernier point"
"Sauvegarder"
"Générer rapport"
```

#### Contrôle vidéo :
```
"Pause"
"Lecture"
```

## 📖 Grammaire des commandes

### Structure générale :
```
[Action] [Type de point] [Type de coup] [Joueur] [Label spécial]
```

### Actions supportées :
- `nouveau point` / `point suivant`
- `annuler` / `supprime`
- `sauvegarder` / `enregistre`
- `générer rapport` / `rapport`
- `pause` / `stop`
- `lecture` / `play`

### Types de points :
- `faute directe`
- `point gagnant`
- `faute provoquée`

### Types de coups :
- `smash`
- `vollée` / `volley`
- `bandeja`
- `víbora` / `vibora`
- `coup droit` / `drive`
- `revers` / `backhand`
- `lob`
- `chiquita`
- `sortie vitre`
- `contre vitre`
- `fond de court`

### Labels spéciaux :
- `cœur bandeja` / `bandeja cœur`
- `cœur smash` / `smash cœur`
- `cœur víbora` / `víbora cœur`

### Joueurs :
Les noms configurés dans l'application (ex: Arnaud, Pierre, Thomas, Lucas)

## 🎯 Architecture technique

### Principe non-bloquant

```
┌─────────────────────┐
│  Thread Principal   │  ← Vidéo + UI (jamais bloqué)
│  - Lecture vidéo    │
│  - Interface Tkinter│
└──────────┬──────────┘
           │
           ↓ (Queue)
┌──────────────────────┐
│  Thread Audio        │  ← Tourne en permanence
│  - Écoute micro      │
│  - Whisper           │
│  - VAD               │
└──────────────────────┘
```

### Flux de traitement :

1. **Capture audio** : PyAudio capture le microphone en continu (16kHz, chunks de 30ms)
2. **VAD** : WebRTC VAD détecte quand vous parlez
3. **Buffer** : Accumulation de l'audio pendant la parole
4. **Silence** : Détection de 900ms de silence → déclenche la transcription
5. **Whisper** : Transcription en arrière-plan (300-800ms)
6. **Parser** : Interprétation de la commande
7. **Exécution** : Ajout au thread principal via `after()`
8. **Vidéo** : Continue à tourner sans interruption ! 🎬

### Performance :
- **Latence VAD** : ~50ms
- **Transcription Whisper** : 300-800ms (modèle `tiny`)
- **Impact vidéo** : **0ms** (threads séparés)

## ⚡ Optimisations

### Modèles Whisper disponibles :
- `tiny` : Ultra rapide (~300ms), précision 95% ✅ Recommandé
- `base` : Rapide (~500ms), précision 97%
- `small` : Moyen (~1s), précision 98%
- `medium` : Lent (~2s), précision 99%

### Changer de modèle :
```python
voice_commander.set_model_size("base")
```

### GPU (optionnel) :
Pour Whisper encore plus rapide avec GPU NVIDIA :
```python
model = WhisperModel("tiny", device="cuda", compute_type="float16")
```

## 🔧 Configuration avancée

### Sensibilité VAD :
```python
voice_commander.vad_mode = 3  # 0-3 (3 = plus sensible)
```

### Seuil de silence :
```python
voice_commander.silence_threshold = 30  # Frames (30 = ~900ms)
```

### Langue :
```python
voice_commander = VoiceCommander(language="fr")  # fr, en, es, etc.
```

## 🐛 Dépannage

### "Module vocal non disponible"
→ Installer les dépendances : `pip install faster-whisper pyaudio webrtcvad`

### "Impossible de démarrer l'écoute"
→ Vérifier que le microphone est connecté et autorisé

### Commandes non reconnues
→ Parler clairement et attendre le silence pour déclencher la transcription

### Latence trop élevée
→ Utiliser le modèle `tiny` au lieu de `base` ou `small`

### PyAudio ne s'installe pas (Windows)
→ Télécharger le wheel depuis https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio

## 💡 Conseils d'utilisation

1. **Parler naturellement** : Pas besoin de crier ou d'articuler exagérément
2. **Pauses claires** : Marquer une pause après chaque commande
3. **Noms précis** : Utiliser les noms exacts configurés pour les joueurs
4. **Environnement calme** : Éviter les bruits de fond importants
5. **Test** : Tester quelques commandes avant le match

## 📊 Exemples de workflows

### Annotation rapide :
```
Vous : "Faute directe Arnaud"
→ Vidéo continue
→ Point ajouté automatiquement
→ Confirmation visuelle

Vous : "Point gagnant smash Pierre"
→ Vidéo continue
→ Point ajouté

Vous : "Annuler"
→ Dernier point supprimé
```

### Match complet :
```
# Pendant le match, sans toucher la souris :
"Faute directe Thomas"
"Point gagnant vollée Lucas"
"Faute provoquée Arnaud"
"Bandeja cœur Pierre"
...

# À la fin :
"Sauvegarder"
"Générer rapport"
```

## 🔮 Évolutions futures

- [ ] Feedback vocal avec TTS (text-to-speech)
- [ ] Commandes de navigation ("recule 5 secondes")
- [ ] Mode dictée pour commentaires
- [ ] Support multi-langues amélioré
- [ ] Calibration automatique du VAD
- [ ] Hotword detection ("OK Padel...")

## 📝 Licence

Même licence que NanoApp Stat

---

**Bon match ! 🎾🎤**
