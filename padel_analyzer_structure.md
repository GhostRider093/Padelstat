# 🧩 ARCHITECTURE COMPLÈTE – ANALYSEUR DE MATCHS DE PADEL LOCAL

## 1. Objectif du projet
Créer une IA locale capable de :
- Lire les fichiers `.json` issus de tes analyses de vidéos (statistiques de match),
- Ajouter un **contexte tactique** issu de livres PDF (via RAG local),
- Générer une **analyse textuelle claire, réaliste et cohérente**,
- Le tout **en local**, utilisable sur n’importe quel PC avec Ollama.

---

## 2. Structure du projet dans VS Code

```
padel-analyzer/
│
├── data/
│   ├── matchs/                ← fichiers JSON bruts
│   └── pdfs/                  ← tes 3 livres tactiques
│
├── embeddings/
│   ├── index.faiss            ← base d’embeddings
│   └── metadata.json
│
├── src/
│   ├── __init__.py
│   ├── preprocess.py          ← extrait et calcule les stats brutes
│   ├── rag_engine.py          ← moteur de recherche contextuelle
│   ├── analyzer.py            ← crée le prompt et appelle Ollama
│   ├── report_generator.py    ← formate le texte final (HTML ou TXT)
│   └── ollama_client.py       ← gère la communication avec Ollama
│
├── config/
│   └── settings.yaml          ← choix du modèle, chemins, tailles de chunks…
│
├── app.py                     ← script principal (ou serveur Flask / Streamlit)
├── requirements.txt
└── README.md
```

---

## 3. Modules et responsabilités

### ⚙️ `preprocess.py`
Extrait les statistiques depuis le JSON :
- points gagnants / fautes / fautes provoquées par joueur
- ratios par type de coup
- sauvegarde d’un `resume_match.json` lisible

```python
import json
from collections import Counter

def calculer_statistiques(fichier_json):
    with open(fichier_json, 'r', encoding='utf-8') as f:
        data = json.load(f)

    points = data["points"]

    stats = {
        "points_gagnants": Counter(),
        "fautes_directes": Counter(),
        "fautes_provoquees": Counter()
    }

    for p in points:
        if p["type"] == "point_gagnant":
            stats["points_gagnants"][p["joueur"]] += 1
        elif p["type"] == "faute_directe":
            stats["fautes_directes"][p["joueur"]] += 1
        elif p["type"] == "faute_provoquee":
            attaquant = p.get("attaquant")
            if attaquant:
                stats["fautes_provoquees"][attaquant] += 1

    resume = []
    for joueur in set(
        list(stats["points_gagnants"].keys()) +
        list(stats["fautes_directes"].keys()) +
        list(stats["fautes_provoquees"].keys())
    ):
        resume.append({
            "joueur": joueur,
            "points_gagnants": stats["points_gagnants"][joueur],
            "fautes_directes": stats["fautes_directes"][joueur],
            "fautes_provoquees": stats["fautes_provoquees"][joueur]
        })

    with open('resume_match.json', 'w', encoding='utf-8') as f:
        json.dump(resume, f, indent=2, ensure_ascii=False)

    return resume
```

---

### 📚 `rag_engine.py`
- Découpe les PDF en **chunks** (via LangChain ou ta logique maison),
- Stocke les **embeddings** FAISS / Chroma,
- Fournit les passages les plus pertinents pour le contexte RAG.

```python
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
import os

def rechercher_contexte(requete: str, index_path='embeddings/index.faiss', top_k=3):
    if not os.path.exists(index_path):
        return "Pas de contexte trouvé."

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectordb = FAISS.load_local(index_path, embeddings)

    docs = vectordb.similarity_search(requete, k=top_k)
    contexte = "\n\n".join([d.page_content for d in docs])
    return contexte
```

---

### 🧠 `analyzer.py`
Crée le prompt complet et appelle Ollama pour générer l’analyse textuelle.

```python
import json
from src.ollama_client import reponse_ollama

def generer_analyse(stats, contexte, modele="llama3.2:3b"):
    prompt = f"""
    Tu es un analyste professionnel de padel.

    Voici les statistiques calculées pour ce match :
    {json.dumps(stats, indent=2, ensure_ascii=False)}

    Voici des extraits d'ouvrages sur le padel :
    {contexte}

    Règles :
    - N’invente aucune valeur.
    - Utilise les extraits pour interpréter les données tactiquement.
    - Structure ta réponse ainsi :
      📊 Résumé global
      🎯 Analyse par joueur
      ⚔️ Comparatif équipes
      💡 Conclusion technique
    """

    return reponse_ollama(prompt, modele)
```

---

### 💬 `report_generator.py`
Formate l’analyse générée en **HTML**.

```python
def generer_html(analyse_texte):
    html = f"""<html><head><meta charset='utf-8'><title>Analyse du match</title></head>
    <body><h1>Analyse du match</h1><pre>{analyse_texte}</pre></body></html>"""
    return html
```

---

### 🔗 `ollama_client.py`
Permet de communiquer avec Ollama via son API locale.

```python
import requests, json

def reponse_ollama(prompt, modele="llama3.2:3b"):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": modele, "prompt": prompt}
    )
    texte = ""
    for chunk in response.iter_lines():
        if chunk:
            texte += json.loads(chunk).get("response", "")
    return texte
```

---

## 4. Pipeline global (`app.py`)

```python
from src.preprocess import calculer_statistiques
from src.rag_engine import rechercher_contexte
from src.analyzer import generer_analyse
from src.report_generator import generer_html

# 1️⃣ Calculer les statistiques
stats = calculer_statistiques("data/matchs/VID_20251217.json")

# 2️⃣ Chercher le contexte RAG
contexte = rechercher_contexte("analyse de jeu au filet et fautes en fond de court", top_k=3)

# 3️⃣ Générer le rapport d'analyse
analyse = generer_analyse(stats, contexte, modele="llama3.2:3b")

# 4️⃣ Créer un rapport HTML
rapport_html = generer_html(analyse)
with open("rapport.html", "w", encoding="utf-8") as f:
    f.write(rapport_html)

print("✅ Rapport généré : rapport.html")
```

---

## 5. Exemple de prompt maître

```text
Tu es un analyste professionnel de padel.

Statistiques brutes du match :
{{Données JSON pré-calculées}}

Contexte de référence (issu d’ouvrages sur le padel) :
{{Passages RAG}}

Instructions :
1. Analyse uniquement les données fournies.
2. Utilise les extraits pour enrichir ton commentaire (stratégie, technique, positionnement).
3. Ne crée aucun chiffre, aucun joueur non mentionné.
4. Écris une analyse professionnelle, structurée et lisible :

📊 RÉSUMÉ GLOBAL  
🎯 ANALYSE PAR JOUEUR  
⚔️ COMPARATIF ÉQUIPES  
💡 CONCLUSION TECHNIQUE

Ne fais pas de calculs. Ne reformate pas le JSON.
```

---

## 6. Technologies recommandées

| Composant | Lib / outil |
|------------|--------------|
| Embeddings | `sentence-transformers` ou `Instructor-XL` |
| FAISS / Chroma | `faiss-cpu` ou `chromadb` |
| Ollama client | `requests` ou `ollama-python` |
| Interface future | Flask / Electron / Streamlit |
| IDE | VS Code (avec Copilot / Claude pour auto-complétion) |

---

## 7. README.md (inclus)

```markdown
# Padel Analyzer

Analyseur local de matchs de padel avec IA et contexte tactique.

## 🚀 Installation

```bash
pip install -r requirements.txt
```

## ⚙️ Démarrage

1. Placez vos fichiers JSON dans `data/matchs/`.
2. Placez vos PDF tactiques dans `data/pdfs/`.
3. Générez les embeddings via `rag_engine.py`.
4. Exécutez :

```bash
python app.py
```

## 📊 Résultat

Un fichier `rapport.html` contenant l’analyse complète du match.

## 🧠 Technologies
- Ollama (LLM local)
- LangChain / FAISS (RAG)
- Python 3.11+

## 📁 Structure
(voir la section architecture principale)
```

---

## 8. Bonus : prompt développeur pour VS Code

```text
Objectif : aider à développer un moteur d’analyse de match de padel.
Contexte : IA locale (Ollama) + RAG (PDF tactiques) + stats JSON.
Règle : toujours séparer calcul logique (Python) et interprétation (LLM).
Style : code modulaire, commenté, compatible cross-platform.
```

---

✅ Ce document contient **tous les éléments complets** : architecture, code Python, pipeline, prompt maître, README et directives Copilot.

