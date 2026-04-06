"""
Fenêtre flottante pour l'analyse en temps réel par Ollama
Affiche les insights de l'IA pendant l'annotation du match
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import json
import requests
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import sys

# Import des fonctions d'ollama_chat.py qui marchent bien
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
try:
    from ollama_chat import (
        chat_with_ollama, 
        SYSTEM_PROMPT as OLLAMA_SYSTEM_PROMPT,
        format_match_context,
        analyze_match_stats,
        check_ollama_status
    )
    OLLAMA_CHAT_AVAILABLE = True
except ImportError:
    print("[OllamaWindow] Impossible d'importer ollama_chat.py")
    OLLAMA_CHAT_AVAILABLE = False


class OllamaLiveWindow(tk.Toplevel):
    """Fenêtre flottante pour l'analyse Ollama en temps réel"""
    
    def __init__(self, parent, autosave_path: Optional[Path] = None):
        super().__init__(parent)
        
        self.title("📊 Analyse IA Live - Ollama")
        self.geometry("500x700")
        
        # Configuration
        self.ollama_url = "http://57.129.110.251:11434/api/generate"
        self.model_name = "qwen2.5:3b"
        self.autosave_path = autosave_path
        self.last_points_count = 0
        self.is_analyzing = False
        
        # Contexte système PADEL
        self.system_prompt = """Tu es une IA spécialisée dans l'analyse de statistiques de PADEL EN TEMPS RÉEL.

Tu reçois les données d'un match EN COURS D'ANNOTATION.

CONSIGNES STRICTES :
1. Analyse UNIQUEMENT les données actuelles (le match n'est pas fini)
2. Donne des insights COURTS et ACTIONABLES (2-3 phrases max)
3. Focus sur les TENDANCES récentes et les profils de joueurs
4. Utilise des émojis pour rendre l'analyse vivante
5. Ne répète pas les chiffres bruts (ils sont déjà affichés)

FORMAT DE RÉPONSE :
- 1 phrase par joueur max
- Identifier les tendances (ex: "Fabrice accumule les fautes fond de court")
- Suggestions tactiques si pertinent

INTERDIT :
- Longues analyses détaillées
- Répétition des stats brutes
- Phrases génériques ("bon joueur", etc.)
- Théorie sur le padel

Sois CONCIS, PERTINENT et SPORTIF."""
        
        self._setup_ui()
        self._check_ollama_status()
        
        # Charger et analyser immédiatement si des données existent
        if self.autosave_path and self.autosave_path.exists():
            self.after(500, self._initial_load)  # Délai pour que l'UI soit prête
        
        # Rendre la fenêtre toujours au premier plan (optionnel)
        self.attributes('-topmost', False)
        
    def _setup_ui(self):
        """Configure l'interface utilisateur"""
        # Frame principale
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # En-tête avec statut
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="🤖 Assistant IA", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        
        self.status_label = ttk.Label(header_frame, text="⚪ Déconnecté", foreground="gray")
        self.status_label.pack(side=tk.RIGHT)
        
        # Stats actuelles
        stats_frame = ttk.LabelFrame(main_frame, text="📈 Stats du match", padding=10)
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Label du fichier chargé
        self.file_label = tk.Label(stats_frame, text="Aucun fichier", 
                                   font=("Consolas", 8), fg="gray", anchor="w")
        self.file_label.pack(fill=tk.X, pady=(0, 5))
        
        self.stats_text = tk.Text(stats_frame, height=6, wrap=tk.WORD, font=("Consolas", 9))
        self.stats_text.pack(fill=tk.X)
        self.stats_text.config(state=tk.DISABLED)
        
        # Zone d'analyse
        analysis_frame = ttk.LabelFrame(main_frame, text="💡 Insights IA", padding=10)
        analysis_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.analysis_text = scrolledtext.ScrolledText(
            analysis_frame, 
            wrap=tk.WORD, 
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            relief=tk.FLAT
        )
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
        
        # Boutons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        self.analyze_btn = ttk.Button(
            button_frame, 
            text="🔄 Analyser maintenant",
            command=self.analyze_now
        )
        self.analyze_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            button_frame, 
            text="🗑️ Effacer",
            command=self.clear_analysis
        ).pack(side=tk.LEFT)
        
        self.auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            button_frame,
            text="Auto (toutes les 3 annotations)",
            variable=self.auto_var
        ).pack(side=tk.RIGHT)
        
    def _check_ollama_status(self):
        """Vérifie si Ollama est accessible"""
        def check():
            try:
                response = requests.get("http://57.129.110.251:11434/api/tags", timeout=5)
                if response.status_code == 200:
                    self.status_label.config(text="🟢 Connecté", foreground="green")
                    self.analyze_btn.config(state=tk.NORMAL)
                else:
                    self.status_label.config(text="🔴 Erreur", foreground="red")
                    self.analyze_btn.config(state=tk.DISABLED)
            except:
                self.status_label.config(text="🔴 Ollama offline", foreground="red")
                self.analyze_btn.config(state=tk.DISABLED)
                
        threading.Thread(target=check, daemon=True).start()
        
    def set_autosave_path(self, path: Path):
        """Définit le chemin du fichier autosave à surveiller"""
        self.autosave_path = path
        self.last_points_count = 0
        # Mettre à jour l'affichage du fichier
        if path:
            self.file_label.config(text=f"📄 {path.name}", fg="green")
        else:
            self.file_label.config(text="Aucun fichier", fg="gray")
        
    def on_point_annotated(self):
        """Appelé après chaque annotation de point"""
        if not self.autosave_path or not self.autosave_path.exists():
            return
            
        # Charger les données
        try:
            with open(self.autosave_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            points_count = len(data.get("points", []))
            
            # Analyser auto toutes les 3 annotations
            if self.auto_var.get() and points_count > self.last_points_count:
                if points_count % 3 == 0:
                    self.analyze_now()
                else:
                    # Juste mettre à jour les stats
                    self._update_stats_display(data)
                    
            self.last_points_count = points_count
            
        except Exception as e:
            print(f"Erreur lecture autosave: {e}")
    
    def _update_stats_display(self, match_data: Dict):
        """Met à jour l'affichage des statistiques"""
        stats = match_data.get("stats", {})
        points_count = len(match_data.get("points", []))
        
        display = f"📊 {points_count} points annotés\n\n"
        
        for joueur, data in stats.items():
            pg = data.get("points_gagnants", 0)
            fd = data.get("fautes_directes", 0)
            display += f"{joueur}: {pg} PG, {fd} FD\n"
        
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, display)
        self.stats_text.config(state=tk.DISABLED)
    
    def analyze_now(self):
        """Lance une analyse immédiate"""
        if self.is_analyzing:
            return
            
        if not self.autosave_path or not self.autosave_path.exists():
            self._add_message("⚠️ Aucun match en cours", "system")
            return
        
        self.is_analyzing = True
        self.analyze_btn.config(state=tk.DISABLED, text="⏳ Analyse...")
        
        threading.Thread(target=self._run_analysis, daemon=True).start()
    
    def _run_analysis(self):
        """Exécute l'analyse dans un thread séparé"""
        try:
            # Charger les données
            with open(self.autosave_path, 'r', encoding='utf-8') as f:
                match_data = json.load(f)
            
            # Mettre à jour les stats
            self.after(0, lambda: self._update_stats_display(match_data))
            
            # Préparer le contexte
            context = self._format_match_context(match_data)
            
            # Construire le prompt
            prompt = f"{self.system_prompt}\n\n{context}\n\nDonne-moi 2-3 insights COURTS sur ce match en cours:"
            
            # Appeler Ollama
            response = self._call_ollama(prompt)
            
            if response:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.after(0, lambda: self._add_message(f"[{timestamp}] {response}", "ai"))
            else:
                self.after(0, lambda: self._add_message("❌ Erreur de connexion Ollama", "system"))
                
        except Exception as e:
            self.after(0, lambda: self._add_message(f"❌ Erreur: {str(e)}", "system"))
        finally:
            self.is_analyzing = False
            self.after(0, lambda: self.analyze_btn.config(state=tk.NORMAL, text="🔄 Analyser maintenant"))
    
    def _format_match_context(self, match_data: Dict) -> str:
        """Formate les données du match pour Ollama"""
        match_info = match_data.get("match", {})
        stats = match_data.get("stats", {})
        points = match_data.get("points", [])
        
        joueurs = match_info.get("joueurs", [])
        joueurs_str = ", ".join([p.get("nom", "") if isinstance(p, dict) else str(p) for p in joueurs])
        
        context = f"""MATCH EN COURS:
Joueurs: {joueurs_str}
Points annotés: {len(points)}

STATS ACTUELLES:
"""
        
        for joueur, data in stats.items():
            context += f"\n{joueur}:\n"
            context += f"  Points gagnants: {data.get('points_gagnants', 0)}\n"
            context += f"  Fautes directes: {data.get('fautes_directes', 0)}\n"
            context += f"  Fautes provoquées (générées): {data.get('fautes_provoquees_generees', 0)}\n"
            context += f"  Fautes provoquées (subies): {data.get('fautes_provoquees_subies', 0)}\n"
            
            # Types de coups récents
            pg_detail = data.get('points_gagnants_detail', {})
            if pg_detail:
                top_coups = sorted(pg_detail.items(), key=lambda x: x[1], reverse=True)[:2]
                if top_coups and top_coups[0][1] > 0:
                    context += f"  Coups favoris: {', '.join([f'{c[0]}({c[1]})' for c in top_coups if c[1] > 0])}\n"
        
        return context
    
    def _call_ollama(self, prompt: str, timeout: int = 15) -> str:
        """Appelle l'API Ollama"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            
            response = requests.post(self.ollama_url, json=payload, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "").strip()
            
        except requests.exceptions.ConnectionError:
            return "❌ Ollama non accessible"
        except requests.exceptions.Timeout:
            return "⏱️ Timeout dépassé"
        except Exception as e:
            return f"❌ Erreur: {str(e)}"
    
    def _add_message(self, message: str, msg_type: str = "ai"):
        """Ajoute un message dans la zone d'analyse"""
        self.analysis_text.insert(tk.END, message + "\n\n")
        self.analysis_text.see(tk.END)
        
        # Limiter l'historique à 10 messages
        lines = self.analysis_text.get(1.0, tk.END).split("\n\n")
        if len(lines) > 12:
            # Garder seulement les 10 derniers
            self.analysis_text.delete(1.0, tk.END)
            self.analysis_text.insert(1.0, "\n\n".join(lines[-10:]))
    
    def clear_analysis(self):
        """Efface l'historique d'analyse"""
        self.analysis_text.delete(1.0, tk.END)
    
    def _initial_load(self):
        """Charge et analyse les données existantes au démarrage"""
        print(f"[OllamaWindow] _initial_load appelé")
        print(f"[OllamaWindow] autosave_path = {self.autosave_path}")
        
        # Si pas de chemin fourni, chercher le dernier autosave
        if not self.autosave_path:
            print(f"[OllamaWindow] Aucun autosave_path, recherche du dernier autosave...")
            data_dir = Path("data")
            if data_dir.exists():
                autosave_files = sorted(data_dir.glob("autosave_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
                if autosave_files:
                    self.autosave_path = autosave_files[0]
                    print(f"[OllamaWindow] Dernier autosave trouvé: {self.autosave_path}")
                    self.file_label.config(text=f"📄 {self.autosave_path.name}", fg="green")
                else:
                    print(f"[OllamaWindow] Aucun fichier autosave trouvé dans data/")
                    self._add_message("⚠️ Aucun match trouvé. Annotez des points pour démarrer.", "system")
                    return
            else:
                print(f"[OllamaWindow] Le dossier data/ n'existe pas")
                self._add_message("⚠️ Dossier data/ introuvable.", "system")
                return
        
        # Vérifier si le fichier existe
        if not self.autosave_path.exists():
            print(f"[OllamaWindow] Le fichier n'existe pas: {self.autosave_path}")
            self._add_message(f"⚠️ Fichier introuvable: {self.autosave_path.name}", "system")
            return
        
        try:
            print(f"[OllamaWindow] Chargement de {self.autosave_path}...")
            with open(self.autosave_path, 'r', encoding='utf-8') as f:
                match_data = json.load(f)
            
            points_count = len(match_data.get("points", []))
            self.last_points_count = points_count
            print(f"[OllamaWindow] {points_count} points chargés")
            
            # Mettre à jour l'affichage des stats
            self._update_stats_display(match_data)
            
            # Lancer une analyse si au moins 3 points
            if points_count >= 3:
                self._add_message(f"🔍 Analyse de {points_count} points...", "system")
                self.analyze_now()
            else:
                self._add_message(f"✅ {points_count} points chargés. Annotez au moins 3 points pour l'analyse.", "system")
        
        except Exception as e:
            print(f"[OllamaWindow] Erreur: {e}")
            import traceback
            traceback.print_exc()
            self._add_message(f"⚠️ Erreur chargement: {str(e)}", "system")

