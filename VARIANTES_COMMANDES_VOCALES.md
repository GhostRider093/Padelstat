# 📋 VARIANTES DES COMMANDES VOCALES - PADEL STAT

**Date de collecte** : 23 décembre 2025  
**Nombre de tests** : 58 transcriptions réelles  
**Méthode** : Google Speech Recognition (fr-FR)

---

## 🎯 STRUCTURE DES COMMANDES

### Format attendu (normalisé)
```
[CATÉGORIE] [JOUEUR] [TYPE_COUP]
```

**Catégories** :
- `point` 
- `faute`
- `faute provoquée [provoquant] [subit] [type_coup]`

**Joueurs** :
- `joueur1`
- `joueur2`

**Types de coups** :
- `service`
- `volée coup droit`
- `volée revers`
- `volée balle haute`
- `fond de court coup droit`
- `fond de court revers`
- `fond de court balle haute`
- `lob`

---

## 📊 VARIANTES DÉTECTÉES

### 1️⃣ CATÉGORIE : POINT

**Commande attendue** : `point`

**Variantes reconnues** :
- ✅ `point` (correct)

---

### 2️⃣ CATÉGORIE : FAUTE

**Commande attendue** : `faute`

**Variantes reconnues** :
- ✅ `faute` (correct)
- ⚠️ `faut`
- ⚠️ `foot`
- ⚠️ `Ford`
- ⚠️ `photos`

---

### 3️⃣ CATÉGORIE : FAUTE PROVOQUÉE

**Commande attendue** : `faute provoquée`

**Variantes reconnues** :
- ✅ `faute provoquée` (correct)
- ⚠️ `faute provoquer`
- ⚠️ `faut provoquer`
- ⚠️ `faut te provoquer`
- ⚠️ `foot pro ok`
- ⚠️ `phoque provoquer`

---

### 4️⃣ JOUEUR 1

**Commande attendue** : `joueur1`

**Variantes reconnues** :
- ✅ `joueur1` (correct - rare)
- ⚠️ `joueur 1` (le plus fréquent)
- ⚠️ `joueur un`
- ⚠️ `jour 1`
- ⚠️ `jour un`
- ⚠️ `jours 1`
- ⚠️ `joue un`
- ⚠️ `genre un`

---

### 5️⃣ JOUEUR 2

**Commande attendue** : `joueur2`

**Variantes reconnues** :
- ✅ `joueur2` (correct - rare)
- ⚠️ `joueur 2` (le plus fréquent)
- ⚠️ `joueur deux`
- ⚠️ `joueur de` (très fréquent !)
- ⚠️ `joueurs de`

---

### 6️⃣ TYPE DE COUP : SERVICE

**Commande attendue** : `service`

**Variantes reconnues** :
- ✅ `service` (correct)
- ⚠️ `services` (fréquent)

---

### 7️⃣ TYPE DE COUP : VOLÉE

**Commande attendue** : `volée`

**Variantes reconnues** :
- ✅ `volée` (correct - rare)
- ⚠️ `volley` (très fréquent)
- ⚠️ `volets` (très fréquent !)
- ⚠️ `volet`
- ⚠️ `volleys`
- ⚠️ `vollée`
- ⚠️ `volé`

---

### 8️⃣ TYPE DE COUP : COUP DROIT

**Commande attendue** : `coup droit`

**Variantes reconnues** :
- ✅ `coup droit` (correct)
- ⚠️ `coup` (isolé)
- ⚠️ `coudra`
- ⚠️ `coups droits`

---

### 9️⃣ TYPE DE COUP : REVERS

**Commande attendue** : `revers`

**Variantes reconnues** :
- ✅ `revers` (correct - rare)
- ⚠️ `rêveur` (fréquent !)
- ⚠️ `rêve`
- ⚠️ `Rover` (très fréquent dans "Franco Rover" pour "fond de court revers")
- ⚠️ `reverre`
- ⚠️ `reverts`

---

### 🔟 TYPE DE COUP : BALLE HAUTE

**Commande attendue** : `balle haute`

**Variantes reconnues** :
- ✅ `balle haute` (correct - rare)
- ⚠️ `ball au` (fréquent)
- ⚠️ `balle au`
- ⚠️ `ball hot`
- ⚠️ `ballotte` (très fréquent !)
- ⚠️ `volley-ball hot` (pour "volée balle haute")
- ⚠️ `volley-ball`
- ⚠️ `balles hautes`

---

### 1️⃣1️⃣ TYPE DE COUP : FOND DE COURT

**Commande attendue** : `fond de court`

**Variantes reconnues** :
- ✅ `fond de court` (correct)
- ⚠️ `fond de cour` (très fréquent)
- ⚠️ `fond de cours`
- ⚠️ `fin de cours` (fréquent !)
- ⚠️ `fond de courbe` (fréquent)
- ⚠️ `fond de Courbevoie` (!!)
- ⚠️ `fond de couverts`
- ⚠️ `Franco Rover` (pour "fond de court revers" !)
- ⚠️ `Francos Rover`

---

### 1️⃣2️⃣ TYPE DE COUP : LOB

**Commande attendue** : `lob`

**Variantes reconnues** :
- ✅ `lob` (correct - rare)
- ⚠️ `lobes` (fréquent)
- ⚠️ `lobs`
- ⚠️ `l'Aube` (fréquent !)
- ⚠️ `de l'Aube`
- ⚠️ `lots`

---

## 🎤 EXEMPLES DE TRANSCRIPTIONS RÉELLES

### ✅ Bien reconnus (après normalisation)

| Transcription originale | Normalisé | Commande valide |
|-------------------------|-----------|-----------------|
| `point joueur 1 services` | `point joueur1 service` | ✅ |
| `faute provoquer joueur un joueur 2` | `faute provoquée joueur1 joueur2` | ✅ (partiel) |
| `point joueur 1 lobes` | `point joueur1 lob` | ✅ |

### ⚠️ Partiellement reconnus (nécessitent amélioration)

| Transcription originale | Normalisé | Problème |
|-------------------------|-----------|----------|
| `point jour 1 volets coup droit` | `point jour 1 volée coup droit` | ❌ `jour 1` non corrigé |
| `point joueur de volley` | `point joueur2 volée` | ⚠️ Manque type de volée |
| `foot joueur de volley coup droit` | `point joueur2 volée coup droit` | ✅ Après correction |

### ❌ Mal reconnus (problèmes majeurs)

| Transcription originale | Normalisé | Problème |
|-------------------------|-----------|----------|
| `point genre` | `point genre` | ❌ `genre` non reconnu |
| `faut toujours un volet` | `faute joueur1 volée` | ⚠️ Contexte difficile |
| `Franco Rover` | `fond de court revers` | ⚠️ Nécessite normalisation spécifique |

---

## 🔧 RÈGLES DE NORMALISATION APPLIQUÉES

```python
# CATÉGORIES
'foot' → 'point'
'Ford' → 'point'
'photos' → 'point'
'faut' → 'faute'
'phoque' → 'faute'
'faut provoquer' → 'faute provoquée'
'faut te provoquer' → 'faute provoquée'
'faute provoquer' → 'faute provoquée'
'foot pro ok' → 'faute provoquée'

# JOUEURS
'joueur 1' → 'joueur1'
'joueur un' → 'joueur1'
'jour 1' → 'joueur1'
'jour un' → 'joueur1'
'jours 1' → 'joueur1'
'joue un' → 'joueur1'
'genre un' → 'joueur1'
'joueur de' → 'joueur2'
'joueurs de' → 'joueur2'
'joueur à un' → 'joueur2'

# TYPES DE COUPS
'services' → 'service'
'volley' → 'volée'
'volets' → 'volée'
'volet' → 'volée'
'volleys' → 'volée'
'lobes' → 'lob'
'lobs' → 'lob'
"l'Aube" → 'lob'
"de l'Aube" → 'lob'
'lots' → 'lob'
'rêveur' → 'revers'
'rêve' → 'revers'
'Rover' → 'revers'
'Franco Rover' → 'fond de court revers'
'Francos Rover' → 'fond de court revers'
'ball au' → 'balle haute'
'balle au' → 'balle haute'
'ball hot' → 'balle haute'
'ballotte' → 'balle haute'
'volley-ball hot' → 'volée balle haute'
'fond de cour' → 'fond de court'
'fond de cours' → 'fond de court'
'fin de cours' → 'fond de court'
'fond de courbe' → 'fond de court'
'fond de Courbevoie' → 'fond de court'
'fond de couverts' → 'fond de court'
'coudra' → 'coup droit'
```

---

## 📈 STATISTIQUES

**Reconnaissance Google Speech** :
- Total : 58 tests
- Échecs complets : 2 (impossibles à comprendre)
- Succès partiel : ~50 (nécessitent normalisation)
- Succès direct : ~6 seulement

**Taux de réussite après normalisation** : ~86% (50/58)

**Problèmes principaux** :
1. 🔴 **"joueur 2"** transcrit comme **"joueur de"** (95% des cas)
2. 🔴 **"volée"** transcrit comme **"volet"** ou **"volley"** (80% des cas)
3. 🔴 **"lob"** transcrit comme **"l'Aube"** ou **"lots"** (70% des cas)
4. 🟡 **"fond de court"** transcrit comme **"fond de courbe"** (50% des cas)
5. 🟡 **"revers"** transcrit comme **"rêveur"** ou **"Rover"** (60% des cas)

---

## ✅ RECOMMANDATIONS

1. **Entraîner les utilisateurs** à prononcer clairement :
   - "joueur DEUX" (pas "joueur de")
   - "vo-LÉE" (avec accent)
   - "LOB" (court et sec)

2. **Améliorer la normalisation** pour les cas problématiques :
   - Contexte grammatical (ex: "joueur de" suivi d'un type de coup → "joueur2")
   - Expressions composées (ex: "Franco Rover" → "fond de court revers")

3. **Ajouter un feedback audio** pour confirmer la commande comprise

4. **Mode correction** : permettre à l'utilisateur de répéter si mal compris

---

**📝 Document généré automatiquement le 23 décembre 2025**  
**📊 Basé sur 58 transcriptions réelles en conditions d'utilisation**
