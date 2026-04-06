"""
Fenêtre de test de prompts IA en live
Permet de tester et affiner les prompts avant intégration
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import os
import json
import requests
from pathlib import Path
from datetime import datetime
import glob
import asyncio
import edge_tts
import threading
import tempfile
from playsound import playsound
import re


class PromptTesterWindow:
    """Fenêtre pour tester les prompts IA en temps réel"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🧪 Test de Prompts IA - PFPADEL")
        self.root.geometry("1400x900")
        self.root.configure(bg="#f5f7fa")
        
        # Configuration Groq (ultra rapide !)
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-70b-versatile"  # Llama 3.1 70B ultra rapide
        self.timeout = 120  # 2 minutes max
        self.voice = "fr-FR-DeniseNeural"  # Voix française naturelle
        self.is_playing = False
        self.last_analysis = ""
        
        # Charger le dernier autosave
        self.match_data = self.load_latest_autosave()
        
        # Vérifier RAG
        self.rag_available = False
        self.rag_context = ""
        try:
            from padel_rag import PadelRAG
            self.rag = PadelRAG()
            stats = self.rag.get_stats()
            if stats['total_chunks'] > 0:
                self.rag_available = True
                print(f"✓ RAG disponible: TACTIQUES GAGNANTES uniquement (filtré sur 3 livres)")
        except:
            print("⚠ RAG non disponible")
        
        self.create_ui()
    
    def load_latest_autosave(self):
        """Charge le rapport HTML au lieu du JSON"""
        html_path = r"E:\projet\padel stat\data\rapport_nouveau_format.html"
        
        if not os.path.exists(html_path):
            print("ERREUR - Fichier HTML non trouvé")
            return None
        
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            print(f"✓ Rapport HTML chargé: {os.path.basename(html_path)}")
            print(f"  {len(html_content)} caractères")
            
            return {'html_content': html_content, 'type': 'html'}
        except Exception as e:
            print(f"ERREUR - Impossible de charger {html_path}: {e}")
            return None
    
    def create_ui(self):
        """Créer l'interface"""
        
        # En-tête
        header = tk.Frame(self.root, bg="#667eea", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="🧪 Test de Prompts IA",
            font=("Segoe UI", 24, "bold"),
            bg="#667eea",
            fg="white"
        )
        title.pack(pady=20)
        
        # Infos match
        if self.match_data:
            if self.match_data.get('type') == 'html':
                info_text = "Rapport HTML chargé pour analyse de commentaire"
            else:
                joueurs = self.match_data.get('match', {}).get('joueurs', [])
                if isinstance(joueurs[0], dict):
                    noms = [j.get('nom', '') for j in joueurs]
                else:
                    noms = joueurs
                
                info_text = f"Match: {' vs '.join(noms)} • {len(self.match_data.get('points', []))} points"
            
            if self.rag_available:
                info_text += " • RAG: TACTIQUES GAGNANTES ✓"
        else:
            info_text = "Aucun match chargé"
        
        info_label = tk.Label(
            self.root,
            text=info_text,
            font=("Segoe UI", 10),
            bg="#f5f7fa",
            fg="#667eea"
        )
        info_label.pack(pady=10)
        
        # Container principal
        main_container = tk.Frame(self.root, bg="#f5f7fa")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # === COLONNE GAUCHE: Prompt ===
        left_frame = tk.Frame(main_container, bg="#f5f7fa")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        prompt_label = tk.Label(
            left_frame,
            text="✏️ Votre Prompt (instructions pour l'IA)",
            font=("Segoe UI", 12, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        )
        prompt_label.pack(anchor="w", pady=(0, 5))
        
        self.prompt_text = scrolledtext.ScrolledText(
            left_frame,
            font=("Consolas", 13),
            wrap=tk.WORD,
            bg="white",
            fg="#2d3748",
            insertbackground="#667eea",
            relief="solid",
            borderwidth=1
        )
        self.prompt_text.pack(fill="both", expand=True)
        
        # Prompt par défaut (nouveau: résumé HTML optimisé pour audio)
        default_prompt = """Tu es un commentateur sportif professionnel de padel.

Voici un rapport HTML complet d'analyse d'un match.

Ta mission :
1️⃣ Crée un commentaire AUDIO synthétique et fluide (200-300 mots MAX)
2️⃣ Structure SIMPLE en 3 parties :
   - Résultat et dynamique générale (2-3 phrases)
   - Points forts de chaque joueur (1 phrase par joueur)
   - Conseil tactique principal (1-2 phrases)

3️⃣ RÈGLES STRICTES :
   ❌ N'INVENTE AUCUN chiffre, AUCUNE stat qui n'est pas dans le rapport
   ❌ Pas de tableaux, pas de listes à puces
   ❌ Pas de symboles (#, *, •, →)
   ❌ Pas d'emojis
   ❌ Pas de parenthèses avec chiffres entre parenthèses
   ✅ Phrases courtes et claires (max 15 mots/phrase)
   ✅ Langage parlé naturel (comme un commentateur TV)
   ✅ Utilise "nous constatons", "on observe", "il apparaît que"

4️⃣ FORMAT DE SORTIE :
   - Texte brut uniquement (pas de HTML)
   - Pas de titres avec ### ou **
   - Séparations par des points, pas de sauts de ligne multiples
   - Style narratif fluide

EXEMPLE DE BON FORMAT :
"Le match s'est terminé sur le score de 6 à 4. Nous observons une forte intensité tout au long de la partie. Arnaud montre une excellente efficacité au filet avec des volées précises. Fabrice affiche un bon placement défensif mais commet quelques fautes directes. Laurent provoque de nombreuses erreurs adverses grâce à son jeu agressif. Alex excelle dans les échanges longs. Le conseil principal serait de travailler la régularité sur les coups de fond de court."

Maintenant, analyse le rapport ci-dessous et produis ton commentaire audio (200-300 mots, texte brut uniquement) :"""
        
        self.prompt_text.insert("1.0", default_prompt)
        
        # Boutons
        buttons_frame = tk.Frame(left_frame, bg="#f5f7fa")
        buttons_frame.pack(pady=10, fill="x")
        
        self.analyze_btn = tk.Button(
            buttons_frame,
            text="🚀 LANCER L'ANALYSE",
            font=("Segoe UI", 11, "bold"),
            bg="#667eea",
            fg="white",
            activebackground="#5568d3",
            activeforeground="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.run_analysis
        )
        self.analyze_btn.pack(side="left", padx=(0, 10))
        
        # Bouton ÉCOUTER
        self.listen_btn = tk.Button(
            buttons_frame,
            text="🔊 ÉCOUTER L'ANALYSE",
            font=("Segoe UI", 11, "bold"),
            bg="#48bb78",
            fg="white",
            activebackground="#38a169",
            activeforeground="white",
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.play_analysis,
            state="disabled"
        )
        self.listen_btn.pack(side="left", padx=(0, 10))
        
        clear_btn = tk.Button(
            buttons_frame,
            text="🗑️ Effacer",
            font=("Segoe UI", 10),
            bg="#e2e8f0",
            fg="#2d3748",
            activebackground="#cbd5e0",
            relief="flat",
            padx=15,
            pady=10,
            cursor="hand2",
            command=lambda: self.prompt_text.delete("1.0", tk.END)
        )
        clear_btn.pack(side="left")
        
        # === COLONNE DROITE: Résultat ===
        right_frame = tk.Frame(main_container, bg="#f5f7fa")
        right_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        result_label = tk.Label(
            right_frame,
            text="📊 Résultat de l'IA",
            font=("Segoe UI", 12, "bold"),
            bg="#f5f7fa",
            fg="#2d3748"
        )
        result_label.pack(anchor="w", pady=(0, 5))
        
        self.result_text = scrolledtext.ScrolledText(
            right_frame,
            font=("Segoe UI", 13),
            wrap=tk.WORD,
            bg="white",
            fg="#2d3748",
            relief="solid",
            borderwidth=1,
            state="disabled"
        )
        self.result_text.pack(fill="both", expand=True)
        
        # Status bar
        self.status_label = tk.Label(
            self.root,
            text="Prêt • Écrivez votre prompt et cliquez sur 'Lancer l'analyse'",
            font=("Segoe UI", 9),
            bg="#f5f7fa",
            fg="#718096",
            anchor="w",
            padx=20
        )
        self.status_label.pack(fill="x", pady=(5, 10))
    
    def run_analysis(self):
        """Lance l'analyse avec le prompt actuel"""
        
        if not self.match_data:
            messagebox.showerror("Erreur", "Aucun match chargé")
            return
        
        user_prompt = self.prompt_text.get("1.0", tk.END).strip()
        
        if not user_prompt:
            messagebox.showwarning("Attention", "Écrivez d'abord un prompt")
            return
        
        # Désactiver le bouton
        self.analyze_btn.config(state="disabled", text="⏳ Analyse en cours...")
        self.status_label.config(text="� Envoi à Groq (ultra rapide)...")
        self.root.update()
        
        try:
            # Construire le prompt complet
            full_prompt = self.build_full_prompt(user_prompt)
            
            # Afficher dans le résultat
            self.update_result("⏳ Envoi à Groq...\n\n(Cela devrait prendre 20-30 secondes)\n")
            
            # Appeler Groq
            self.status_label.config(text="🤖 L'IA analyse (Groq ultra rapide)...")
            self.root.update()
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                self.groq_url,
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": full_prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=self.timeout
            )
            
            # Si erreur, afficher les détails
            if response.status_code != 200:
                error_details = response.json()
                raise Exception(f"Groq API Error: {error_details}")
            
            response.raise_for_status()
            
            result = response.json()
            analysis = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            if not analysis:
                raise Exception("Réponse vide de Groq")
            
            # Afficher le résultat
            self.update_result(analysis)
            self.last_analysis = analysis
            self.listen_btn.config(state="normal")  # Activer le bouton écouter
            self.status_label.config(text="✅ Analyse terminée")
            
        except requests.exceptions.Timeout:
            self.update_result("❌ ERREUR: Timeout (>2 min)\n\nEssayez un prompt plus court.")
            self.status_label.config(text="❌ Timeout")
        except requests.exceptions.ConnectionError:
            self.update_result("❌ ERREUR: Impossible de se connecter à Groq\n\nVérifiez votre connexion internet.")
            self.status_label.config(text="❌ Groq non disponible")
        except Exception as e:
            self.update_result(f"❌ ERREUR:\n\n{e}")
            self.status_label.config(text=f"❌ Erreur: {e}")
        finally:
            self.analyze_btn.config(state="normal", text="🚀 LANCER L'ANALYSE")
    
    def build_full_prompt(self, user_prompt):
        """Construit le prompt complet avec le HTML"""
        parts = []
        
        # Prompt utilisateur
        parts.append(user_prompt)
        parts.append("\n" + "="*80 + "\n")
        
        # Pas de RAG pour le résumé HTML (on résume juste le rapport)
        
        # Contenu HTML du rapport
        if self.match_data and self.match_data.get('type') == 'html':
            parts.append("=== RAPPORT HTML À RÉSUMER ===\n")
            html_content = self.match_data.get('html_content', '')
            
            # Nettoyer le HTML (enlever scripts, styles)
            import re
            # Enlever les scripts
            html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL)
            # Enlever les styles
            html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL)
            
            parts.append(html_clean)
            parts.append("\n" + "="*80 + "\n")
        
        parts.append("\nRésume maintenant ce rapport:")
        
        return "\n".join(parts)
    
    def update_result(self, text):
        """Met à jour le texte du résultat"""
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        self.result_text.config(state="disabled")
        self.root.update()
    
    def play_analysis(self):
        """Lit l'analyse avec synthèse vocale Edge-TTS"""
        if not self.last_analysis:
            messagebox.showwarning("Attention", "Aucune analyse à lire")
            return
        
        if self.is_playing:
            messagebox.showinfo("Info", "Lecture audio déjà en cours")
            return
        
        # Lancer la synthèse dans un thread séparé
        thread = threading.Thread(target=self._play_tts_thread, daemon=True)
        thread.start()
    
    def _play_tts_thread(self):
        """Thread pour la synthèse vocale (asynchrone)"""
        try:
            self.is_playing = True
            self.listen_btn.config(state="disabled", text="🔊 Lecture en cours...")
            self.status_label.config(text="🔊 Synthèse vocale en cours...")
            self.root.update()
            
            # Nettoyer le texte (enlever HTML)
            text = self._clean_html(self.last_analysis)
            
            # Créer fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_path = temp_file.name
            temp_file.close()
            
            # Synthèse TTS
            asyncio.run(self._generate_speech(text, temp_path))
            
            # Lecture
            self.status_label.config(text="🔊 Lecture audio...")
            playsound(temp_path)
            
            # Nettoyage
            os.unlink(temp_path)
            
            self.status_label.config(text="✅ Lecture terminée")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lecture audio:\n{e}")
            self.status_label.config(text="❌ Erreur lecture audio")
        finally:
            self.is_playing = False
            self.listen_btn.config(state="normal", text="🔊 ÉCOUTER L'ANALYSE")
    
    async def _generate_speech(self, text, output_path):
        """Génère le fichier audio avec Edge-TTS"""
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
    
    def _clean_html(self, text):
        """Nettoie le HTML pour la lecture vocale naturelle - PARSING COMPLET"""
        import html
        
        # Décoder les entités HTML d'abord
        text = html.unescape(text)
        
        # Enlever complètement les balises script et style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Enlever toutes les balises HTML
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Enlever TOUS les emojis et symboles spéciaux
        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26FF\u2700-\u27BF\U0001F300-\U0001F9FF]', '', text)
        
        # ENLEVER TOUS LES SYMBOLES (*, #, •, -, etc.)
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
        
        # Enlever tirets et slashes (sauf dans les mots composés)
        text = re.sub(r'\s+-\s+', ' ', text)  # Tiret entouré d'espaces
        text = re.sub(r'--+', ' ', text)  # Tirets multiples
        text = text.replace('/', ' ')
        
        # Enlever parenthèses et crochets vides ou avec peu de contenu
        text = re.sub(r'\([^)]{0,3}\)', '', text)
        text = re.sub(r'\[[^\]]{0,3}\]', '', text)
        text = re.sub(r'\{[^}]{0,3}\}', '', text)
        
        # Remplacer les virgules par des points (pauses plus claires)
        text = text.replace(',', '. ')
        
        # Enlever les pourcentages isolés et nombres sans contexte
        text = re.sub(r'\b\d+\s*%', '', text)  # Pourcentages
        text = re.sub(r'\b\d+\.\d+\b', '', text)  # Décimaux isolés
        
        # Enlever les répétitions de mots (bug d'IA)
        words = text.split()
        cleaned_words = []
        for i, word in enumerate(words):
            if i == 0 or word.lower() != words[i-1].lower():
                cleaned_words.append(word)
        text = ' '.join(cleaned_words)
        
        # Nettoyer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Nettoyer les points multiples
        text = re.sub(r'\.{2,}', '.', text)
        
        # Supprimer les lignes vides
        text = re.sub(r'\n\s*\n', '\n', text)
        
        return text.strip()
    
    def run(self):
        """Lance la fenêtre"""
        self.root.mainloop()


if __name__ == "__main__":
    app = PromptTesterWindow()
    app.run()
