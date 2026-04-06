# 🎾 PFPADEL Video Stats

Application d'analyse statistique de matchs de padel à partir de vidéos MP4.

## 🚀 Installation

### Prérequis
- Python 3.10 ou supérieur
- VLC Media Player (pour la lecture vidéo avec son)

### Installation des dépendances

```bash
pip install -r requirements.txt
```

### FFmpeg (automatique)

**FFmpeg est téléchargé automatiquement** au premier lancement si non détecté.

Si le téléchargement automatique échoue, vous pouvez :
1. Télécharger FFmpeg manuellement : https://www.gyan.dev/ffmpeg/builds/
2. Extraire `ffmpeg.exe` dans le dossier `ffmpeg/` du projet

Ou lancer le script de téléchargement :
```bash
python download_ffmpeg.py
```

## 💻 Utilisation

### Lancement

```bash
python main.py
```

### Workflow

1. **Charger une vidéo** : Bouton "📁 Charger Vidéo" ou `Ctrl+O`
2. **Configurer les joueurs** : Noms des 4 joueurs dans le panneau droit
3. **Analyser les points** :
   - Appuyez sur **ESPACE** pour mettre en pause et annoter
   - Choisissez le type de point : **F** (faute), **P** (point gagnant), **E** (faute provoquée)
   - Sélectionnez le joueur : **1**, **2**, **3**, **4**
   - Validez avec **ENTRÉE**
   - 10 images sont automatiquement capturées avant chaque point

### ⌨️ Raccourcis clavier

#### Navigation vidéo
- **ESPACE** : Pause et annoter le point
- **→** : Avancer de 2 secondes
- **←** : Reculer de 2 secondes
- **↑** : Avancer de 10 secondes
- **↓** : Reculer de 10 secondes
- **F11** : Plein écran

#### Annotation rapide
- **F** : Faute directe
- **P** : Point gagnant
- **E** : Faute provoquée
- **1-4** : Sélectionner joueur 1, 2, 3 ou 4
- **ENTRÉE** : Valider l'annotation

#### Actions
- **R** : Supprimer le dernier point
- **S** : Sauvegarder rapidement (JSON)
- **H** : Afficher l'aide
- **N** : Point suivant
- **B** : Point précédent

#### Clips vidéo
- **🎥 Sauvegarder Clip** : Extraire un segment de vidéo
  - **↑** : Ajuster le temps de début
  - **↓** : Ajuster le temps de fin
  - **←→** : ±1 seconde
  - **ENTRÉE** : Sauvegarder le clip

### 📊 Exports

#### JSON
Sauvegarde complète de toutes les annotations avec horodatage.

#### CSV (Excel)
Export des statistiques pour analyse dans Excel :
- Délimiteur : point-virgule (`;`)
- Encodage : UTF-8 avec BOM

#### HTML
Rapport visuel complet avec :
- **Graphiques interactifs** (Chart.js)
  - Distribution des types de points (camembert)
  - Statistiques par joueur (barres)
  - Évolution temporelle (ligne)
- **Analyse chronologique** : 5 tranches de 20% du match
- **Statistiques détaillées** pour chaque joueur
- **Design moderne** avec animations CSS

### 📁 Structure des données

```
data/
├── autosaves/          # Sauvegardes automatiques
├── backups/            # Backups des annotations
├── clips/              # Clips vidéo extraits
├── images/             # Captures d'écran (10 frames/point)
│   ├── point_001/
│   │   ├── frame_01.png
│   │   ├── frame_02.png
│   │   └── ...
│   └── point_002/
├── exports/            # Exports JSON/CSV
└── reports/            # Rapports HTML
```

### 🔄 Restauration de session

L'application détecte automatiquement les sessions précédentes au démarrage.
Vous pouvez reprendre l'analyse exactement où vous vous êtes arrêté.

## 🎯 Points gagnants (5 types)

Lors de l'annotation d'un point gagnant (**P**), sélectionnez le type de coup :
1. **Volée coup droit**
2. **Volée revers**
3. **Smash**
4. **Amorti**
5. **Fond de court**

## 🛠️ Création d'un exécutable

### Méthode simple (Windows)

Double-cliquez sur `BUILD.bat` pour créer automatiquement l'exécutable.

### Méthode manuelle

```bash
# Installer PyInstaller
pip install pyinstaller

# S'assurer que FFmpeg est téléchargé
python download_ffmpeg.py

# Créer l'exécutable
pyinstaller PFPADEL.spec
```

L'exécutable sera dans `dist/PFPADEL_VideoStats.exe` (~150 MB avec FFmpeg embarqué).

### Distribution

L'exécutable est **totalement autonome** et inclut :
- Python et toutes les bibliothèques
- FFmpeg pour le découpage vidéo
- Tous les fichiers de configuration

L'utilisateur final n'a besoin que de :
- **VLC Media Player** (gratuit) : https://www.videolan.org/

### Lancement rapide (développement)

Double-cliquez sur `PFPADEL.bat` pour lancer avec vérification automatique des dépendances.

## 📦 Dépendances

- **python-vlc** 3.0.20123 : Lecture vidéo avec son
- **opencv-python** 4.9.0.80 : Capture d'images précise
- **Pillow** 10.2.0 : Traitement d'images
- **NumPy** 1.26.4 : Calculs numériques
- **tkinter** : Interface graphique (inclus avec Python)
- **FFmpeg** : Découpage vidéo (téléchargement automatique)

## 📁 Structure du projet

```
PFPADEL/
├── app/
│   ├── ui/                 # Interface graphique Tkinter
│   ├── video/              # Gestion vidéo (VLC + OpenCV + FFmpeg)
│   ├── annotations/        # Système d'annotations avec autosave
│   ├── exports/            # Exports JSON/CSV/HTML
│   └── config/
│       ├── players.json           # Configuration joueurs
│       └── player_templates.json  # Templates joueurs
├── data/
│   ├── autosaves/          # Sauvegardes auto
│   ├── backups/            # Backups annotations
│   ├── clips/              # Clips vidéo extraits
│   ├── images/             # 10 frames par point
│   ├── exports/            # JSON/CSV
│   └── reports/            # Rapports HTML
├── ffmpeg/                 # FFmpeg embarqué (auto-téléchargé)
├── download_ffmpeg.py      # Script téléchargement FFmpeg
├── main.py                 # Point d'entrée
└── requirements.txt        # Dépendances Python
```

## 🎨 Interface

- **Thème moderne** : Dégradé violet/bleu (#667eea → #764ba2)
- **Overlay vidéo** : Affichage du nombre de points et dernier point
- **Marqueurs de progression** : Visualisation des points sur la barre de temps
- **Animations fluides** : Transitions CSS pour une expérience agréable

## 🐛 Dépannage

### FFmpeg introuvable
- Vérifiez que `ffmpeg/ffmpeg.exe` existe
- Relancez `python download_ffmpeg.py`
- Téléchargez manuellement et placez dans `ffmpeg/`

### VLC non trouvé
- Installez VLC Media Player : https://www.videolan.org/
- Redémarrez l'application

### Vidéo sans son
- Vérifiez que VLC est correctement installé
- Le son est géré par VLC, pas OpenCV

## 👨‍💻 Auteur

Développé pour NanoApp Stat - Analyse professionnelle de matchs de padel - 2025
