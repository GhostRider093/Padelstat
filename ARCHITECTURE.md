# 🏗️ Architecture Technique - PFPADEL Video Stats

## 📐 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    PFPADEL Video Stats                   │
│                  (Interface Tkinter)                     │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    │              │              │
┌───▼────┐   ┌────▼─────┐   ┌───▼────────┐
│  VLC   │   │  OpenCV  │   │   FFmpeg   │
│ Player │   │  Frames  │   │  Cutter    │
└───┬────┘   └────┬─────┘   └───┬────────┘
    │             │              │
    │      ┌──────▼──────┐       │
    │      │ Annotations │       │
    │      │  Manager    │       │
    │      └──────┬──────┘       │
    │             │              │
┌───▼─────────────▼──────────────▼────┐
│         Data Layer (JSON/CSV)        │
│  - Autosave    - Backups    - Clips │
└──────────────────────────────────────┘
```

## 🎯 Composants Principaux

### 1. Interface Utilisateur (`app/ui/`)

**main_window.py** - Fenêtre principale Tkinter
- **Responsabilités** :
  - Gestion de l'interface graphique
  - Gestion des événements clavier
  - Coordination des composants
  - Affichage des overlays
- **Dépendances** : VideoPlayer, AnnotationManager, VideoCutter
- **Technologies** : Tkinter, Canvas pour vidéo

**Bindings clavier** :
```python
SPACE   → pause_and_annotate()
F/P/E   → select_point_type()
1-4     → select_player()
ENTER   → validate_annotation()
←→↑↓    → skip_forward/backward()
R       → remove_last()
S       → quick_save()
H       → show_help()
N/B     → next/previous_point()
```

### 2. Lecteur Vidéo Hybride (`app/video/`)

**video_player.py** - Architecture hybride VLC + OpenCV
```
VLC (python-vlc)          OpenCV (cv2)
    ↓                         ↓
Lecture vidéo          Capture précise
Son natif              10 frames/point
Contrôles              Analyse frame
```

**Méthodes clés** :
```python
load_video(path)              # Charge vidéo dans VLC et OpenCV
play() / pause()              # Contrôle lecture
forward(seconds)              # Avance de N secondes
rewind(seconds)               # Recule de N secondes
capture_frames_before(folder) # Capture 10 frames avant timestamp
get_current_time()            # Position actuelle (ms)
```

**video_cutter.py** - Découpage vidéo avec FFmpeg
```python
_find_ffmpeg()           # Cherche ffmpeg.exe (projet ou PATH)
_download_ffmpeg()       # Télécharge auto si absent (~90 MB)
check_ffmpeg()           # Vérifie disponibilité
cut_video(start, end)    # Extrait segment sans réencodage
```

### 3. Gestion des Annotations (`app/annotations/`)

**annotation_manager.py** - Stockage et autosave
```python
add_annotation(type, player, timestamp, frame_path)
remove_last()                    # Annule dernier point
autosave()                       # Sauvegarde auto (JSON)
find_latest_autosave()           # Détecte session précédente
analyze_chronology()             # Analyse temporelle (5×20%)
get_stats()                      # Calcule statistiques
```

**Structure annotation** :
```json
{
  "id": 1,
  "type": "point_gagnant",
  "winning_shot_type": "smash",
  "player": "Joueur 1",
  "team": 1,
  "timestamp": 45.12,
  "frame": 1234,
  "screenshots": ["frame_01.png", ..., "frame_10.png"],
  "datetime": "2025-12-04T14:30:15"
}
```

### 4. Exports (`app/exports/`)

**json_exporter.py** - Export JSON complet
- Métadonnées match
- Liste complète annotations
- Statistiques globales

**csv_exporter.py** - Export Excel
- Délimiteur : `;` (Excel FR)
- Encodage : UTF-8 BOM
- Colonnes : ID, Type, Joueur, Équipe, Temps, Frame, etc.

**html_generator.py** - Rapports HTML interactifs
```html
<!DOCTYPE html>
<html>
  <head>
    <style> /* CSS moderne avec gradients */ </style>
    <script src="Chart.js CDN"></script>
  </head>
  <body>
    <section class="stats">
      <!-- Stats globales -->
    </section>
    <section class="charts">
      <canvas id="typeChart"></canvas>      <!-- Camembert -->
      <canvas id="playerChart"></canvas>    <!-- Barres -->
      <canvas id="timelineChart"></canvas>  <!-- Ligne -->
    </section>
    <section class="chronology">
      <!-- 5 tranches de 20% du match -->
    </section>
  </body>
</html>
```

**Graphiques Chart.js** :
1. **Doughnut** : Distribution types points
2. **Bar** : Stats par joueur
3. **Line** : Évolution temporelle

## 🔄 Flux de Données

### Annotation d'un point
```
1. User presse ESPACE
   ↓
2. VideoPlayer.pause()
   ↓
3. MainWindow affiche menu annotation
   ↓
4. User tape F/P/E → type sélectionné
   ↓
5. User tape 1-4 → joueur sélectionné
   ↓
6. User presse ENTRÉE
   ↓
7. VideoPlayer.capture_frames_before(10)
   ↓
8. AnnotationManager.add_annotation(...)
   ↓
9. AnnotationManager.autosave()
   ↓
10. JSON écrit dans data/autosaves/
    ↓
11. Backup copié dans data/backups/
    ↓
12. Interface mise à jour (compteur, overlay)
```

### Extraction de clip vidéo
```
1. User clique "🎥 Sauvegarder Clip"
   ↓
2. Dialog clavier s'ouvre (start=current_time, end=current_time+10)
   ↓
3. User navigue avec ↑↓←→
   ↓
4. User presse ENTRÉE
   ↓
5. VideoCutter.cut_video(input, start, end)
   ↓
6. FFmpeg subprocess : -i input -ss start -t duration -c copy output
   ↓
7. Si erreur : fallback avec réencodage (-c:v libx264 -c:a aac)
   ↓
8. Clip sauvé dans data/clips/
```

## 🗄️ Stockage

### Structure fichiers
```
data/
├── autosaves/
│   └── autosave_YYYYMMDD_HHMMSS.json  (dernière session)
├── backups/
│   └── backup_YYYYMMDD_HHMMSS.json    (rotation 10 fichiers)
├── clips/
│   └── clip_YYYYMMDD_HHMMSS_45s_10s.mp4
├── images/
│   ├── point_001/
│   │   ├── frame_01.png  (-9 frames)
│   │   ├── ...
│   │   └── frame_10.png  (moment exact)
│   └── point_002/
├── exports/
│   └── match_YYYYMMDD_HHMMSS.json
│   └── stats_YYYYMMDD_HHMMSS.csv
└── reports/
    └── rapport_YYYYMMDD_HHMMSS.html
```

### Format JSON (autosave)
```json
{
  "metadata": {
    "video_path": "E:/Videos/match.mp4",
    "date": "2025-12-04",
    "players": {
      "team1": ["Joueur 1", "Joueur 2"],
      "team2": ["Joueur 3", "Joueur 4"]
    }
  },
  "annotations": [
    { "id": 1, "type": "faute_directe", ... },
    { "id": 2, "type": "point_gagnant", ... }
  ],
  "statistics": {
    "total_points": 42,
    "fautes_directes": 15,
    "points_gagnants": 20,
    "fautes_provoquees": 7
  }
}
```

## 🔌 Dépendances Externes

### Python Packages
```
python-vlc==3.0.20123       # VLC bindings
opencv-python==4.9.0.80     # Computer vision
Pillow==10.2.0              # Image processing
numpy==1.26.4               # Numerical computing
```

### Binaires
```
VLC Media Player (3.0+)     # Lecture vidéo avec son
FFmpeg (essentials)         # Découpage vidéo
```

### CDN (HTML reports)
```javascript
Chart.js 4.4.0              // Graphiques interactifs
```

## ⚡ Performance

### Optimisations
- **VLC pour le son** : Évite réencodage OpenCV
- **FFmpeg `-c copy`** : Copie codec sans réencodage (rapide)
- **Autosave asynchrone** : N'interrompt pas l'interface
- **Capture frames** : OpenCV seek précis vs VLC approximatif

### Limites
- **Fichier vidéo** : Max 2 GB recommandé (OpenCV RAM)
- **Annotations** : Max ~1000 points (perf JSON)
- **FFmpeg download** : Requiert ~90 MB espace disque

## 🔒 Sécurité & Fiabilité

### Autosave
- Sauvegarde après **chaque** annotation
- Rotation backups (10 derniers fichiers)
- Détection crash au redémarrage

### Validation
- Vérification format vidéo avant chargement
- Test FFmpeg avant extraction clip
- Gestion erreurs subprocess (FFmpeg)

### Logs
```python
try:
    # Opération risquée
except Exception as e:
    print(f"❌ Erreur : {e}")
    # Pas de crash, message user-friendly
```

## 🚀 Build & Distribution

### PyInstaller
```bash
pyinstaller PFPADEL.spec
```

**Contenu exécutable** :
- Python 3.10 runtime
- Toutes dépendances pip
- FFmpeg.exe embarqué
- Fichiers config (players.json, templates)

**Taille finale** : ~150 MB

### Dépendances utilisateur
- **VLC Media Player** (seule dépendance externe)

## 📚 Points d'Extension

### Ajouter un type de point
1. Modifier `app/annotations/annotation_manager.py`
2. Ajouter raccourci dans `app/ui/main_window.py`
3. Mettre à jour `config.json`

### Nouveau format d'export
1. Créer `app/exports/xxx_exporter.py`
2. Implémenter `export(annotations, metadata)`
3. Ajouter bouton dans `main_window.py`

### Intégration API externe
```python
# app/integrations/padel_manager_api.py
def sync_match(annotations):
    # POST vers API externe
    pass
```

---

**Version** : 1.0.0  
**Dernière mise à jour** : 2025-12-04
