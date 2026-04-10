"""
Script simple pour communiquer avec Ollama
Utilise le modèle GPTOS 20B (ou autre modèle configuré)
Version améliorée avec gestion d'erreurs, timeout et vérification de statut
Peut analyser les matchs de padel et leurs statistiques
"""

import requests
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List

# Sauvegarde de la fonction print d'origine pour gérer les emojis sur Windows
_builtin_print = print


def safe_print(*args, **kwargs):
    """Imprime en remplaçant les caractères non encodables si nécessaire."""
    try:
        _builtin_print(*args, **kwargs)
    except UnicodeEncodeError:
        file = kwargs.get("file", sys.stdout)
        encoding = getattr(file, "encoding", None) or "utf-8"
        sep = kwargs.get("sep", " ")
        end = kwargs.get("end", "\n")
        flush = kwargs.get("flush", False)
        text = sep.join(str(arg) for arg in args)
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        file.write(safe_text)
        file.write(end)
        if flush:
            file.flush()


# Redéfinition globale pour le script
print = safe_print

# Configuration
OLLAMA_URL = "http://57.129.110.251:11434/api/generate"
MODEL_NAME = "qwen2.5:3b"  # Modèle hébergé sur serveur distant
TIMEOUT = 30  # Timeout en secondes
MAX_HISTORY = 3  # Nombre maximum d'échanges à conserver dans l'historique
DATA_DIR = Path("data")  # Répertoire des fichiers de match

# Contexte système pour l'IA - Instructions d'analyse de padel
SYSTEM_PROMPT = """Tu es une IA spécialisée dans l'analyse de statistiques de PADEL.

Tu vas recevoir un fichier JSON qui décrit un match de padel filmé et annoté.
Ce fichier contient :
- Les informations du match (date, joueurs, équipes, positions)
- La liste chronologique des points avec événements détaillés
- Des statistiques déjà calculées par joueur

IMPORTANT :
- Le padel se joue en 2 équipes de 2 joueurs
- Un point peut être :
  - "point_gagnant"
  - "faute_directe"
  - "faute_provoquee"
- Une faute provoquée est attribuée à l'attaquant, mais pénalise le défenseur
- Certaines entrées peuvent être en double (même timestamp et frame) → ne pas les recompter deux fois
- Les statistiques finales se trouvent dans l'objet "stats"

TON RÔLE :
1. Vérifier la cohérence globale des statistiques
2. Résumer les performances de chaque joueur
3. Identifier :
   - joueur le plus offensif
   - joueur le plus en difficulté
   - joueur le plus propre (peu de fautes)
4. Comparer les deux équipes
5. Donner une analyse PADEL (attaque, régularité, fautes, efficacité)

FORMAT DE SORTIE OBLIGATOIRE :
- Résumé global du match
- Analyse par joueur (1 paragraphe chacun)
- Analyse par équipe
- Points forts / points faibles
- Conclusion simple et lisible

INTERDICTIONS :
- Ne pas réécrire le JSON
- Ne pas expliquer le code
- Ne pas inventer de statistiques
- Ne pas faire de théorie générale sur le padel

Tu réponds en français, de manière claire, structurée et orientée analyse sportive.
"""

# Contexte global pour l'analyse de match
match_context = {
    "match_data": None,
    "match_file": None,
    "stats": None
}

def load_match_data(match_file: str) -> Optional[Dict]:
    """
    Charge les données d'un match depuis un fichier JSON
    
    Args:
        match_file: Chemin vers le fichier JSON du match
        
    Returns:
        Dictionnaire avec les données du match ou None
    """
    try:
        with open(match_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {match_file}")
        return None
    except json.JSONDecodeError:
        print(f"❌ Erreur de lecture du fichier JSON: {match_file}")
        return None
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return None

def analyze_match_stats(match_data: Dict) -> Dict:
    """
    Utilise les statistiques DÉJÀ CALCULÉES par l'AnnotationManager
    (au lieu de les recalculer depuis la liste des points)
    
    Args:
        match_data: Données du match avec clé "stats" contenant les stats complètes
        
    Returns:
        Dictionnaire avec les statistiques (format compatible LiveHTML)
    """
    points = match_data.get("points", [])
    match_info = match_data.get("match", {})
    
    # PRIORITÉ AUX STATS DÉJÀ CALCULÉES (complètes et exactes)
    annotation_stats = match_data.get("stats", {})
    
    stats = {
        "total_points": len(points),
        "joueurs": {},
        "types_coups": {},
        "fautes": {"directes": 0, "provoquees": 0}
    }
    
    # Convertir depuis le format AnnotationManager vers le format attendu
    for joueur_nom, joueur_stats in annotation_stats.items():
        if joueur_nom == "match":  # Sauter les stats globales
            continue
            
        pg = joueur_stats.get("points_gagnants", 0)
        fd = joueur_stats.get("fautes_directes", 0)
        fp_generees = joueur_stats.get("fautes_provoquees_generees", 0)
        fp_subies = joueur_stats.get("fautes_provoquees_subies", 0)
        
        stats["joueurs"][joueur_nom] = {
            "points_gagnes": pg,
            "fautes_directes": fd,
            "fautes_provoquees": fp_generees,  # Compatibilité avec LiveHTML
            "fautes_subies": fp_subies,  # Compatibilité avec LiveHTML
            "impact": (pg + fp_generees) - (fd + fp_subies),
            "types_coups": joueur_stats.get("points_gagnants_detail", {})
        }
        
        stats["fautes"]["directes"] += fd
        stats["fautes"]["provoquees"] += fp_generees
    
    return stats

def format_match_context(match_data: Dict, stats: Dict) -> str:
    """
    Formate les données du match en texte pour le contexte Ollama
    UTILISE LES STATS COMPLÈTES DU JSON (fautes_subies, impact, etc.)
    
    Args:
        match_data: Données du match
        stats: Statistiques calculées (peut être ignoré si match_data contient "stats")
        
    Returns:
        Texte formaté pour le contexte
    """
    match_info = match_data.get("match", {})
    joueurs = match_info.get("joueurs", [])
    joueurs_str = ", ".join([p if isinstance(p, str) else p.get("nom", "") for p in joueurs])
    
    # PRIORITÉ AUX STATS DU JSON (complètes avec fautes_subies, impact, etc.)
    json_stats = match_data.get("stats", {})
    if json_stats and "joueurs" in json_stats:
        stats = json_stats  # Utiliser les stats du JSON
    
    total_points = stats.get("total_points", len(match_data.get("points", [])))
    
    context = f"""CONTEXTE DU MATCH ANALYSÉ:
Date: {match_info.get('date', 'Inconnue')}
Joueurs: {joueurs_str}
Total de points annotés: {total_points}

STATISTIQUES COMPLÈTES PAR JOUEUR:
"""
    
    for joueur, player_stats in stats.get("joueurs", {}).items():
        context += f"\n{joueur}:"
        context += f"\n  - Points gagnants: {player_stats.get('points_gagnes', 0)}"
        context += f"\n  - Fautes directes: {player_stats.get('fautes_directes', 0)}"
        
        # Fautes provoquées SUBIES (défenseur) vs GÉNÉRÉES (attaquant)
        # Compatible avec anciens et nouveaux noms de champs
        fp_subies = player_stats.get('fautes_provoquees_subies', 
                                      player_stats.get('fautes_subies',
                                      player_stats.get('fautes_provoquees_defenseur', 0)))
        fp_generees = player_stats.get('fautes_provoquees_generees',
                                       player_stats.get('fautes_provoquees',
                                       player_stats.get('fautes_provoquees_attaquant', 0)))
        context += f"\n  - Fautes SUBIES (défenseur): {fp_subies}"
        context += f"\n  - Fautes GÉNÉRÉES (attaquant): {fp_generees}"
        
        # NOUVEAU: Impact sur le match (différentiel)
        impact = player_stats.get('impact', 0)
        if impact != 0:
            context += f"\n  - IMPACT SUR LE MATCH: {impact:+d} points"
        
        # Coups gagnants par type
        if player_stats.get('types_coups'):
            context += "\n  - Points gagnants par coup:"
            for coup, count in player_stats['types_coups'].items():
                if count > 0:
                    context += f"\n    • {coup}: {count}"
        
        # NOUVEAU: Coups techniques détaillés
        coups_tech = player_stats.get('coups_techniques', {})
        if coups_tech:
            context += "\n  - Analyse technique:"
            for coup_type, details in coups_tech.items():
                total = details.get('total', 0)
                if total > 0:
                    gagnants = details.get('gagnants', 0)
                    fautes = details.get('fautes', 0)
                    reussite = (gagnants / total * 100) if total > 0 else 0
                    context += f"\n    • {coup_type}: {total} coups ({reussite:.0f}% réussite - {gagnants} gagnants, {fautes} fautes)"
    
    context += f"\n\nFAUTES TOTALES:"
    context += f"\n  - Fautes directes: {stats.get('fautes', {}).get('directes', 0)}"
    context += f"\n  - Fautes provoquées: {stats.get('fautes', {}).get('provoquees', 0)}"
    
    context += "\n\n---\n"
    
    return context

def list_available_matches() -> List[str]:
    """
    Liste tous les fichiers de match disponibles dans le répertoire data
    
    Returns:
        Liste des noms de fichiers de match
    """
    if not DATA_DIR.exists():
        return []
    
    matches = []
    for file in DATA_DIR.glob("match_*.json"):
        matches.append(file.name)
    
    return sorted(matches, reverse=True)  # Plus récents en premier

def check_ollama_status() -> bool:
    """
    Vérifie si Ollama est démarré et accessible
    
    Returns:
        True si Ollama est accessible, False sinon
    """
    try:
        response = requests.get("http://57.129.110.251:11434/api/tags", timeout=5)
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except Exception:
        return False

def chat_with_ollama(prompt: str, stream: bool = True, timeout: int = TIMEOUT) -> str:
    """
    Envoie un prompt à Ollama et récupère la réponse
    
    Args:
        prompt: Le texte à envoyer au modèle
        stream: Si True, affiche la réponse en temps réel
        timeout: Timeout en secondes pour la requête
    
    Returns:
        La réponse complète du modèle
    """
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": stream
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=stream, timeout=timeout)
        response.raise_for_status()
        
        full_response = ""
        
        if stream:
            # Affichage en streaming
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    data = json.loads(line)
                    token = data.get("response", "")
                    print(token, end="", flush=True)
                    full_response += token
                    
                    if data.get("done", False):
                        print()  # Nouvelle ligne à la fin
                        break
        else:
            # Réponse complète
            data = response.json()
            full_response = data.get("response", "")
            print(full_response)
        
        return full_response
        
    except requests.exceptions.ConnectionError:
        print("❌ Erreur: Impossible de se connecter à Ollama.")
        print("   Assurez-vous qu'Ollama est lancé (ollama serve)")
        return ""
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP: {e}")
        if e.response.status_code == 404:
            print(f"   Le modèle '{MODEL_NAME}' est-il bien installé? (ollama pull {MODEL_NAME})")
        return ""
    except requests.exceptions.Timeout:
        print(f"❌ Timeout: La requête a dépassé {timeout} secondes")
        return ""
    except json.JSONDecodeError:
        print("❌ Erreur: Réponse d'Ollama mal formatée")
        return ""
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        return ""

def chat_interactif():
    """Mode chat interactif avec Ollama et analyse de match"""
    print("=" * 60)
    print(f"Chat Ollama - Modèle: {MODEL_NAME}")
    print("Analyse de matchs de Padel")
    print("=" * 60)
    print("Commandes spéciales:")
    print("  - 'exit' ou 'quit': Quitter")
    print("  - 'clear': Effacer l'historique")
    print("  - 'status': Vérifier le statut d'Ollama")
    print("  - 'matches': Lister les matchs disponibles")
    print("  - 'load <fichier>': Charger un match pour l'analyser")
    print("  - 'info': Afficher les infos du match chargé")
    print("-" * 60)
    
    historique = []
    
    # Vérification initiale
    if not check_ollama_status():
        print("⚠️  Ollama n'est pas accessible. Démarrez-le avec: ollama serve")
        print("   Le script peut quand même fonctionner si Ollama démarre plus tard.")
        input("Appuyez sur Entrée pour continuer...")
    
    # 🔥 AUTO-CHARGEMENT du dernier match disponible
    print("\n🔍 Recherche du dernier match...")
    matches = list_available_matches()
    if matches:
        latest_match = matches[0]  # Le plus récent
        filepath = DATA_DIR / latest_match
        match_data = load_match_data(filepath)
        
        if match_data:
            match_context["match_data"] = match_data
            match_context["match_file"] = latest_match
            match_context["stats"] = analyze_match_stats(match_data)
            
            match_info = match_data.get("match", {})
            joueurs = match_info.get("joueurs", [])
            joueurs_str = ", ".join([p if isinstance(p, str) else p.get("nom", "") for p in joueurs])
            
            print(f"✅ Match chargé automatiquement: {latest_match}")
            print(f"   📅 Date: {match_info.get('date', 'Inconnue')}")
            print(f"   👥 Joueurs: {joueurs_str}")
            print(f"   📊 Points annotés: {match_context['stats']['total_points']}")
            print("\n💡 Le match est prêt à être analysé ! Posez vos questions.")
    else:
        print("ℹ️  Aucun match trouvé dans le dossier 'data'")
        print("   Utilisez 'matches' pour lister les matchs disponibles")
    
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n🧑 Vous: ").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Au revoir!")
                break
                
            if user_input.lower() == 'clear':
                historique = []
                print("✨ Historique effacé")
                continue
                
            if user_input.lower() == 'status':
                status = "✅ Ollama accessible" if check_ollama_status() else "❌ Ollama inaccessible"
                print(f"📊 Statut: {status}")
                if match_context["match_data"]:
                    print(f"📋 Match chargé: {match_context['match_file']}")
                else:
                    print("📋 Aucun match chargé")
                continue
            
            if user_input.lower() == 'matches':
                matches = list_available_matches()
                if matches:
                    print(f"\n📁 {len(matches)} match(s) disponible(s):")
                    for i, match in enumerate(matches[:10], 1):  # Limiter à 10
                        print(f"  {i}. {match}")
                    if len(matches) > 10:
                        print(f"  ... et {len(matches) - 10} autres")
                    print("\nUtilisez 'load <fichier>' pour charger un match")
                else:
                    print("❌ Aucun match trouvé dans le dossier 'data'")
                continue
            
            if user_input.lower().startswith('load '):
                filename = user_input[5:].strip()
                
                # Si c'est un numéro, charger depuis la liste
                if filename.isdigit():
                    matches = list_available_matches()
                    idx = int(filename) - 1
                    if 0 <= idx < len(matches):
                        filename = matches[idx]
                    else:
                        print(f"❌ Numéro invalide. Utilisez 'matches' pour voir la liste.")
                        continue
                
                # Ajouter le chemin complet
                if not filename.startswith("data"):
                    filepath = DATA_DIR / filename
                else:
                    filepath = Path(filename)
                
                # Charger le match
                match_data = load_match_data(filepath)
                if match_data:
                    match_context["match_data"] = match_data
                    match_context["match_file"] = filename
                    match_context["stats"] = analyze_match_stats(match_data)
                    
                    match_info = match_data.get("match", {})
                    joueurs = match_info.get("joueurs", [])
                    joueurs_str = ", ".join([p if isinstance(p, str) else p.get("nom", "") for p in joueurs])
                    
                    print(f"✅ Match chargé: {filename}")
                    print(f"   Joueurs: {joueurs_str}")
                    print(f"   Points: {match_context['stats']['total_points']}")
                    print("\nVous pouvez maintenant poser des questions sur ce match!")
                continue
            
            if user_input.lower() == 'info':
                if match_context["match_data"]:
                    context = format_match_context(
                        match_context["match_data"],
                        match_context["stats"]
                    )
                    print("\n" + context)
                else:
                    print("❌ Aucun match chargé. Utilisez 'load <fichier>' d'abord.")
                continue
            
            # Construire le contexte avec le match si chargé
            prompt_parts = []
            
            # Ajouter le contexte système si un match est chargé
            if match_context["match_data"]:
                prompt_parts.append(SYSTEM_PROMPT)
                prompt_parts.append("")  # Ligne vide pour séparer
                
                # Ajouter le contexte du match
                match_ctx = format_match_context(
                    match_context["match_data"],
                    match_context["stats"]
                )
                prompt_parts.append(match_ctx)
            
            # Ajouter l'historique
            if historique:
                contexte = "\n".join([
                    f"User: {h['user']}\nAssistant: {h['assistant']}" 
                    for h in historique[-MAX_HISTORY:]
                ])
                prompt_parts.append(contexte)
            
            # Ajouter la question actuelle
            prompt_parts.append(f"User: {user_input}\nAssistant:")
            
            prompt = "\n".join(prompt_parts)
            
            print("\n🤖 Assistant: ", end="", flush=True)
            reponse = chat_with_ollama(prompt, stream=True)
            
            # Sauvegarder dans l'historique
            if reponse:
                historique.append({
                    "user": user_input,
                    "assistant": reponse
                })
                
        except KeyboardInterrupt:
            print("\n\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")

def exemple_simple():
    """Exemple d'utilisation simple"""
    print("Exemple d'utilisation simple d'Ollama\n")
    
    # Vérifier le statut avant de commencer
    if not check_ollama_status():
        print("❌ Ollama n'est pas accessible. Démarrez-le d'abord.")
        return
    
    prompts = [
        "Explique-moi ce qu'est le padel en une phrase.",
        "Quelle est la capitale de la France?",
        "Écris un haiku sur le tennis."
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'='*60}")
        print(f"Question {i}: {prompt}")
        print(f"{'='*60}")
        print("Réponse: ", end="", flush=True)
        chat_with_ollama(prompt, stream=True)
        print()

def prompt_unique(prompt: str):
    """Exécute un prompt unique"""
    print(f"Question: {prompt}\n")
    print("Réponse: ", end="", flush=True)
    reponse = chat_with_ollama(prompt, stream=True)
    return reponse

if __name__ == "__main__":
    # Vérifier et afficher le statut au démarrage
    status = check_ollama_status()
    status_msg = "✅ Ollama accessible" if status else "⚠️  Ollama inaccessible"
    print(f"\n{status_msg}")
    
    # Gestion des arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "exemple":
            exemple_simple()
        elif sys.argv[1] == "status":
            print(f"📊 Statut Ollama: {status_msg}")
        else:
            # Utiliser l'argument comme prompt unique
            prompt = " ".join(sys.argv[1:])
            prompt_unique(prompt)
    else:
        # Mode interactif par défaut
        chat_interactif()
