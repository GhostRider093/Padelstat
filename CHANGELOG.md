# Changelog - PFPADEL Video Stats

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

## [1.0.0] - 2025-12-04

### ✨ Fonctionnalités principales

#### 🎥 Lecture vidéo
- Lecteur vidéo hybride VLC (son) + OpenCV (précision)
- Contrôles: Play/Pause, vitesse (0.25x à 2x), plein écran
- Barre de progression avec aperçu du temps
- Navigation précise: ±2s, ±10s

#### ⌨️ Workflow 100% clavier
- **ESPACE** : Pause et annotation
- **F/P/E** : Types de points (Faute/Point gagnant/Faute provoquée)
- **1-4** : Sélection joueur
- **ENTRÉE** : Validation
- **→←↑↓** : Navigation temporelle
- **R** : Supprimer dernier point
- **S** : Sauvegarde rapide
- **H** : Aide
- **N/B** : Point suivant/précédent

#### 📸 Capture automatique
- 10 frames capturées avant chaque point
- Organisation en dossiers `point_XXX/`
- Format PNG haute qualité

#### 📊 Exports multiples
- **JSON** : Données complètes avec timestamps
- **CSV** : Format Excel (délimiteur `;`, UTF-8 BOM)
- **HTML** : Rapport interactif avec Chart.js
  - Graphique camembert (types de points)
  - Graphique barres (stats par joueur)
  - Graphique ligne (évolution temporelle)
  - Analyse chronologique (5 tranches de 20%)

#### 🎬 Clips vidéo
- Extraction de segments avec FFmpeg
- Navigation clavier dans le sélecteur (↑↓←→)
- Sauvegarde rapide sans réencodage
- Clips stockés dans `data/clips/`

#### 💾 Gestion de session
- Autosave après chaque annotation
- Backups automatiques (rotation)
- Restauration automatique au démarrage
- Détection de sessions précédentes

#### 🎨 Interface moderne
- Thème violet/bleu (#667eea → #764ba2)
- Overlay stats sur vidéo (nombre points, dernier point)
- Marqueurs colorés sur barre de progression
- Animations CSS fluides

#### 🔧 Installation simplifiée
- **FFmpeg** téléchargé automatiquement au premier lancement
- Script `download_ffmpeg.py` pour téléchargement manuel
- Lanceur Windows `PFPADEL.bat` avec vérifications
- Builder `BUILD.bat` pour créer l'exécutable

### 📦 Points gagnants détaillés
1. Volée coup droit
2. Volée revers
3. Smash
4. Amorti
5. Fond de court

### 🛠️ Technologies
- Python 3.10+
- python-vlc 3.0.20123
- opencv-python 4.9.0.80
- Pillow 10.2.0
- NumPy 1.26.4
- FFmpeg (auto-téléchargé)
- Chart.js 4.4.0 (CDN)

### 🎯 Architecture
- VLC : Lecture vidéo avec son
- OpenCV : Capture précise de frames
- FFmpeg : Découpage vidéo sans perte
- Tkinter : Interface graphique moderne
- JSON : Stockage avec autosave
- HTML/CSS/JS : Rapports interactifs

---

## Roadmap future

### [1.1.0] - À venir
- [ ] Intégration clips dans rapports HTML
- [ ] Templates de joueurs pré-configurés
- [ ] Mode quick analysis (annotation ultra-rapide)
- [ ] Export vers plateformes de stats (Padel Manager, etc.)
- [ ] Statistiques avancées (trajectoires, zones)
- [ ] Support multi-langues (FR/EN/ES)

### [1.2.0] - En réflexion
- [ ] Analyse IA automatique (détection points)
- [ ] Heatmaps de position
- [ ] Comparaison de matchs
- [ ] API REST pour intégration externe
- [ ] Mode cloud (sync multi-appareils)

---

**Auteur** : PFPADEL Team  
**License** : Propriétaire  
**Contact** : [email protected]
