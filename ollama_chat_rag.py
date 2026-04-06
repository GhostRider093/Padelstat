"""
Chat IA avec Ollama enrichi par RAG (Retrieval Augmented Generation)
Version améliorée de ollama_chat.py avec connaissances des livres de padel
"""

import requests
import json
import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
from padel_rag import PadelRAG

# Sauvegarde de la fonction print d'origine
_builtin_print = print


def safe_print(*args, **kwargs):
    """Imprime en remplaçant les caractères non encodables."""
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


print = safe_print

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"
TIMEOUT = 60
MAX_HISTORY = 5
DATA_DIR = Path("data")

# Initialiser le système RAG
rag = PadelRAG()

# Contexte système enrichi
SYSTEM_PROMPT = """Tu es une IA spécialisée dans l'analyse de PADEL.

Tu as accès à :
1. Des statistiques de matchs annotés (JSON)
2. Des connaissances tirées de livres de référence sur le padel

Quand on te pose une question:
- Si elle concerne les STATISTIQUES d'un match spécifique → analyse le JSON
- Si elle concerne la TECHNIQUE, TACTIQUE, THÉORIE → utilise les connaissances des livres
- Si elle mélange les deux → combine les deux sources

IMPORTANT pour les statistiques:
- Le padel se joue en 2 équipes de 2 joueurs
- Points: point_gagnant, faute_directe, faute_provoquee
- Une faute provoquée est attribuée à l'attaquant mais pénalise le défenseur
- Les stats finales sont dans l'objet "stats"

FORMAT DE SORTIE:
- Réponse claire et structurée
- Citations des sources (livre ou stats du match)
- Conseils pratiques quand c'est pertinent

INTERDICTIONS:
- Ne pas inventer de statistiques
- Ne pas réécrire le JSON
- Ne pas faire de théorie sans source

Tu réponds en français, de manière professionnelle et pédagogique.
"""


class OllamaChatRAG:
    """Chat Ollama avec support RAG"""
    
    def __init__(self):
        self.history = []
        self.match_data = None
        self.match_file = None
        self.rag_enabled = True
        
        # Vérifier si la base RAG contient des données
        stats = rag.get_stats()
        if stats['total_chunks'] == 0:
            print("ATTENTION - Base RAG vide. Lancez: python padel_rag.py index")
            self.rag_enabled = False
        else:
            print(f"OK - Base RAG chargee: {stats['total_books']} livre(s), {stats['total_chunks']} chunks")
    
    def load_match(self, match_file: str) -> bool:
        """Charge un fichier de match"""
        try:
            with open(match_file, 'r', encoding='utf-8') as f:
                self.match_data = json.load(f)
            self.match_file = match_file
            print(f"OK - Match charge: {match_file}")
            return True
        except Exception as e:
            print(f"ERREUR - Impossible de charger le match: {e}")
            return False
    
    def build_prompt(self, user_message: str) -> str:
        """Construit le prompt complet avec RAG"""
        parts = []
        
        # Système
        parts.append(SYSTEM_PROMPT)
        parts.append("\n" + "="*60 + "\n")
        
        # Contexte RAG (si activé et pertinent)
        if self.rag_enabled:
            rag_context = rag.get_context_for_query(user_message, n_results=3)
            if rag_context:
                parts.append(rag_context)
                parts.append("\n" + "="*60 + "\n")
        
        # Contexte du match (si chargé)
        if self.match_data:
            parts.append("=== DONNÉES DU MATCH ===")
            parts.append(json.dumps(self.match_data, ensure_ascii=False, indent=2))
            parts.append("\n" + "="*60 + "\n")
        
        # Historique de conversation
        for entry in self.history[-MAX_HISTORY:]:
            parts.append(f"Utilisateur: {entry['user']}")
            parts.append(f"Assistant: {entry['assistant']}")
            parts.append("")
        
        # Question actuelle
        parts.append(f"Utilisateur: {user_message}")
        parts.append("Assistant:")
        
        return "\n".join(parts)
    
    def chat(self, message: str) -> str:
        """Envoie un message et récupère la réponse"""
        if not message.strip():
            return ""
        
        # Construire le prompt avec RAG
        full_prompt = self.build_prompt(message)
        
        # Requête vers Ollama
        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": False
        }
        
        try:
            print("\n[Recherche dans les livres...]" if self.rag_enabled else "\n[Analyse...]")
            
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            
            result = response.json()
            assistant_response = result.get("response", "").strip()
            
            # Ajouter à l'historique
            self.history.append({
                "user": message,
                "assistant": assistant_response
            })
            
            return assistant_response
            
        except requests.exceptions.Timeout:
            return "ERREUR - Timeout (Ollama trop lent ou modèle trop gros)"
        except requests.exceptions.ConnectionError:
            return "ERREUR - Impossible de se connecter à Ollama (est-il lancé ?)"
        except Exception as e:
            return f"ERREUR - {e}"
    
    def clear_history(self):
        """Efface l'historique"""
        self.history = []
        print("Historique efface")
    
    def save_conversation(self, filename: str = "data/conversation_rag.json"):
        """Sauvegarde la conversation"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({
                    "match_file": self.match_file,
                    "history": self.history
                }, f, ensure_ascii=False, indent=2)
            print(f"Conversation sauvegardee: {filename}")
        except Exception as e:
            print(f"ERREUR - Impossible de sauvegarder: {e}")


def interactive_mode():
    """Mode interactif"""
    chat = OllamaChatRAG()
    
    print("\n" + "="*60)
    print("CHAT IA PADEL avec RAG")
    print("="*60)
    print(f"Modele: {MODEL_NAME}")
    print(f"RAG: {'Active' if chat.rag_enabled else 'Desactive (base vide)'}")
    print("\nCommandes:")
    print("  /match <fichier>  - Charger un match")
    print("  /clear            - Effacer l'historique")
    print("  /save             - Sauvegarder la conversation")
    print("  /stats            - Stats de la base RAG")
    print("  /quit             - Quitter")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("Vous: ").strip()
            
            if not user_input:
                continue
            
            # Commandes
            if user_input.startswith("/"):
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                
                if cmd == "/quit":
                    print("Au revoir!")
                    break
                
                elif cmd == "/clear":
                    chat.clear_history()
                
                elif cmd == "/save":
                    chat.save_conversation()
                
                elif cmd == "/stats":
                    stats = rag.get_stats()
                    print(f"\nLivres: {stats['total_books']}")
                    print(f"Chunks: {stats['total_chunks']}")
                    if stats['books']:
                        print("Liste:")
                        for book in stats['books']:
                            print(f"  - {book}")
                
                elif cmd == "/match":
                    if len(cmd_parts) > 1:
                        match_file = cmd_parts[1]
                        if not os.path.exists(match_file):
                            # Essayer dans data/
                            match_file = os.path.join("data", match_file)
                        chat.load_match(match_file)
                    else:
                        print("Usage: /match <fichier>")
                
                else:
                    print(f"Commande inconnue: {cmd}")
                
                continue
            
            # Question normale
            response = chat.chat(user_input)
            print(f"\nIA: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nInterruption. Au revoir!")
            break
        except EOFError:
            break


def main():
    """Point d'entrée principal"""
    if len(sys.argv) > 1:
        # Mode avec fichier de match en argument
        match_file = sys.argv[1]
        
        if not os.path.exists(match_file):
            print(f"ERREUR - Fichier introuvable: {match_file}")
            return
        
        chat = OllamaChatRAG()
        chat.load_match(match_file)
        
        print("\nMatch charge. Mode interactif.\n")
        interactive_mode()
    else:
        # Mode interactif simple
        interactive_mode()


if __name__ == "__main__":
    main()
