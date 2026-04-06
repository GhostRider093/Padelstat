# 🚀 Optimisation GPU pour Ollama

## ⚠️ Problème : "Ça rame" avec le modèle actuel

Le modèle **gpt-oss:20b** (20 milliards de paramètres) est TRÈS gourmand en ressources.

### Configuration actuelle détectée :
- **Modèle** : `gpt-oss:20b`
- **GPU** : NVIDIA GeForce RTX 4070 SUPER
- **Accélération** : D3D11VA hardware decoding

---

## ✅ Solutions pour améliorer les performances

### Option 1 : Modèles plus légers (RECOMMANDÉ) ⚡

Remplacer `gpt-oss:20b` par un modèle plus rapide :

```bash
# Modèles optimisés pour RTX 4070 SUPER :

# 1. Llama 3.2 - 3B (TRÈS RAPIDE)
ollama pull llama3.2:3b

# 2. Gemma 2 - 9B (Bon compromis vitesse/qualité)
ollama pull gemma2:9b

# 3. Mistral - 7B (Excellent rapport qualité/vitesse)
ollama pull mistral:7b

# 4. Phi-3 Mini (Ultra rapide, léger)
ollama pull phi3:mini
```

**Ensuite modifier dans** `ollama_chat.py` **ligne 42** :
```python
MODEL_NAME = "llama3.2:3b"  # Au lieu de "gpt-oss:20b"
```

---

### Option 2 : Vérifier l'utilisation GPU 🔍

```bash
# Vérifier qu'Ollama utilise bien le GPU
ollama ps

# Lister les modèles installés
ollama list

# Tester les performances d'un modèle
ollama run llama3.2:3b "Teste de vitesse"
```

Si Ollama n'utilise PAS le GPU :
```bash
# Windows : Définir la variable d'environnement
set CUDA_VISIBLE_DEVICES=0

# Ou dans PowerShell :
$env:CUDA_VISIBLE_DEVICES=0
```

---

### Option 3 : Optimiser les paramètres Ollama ⚙️

Créer/modifier le fichier Ollama config (Windows) :
`%USERPROFILE%\.ollama\config.json`

```json
{
  "gpu_layers": -1,
  "num_thread": 8,
  "num_gpu": 1,
  "main_gpu": 0,
  "low_vram": false
}
```

---

### Option 4 : Quantization (Réduire la précision) 📉

Les modèles quantifiés sont plus rapides :

```bash
# Versions quantifiées (Q4 = 4-bit, Q8 = 8-bit)
ollama pull llama3.2:3b-q4_K_M    # Plus rapide
ollama pull mistral:7b-q4_K_M      # Bon compromis
ollama pull gemma2:9b-q8_0         # Meilleure qualité
```

---

## 📊 Comparaison des modèles

| Modèle | Taille | Vitesse | Qualité | VRAM | Recommandation |
|--------|--------|---------|---------|------|----------------|
| **gpt-oss:20b** | 20B | 🐌 Lent | ⭐⭐⭐⭐⭐ | ~12-16GB | Trop lourd |
| **llama3.2:3b** | 3B | ⚡⚡⚡ Rapide | ⭐⭐⭐⭐ | ~2GB | ✅ OPTIMAL |
| **mistral:7b** | 7B | ⚡⚡ Moyen | ⭐⭐⭐⭐ | ~4GB | ✅ Bon choix |
| **gemma2:9b** | 9B | ⚡⚡ Moyen | ⭐⭐⭐⭐⭐ | ~6GB | ✅ Qualité++ |
| **phi3:mini** | 3.8B | ⚡⚡⚡ Rapide | ⭐⭐⭐ | ~2.5GB | Pour tests rapides |

**Votre RTX 4070 SUPER a 12GB de VRAM** → Peut gérer jusqu'à 13B confortablement

---

## 🎯 Recommandation finale

### Pour l'analyse LIVE de match (priorité vitesse) :
```bash
ollama pull llama3.2:3b
```

Puis modifier `ollama_chat.py` ligne 42 :
```python
MODEL_NAME = "llama3.2:3b"
```

### Pour les rapports détaillés (priorité qualité) :
```bash
ollama pull gemma2:9b
```

---

## 🧪 Tester les performances

```bash
# 1. Installer un modèle rapide
ollama pull llama3.2:3b

# 2. Tester
ollama run llama3.2:3b "Analyse ce match de padel rapidement"

# 3. Chronométrer
time ollama run llama3.2:3b "Test de vitesse GPU"
```

---

## ⚡ Résultat attendu

Avec **llama3.2:3b** :
- **Avant** : 10-15 secondes par analyse (gpt-oss:20b)
- **Après** : 2-3 secondes par analyse (llama3.2:3b)
- **Gain** : **5x plus rapide** 🚀

---

## 🔧 Modification du code

**Dans** `ollama_chat.py` **:**
```python
# Ligne 42 - AVANT
MODEL_NAME = "gpt-oss:20b"  # LENT

# Ligne 42 - APRÈS
MODEL_NAME = "llama3.2:3b"  # RAPIDE ⚡
```

**Dans** `app/exports/live_html_generator.py` **:**
```python
# Ligne 33 - Mettre le même
self.model_name = "llama3.2:3b"
```

---

## 📝 Notes importantes

1. **Le GPU est bien détecté** (D3D11VA visible dans les logs)
2. Le problème vient du **modèle trop gros** (20B paramètres)
3. La RTX 4070 SUPER est **excellente** pour l'IA
4. **llama3.2:3b** est parfait pour l'analyse sportive live

---

## 🆘 Si ça rame toujours après changement

1. **Vérifier VRAM disponible** :
   ```bash
   nvidia-smi
   ```

2. **Fermer VLC et autres apps lourdes** pendant l'analyse

3. **Réduire le timeout** dans `ollama_chat.py` ligne 43 :
   ```python
   TIMEOUT = 15  # Au lieu de 30
   ```

4. **Désactiver l'analyse auto** tous les 3 points :
   Dans `app/ui/main_window.py`, modifier la logique d'appel

---

## ✨ Conclusion

**Action immédiate** :
```bash
ollama pull llama3.2:3b
```

Puis modifier `MODEL_NAME` dans le code → **5x plus rapide** ! 🚀
