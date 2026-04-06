# 🎾 Schéma de Dénomination et Hiérarchie des Coups - NanoApp Stat

## 📊 Structure Hiérarchique Complète

```
ANNOTATION
│
├─── TYPE DE POINT (Niveau 1)
│    ├─ Point Gagnant
│    ├─ Faute Directe
│    └─ Faute Provoquée
│
└─── JOUEUR(S) (Niveau 2)
     ├─ Joueur unique (Point Gagnant / Faute Directe)
     └─ 2 Joueurs (Faute Provoquée : Attaquant + Défenseur)
     │
     └─── ZONE DE FRAPPE (Niveau 3)
          ├─ Service ───────────────────────► FIN
          ├─ Lob ──────────────────────────► FIN
          ├─ Fond de court ─┐
          └─ Volée ─────────┤
                            │
                            └─── TECHNIQUE (Niveau 4)
                                 ├─ Coup Droit (CD) ──────► FIN
                                 ├─ Revers (R) ────────────► FIN
                                 └─ Balle Haute (BH) ─┐
                                                       │
                                                       └─── COUP FINAL (Niveau 5)
                                                            ├─ Víbora ► FIN
                                                            ├─ Bandeja ► FIN
                                                            └─ Smash à plat ► FIN
```

---

## 🔄 Arbre de Décision Progressif

### **Étape 1 : Type de Point**
```
┌─────────────────────────────────┐
│   Quel type de point ?          │
├─────────────────────────────────┤
│  1. Point Gagnant               │
│  2. Faute Directe               │
│  3. Faute Provoquée             │
└─────────────────────────────────┘
```

### **Étape 2 : Joueur(s)**

#### Pour Point Gagnant ou Faute Directe :
```
┌─────────────────────────────────┐
│   Qui a marqué/fauté ?          │
├─────────────────────────────────┤
│  • [Joueur 1]                   │
│  • [Joueur 2]                   │
│  • [Joueur 3]                   │
│  • [Joueur 4]                   │
└─────────────────────────────────┘
```

#### Pour Faute Provoquée :
```
┌─────────────────────────────────┐
│   Qui a provoqué la faute ?     │
│   (Attaquant)                   │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│   Qui a commis la faute ?       │
│   (Défenseur)                   │
└─────────────────────────────────┘
```

### **Étape 3 : Zone de Frappe**
```
┌─────────────────────────────────┐
│   Où le coup a été joué ?       │
├─────────────────────────────────┤
│  1. Service          → FIN      │
│  2. Fond de court    → Suite    │
│  3. Volée            → Suite    │
│  4. Lob              → FIN      │
└─────────────────────────────────┘
```

### **Étape 4 : Technique** (si Fond de court ou Volée)
```
┌─────────────────────────────────┐
│   Quelle technique ?            │
├─────────────────────────────────┤
│  1. Coup Droit (CD)  → FIN      │
│  2. Revers (R)       → FIN      │
│  3. Balle Haute (BH) → Suite    │
└─────────────────────────────────┘
```

### **Étape 5 : Coup Final** (si Balle Haute)
```
┌─────────────────────────────────┐
│   Quel coup de balle haute ?    │
├─────────────────────────────────┤
│  1. Víbora           → FIN      │
│  2. Bandeja          → FIN      │
│  3. Smash à plat     → FIN      │
└─────────────────────────────────┘
```

---

## 📝 Dénomination Progressive (Construction du Nom)

### **Format de Construction**

```
[Type Point] + [Joueur] + [Zone] + [Technique] + [Coup Final]
```

### **Exemples de Construction Progressive**

#### **Exemple 1 : Coup Simple**
```
Étape 1 : "Point Gagnant"
Étape 2 : + "Pierre"
Étape 3 : + "Service"
= Point Gagnant - Pierre - Service
```

#### **Exemple 2 : Coup à 2 Niveaux**
```
Étape 1 : "Point Gagnant"
Étape 2 : + "Thomas"
Étape 3 : + "Volée"
Étape 4 : + "Coup Droit"
= Point Gagnant - Thomas - Volée - Coup Droit
```

#### **Exemple 3 : Coup Complet (5 Niveaux)**
```
Étape 1 : "Point Gagnant"
Étape 2 : + "Arnaud"
Étape 3 : + "Fond de court"
Étape 4 : + "Balle Haute"
Étape 5 : + "Smash"
= Point Gagnant - Arnaud - Fond de court - Balle Haute - Smash
```

#### **Exemple 4 : Faute Provoquée**
```
Étape 1 : "Faute Provoquée"
Étape 2a : + "Lucas" (attaquant)
Étape 2b : + "Pierre" (défenseur)
Étape 3 : + "Volée"
Étape 4 : + "Balle Haute"
Étape 5 : + "Víbora"
= Faute Provoquée - Lucas vs Pierre - Volée - Balle Haute - Víbora
```

---

## 🎯 Matrice des Profondeurs

| Zone de Frappe   | Profondeur Min | Profondeur Max | Exemple                                          |
|------------------|----------------|----------------|--------------------------------------------------|
| **Service**      | 3 niveaux      | 3 niveaux      | Point - Joueur - Service                        |
| **Lob**          | 3 niveaux      | 3 niveaux      | Point - Joueur - Lob                            |
| **Fond CD/R**    | 4 niveaux      | 4 niveaux      | Point - Joueur - Fond - Coup Droit              |
| **Volée CD/R**   | 4 niveaux      | 4 niveaux      | Point - Joueur - Volée - Revers                 |
| **Fond BH**      | 5 niveaux      | 5 niveaux      | Point - Joueur - Fond - Balle Haute - Smash     |
| **Volée BH**     | 5 niveaux      | 5 niveaux      | Point - Joueur - Volée - Balle Haute - Bandeja  |

---

## 🔢 Toutes les Combinaisons Possibles

### **1. Service (Simple - 3 niveaux)**
```
Point Gagnant → Joueur → Service
Faute Directe → Joueur
Faute Provoquée → Joueur A vs Joueur B → Service
```

**Total : 3 types × 4 joueurs = 12 combinaisons**

---

### **2. Lob (Simple - 3 niveaux)**
```
Point Gagnant → Joueur → Lob
Faute Provoquée → Joueur A vs Joueur B → Lob
```

**Total : 2 types × 4 joueurs = 8 combinaisons**

---

### **3. Fond de court (Double - 4 niveaux)**

#### Sans Balle Haute :
```
Point Gagnant → Joueur → Fond de court → Coup Droit
Point Gagnant → Joueur → Fond de court → Revers
Faute Provoquée → Joueur A vs B → Fond de court → Coup Droit
Faute Provoquée → Joueur A vs B → Fond de court → Revers
```

**Total : 2 techniques × 2 types × 4 joueurs = 16 combinaisons**

#### Avec Balle Haute :
```
Point Gagnant → Joueur → Fond → Balle Haute → Víbora
Point Gagnant → Joueur → Fond → Balle Haute → Bandeja
Point Gagnant → Joueur → Fond → Balle Haute → Smash
(× Faute Provoquée)
```

**Total : 3 coups × 2 types × 4 joueurs = 24 combinaisons**

**Sous-total Fond de court : 40 combinaisons**

---

### **4. Volée (Double - 4 niveaux)**

Structure identique à Fond de court :
- Sans BH : 16 combinaisons
- Avec BH : 24 combinaisons

**Sous-total Volée : 40 combinaisons**

---

## 📊 Récapitulatif Global

| Catégorie          | Nombre de combinaisons |
|--------------------|------------------------|
| Service            | 12                     |
| Lob                | 8                      |
| Fond de court      | 40                     |
| Volée              | 40                     |
| Faute Directe      | 4                      |
| **TOTAL**          | **~104 combinaisons**  |

*(sans compter les combinaisons de joueurs dans les fautes provoquées : 4×3=12 par type)*

---

## 🗂️ Codes Internes (Structure de Données)

### **Format JSON d'une annotation complète**

```json
{
  "type": "point_gagnant",
  "joueur": "Pierre",
  "zone": "fond_de_court",
  "technique": "BH",
  "coup_final": "bandeja",
  "timestamp": 125.8,
  "description": "Point Gagnant - Pierre - Fond de court - Balle Haute - Bandeja"
}
```

### **Format JSON Faute Provoquée**

```json
{
  "type": "faute_provoquee",
  "joueur": "Thomas",
  "joueur_subit": "Lucas",
  "zone": "volee",
  "technique": "R",
  "timestamp": 89.2,
  "description": "Faute Provoquée - Thomas vs Lucas - Volée - Revers"
}
```

---

## 🎤 Traduction en Commandes Vocales

### **Règle de Construction**
```
OK [type] [joueur] [zone] [technique] [coup_final] [joueur_2] OK
```

### **Exemples de Traduction**

| Annotation Complète                                    | Commande Vocale                                         |
|--------------------------------------------------------|---------------------------------------------------------|
| Point Gagnant - Pierre - Service                      | `OK point Pierre service OK`                           |
| Point Gagnant - Thomas - Volée - Coup Droit           | `OK point Thomas volée coup droit OK`                  |
| Point Gagnant - Arnaud - Fond - Balle Haute - Smash   | `OK point Arnaud fond de court balle haute smash OK`   |
| Faute Directe - Lucas                                  | `OK faute directe Lucas OK`                            |
| Faute Provoquée - Pierre vs Thomas - Volée - Revers   | `OK faute provoquée Pierre volée revers Thomas OK`     |

---

## 🔧 Nomenclature des Identifiants

### **Zones**
```python
zones = {
    'service': 'Service',
    'fond_de_court': 'Fond de court',
    'volee': 'Volée',
    'lobe': 'Lob'
}
```

### **Techniques**
```python
techniques = {
    'CD': 'Coup Droit',
    'R': 'Revers',
    'BH': 'Balle Haute'
}
```

### **Coups Finaux (Balle Haute)**
```python
coups_finaux = {
    'vibora': 'Víbora',
    'bandeja': 'Bandeja',
    'smash': 'Smash à plat'
}
```

---

## 💡 Logique de Validation

### **Règles de Validation**

1. **Service et Lob** → Pas de technique ni coup final
2. **Fond de court / Volée** → Technique obligatoire
3. **Technique CD ou R** → Pas de coup final
4. **Technique BH** → Coup final obligatoire
5. **Faute Directe** → Seulement joueur (pas de zone)
6. **Faute Provoquée** → 2 joueurs obligatoires

### **Arbre de Validation**

```
Point enregistré ?
│
├─ Type = Faute Directe ?
│  └─ Joueur défini ? → ✅ VALIDE
│
├─ Type = Point Gagnant ou Faute Provoquée ?
│  │
│  ├─ Zone = Service ou Lob ?
│  │  └─ Joueur(s) défini(s) ? → ✅ VALIDE
│  │
│  └─ Zone = Fond de court ou Volée ?
│     │
│     ├─ Technique = CD ou R ?
│     │  └─ Joueur(s) défini(s) ? → ✅ VALIDE
│     │
│     └─ Technique = BH ?
│        └─ Coup final défini ?
│           └─ Joueur(s) défini(s) ? → ✅ VALIDE
```

---

**Date de création :** 23 décembre 2025  
**Version :** 1.0
