"""
Interface de chat agent avec Ollama pour Tkinter
Permet d'interagir avec l'IA pour obtenir des analyses, générer des rapports, etc.
"""

import tkinter as tk
from tkinter import scrolledtext, ttk
from threading import Thread
import requests
import json
import webbrowser
import os


class AgentThread(Thread):
    """Thread pour les requêtes à l'agent Ollama"""
    
    def __init__(self, message, context, callback, error_callback, action_callback):
        super().__init__(daemon=True)
        self.message = message
        self.context = context or {}
        self.callback = callback
        self.error_callback = error_callback
        self.action_callback = action_callback
        self.model = "llama3.2:3b"
        
    def run(self):
        try:
            # Analyser la demande pour détecter des actions
            action_result = self._detect_and_execute_action()
            if action_result:
                return
            
            # Sinon, conversation normale
            system_prompt = self._build_system_prompt()
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\nUtilisateur: {self.message}\n\nAssistant:",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 500
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get("response", "Désolé, je n'ai pas pu générer de réponse.")
                self.callback(answer)
            else:
                self.error_callback(f"Erreur {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error_callback("⏱️ Timeout - L'IA a mis trop de temps à répondre")
        except Exception as e:
            self.error_callback(f"❌ Erreur: {str(e)}")
    
    def _detect_and_execute_action(self):
        """Détecte et exécute des actions basées sur le message"""
        message_lower = self.message.lower()
        
        # Génération de rapport HTML
        if any(word in message_lower for word in ["rapport", "html", "ouvre", "génère", "affiche"]):
            if any(word in message_lower for word in ["rapport", "html"]):
                self.action_callback("generate_report", {})
                self.callback("✅ Je génère le rapport HTML live pour vous...")
                return True
        
        # Analyse du match
        if any(word in message_lower for word in ["analyse", "résumé", "match"]) and "stats" in message_lower:
            self.action_callback("analyze_match", {})
            return True
        
        # Conseils tactiques
        if any(word in message_lower for word in ["conseil", "améliorer", "stratégie", "tactique"]):
            self.action_callback("tactical_advice", {})
            return True
        
        return False
    
    def _build_system_prompt(self):
        """Construit le prompt système avec contexte"""
        prompt = """Tu es un assistant expert en padel intégré dans l'application Padel Stat.

Tu peux aider l'utilisateur à:
- Analyser les statistiques de match
- Générer des rapports HTML (dis "rapport HTML" ou "génère le rapport")
- Donner des conseils tactiques
- Expliquer les données
- Répondre aux questions sur le padel

Contexte actuel:
"""
        
        if self.context.get("match_loaded"):
            prompt += f"\n- Match en cours: {self.context.get('match_name', 'Sans nom')}"
            prompt += f"\n- Nombre de points: {self.context.get('num_points', 0)}"
            
            if self.context.get("score"):
                prompt += f"\n- Score: {self.context['score']}"
        else:
            prompt += "\n- Aucun match chargé actuellement"
        
        prompt += "\n\nRéponds de manière concise et utile en français (max 250 mots). Utilise des emojis pour rendre tes réponses plus vivantes 🎾"
        
        return prompt


class AgentChatWindow:
    """Fenêtre de chat avec l'agent IA - peut être intégrée ou détachée"""
    
    def __init__(self, parent, container=None, action_callback=None):
        """
        parent: fenêtre parente (MainWindow)
        container: Frame parent pour mode intégré (None = mode détaché)
        action_callback: fonction appelée quand l'agent déclenche une action
                        Signature: action_callback(action_type, params)
        """
        self.parent = parent
        self.action_callback = action_callback
        self.context = {}
        self.agent_thread = None
        self.is_detached = container is None
        self.container = container
        self.detached_window = None
        
        if self.is_detached:
            # Mode détaché - créer une fenêtre Toplevel
            self.window = tk.Toplevel(parent.root)
            self.window.title("🤖 Agent Padel IA")
            self.window.geometry("500x700")
            self.window.configure(bg="white")
            self.window.protocol("WM_DELETE_WINDOW", self.hide)
        else:
            # Mode intégré - utiliser le container fourni
            self.window = tk.Frame(container, bg="white")
        
        self._create_ui()
        
        # Message de bienvenue
        self.add_agent_message(
            "👋 Salut ! Je suis ton assistant padel IA.\n\n"
            "Je peux t'aider à:\n"
            "• 📊 Analyser tes statistiques de match\n"
            "• 📄 Générer des rapports HTML\n"
            "• 💡 Donner des conseils tactiques\n"
            "• 📈 Expliquer les données\n\n"
            "Pose-moi une question ou clique sur une suggestion !"
        )
        
        # Cacher par défaut si détaché
        if self.is_detached:
            self.hide()
    
    def _create_ui(self):
        """Crée l'interface"""
        # Header
        header = tk.Frame(self.window, bg="#0084ff", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="🤖 Agent Padel IA",
            font=("Segoe UI", 16, "bold"),
            bg="#0084ff",
            fg="white"
        )
        title.pack(side="left", pady=15, padx=15)
        
        # Bouton détacher/réattacher
        detach_btn = tk.Button(
            header,
            text="🔗" if not self.is_detached else "⬅",
            command=self.detach if not self.is_detached else self.reattach,
            font=("Segoe UI", 12),
            bg="#0084ff",
            fg="white",
            relief="flat",
            cursor="hand2",
            activebackground="#0073e6",
            padx=10
        )
        detach_btn.pack(side="right", pady=15, padx=15)
        
        # Zone de messages
        messages_frame = tk.Frame(self.window, bg="white")
        messages_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ScrolledText pour les messages
        self.chat_display = scrolledtext.ScrolledText(
            messages_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            bg="white",
            relief="flat",
            state="disabled",
            cursor="arrow"
        )
        self.chat_display.pack(fill="both", expand=True)
        
        # Tags pour le style
        self.chat_display.tag_config("user", foreground="#0084ff", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("agent", foreground="#333", font=("Segoe UI", 10))
        self.chat_display.tag_config("error", foreground="#ff0000", font=("Segoe UI", 10))
        self.chat_display.tag_config("user_bg", background="#e3f2fd", lmargin1=10, lmargin2=10, rmargin=50)
        self.chat_display.tag_config("agent_bg", background="#f5f5f5", lmargin1=50, lmargin2=50, rmargin=10)
        
        # Zone de suggestions
        suggestions_frame = tk.Frame(self.window, bg="white")
        suggestions_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        suggestions = [
            ("📊 Analyse", "Analyse le match en cours"),
            ("📄 Rapport", "Génère le rapport HTML"),
            ("💡 Conseils", "Donne des conseils tactiques"),
        ]
        
        for emoji_text, command_text in suggestions:
            btn = tk.Button(
                suggestions_frame,
                text=emoji_text,
                command=lambda t=command_text: self.send_suggestion(t),
                font=("Segoe UI", 9),
                bg="#f0f2f5",
                fg="#333",
                relief="flat",
                padx=10,
                pady=5,
                cursor="hand2",
                activebackground="#e4e6eb"
            )
            btn.pack(side="left", padx=2)
        
        # Zone de saisie
        input_frame = tk.Frame(self.window, bg="white")
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.input_field = tk.Entry(
            input_frame,
            font=("Segoe UI", 11),
            bg="#f0f2f5",
            fg="#333",
            relief="flat",
            insertbackground="#0084ff"
        )
        self.input_field.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 5))
        self.input_field.bind("<Return>", lambda e: self.send_message())
        
        self.send_btn = tk.Button(
            input_frame,
            text="Envoyer 🚀",
            command=self.send_message,
            font=("Segoe UI", 10, "bold"),
            bg="#0084ff",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2",
            activebackground="#0073e6"
        )
        self.send_btn.pack(side="left")
    
    def send_suggestion(self, text):
        """Envoie une suggestion prédéfinie"""
        self.input_field.delete(0, tk.END)
        self.input_field.insert(0, text)
        self.send_message()
    
    def send_message(self):
        """Envoie un message à l'agent"""
        message = self.input_field.get().strip()
        if not message:
            return
        
        # Afficher le message utilisateur
        self.add_user_message(message)
        self.input_field.delete(0, tk.END)
        
        # Désactiver l'input pendant le traitement
        self.send_btn.config(state="disabled", text="Réflexion...")
        self.input_field.config(state="disabled")
        
        # Lancer le thread agent
        self.agent_thread = AgentThread(
            message,
            self.context,
            self.on_response,
            self.on_error,
            self.on_action
        )
        self.agent_thread.start()
    
    def add_user_message(self, text):
        """Ajoute un message utilisateur"""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.insert(tk.END, f"Vous: {text}\n", ("user", "user_bg"))
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
    
    def add_agent_message(self, text):
        """Ajoute un message agent"""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.insert(tk.END, f"🤖 Agent: {text}\n", ("agent", "agent_bg"))
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
    
    def add_error_message(self, text):
        """Ajoute un message d'erreur"""
        self.chat_display.config(state="normal")
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.insert(tk.END, f"❌ {text}\n", "error")
        self.chat_display.config(state="disabled")
        self.chat_display.see(tk.END)
    
    def on_response(self, response):
        """Gère la réponse de l'agent"""
        self.add_agent_message(response)
        self._reactivate_input()
    
    def on_action(self, action_type, params):
        """Gère une action déclenchée par l'agent"""
        if self.action_callback:
            self.action_callback(action_type, params)
        self._reactivate_input()
    
    def on_error(self, error_msg):
        """Gère une erreur"""
        self.add_error_message(error_msg)
        self._reactivate_input()
    
    def _reactivate_input(self):
        """Réactive l'interface"""
        self.send_btn.config(state="normal", text="Envoyer 🚀")
        self.input_field.config(state="normal")
        self.input_field.focus()
    
    def update_context(self, match_data=None, stats=None):
        """Met à jour le contexte de l'agent"""
        if match_data:
            self.context["match_loaded"] = True
            self.context["match_name"] = match_data.get("name", "Match sans nom")
            self.context["num_points"] = len(match_data.get("points", []))
            self.context["score"] = match_data.get("score", "")
            self.context["teams"] = match_data.get("teams", {})
        
        if stats:
            self.context["stats"] = stats
    
    def clear_context(self):
        """Efface le contexte"""
        self.context = {}
    
    def show(self):
        """Affiche la fenêtre"""
        self.window.deiconify()
        self.window.lift()
        self.input_field.focus()
    
    def hide(self):
        """Cache la fenêtre"""
        self.window.withdraw()
    
    def toggle(self):
        """Toggle l'affichage"""
        if self.is_detached:
            if self.window.state() == "withdrawn":
                self.show()
            else:
                self.hide()
        else:
            # En mode intégré, toggle pack/pack_forget
            if self.window.winfo_ismapped():
                self.window.pack_forget()
            else:
                self.window.pack(fill="both", expand=True)
    
    def detach(self):
        """Détache la fenêtre de chat dans une fenêtre séparée"""
        if self.is_detached:
            return  # Déjà détachée
        
        # Créer une nouvelle fenêtre Toplevel
        self.detached_window = tk.Toplevel(self.parent.root)
        self.detached_window.title("🤖 Agent Padel IA")
        self.detached_window.geometry("500x700")
        self.detached_window.configure(bg="white")
        self.detached_window.protocol("WM_DELETE_WINDOW", self.reattach)
        
        # Déplacer le contenu vers la nouvelle fenêtre
        self.window.pack_forget()
        old_window = self.window
        self.window = self.detached_window
        
        # Recréer l'UI dans la nouvelle fenêtre
        for widget in old_window.winfo_children():
            widget.destroy()
        
        self._create_ui()
        self.is_detached = True
    
    def reattach(self):
        """Réattache la fenêtre de chat dans l'interface principale"""
        if not self.is_detached or not self.container:
            return
        
        # Détruire la fenêtre détachée
        if self.detached_window:
            self.detached_window.destroy()
            self.detached_window = None
        
        # Recréer dans le container original
        self.window = tk.Frame(self.container, bg="white")
        self._create_ui()
        self.window.pack(fill="both", expand=True)
        self.is_detached = False
