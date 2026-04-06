# Documentation : Rapports HTML

## 📊 Vue d'ensemble

L'application génère **deux types de rapports HTML** distincts :

---

## 1️⃣ Live Analysis (Analyse en Temps Réel)

### Caractéristiques
- **Fichier généré** : `data/live_analysis.html`
- **Source de données** : Mémoire (`annotation_manager.export_to_dict()`) - **Données en temps réel**
- **Rafraîchissement** : Automatique toutes les 5 secondes
- **Analyse IA** : Déclenchée toutes les 3 points
- **Captures vidéo** : Non
- **Vitesse** : ⚡ Instantané (pas de lecture de fichier)

### Générateur
- **Code** : `app/exports/live_html_generator.py`
- **Classe** : `LiveHTMLGenerator`
- **Méthode** : `generate_html(match_data, force_analyze=False)`

### Flux de données
```
annotation_manager (données en mémoire)
    ↓
annotation_manager.export_to_dict()
    ↓
LiveHTMLGenerator.generate_html(match_data)
    ↓
data/live_analysis.html (auto-refresh 5s)
```

### Utilisation
- S'ouvre automatiquement dans le navigateur
- Se met à jour automatiquement pendant l'annotation
- Affiche l'analyse IA évolutive (historique de 10 conversations max)
- **Utilise les mêmes données que le Rapport Rapide (mémoire directe)**

### Fichiers JSON utilisés
1. **Aucun fichier autosave** - Données en mémoire directement
2. **Historique IA** : `data/ai_history.json`

---

## 2️⃣ Rapport HTML (Générateur Traditionnel)

Ce générateur produit **deux types de rapports** selon le mode :

### A. Rapport Rapide (Fast Mode)
- **Fichier généré** : `data/rapport_YYYYMMDD_HHMMSS.html`
- **Fichier source** : **AUCUN** - utilise les données en mémoire (`annotation_manager.export_to_dict()`)
- **Rafraîchissement** : Généré sur demande uniquement
- **Analyse IA** : Non (rapport statique)
- **Captures vidéo** : ❌ Non (mode rapide)
- **Temps de génération** : ~1-2 secondes

### B. Rapport Complet (Full Mode)
- **Fichier généré** : `data/rapport_YYYYMMDD_HHMMSS.html`
- **Fichier source** : **AUCUN** - utilise les données en mémoire (`annotation_manager.export_to_dict()`)
- **Rafraîchissement** : Généré sur demande uniquement
- **Analyse IA** : Non (rapport statique)
- **Captures vidéo** : ✅ Oui (6 frames par défaut, configurable)
- **Temps de génération** : Variable selon le nombre de points (peut être long)

### Générateur
- **Code** : `app/exports/html_generator.py`
- **Classe** : `HTMLGenerator`
- **Méthode** : `generate_report(annotation_manager, output_path=None, video_player=None, fast_mode=False, num_frames=6)`

### Flux de données
```
annotation_manager (données en mémoire)
    ↓
annotation_manager.export_to_dict()
    ↓
HTMLGenerator.generate_report(fast_mode=True/False)
    ↓
data/rapport_YYYYMMDD_HHMMSS.html
```

### Fichiers JSON utilisés
**AUCUN** - Les rapports HTML ne lisent pas de fichier JSON. Ils accèdent directement aux données en mémoire via `annotation_manager.export_to_dict()`.

---

## 🔄 Comparaison

| Caractéristique | Live Analysis | Rapport Rapide | Rapport Complet |
|----------------|---------------|----------------|-----------------|
| **Fichier généré** | `data/live_analysis.html` | `data/rapport_YYYYMMDD_HHMMSS.html` | `data/rapport_YYYYMMDD_HHMMSS.html` |
| **Source de données** | Mémoire (`annotation_manager`) | Mémoire (`annotation_manager`) | Mémoire (`annotation_manager`) |
| **Lit un JSON ?** | ❌ Non (mémoire directe) | ❌ Non (mémoire directe) | ❌ Non (mémoire directe) |
| **Auto-refresh** | ✅ Oui (5s) | ❌ Non (statique) | ❌ Non (statique) |
| **Analyse IA** | ✅ Oui (évolutive) | ❌ Non | ❌ Non |
| **Captures vidéo** | ❌ Non | ❌ Non | ✅ Oui (6 frames/point) |
| **Génération** | Automatique (chaque point) | Sur demande (menu) | Sur demande (menu) |
| **Vitesse** | Instantané | ~1-2s | Variable (lent si beaucoup de points) |
| **Taille** | Léger (~50-100KB) | Moyen (~200-500KB) | Lourd (~1-5MB avec captures) |
| **Usage** | Suivi en temps réel | Archive rapide | Archive finale avec images |

---

## 📂 Structure des fichiers

```
data/ (auto-save continu)
├── match_20251218_071907.json                          ← Match final exporté (via menu "Export JSON")
├── ai_history.json                                      ← Historique IA (Live Analysis uniquement)
├── live_analysis.html                                   ← Live Analysis (rafraîchi auto toutes les 5s)
└── rapport_20251218_123456.html                        ← Rapport HTML (rapide ou complet)
```

### Origine des fichiers

**Fichiers autosave** (`autosave_*.json`) :
- Créés automatiquement pendant l'annotation
- Sauvegarde continue toutes les 30 secondes
- Format : `autosave_<nom_video>_<timestamp>.json`
- Utilisés pour : Récupération après crash, rechargement de session
- **Ne sont PLUS utilisés par le Live Analysis** (qui utilise les données en mémoire)
- Supprimés automatiquement lors du chargement d'une nouvelle vidéo

**Fichiers match finaux** (`match_*.json`) :
- Créés manuellement via menu **"Fichier > Exporter en JSON"**
- Code : `app/exports/json_exporter.py` ligne 28
- Format : `match_<timestamp>.json`
- Contenu : Rapide
```python
# app/ui/main_window.py ligne 3222-3228
def generate_html_fast(self):
    filepath = self.html_generator.generate_report(
        self.annotation_manager,  # Données en mémoire
        video_player=self.video_player,
        fast_mode=True  # Pas de captures vidéo
    )
```

### Rapport Complet
```python
# app/ui/main_window.py ligne 3240-3253
def generate_html_full(self):
    filepath = self.html_generator.generate_report(
        self.annotation_manager,  # Données en mémoire
        video_player=self.video_player,
        fast_mode=False,  # Avec captures vidéo
        num_frames=6
    )
```

### Export JSON (création de match_*.json)
```python
# app/exports/json_exporter.py ligne 28-31
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(
    annotation_manager.data_folder,
    f"match_{timestamp}.json"  # ← Fichier match_20251218_071907.json

---

## 🔧 Appels dans le code

### Live Analysis
```python
# app/ui/main_window.py ligne ~3440-3458
def toggle_ollama_live(self):
    from app.exports.live_html_generator import generate_live_report
    match_data = self.annotation_manager.export_to_dict()  # Données en mémoire
    generate_live_report(match_data, force_analyze=True)
```

### Rapport Complet
```python
# app/ui/main_window.py ligne 3208-3214
def generate_html(self):
    filepath = self.html_generator.generate_report(
        self.annotation_manager,  # Données en mémoire
        video_player=self.video_player,
        fast_mode=False,
        num_frames=6
    )
```

---

## ⚠️ Points d'attention

### Live Analysis
- ⚡ **Données instantanées** : Utilise `annotation_manager.export_to_dict()` comme le rapport rapide
- 🔄 **Pas de délai** : Plus besoin d'attendre l'autosave (30s), les données sont en temps réel
- 🤖 Nécessite Ollama pour l'analyse IA
- 📊 Historique IA limité à 10 conversations (économie de tokens)

### Rapport Complet
- 🎥 Génération des captures peut être lente (mode normal)
- 💾 Utiliser `fast_mode=True` pour génération instantanée
- 📦 Fichier HTML volumineux avec captures intégrées en base64

---

## 🐛 Bugs connus

### Live Analysis - Analyse IA
**Problème** : Les fautes provoquées/subies/impact manquent dans le commentaire IA

**Cause** : Incohérence de noms de champs dans `ollama_chat.py` ligne 221-224
- Le code cherche : `fautes_provoquees_subies`, `defenseur`, `generees`, `attaquant`
- Les stats calculent : `fautes_provoquees`, `fautes_subies`

**Solution** : Corriger `format_match_context()` dans [ollama_chat.py](ollama_chat.py#L221-L224)

---

## 📝 Remarques

- Le **Live Analysis** est idéal pour suivre le match en direct
- Le **Rapport Complet** est idéal pour l'archivage et l'analyse post-match
- Les deux rapports utilisent les mêmes statistiques de base (calculs identiques)
- Seul le Live Analysis bénéficie de l'analyse IA évolutive
