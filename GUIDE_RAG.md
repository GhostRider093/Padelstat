# 🤖 Guide RAG - Système de Connaissances Padel

## 🎯 Qu'est-ce que le RAG ?

**RAG** (Retrieval Augmented Generation) = enrichir l'IA avec vos livres de padel.

Au lieu de demander à l'IA d'inventer, elle va **chercher dans vos livres** et répondre avec des vraies références !

## 📚 Étape 1 : Ajouter vos livres PDF

1. Placez vos 3 PDFs de padel dans le dossier `data/books/`
2. Exemple de noms :
   - `Padel_Technique_Avancee.pdf`
   - `Tactiques_Padel_Pro.pdf`
   - `Guide_Complet_Padel.pdf`

## 🔧 Étape 2 : Indexer les livres

Lancez cette commande **une seule fois** :

```bash
python padel_rag.py index
```

Cela va :
- ✅ Extraire le texte des PDFs (peut prendre 2-5 min)
- ✅ Découper en morceaux intelligents (~800 caractères)
- ✅ Créer les embeddings avec Ollama (utilise nomic-embed-text)
- ✅ Stocker dans ChromaDB (base de données vectorielle)

**Sortie attendue :**
```
============================================================
INDEXATION DE 3 LIVRE(S)
============================================================
Extraction de 250 pages depuis Padel_Technique_Avancee.pdf...
OK - 250 pages extraites (125432 caractères)
OK - 157 chunks créés
  ... Batch 1/2 indexé
  ... Batch 2/2 indexé
OK - 157 chunks indexés pour 'Padel_Technique_Avancee'
Total dans la collection: 157 chunks
...
```

## 📊 Étape 3 : Vérifier l'indexation

```bash
python padel_rag.py stats
```

Vous devriez voir :
```
============================================================
STATISTIQUES DE LA BASE RAG
============================================================
Nombre de livres indexés: 3
Nombre total de chunks: 450
Livres:
  - Padel_Technique_Avancee
  - Tactiques_Padel_Pro
  - Guide_Complet_Padel
============================================================
```

## 🔍 Étape 4 : Tester la recherche

```bash
python padel_rag.py search "Comment faire une bandeja"
```

Résultat :
```
============================================================
RÉSULTAT 1
Livre: Padel_Technique_Avancee
Chunk: 45/157
Score: 0.8523
============================================================
La bandeja est un coup emblématique du padel. Elle se joue 
à mi-hauteur, avec une trajectoire descendante. Le but est 
de faire rebondir la balle dans le coin adverse pour créer 
une position d'attaque...
```

## 💬 Étape 5 : Utiliser le chat IA avec RAG

### Mode 1 : Chat simple avec connaissances

```bash
python ollama_chat_rag.py
```

Exemples de questions :
- "Quelle est la différence entre bandeja et víbora ?"
- "Comment améliorer mon service ?"
- "Tactiques pour jouer contre des attaquants"

### Mode 2 : Chat avec analyse de match

```bash
python ollama_chat_rag.py data/match_20251220_001448.json
```

Exemples de questions :
- "Analyse les performances de ce match"
- "Quel joueur devrait travailler sa bandeja ?"
- "Compare ce match aux tactiques recommandées dans les livres"

## 🎮 Commandes dans le chat

Une fois dans le chat interactif :

| Commande | Description |
|----------|-------------|
| `/match <fichier>` | Charger un fichier de match |
| `/stats` | Voir les stats de la base RAG |
| `/clear` | Effacer l'historique de conversation |
| `/save` | Sauvegarder la conversation |
| `/quit` | Quitter |

## 🔄 Réindexer (si vous ajoutez/modifiez des livres)

Si vous ajoutez de nouveaux PDFs :

```bash
# Réinitialiser la base (supprime tout)
python padel_rag.py reset

# Réindexer tous les PDFs
python padel_rag.py index
```

## 🧪 Exemple de conversation avec RAG

```
Vous: Quelle est la différence entre bandeja et víbora ?

[Recherche dans les livres...]

IA: D'après les livres de référence sur le padel :

La BANDEJA est un coup offensif joué à mi-hauteur avec une 
trajectoire descendante. L'objectif est de faire rebondir 
la balle dans le coin adverse pour maintenir la pression 
sans prendre trop de risques.

La VÍBORA est un coup plus agressif, joué plus haut et avec 
un effet lifté prononcé. La balle sort de la vitre arrière 
avec un rebond latéral imprévisible, créant une vraie 
difficulté pour l'adversaire.

Choix tactique :
- Bandeja → Maintenir la pression, position sûre
- Víbora → Chercher le point, plus risqué

[Source: Padel_Technique_Avancee, chapitres 4 et 5]
```

## 📈 Avantages du système RAG

✅ **Réponses basées sur vos livres** (pas d'invention)
✅ **Citations des sources** (vous savez d'où vient l'info)
✅ **Combine stats + théorie** (analyse match + connaissances)
✅ **Scalable** (ajoutez autant de livres que vous voulez)
✅ **Rapide** (recherche vectorielle en millisecondes)

## ⚠️ Prérequis

1. **Ollama installé et lancé** : `ollama serve`
2. **Modèle téléchargé** : `ollama pull llama3.2:3b`
3. **Embedding model** : `ollama pull nomic-embed-text` (ChromaDB l'utilise automatiquement)
4. **PDFs avec texte extractible** (pas des scans sans OCR)

## 🐛 Dépannage

### "Base RAG vide"
→ Lancez `python padel_rag.py index`

### "Aucun texte extrait du PDF"
→ Votre PDF est peut-être scanné. Utilisez un OCR (Tesseract) ou trouvez une version avec texte.

### "Impossible de se connecter à Ollama"
→ Vérifiez qu'Ollama est lancé : `ollama serve`

### "Modèle non trouvé"
→ Téléchargez le modèle : `ollama pull llama3.2:3b`

## 📝 Architecture technique

```
┌─────────────────────────────────────────────────────┐
│                  VOS LIVRES PDF                      │
│         (data/books/*.pdf)                           │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │  padel_rag.py       │
         │  - Extraction PDF   │
         │  - Chunking         │
         │  - Embeddings       │
         └─────────┬───────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │    ChromaDB         │
         │  (base vectorielle) │
         │  data/chroma_db/    │
         └─────────┬───────────┘
                   │
                   ▼
         ┌─────────────────────┐
         │ ollama_chat_rag.py  │
         │  - Recherche RAG    │
         │  - Prompt Ollama    │
         │  - Analyse match    │
         └─────────────────────┘
```

## 🚀 Prochaines étapes

1. ✅ Ajoutez vos 3 PDFs dans `data/books/`
2. ✅ Lancez `python padel_rag.py index`
3. ✅ Testez `python padel_rag.py search "bandeja"`
4. ✅ Lancez le chat : `python ollama_chat_rag.py`
5. 🎉 Profitez de votre IA coach de padel !
