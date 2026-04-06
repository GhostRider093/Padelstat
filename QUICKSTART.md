# 🚀 Guide de Démarrage Rapide - PFPADEL Video Stats

## Installation Express (Windows)

### 1️⃣ Prérequis (5 minutes)

**Python 3.10+**
- Télécharger : https://www.python.org/downloads/
- ✅ Cocher "Add Python to PATH" lors de l'installation

**VLC Media Player**
- Télécharger : https://www.videolan.org/
- Installation standard

### 2️⃣ Lancement (1 clic)

Double-cliquez sur : **`PFPADEL.bat`**

Le script va automatiquement :
- ✅ Vérifier Python
- ✅ Installer les dépendances
- ✅ Télécharger FFmpeg (~90 MB)
- ✅ Lancer l'application

---

## Premier Match (10 minutes)

### Étape 1 : Charger la vidéo
1. Cliquez sur **📁 Charger Vidéo**
2. Sélectionnez votre fichier MP4/AVI/MOV

### Étape 2 : Configurer les joueurs
Dans le panneau de droite, entrez les noms :
- **Équipe 1** : Joueur 1, Joueur 2
- **Équipe 2** : Joueur 3, Joueur 4

### Étape 3 : Analyser les points

**Workflow ultra-rapide** :
```
Regardez la vidéo → Point marqué → ESPACE
        ↓
Menu apparaît → F/P/E (type)
        ↓
Sélection joueur → 1/2/3/4
        ↓
Validation → ENTRÉE
        ↓
10 images capturées automatiquement ✨
```

### Étape 4 : Exporter les résultats

En fin de match :
1. **📊 Exporter CSV** → Pour Excel
2. **📈 Générer Rapport HTML** → Rapport visuel avec graphiques

---

## ⌨️ Raccourcis Essentiels

### Navigation
| Touche | Action |
|--------|--------|
| **ESPACE** | ⏸️ Pause + Annoter |
| **→** | ⏩ +2 secondes |
| **←** | ⏪ -2 secondes |
| **↑** | ⏩ +10 secondes |
| **↓** | ⏪ -10 secondes |

### Annotation
| Touche | Action |
|--------|--------|
| **F** | 🔴 Faute directe |
| **P** | 🟢 Point gagnant |
| **E** | 🟡 Faute provoquée |
| **1-4** | 👤 Joueur 1 à 4 |
| **ENTRÉE** | ✅ Valider |

### Actions Rapides
| Touche | Action |
|--------|--------|
| **R** | ↩️ Annuler dernier point |
| **S** | 💾 Sauvegarde rapide |
| **H** | ❓ Afficher l'aide |
| **N** | ➡️ Point suivant |
| **B** | ⬅️ Point précédent |

---

## 🎯 Types de Points Gagnants

Quand vous tapez **P** (Point gagnant), choisissez le coup :

| Numéro | Type de Coup |
|--------|-------------|
| **1** | 🎾 Volée coup droit |
| **2** | 🎾 Volée revers |
| **3** | 💥 Smash |
| **4** | 🪶 Amorti |
| **5** | 🏃 Fond de court |

---

## 📊 Exports

### JSON
- **Quand ?** Sauvegarde brute de toutes les données
- **Utilisé pour ?** Backup, import dans d'autres outils
- **Localisation** : `data/exports/match_YYYYMMDD_HHMMSS.json`

### CSV
- **Quand ?** Analyse Excel, tableurs
- **Format** : Délimiteur `;` pour Excel français
- **Localisation** : `data/exports/stats_YYYYMMDD_HHMMSS.csv`

### HTML
- **Quand ?** Rapport visuel avec graphiques
- **Contenu** : 
  - 📊 3 graphiques interactifs (Chart.js)
  - 📈 Analyse chronologique (5 tranches)
  - 👤 Stats détaillées par joueur
- **Localisation** : `data/reports/rapport_YYYYMMDD_HHMMSS.html`

---

## 🎬 Extraire des Clips

1. Positionnez la vidéo au début de la séquence
2. Cliquez sur **🎥 Sauvegarder Clip**
3. Naviguez avec le clavier :
   - **↑** : Ajuster début
   - **↓** : Ajuster fin
   - **←→** : ±1 seconde
4. **ENTRÉE** pour sauvegarder

Le clip est enregistré dans : `data/clips/`

---

## 💡 Astuces Pro

### 🔥 Workflow optimal
1. **Première passe** : Annotez TOUS les points rapidement
2. **Deuxième passe** : Vérifiez avec **N/B** (suivant/précédent)
3. **Export** : CSV + HTML pour analyse complète

### 📸 Captures automatiques
Les 10 frames avant chaque point sont dans :
```
data/images/point_001/
    ├── frame_01.png  (10 images avant)
    ├── frame_02.png
    └── ...
    └── frame_10.png  (moment du point)
```

### 💾 Autosave
L'application sauvegarde automatiquement après chaque point.
Si crash → Relancez, vos données sont protégées ! ✨

### 🔄 Reprendre une session
Au démarrage, l'application détecte automatiquement vos sessions précédentes.
Cliquez **Oui** pour reprendre là où vous vous êtes arrêté.

---

## ❓ Problèmes Courants

### La vidéo ne se charge pas
- ✅ Vérifiez que VLC est installé
- ✅ Format supporté : MP4, AVI, MOV, MKV
- ✅ Relancez l'application

### Pas de son
- ✅ VLC doit être installé (le son passe par VLC)
- ✅ Vérifiez le volume système

### FFmpeg introuvable
- ✅ Relancez : `python download_ffmpeg.py`
- ✅ Téléchargement manuel : https://www.gyan.dev/ffmpeg/builds/
- ✅ Placer `ffmpeg.exe` dans le dossier `ffmpeg/`

### Erreur Python
- ✅ Version Python >= 3.10 ?
- ✅ Réinstallez les dépendances : `pip install -r requirements.txt`

---

## 🏆 Vous êtes Prêt !

**Workflow complet en 3 clics** :
1. Double-clic sur `PFPADEL.bat`
2. Chargez votre vidéo
3. **ESPACE** → Annotez → **ENTRÉE**

**Bon match ! 🎾**

---

*Pour plus d'infos : Consultez le `README.md` complet*
