# 💾 Système de sauvegarde automatique

## 🔄 Autosave - Protection contre la perte de données

PFPADEL Video Stats intègre un **système de sauvegarde automatique** qui protège vos annotations contre toute perte de données.

---

## ✅ Fonctionnement automatique

### 📝 Sauvegarde après chaque action

Le système sauvegarde **automatiquement** après :
- ✓ Chaque faute directe enregistrée
- ✓ Chaque point gagnant annoté
- ✓ Chaque faute provoquée ajoutée
- ✓ Chaque suppression d'annotation

**Vous n'avez rien à faire**, tout est automatique !

---

## 📂 Structure des fichiers

### Fichiers créés

```
data/
├── autosave_match1_20251204_153045.json    # Autosave actif
├── match1_final.json                        # Export manuel
├── rapport_match1.html                      # Rapport HTML
├── backups/
│   ├── autosave_match1_20251204_153045.json # Backup 1
│   ├── autosave_match1_20251204_154012.json # Backup 2
│   └── autosave_match1_20251204_155203.json # Backup 3
└── screens/
    ├── point_001.png
    ├── point_002.png
    └── ...
```

### Nomenclature

**Format d'autosave** : `autosave_{nom_vidéo}_{date}_{heure}.json`

Exemple : `autosave_match_final_20251204_153045.json`
- `match_final` = nom de la vidéo (sans extension)
- `20251204` = date (AAAAMMJJ)
- `153045` = heure (HHMMSS)

---

## 🔄 Backups multiples

### Protection renforcée

À chaque sauvegarde automatique :
1. L'ancien autosave est **copié** dans `data/backups/`
2. Le nouveau autosave **remplace** l'ancien dans `data/`

**Résultat** : Vous conservez **TOUTES** les versions précédentes !

### Exemple de progression

```
14h30 : 5 points annotés  → autosave_v1.json
14h35 : 10 points         → autosave_v2.json (v1 → backup)
14h40 : 15 points         → autosave_v3.json (v2 → backup)
```

**Si problème** : Vous pouvez récupérer n'importe quelle version !

---

## 📖 Restauration automatique

### Détection intelligente

Quand vous chargez une vidéo, le système :
1. ✅ Détecte automatiquement s'il existe un autosave pour cette vidéo
2. 📋 Affiche le fichier le plus récent
3. ❓ Vous demande si vous voulez le charger

### Dialog de restauration

```
┌─────────────────────────────────────┐
│      Autosave détecté               │
├─────────────────────────────────────┤
│ Un autosave existe pour cette vidéo │
│                                     │
│ Fichier: autosave_match1_...json   │
│ Date: 04/12/2025 15:30:45          │
│                                     │
│ Voulez-vous charger cet autosave ?  │
│                                     │
│     [Oui]           [Non]           │
└─────────────────────────────────────┘
```

**Choisissez** :
- `Oui` → Reprend là où vous étiez
- `Non` → Démarre une nouvelle session

---

## 🔧 Chargement manuel

### Bouton "📂 Charger Autosave"

Situé dans le panneau de droite, ce bouton permet de :
- 📂 Parcourir tous les autosaves et backups
- 🔍 Voir la date de chaque fichier
- ✅ Charger n'importe quelle version

### Procédure

1. Cliquez sur `📂 Charger Autosave`
2. Naviguez dans `data/` ou `data/backups/`
3. Sélectionnez le fichier JSON souhaité
4. Validez

**Résultat** : Toutes les annotations sont restaurées !

### Informations affichées

```
┌─────────────────────────────────────┐
│      Autosave chargé                │
├─────────────────────────────────────┤
│ ✓ Données restaurées avec succès!  │
│                                     │
│ Vidéo: match_final.mp4              │
│ Points: 23                          │
│ Joueurs: J1, J2, J3, J4             │
│                                     │
│               [OK]                  │
└─────────────────────────────────────┘
```

---

## 💡 Cas d'usage

### Scénario 1 : Crash inattendu

**Problème** : L'application plante après 30 points annotés

**Solution** :
1. Relancez l'application
2. Chargez la vidéo
3. Acceptez l'autosave détecté
4. ✅ Vos 30 points sont restaurés !

---

### Scénario 2 : Erreur d'annotation

**Problème** : Vous avez supprimé 5 points par erreur

**Solution** :
1. Cliquez sur `📂 Charger Autosave`
2. Naviguez dans `data/backups/`
3. Chargez un backup d'il y a 5 minutes
4. ✅ Points restaurés !

---

### Scénario 3 : Plusieurs sessions

**Situation** : Vous annotez en 3 sessions (matin/après-midi/soir)

**Autosaves créés** :
- `autosave_match1_20251204_093000.json` (matin)
- `autosave_match1_20251204_143000.json` (après-midi)
- `autosave_match1_20251204_203000.json` (soir)

**Avantage** : Vous pouvez revenir à n'importe quelle session !

---

## 📊 Export final

### Différence autosave vs export

| Autosave | Export manuel |
|----------|---------------|
| Automatique | Sur demande |
| Nom technique | Nom personnalisable |
| Multiple versions | Un fichier final |
| Fichiers temporaires | Archive définitive |

### Workflow recommandé

1. **Pendant l'annotation** : L'autosave fonctionne automatiquement
2. **À la fin** : Exportez manuellement avec un nom explicite
   - `💾 Exporter JSON` → `match_finale_2025.json`
   - `📊 Générer Rapport` → `rapport_finale_2025.html`

---

## 🛡️ Sécurité des données

### Protection multi-niveaux

1. **Niveau 1** : Autosave actif dans `data/`
2. **Niveau 2** : Backups multiples dans `data/backups/`
3. **Niveau 3** : Export manuel final

**Résultat** : Perte de données quasi impossible ! 🔒

---

## ⚙️ Configuration technique

### Emplacement des fichiers

- **Autosaves actifs** : `data/autosave_*.json`
- **Backups** : `data/backups/autosave_*.json`
- **Exports** : `data/match_*.json` (nom personnalisé)
- **Rapports** : `data/rapport_*.html`

### Format JSON

Le format est identique pour :
- Autosaves
- Backups
- Exports manuels

Tous les fichiers sont **compatibles** et **interchangeables** !

---

## 🎯 Bonnes pratiques

### ✅ À faire

- Laissez l'autosave fonctionner automatiquement
- Exportez manuellement à la fin du match
- Conservez les backups importants
- Utilisez des noms de vidéo explicites

### ❌ À éviter

- Ne supprimez pas le dossier `data/backups/`
- N'éditez pas manuellement les JSON (risque de corruption)
- Ne renommez pas les autosaves (le système ne les retrouvera pas)

---

## 🚀 Résumé

**Avec PFPADEL Video Stats** :
- ✅ Sauvegarde automatique après chaque action
- ✅ Backups multiples conservés
- ✅ Restauration automatique détectée
- ✅ Chargement manuel possible
- ✅ Protection maximale contre la perte de données

**Travaillez en toute sérénité ! 🎾💾**
