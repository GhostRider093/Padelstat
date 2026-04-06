# 🎤 Commandes Vocales Complètes - NanoApp Stat Padel

## 📋 Vue d'ensemble

Ce document liste **TOUTES** les commandes vocales nécessaires pour remplacer entièrement le workflow clavier de l'application.

## ✅ Nouveau workflow recommandé (PTT)

Le système vocal principal est maintenant le **Push-to-Talk** :

- Activer avec le bouton **"🎤 ACTIVER VOCAL (V)"**
- **Appuyer sur `V`** → démarre l'enregistrement (timestamp capturé)
- Parler la commande
- **Rappuyer sur `V`** → stop → transcription → parsing → point ajouté si reconnu
- Chaque capture est enregistrée en **WAV** dans `data/voice_audio/` (utile pour revenir dessus)

Notes :
- En PTT, le mot de réveil **"OK" n'est pas requis** (tu peux dire directement "faute directe Arnaud").
- L'ancien mode "mains-libres" ("OK ...") est désactivé par défaut.

### 🟩 / 🟥 Reconnu vs non reconnu (important)

Après transcription + parsing, l’app affiche un **drapeau** dans le bandeau vocal :

- **🟩 STAT RECONNUE** = la commande est **valide** et un **point est ajoutable**.
- **🟥 STAT NON RECONNUE** = la commande est **incomplète** (champs manquants) ou hors format.

Règles actuelles (validation stricte) :

- **Faute directe** : `type de point` + `joueur` (**type de coup optionnel**)
    - Exemple PTT : `faute directe Pierre`
- **Point gagnant** : `type de point` + `joueur` + **`type de coup` obligatoire**
    - Exemple PTT : `point gagnant Pierre smash`
- **Faute provoquée** : `type de point` + `attaquant` + **`défenseur` obligatoire**
    - Exemple PTT : `faute provoquée Thomas service Lucas`

### 🌳 Bandeau vocal “en arbre” (lecture rapide)

Le bandeau affiche les champs compris sous forme hiérarchique, par exemple :

```
🟩 STAT RECONNUE
Stat: Faute directe
    ├─ Joueur: Pierre
    ├─ Défenseur: —
    ├─ Coup: —
    ├─ Zone: —
    ├─ Diagonale: —
    └─ Label: —
```

### 🔍 Review vocal (corriger les non reconnues)

Si une commande n’est pas reconnue, tu peux la rattraper :

1) Cliquer **"🔍 REVIEW VOCAL"**
2) Sélectionner une ligne **❌**
3) Utiliser :
     - **"▶️ Rejouer vidéo"** : saute au bon timestamp
     - **"🔊 Écouter audio (WAV)"** : rejoue l’audio enregistré
     - **"✏️ Corriger manuellement"** : retape/ajuste la commande, puis l’app valide et crée l’annotation
     - **"🗑️ Ignorer"** : supprime la commande de la liste

À noter : les enregistrements audio restent disponibles en WAV dans `data/voice_audio/`.

### 🟣 Marqueurs timeline (non reconnues)

La timeline affiche des **triangles violets** aux timestamps des commandes vocales **non reconnues** pour les repérer instantanément.

---

## 🎯 Types d'Annotations (3 catégories)

### 1. Point Gagnant (🏆)
### 2. Faute Directe (⚠️)
### 3. Faute Provoquée (🎯)

---

## 📝 Format des Commandes Vocales

### **Format Standard (ancien mains-libres “OK … OK”)**
```
OK [type] [joueur] [zone] [technique] [coup_final] OK
```

> Ce format correspond à l’ancien mode “mains-libres” (désactivé par défaut).

### **Format PTT (recommandé, sans “OK”)**

En PTT, tu peux dire les mêmes commandes **sans le mot OK** au début/à la fin.

Exemples :

- `faute directe Arnaud`
- `point gagnant Pierre smash`
- `faute provoquée Thomas service Lucas`

### **Format Simplifié pour Faute Directe (ancien mains-libres)**
```
OK faute directe [joueur] OK
```

---

## 🏆 1. POINT GAGNANT - Commandes Complètes

### **A. Service**
```
point gagnant [joueur] service
```

**Exemples :**
- `point gagnant Arnaud service`
- `point gagnant Pierre service`
- `point gagnant Thomas service`
- `point gagnant Lucas service`

---

### **B. Fond de Court**

#### B1. Fond de court Coup Droit
```
point gagnant [joueur] fond de court coup droit
```

**Exemples :**
- `point gagnant Arnaud fond de court coup droit`
- `point gagnant Pierre fond de court coup droit`
- `point gagnant Thomas fond de court coup droit`
- `point gagnant Lucas fond de court coup droit`

#### B2. Fond de court Revers
```
point gagnant [joueur] fond de court revers
```

**Exemples :**
- `point gagnant Arnaud fond de court revers`
- `point gagnant Pierre fond de court revers`
- `point gagnant Thomas fond de court revers`
- `point gagnant Lucas fond de court revers`

#### B3. Fond de court Balle Haute

##### B3.1. Fond de court Balle Haute Víbora
```
point gagnant [joueur] fond de court balle haute víbora
```

**Exemples :**
- `point gagnant Arnaud fond de court balle haute víbora`
- `point gagnant Pierre fond de court balle haute víbora`
- `point gagnant Thomas fond de court balle haute víbora`
- `point gagnant Lucas fond de court balle haute víbora`

##### B3.2. Fond de court Balle Haute Bandeja
```
point gagnant [joueur] fond de court balle haute bandeja
```

**Exemples :**
- `point gagnant Arnaud fond de court balle haute bandeja`
- `point gagnant Pierre fond de court balle haute bandeja`
- `point gagnant Thomas fond de court balle haute bandeja`
- `point gagnant Lucas fond de court balle haute bandeja`

##### B3.3. Fond de court Balle Haute Smash
```
point gagnant [joueur] fond de court balle haute smash
```

**Exemples :**
- `point gagnant Arnaud fond de court balle haute smash`
- `point gagnant Pierre fond de court balle haute smash`
- `point gagnant Thomas fond de court balle haute smash`
- `point gagnant Lucas fond de court balle haute smash`

---

### **C. Volée**

#### C1. Volée Coup Droit
```
point gagnant [joueur] volée coup droit
```

**Exemples :**
- `point gagnant Arnaud volée coup droit`
- `point gagnant Pierre volée coup droit`
- `point gagnant Thomas volée coup droit`
- `point gagnant Lucas volée coup droit`

#### C2. Volée Revers
```
point gagnant [joueur] volée revers
```

**Exemples :**
- `point gagnant Arnaud volée revers`
- `point gagnant Pierre volée revers`
- `point gagnant Thomas volée revers`
- `point gagnant Lucas volée revers`

#### C3. Volée Balle Haute

##### C3.1. Volée Balle Haute Víbora
```
point gagnant [joueur] volée balle haute víbora
```

**Exemples :**
- `point gagnant Arnaud volée balle haute víbora`
- `point gagnant Pierre volée balle haute víbora`
- `point gagnant Thomas volée balle haute víbora`
- `point gagnant Lucas volée balle haute víbora`

##### C3.2. Volée Balle Haute Bandeja
```
point gagnant [joueur] volée balle haute bandeja
```

**Exemples :**
- `point gagnant Arnaud volée balle haute bandeja`
- `point gagnant Pierre volée balle haute bandeja`
- `point gagnant Thomas volée balle haute bandeja`
- `point gagnant Lucas volée balle haute bandeja`

##### C3.3. Volée Balle Haute Smash
```
point gagnant [joueur] volée balle haute smash
```

**Exemples :**
- `point gagnant Arnaud volée balle haute smash`
- `point gagnant Pierre volée balle haute smash`
- `point gagnant Thomas volée balle haute smash`
- `point gagnant Lucas volée balle haute smash`

---

### **D. Lob**
```
point gagnant [joueur] lob
```

**Exemples :**
- `point gagnant Arnaud lob`
- `point gagnant Pierre lob`
- `point gagnant Thomas lob`
- `point gagnant Lucas lob`

---

## ⚠️ 2. FAUTE DIRECTE - Commandes Complètes

```
faute directe [joueur]
```

**Exemples :**
- `faute directe Arnaud`
- `faute directe Pierre`
- `faute directe Thomas`
- `faute directe Lucas`

---

## 🎯 3. FAUTE PROVOQUÉE - Commandes Complètes

### **Format**
```
faute provoquée [attaquant] [zone] [technique] [coup_final] [défenseur]
```

### **A. Faute Provoquée Service**
```
faute provoquée [attaquant] service [défenseur]
```

**Exemples :**
- `faute provoquée Arnaud service Pierre`
- `faute provoquée Pierre service Thomas`
- `faute provoquée Thomas service Lucas`
- `faute provoquée Lucas service Arnaud`

---

### **B. Faute Provoquée Fond de Court**

#### B1. Fond de court Coup Droit
```
faute provoquée [attaquant] fond de court coup droit [défenseur]
```

**Exemples :**
- `faute provoquée Arnaud fond de court coup droit Pierre`
- `faute provoquée Pierre fond de court coup droit Thomas`

#### B2. Fond de court Revers
```
faute provoquée [attaquant] fond de court revers [défenseur]
```

#### B3. Fond de court Balle Haute (Víbora/Bandeja/Smash)
```
faute provoquée [attaquant] fond de court balle haute [víbora|bandeja|smash] [défenseur]
```

---

### **C. Faute Provoquée Volée**

#### C1. Volée Coup Droit
```
faute provoquée [attaquant] volée coup droit [défenseur]
```

**Exemples :**
- `faute provoquée Arnaud volée coup droit Pierre`
- `faute provoquée Pierre volée coup droit Thomas`

#### C2. Volée Revers
```
faute provoquée [attaquant] volée revers [défenseur]
```

#### C3. Volée Balle Haute (Víbora/Bandeja/Smash)
```
faute provoquée [attaquant] volée balle haute [víbora|bandeja|smash] [défenseur]
```

---

### **D. Faute Provoquée Lob**
```
faute provoquée [attaquant] lob [défenseur]
```

**Exemples :**
- `faute provoquée Arnaud lob Pierre`
- `faute provoquée Pierre lob Thomas`

---

## ⚙️ 4. COMMANDES DE CONTRÔLE

### **Navigation & Contrôle Vidéo**
```
lecture                → Play/Pause (lecture)
pause                  → Play/Pause (pause)
```

### **Gestion des Points**
```
annuler                → Supprimer dernier point
supprimer              → Supprimer dernier point (alias)
```

### **Sauvegarde & Rapports**
```
sauvegarder            → Sauvegarde rapide
rapport                → Générer rapport
générer rapport        → Générer rapport (alias)
```

---

## 📊 Récapitulatif du Nombre de Commandes

### **Points Gagnants**
- Service : **4 commandes** (1 par joueur)
- Fond de court CD : **4 commandes**
- Fond de court R : **4 commandes**
- Fond de court BH Víbora : **4 commandes**
- Fond de court BH Bandeja : **4 commandes**
- Fond de court BH Smash : **4 commandes**
- Volée CD : **4 commandes**
- Volée R : **4 commandes**
- Volée BH Víbora : **4 commandes**
- Volée BH Bandeja : **4 commandes**
- Volée BH Smash : **4 commandes**
- Lob : **4 commandes**

**Total Points Gagnants : 48 commandes**

### **Fautes Directes**
- **4 commandes** (1 par joueur)

### **Fautes Provoquées**
- Service : **12 combinaisons** (4 attaquants × 3 défenseurs possibles)
- Fond de court CD : **12 combinaisons**
- Fond de court R : **12 combinaisons**
- Fond de court BH Víbora : **12 combinaisons**
- Fond de court BH Bandeja : **12 combinaisons**
- Fond de court BH Smash : **12 combinaisons**
- Volée CD : **12 combinaisons**
- Volée R : **12 combinaisons**
- Volée BH Víbora : **12 combinaisons**
- Volée BH Bandeja : **12 combinaisons**
- Volée BH Smash : **12 combinaisons**
- Lob : **12 combinaisons**

**Total Fautes Provoquées : 144 commandes**

### **Contrôles**
- **7 commandes**

---

## 🎯 **TOTAL GÉNÉRAL : ~200+ commandes vocales uniques**

---

## 🔧 Variantes de Prononciation à Gérer

### **Noms de joueurs**
- Arnaud → Arnold, Arno, Arnault
- Pierre → Pier, Piero
- Thomas → Toma, Tom
- Lucas → Luca, Lucass

### **Termes techniques**
- Víbora → Vibora, Vipère, Vibore
- Bandeja → Bande jà, Bandéja
- Volée → Volé, Vollée, Volet
- Coup droit → Coup-droit, Cou droit, Drive
- Revers → Reverre, Reverts, Backhand
- Lob → Lobe, Globe, Lobé

### **Zones**
- Fond de court → Fond-de-court, Fon de court
- Balle haute → Balle-haute, Bal haute

---

## 💡 Recommandations d'Implémentation

### **1. Prompt Initial Whisper**
```python
initial_prompt = """
Noms de joueurs : Arnaud, Pierre, Thomas, Lucas.
Termes padel : service, fond de court, volée, lob, coup droit, revers, 
balle haute, víbora, bandeja, smash, faute directe, faute provoquée, 
point gagnant.
"""
```

### **2. Post-Processing Automatique**
```python
corrections = {
    "arnold": "arnaud",
    "arno": "arnaud",
    "pier": "pierre",
    "toma": "thomas",
    "tom": "thomas",
    "luca": "lucas",
    "vibora": "víbora",
    "vipère": "víbora",
    "bande jà": "bandeja",
    "volé": "volée",
    "volet": "volée",
    "cou droit": "coup droit",
    "reverre": "revers",
    "lobe": "lob",
    "fon de court": "fond de court",
    "bal haute": "balle haute",
}
```

### **3. Validation Stricte**
- Ne pas dépendre d'un mot de réveil (en PTT, pas de "OK" requis)
- Valider la structure selon le type (point/faute directe/faute provoquée)
- Rejeter les commandes incomplètes

---

## 📝 Prochaines Étapes

1. ✅ **Dataset créé** (ce fichier)
2. ⏳ Créer `voice_optimizer.py` avec prompt + corrections
3. ⏳ Créer `test_voice_accuracy.py` pour tester toutes les commandes
4. ⏳ Intégrer dans `voice_commander.py`
5. ⏳ Tests en conditions réelles

---

**Date de création :** 23 décembre 2025  
**Version :** 1.0
