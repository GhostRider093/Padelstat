"""
Test de nettoyage audio avec le texte du rapport
"""
import re
import asyncio
import edge_tts
import tempfile
import os
from playsound import playsound

def clean_text_for_speech(text):
    """Nettoie le texte pour la synthèse vocale - PARSING COMPLET"""
    import html as html_module
    
    # Décoder les entités HTML d'abord
    text = html_module.unescape(text)
    
    # Enlever complètement les balises script et style
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Enlever toutes les balises HTML et markdown
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **gras** → gras
    text = re.sub(r'\*([^*]+)\*', r'\1', text)  # *italique* → italique
    
    # Enlever les tableaux markdown (| ... |)
    text = re.sub(r'\|[^\n]+\|', '', text)
    text = re.sub(r'[-|]+', '', text)
    
    # Enlever les titres markdown (###, ##, #)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Enlever TOUS les emojis
    text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF🎾]', '', text)
    
    # ENLEVER TOUS LES SYMBOLES
    text = re.sub(r'[*#•⚡🎯📊💡⚔️✓×÷±§¶†‡°¢£¤¥¦©®™´¨≠¬µ~◊∫ª≤≥]', '', text)
    text = re.sub(r'[→←↑↓↔↕⇒⇐⇑⇓⇔]', ' ', text)
    
    # Enlever les underscores, pipes, backslashes
    text = text.replace('_', ' ')
    text = text.replace('|', ' ')
    text = text.replace('\\', ' ')
    text = text.replace('`', '')
    
    # Remplacer les séparateurs par des pauses
    text = text.replace(':', '. ')
    text = text.replace(';', '. ')
    text = text.replace('•', '. ')
    
    # Enlever tirets et slashes
    text = re.sub(r'\s+-\s+', ' ', text)
    text = re.sub(r'--+', ' ', text)
    text = text.replace('/', ' ')
    text = text.replace('–', ' ')  # Tiret long
    text = text.replace('—', ' ')  # Tiret cadratin
    
    # Enlever parenthèses et crochets avec contenu court
    text = re.sub(r'\([^)]{0,5}\)', '', text)
    text = re.sub(r'\[[^\]]{0,5}\]', '', text)
    
    # Remplacer virgules par points
    text = text.replace(',', '. ')
    
    # Enlever pourcentages isolés
    text = re.sub(r'\b\d+\s*%', '', text)
    text = re.sub(r'\b\d+\.\d+\b', '', text)
    
    # Enlever répétitions
    words = text.split()
    cleaned_words = []
    for i, word in enumerate(words):
        if i == 0 or word.lower() != words[i-1].lower():
            cleaned_words.append(word)
    text = ' '.join(cleaned_words)
    
    # Nettoyer espaces et points multiples
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()

async def generate_speech(text, output_path):
    """Génère l'audio avec Edge-TTS"""
    voice = "fr-FR-DeniseNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

# Texte de test fourni par l'utilisateur
test_text = """**Rapport de match – résumé **

| Éléments clés | Détails |
|---------------|---------|
| **Date** | 30/06/2023 |
| **Lieu** | Court 3 – Surface synthétique |
| **Tournoi** | Open du Grand Est (Open du Grand Est, 2023) |
| **Score final** | 6 – 4 (même format de match à un set) |
| **Joueurs (rangées)** | **Fabrice (3)** – Arnaud (1) – Alex (4) – Laurent (8) |
| **Ensemble des points** | 220 points détaillés (1 – 220) |

### 1. Résultat du match
- Le match s'est conclu par un score de **6‑4**.
- Le dernier point signalé était un **faute directe** de Laurent (#220), indiquant que le match était encore en cours ou que le rapport n'inclut pas le point final.
- Les points de victoire (*Point Gagnant*) sont répartis entre Fabrice, Alex, Arnaud, et Laurent, avec des actions dominantes comme les *volées* et les *smash*.

### 2. Types de points observés
| Catégorie | Nombre (approximatif) | Principales actions |
|-----------|-----------------------|---------------------|
| **Points gagnants** | ~15 % (environ 30) | Volées (coup droit, revers), smash, services puissants |
| **Faute directe** | ~12 % | Fréquent chez Arnaud, Alex, Fabrice, et Laurent |
| **Faute provoquée** | ~50 % | Arnaud et Laurent provoquent souvent des fautes chez leurs adversaires (Alex, Fabrice). |
| **Volées (ex. « 🎾 Volée coup droit »)** | Plusieurs fois | Stratégie clé pour gagner des points rapides |

### 3. Tendances observées
- **Arnaud** et **Laurent** sont les principaux *forceurs* de fautes.  
  - Arnaud provoque des fautes sur Alex et Laurent, tandis que Laurent cible Arnaud et Fabrice.
- **Alex** montre plusieurs *faute directe* dans la série de points, ce qui indique des difficultés de maintien de la constance.
- **Fabrice** affiche un mélange de *faute directe* et de *volées* réussies, indiquant un jeu plus technique mais aussi fragile.
- La majorité des points gagnants impliquent des *volées*, soulignant l'importance du jeu de volée dans ce match.

### 4. Points marquants
- **Smash** et **serve** puissants, notamment par Arnaud et Alex.  
- **Volées** fréquentes comme tactique gagnante, notamment par Fabrice et Alex.  
- Plusieurs *faute provoquée* sont dues à des échanges de coups puissants (smash, service) provoquant des fautes du receveur.

### 5. Conclusion
- Le match a été dominé par un nombre élevé de *faute provoquée*, mettant en évidence un jeu agressif et de forte pression.  
- La distribution des *points gagnants* montre une préférence pour le jeu de volée, indiquant que les joueurs qui maîtrisaient cette tactique ont eu un avantage décisif.  
- Le rapport montre une forte tension et un jeu très contesté, avec des erreurs fréquentes de tous les joueurs.

---

Ce résumé offre une vue d'ensemble du déroulement du match, de la répartition des points, des erreurs et des stratégies clés employées par chaque joueur."""

print("🧹 Nettoyage du texte...")
cleaned = clean_text_for_speech(test_text)

print("\n" + "="*80)
print("TEXTE NETTOYÉ (ce qui sera lu):")
print("="*80)
print(cleaned)
print("="*80)

print("\n🎙️ Génération de l'audio...")
temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
temp_path = temp_file.name
temp_file.close()

asyncio.run(generate_speech(cleaned, temp_path))

print(f"✅ Audio généré: {temp_path}")
print("🔊 Lecture en cours...")

playsound(temp_path)

print("✅ Lecture terminée!")

# Nettoyage
os.unlink(temp_path)
print("🗑️ Fichier temporaire supprimé")
