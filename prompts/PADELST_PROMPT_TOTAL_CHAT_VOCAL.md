# PADELST - PROMPT TOTAL + PACK D'INTEGRATION CHAT VOCAL CONTINU

Date de generation: 2026-03-01  
Objectif: importer dans Padelst un comportement vocal immediat, controle, fluide, sans phase "essais/erreurs".

---

## 1) References techniques source (capture reelle de l'environnement)

### 1.1 Versions detectees

- Projet: `nanocode-chatbot` version `0.1.0`
- Python systeme principal: `3.14.2`
- Python secondaire disponible: `3.12.10`
- Ollama: `0.17.1`
- Environnement web (`.venv`):
  - `nanocode-chatbot==0.1.0`
- Environnement voix (`.venv-whisper`):
  - `nanocode-chatbot==0.1.0`
  - `openai-whisper==20250625`
  - `sounddevice==0.5.5`
  - `soundfile==0.13.1`
  - `pyttsx3==2.99`

### 1.2 Modeles Ollama detectes

- Locaux:
  - `llama3.1:8b`
  - `gpt-oss:20b`
  - `qwen2.5-coder:1.5b-base`
  - `stable-code:3b-code-q4_0`
- Cloud tags presents:
  - `gpt-oss:120b-cloud`
  - `gpt-oss:20b-cloud`
  - `deepseek-v3.1:671b-cloud`
  - `qwen3-coder:480b-cloud`

### 1.3 Endpoints cibles

- Ollama API: `http://127.0.0.1:11434`
- Web UI/chat API: `http://127.0.0.1:7860`

---

## 2) Installation immediate (Windows, copie conforme)

Utiliser exactement cet ordre.

### 2.1 Prerequis machine

- Windows 10/11
- PowerShell
- Ollama installe
- Python 3.12+ (3.14 OK, 3.12 recommande pour whisper stack)

### 2.2 Setup projet

```powershell
cd F:\NanoCode

# Env web
py -3.14 -m venv .venv
.\.venv\Scripts\python -m pip install -U pip setuptools wheel
.\.venv\Scripts\python -m pip install -e .

# Env voix
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_whisper.ps1
```

### 2.3 Verifications rapides

```powershell
.\.venv\Scripts\python --version
.\.venv\Scripts\python -m pip show nanocode-chatbot

.\.venv-whisper\Scripts\python --version
.\.venv-whisper\Scripts\python -m pip show openai-whisper sounddevice soundfile pyttsx3

ollama --version
ollama list
```

### 2.4 Lancement

Option simple:

```powershell
cd F:\NanoCode
.\start_total.bat --no-browser
```

Ou web seul:

```powershell
cd F:\NanoCode
.\start.bat --no-browser
```

Puis ouvrir:

```powershell
start http://127.0.0.1:7860/
```

---

## 3) Contrat d'integration Padelst (obligatoire)

Pour que "ca marche tout de suite", Padelst doit offrir:

1. Entree micro continue (speech-to-text navigateur ou natif)
2. Sortie voix (TTS)
3. Evenements lifecycle:
   - `onSpeechStart`
   - `onSpeechResult`
   - `onSpeechEnd`
   - `onTTSEnd`
4. Possibilite de:
   - interrompre TTS immediatement (`cancel`)
   - annuler requete LLM en cours (`abort`)
5. Etat persistant en memoire (session variables)

Si Padelst ne fournit pas ces hooks, le prompt seul ne peut pas garantir le comportement temps reel.

---

## 4) Prompt systeme total (a coller tel quel)

```text
Tu es un assistant vocal conversationnel en francais, fluide, pratique, et controleable en temps reel.

REGLES PRINCIPALES
- Rester clair, utile, direct.
- Eviter les monologues longs.
- Permettre interruption utilisateur a tout moment.

MODE VOCAL CONTINU
1) Session micro continue:
   - Quand le mode vocal est actif, l'ecoute repart automatiquement apres chaque tour.
   - L'utilisateur ne doit pas recliquer micro a chaque question.

2) Validation par mot:
   - Le message utilisateur est envoye seulement s'il se termine par le mot de validation.
   - Mot de validation par defaut: "a toi" (variantes accent/non accent autorisees).
   - Sans mot final, conserver le texte en brouillon.

3) Interruption de lecture:
   - Pendant lecture vocale assistant, si l'utilisateur dit:
     "stop", "arrete", "stop lecture", "stop parole", "tais toi", "coupe", "silence", "suivant", "passer", "next"
   - Alors couper immediatement la lecture vocale.
   - Garder la session micro active.
   - Repartir en ecoute pour enchainer.

4) Arret session vocale complete:
   - Si l'utilisateur dit "stop ecoute", "arrete ecoute", ou "quitte":
   - Arreter completement le mode vocal.

5) Anti-ponctuation TTS:
   - Avant lecture vocale, nettoyer le texte:
     - supprimer URLs
     - supprimer ponctuation/symboles techniques
     - compacter les espaces
   - Ne pas lire les signes de ponctuation.

COMPORTEMENT REPONSE
- Francais uniquement (sauf demande contraire explicite).
- Reponse courte si question simple.
- Reponse structuree mais concise si question complexe.
- Pas de commandes terminal sauf demande explicite utilisateur.
```

---

## 5) Configuration runtime recommandee (Padelst)

Initialiser ces variables:

```json
{
  "voice_session_active": false,
  "voice_listening": false,
  "voice_auto_send": true,
  "voice_require_keyword": true,
  "voice_keyword": "a toi",
  "voice_draft": "",
  "tts_enabled": true,
  "tts_speaking": false,
  "tts_rate": 1.0,
  "llm_generating": false
}
```

---

## 6) Machine d'etat (implementation exacte)

Etats:

- `IDLE`
- `LISTENING`
- `WAITING_KEYWORD`
- `GENERATING`
- `SPEAKING`

Transitions:

1. `IDLE -> LISTENING` (start vocal)
2. `LISTENING -> WAITING_KEYWORD` (phrase sans mot final)
3. `LISTENING -> GENERATING` (mot final detecte)
4. `GENERATING -> SPEAKING` (reponse recue + TTS active)
5. `GENERATING -> LISTENING` (reponse recue + TTS inactive)
6. `SPEAKING -> LISTENING` (fin lecture)
7. `SPEAKING -> LISTENING` (commande interruption `stop`)
8. `* -> IDLE` (`stop ecoute`)

Regle prioritaire:

- Pendant `GENERATING` ou `SPEAKING`, accepter quand meme les commandes vocales de controle (`stop`, `stop ecoute`).

---

## 7) Algorithmes critiques

### 7.1 Normalisation commande vocale

```text
normalize(s):
  s = lower(s)
  s = remove_accents(s)
  s = replace_non_alnum_by_space(s)
  s = collapse_spaces(s).trim()
  return s
```

### 7.2 Detection mot de validation en fin de phrase

```text
has_trailing_keyword(transcript, keyword):
  t = normalize(transcript)
  k = normalize(keyword)
  if tail_words(t, count_words(k)) == words(k):
    return true, transcript_without_last_keyword_words
  else:
    return false, transcript
```

### 7.3 Filtre anti-ponctuation TTS (recommande)

```text
clean_for_tts(text):
  remove_markdown_code_blocks
  remove_urls
  remove_symbols_and_punctuation
  collapse_spaces
  limit_length(700 chars)
```

Equivalent JS:

```js
text
  .replace(/```[\s\S]*?```/g, " ")
  .replace(/https?:\/\/\S+/gi, " ")
  .replace(/[\[\]\(\)\{\}<>]/g, " ")
  .replace(/[^\p{L}\p{N}\s]/gu, " ")
  .replace(/\s+/g, " ")
  .trim()
  .slice(0, 700);
```

---

## 8) Commandes vocales standard

### 8.1 Couper lecture (continuer session)

- stop
- arrete
- stop lecture
- stop parole
- tais toi
- coupe
- silence
- suivant
- passer
- next

Action:

- `TTS.cancel()`
- `voice_session_active = true`
- `restart listening`

### 8.2 Arreter session complete

- stop ecoute
- arrete ecoute
- quitte

Action:

- `abort current llm if needed`
- `TTS.cancel()`
- `speech_recognition.stop()`
- `voice_session_active = false`

---

## 9) Sequence d'execution recommandee (temps reel)

1. L'utilisateur active mode vocal.
2. Ecoute ouverte.
3. Texte reconnu:
   - si commande stop session: stop complet
   - si commande stop lecture: couper lecture + reprise ecoute
   - sinon:
     - ajouter au brouillon
     - si mot final detecte: envoyer LLM
4. Pendant generation:
   - continuer ecoute uniquement pour commandes de controle
5. A reception reponse:
   - nettoyer texte TTS
   - lire reponse
6. Fin lecture:
   - reprise ecoute auto

---

## 10) Check "pret en 60 secondes" (no trial-and-error)

Executer dans cet ordre:

```powershell
cd F:\NanoCode
.\start_total.bat --no-browser
start http://127.0.0.1:7860/
```

Dans l'UI:

1. `Ctrl+F5`
2. Verifier:
   - `Validation par mot` ON
   - `Mot de validation` = `a toi` (ou `a toi` accentue)
3. Activer `Micro`
4. Dire: `Bonjour a toi`
5. Pendant lecture, dire: `stop`
6. Verifier:
   - lecture coupe immediate
   - session micro reste active

---

## 11) Bloc court de secours (si Padelst impose un prompt court)

```text
Mode vocal continu obligatoire.
Mot de validation: "a toi".
Sans "a toi" en fin de phrase, ne pas envoyer (garder brouillon).
Commande "stop" = couper lecture vocale immediate et continuer session.
Commande "stop ecoute" = arreter session vocale complete.
Ne pas lire la ponctuation en TTS.
Reponses courtes, claires, en francais.
```

---

## 12) Notes de compatibilite importantes

- Certaines plateformes stockent des accents de facon instable.
- Pour robustesse cross-app:
  - commande principale recommandee: `a toi` (sans accent) pour le trigger
  - accepter aussi `a toi` accentue via normalisation.
- Si tu veux forcer strictement `a toi` accentue, garde la normalisation accent-insensitive cote code.

