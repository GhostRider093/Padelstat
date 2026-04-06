"""
Dialogues d'annotation V2 - Structure détaillée complète
Tous les coups sont détaillés : Service / Fond de court / Volée
Avec sous-niveaux : CD (Coup Droit) / R (Revers) / BH (Balle Haute)
Et si BH : Víbora / Bandeja / Smash à plat
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Optional


class AnnotationDialogV2:
    """
    Dialogue d'annotation V2 avec structure complète
    Gère : Points Gagnants, Fautes Directes, Fautes Provoquées
    """
    
    def __init__(self, parent, annotation_type: str, players: List[str]):
        """
        Args:
            parent: Fenêtre parente
            annotation_type: 'point_gagnant', 'faute_directe', 'faute_provoquee'
            players: Liste des joueurs
        """
        self.result = None
        self.annotation_type = annotation_type
        self.players = players
        self.parent = parent
        
        # Créer la fenêtre
        self.top = tk.Toplevel(parent)
        self.top.title("Annotation V2")
        self.top.geometry("450x600")
        self.top.resizable(False, False)
        self.top.configure(bg="#f5f7fa")
        
        # Centrer
        self.top.transient(parent)
        self.top.grab_set()
        
        # État du workflow
        self.state = {
            'step': 1,  # 1=joueur, 2=zone, 3=technique, 4=coup_final
            'joueur': None,
            'joueur_subit': None,  # Pour faute provoquée
            'zone': None,  # service, fond_de_court, volee
            'technique': None,  # CD, R, BH
            'coup_final': None  # vibora, bandeja, smash (si BH)
        }
        
        # Container principal
        self.main_frame = tk.Frame(self.top, bg="#f5f7fa")
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Bindings clavier globaux
        self.top.bind("<Escape>", lambda e: self._cancel())
        self.top.bind("<BackSpace>", lambda e: self._go_back())
        
        # Afficher l'étape 1
        self._show_step_1()
    
    def _go_back(self):
        """Retourne à l'étape précédente"""
        if self.state['step'] == 2:
            self._show_step_1()
        elif self.state['step'] == 3:
            self._show_step_2()
        elif self.state['step'] == 4:
            self._show_step_3()

    def _clear_frame(self):
        """Efface le contenu du frame principal et les bindings temporaires"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        # Nettoyer les touches numériques
        for i in range(1, 10):
            self.top.unbind(str(i))
        self.top.unbind("<Return>")
    
    def _show_step_1(self):
        """Étape 1 : Sélection du/des joueur(s)"""
        self.state['step'] = 1
        self._clear_frame()
        
        # Titre selon le type
        titles = {
            'point_gagnant': '🏆 Point Gagnant',
            'faute_directe': '⚠️ Faute Directe',
            'faute_provoquee': '🎯 Faute Provoquée'
        }
        
        tk.Label(self.main_frame, 
                text=titles.get(self.annotation_type, "Annotation"),
                font=("Segoe UI", 16, "bold"),
                bg="#f5f7fa", fg="#667eea").pack(pady=(0, 20))
        
        # Sélection joueur(s)
        if self.annotation_type == 'faute_provoquee':
            # 2 joueurs : attaquant et défenseur
            tk.Label(self.main_frame, 
                    text="Attaquant (provoque la faute) :",
                    font=("Segoe UI", 11, "bold"),
                    bg="#f5f7fa", fg="#333").pack(anchor="w", pady=(10, 5))
            
            self.joueur_var = tk.StringVar()
            combo1 = ttk.Combobox(self.main_frame, 
                                 textvariable=self.joueur_var,
                                 values=self.players, 
                                 state="readonly",
                                 font=("Segoe UI", 11))
            combo1.pack(fill="x", pady=(0, 20))
            if self.players:
                combo1.current(0)
            
            tk.Label(self.main_frame, 
                    text="Défenseur (subit/fait la faute) :",
                    font=("Segoe UI", 11, "bold"),
                    bg="#f5f7fa", fg="#333").pack(anchor="w", pady=(10, 5))
            
            self.joueur_subit_var = tk.StringVar()
            combo2 = ttk.Combobox(self.main_frame, 
                                 textvariable=self.joueur_subit_var,
                                 values=self.players, 
                                 state="readonly",
                                 font=("Segoe UI", 11))
            combo2.pack(fill="x", pady=(0, 30))
            if len(self.players) > 1:
                combo2.current(1)
        else:
            # 1 seul joueur
            label_text = "Joueur :" if self.annotation_type == 'point_gagnant' else "Joueur (fautif) :"
            tk.Label(self.main_frame, 
                    text=label_text,
                    font=("Segoe UI", 11, "bold"),
                    bg="#f5f7fa", fg="#333").pack(anchor="w", pady=(10, 5))
            
            self.joueur_var = tk.StringVar()
            combo = ttk.Combobox(self.main_frame, 
                                textvariable=self.joueur_var,
                                values=self.players, 
                                state="readonly",
                                font=("Segoe UI", 11))
            combo.pack(fill="x", pady=(0, 30))
            if self.players:
                combo.current(0)
        
        # Boutons
        btn_frame = tk.Frame(self.main_frame, bg="#f5f7fa")
        btn_frame.pack(side="bottom", pady=20)
        
        tk.Button(btn_frame, text="Suivant [Entrée] →", 
                 command=self._validate_step_1,
                 font=("Segoe UI", 11, "bold"), 
                 bg="#667eea", fg="white",
                 relief="flat", padx=30, pady=10, 
                 cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Annuler [Echap]", 
                 command=self._cancel,
                 font=("Segoe UI", 11), 
                 bg="#e0e0e0", fg="#555",
                 relief="flat", padx=30, pady=10, 
                 cursor="hand2").pack(side="left", padx=5)
        
        # Binding Entrée
        self.top.bind("<Return>", lambda e: self._validate_step_1())
    
    def _validate_step_1(self):
        """Valide l'étape 1 et passe à l'étape 2"""
        self.state['joueur'] = self.joueur_var.get()
        
        if self.annotation_type == 'faute_provoquee':
            self.state['joueur_subit'] = self.joueur_subit_var.get()
        
        self.state['step'] = 2
        self._show_step_2()
    
    def _show_step_2(self):
        """Étape 2 : Sélection de la zone de frappe"""
        self.state['step'] = 2
        self._clear_frame()
        
        tk.Label(self.main_frame, 
                text="🎾 Zone de frappe",
                font=("Segoe UI", 16, "bold"),
                bg="#f5f7fa", fg="#667eea").pack(pady=(0, 10))
        
        tk.Label(self.main_frame, 
                text=f"Joueur : {self.state['joueur']}",
                font=("Segoe UI", 10),
                bg="#f5f7fa", fg="#666").pack(pady=(0, 30))
        
        # Options de zones
        zones = [
            ('service', '1. 🎾 Service', '#3b82f6'),
            ('fond_de_court', '2. ⚡ Fond de court', '#10b981'),
            ('volee', '3. 🏐 Volée', '#f59e0b'),
            ('lobe', '4. 🌙 Lobe', '#8b5cf6')
        ]
        
        for i, (zone_id, label, color) in enumerate(zones, 1):
            btn = tk.Button(self.main_frame, 
                           text=label,
                           command=lambda z=zone_id: self._select_zone(z),
                           font=("Segoe UI", 12, "bold"),
                           bg=color, fg="white",
                           relief="flat", 
                           pady=15,
                           cursor="hand2",
                           activebackground=color)
            btn.pack(fill="x", pady=8)
            # Binding numérique
            self.top.bind(str(i), lambda e, z=zone_id: self._select_zone(z))
        # Binding spécial pour '4' (4ème option = lobe)
        self.top.bind('4', lambda e: self._select_zone('lobe'))
        
        # Bouton retour
        tk.Button(self.main_frame, 
                 text="← Retour [Retour Arrière]",
                 command=lambda: self._show_step_1(),
                 font=("Segoe UI", 10),
                 bg="#e0e0e0", fg="#555",
                 relief="flat", padx=20, pady=8,
                 cursor="hand2").pack(side="bottom", pady=20)
    
    def _select_zone(self, zone: str):
        """Sélectionne la zone et passe à l'étape suivante"""
        self.state['zone'] = zone
        
        if zone in ['service', 'lobe']:
            # Service et Lobe = pas de sous-détails, on termine
            self._finalize()
        else:
            # Fond de court ou Volée = choix technique
            self.state['step'] = 3
            self._show_step_3()
    
    def _show_step_3(self):
        """Étape 3 : Sélection de la technique (CD/R/BH)"""
        self.state['step'] = 3
        self._clear_frame()
        
        zone_labels = {
            'fond_de_court': '⚡ Fond de court',
            'volee': '🏐 Volée'
        }
        
        tk.Label(self.main_frame, 
                text=f"{zone_labels.get(self.state['zone'], '')} - Technique",
                font=("Segoe UI", 16, "bold"),
                bg="#f5f7fa", fg="#667eea").pack(pady=(0, 10))
        
        tk.Label(self.main_frame, 
                text=f"Joueur : {self.state['joueur']}",
                font=("Segoe UI", 10),
                bg="#f5f7fa", fg="#666").pack(pady=(0, 30))
        
        # Options de technique
        techniques = [
            ('CD', '1. 👉 Coup Droit', '#22c55e'),
            ('R', '2. 👈 Revers', '#ef4444'),
            ('BH', '3. ⬆️ Balle Haute', '#f59e0b')
        ]
        
        for i, (tech_id, label, color) in enumerate(techniques, 1):
            btn = tk.Button(self.main_frame, 
                           text=label,
                           command=lambda t=tech_id: self._select_technique(t),
                           font=("Segoe UI", 12, "bold"),
                           bg=color, fg="white",
                           relief="flat", 
                           pady=15,
                           cursor="hand2",
                           activebackground=color)
            btn.pack(fill="x", pady=8)
            # Binding numérique
            self.top.bind(str(i), lambda e, t=tech_id: self._select_technique(t))
        
        # Bouton retour
        tk.Button(self.main_frame, 
                 text="← Retour [Retour Arrière]",
                 command=lambda: self._show_step_2(),
                 font=("Segoe UI", 10),
                 bg="#e0e0e0", fg="#555",
                 relief="flat", padx=20, pady=8,
                 cursor="hand2").pack(side="bottom", pady=20)
    
    def _select_technique(self, technique: str):
        """Sélectionne la technique"""
        self.state['technique'] = technique
        
        if technique == 'BH':
            # Balle haute = choix du coup final
            self.state['step'] = 4
            self._show_step_4()
        else:
            # CD ou R = on termine
            self._finalize()
    
    def _show_step_4(self):
        """Étape 4 : Sélection du coup final (Víbora/Bandeja/Smash)"""
        self.state['step'] = 4
        self._clear_frame()
        
        tk.Label(self.main_frame, 
                text="⬆️ Balle Haute - Coup final",
                font=("Segoe UI", 16, "bold"),
                bg="#f5f7fa", fg="#667eea").pack(pady=(0, 10))
        
        tk.Label(self.main_frame, 
                text=f"Joueur : {self.state['joueur']}",
                font=("Segoe UI", 10),
                bg="#f5f7fa", fg="#666").pack(pady=(0, 30))
        
        # Options de coup final
        coups = [
            ('vibora', '1. 🐍 Víbora', '#8b5cf6'),
            ('bandeja', '2. 🔥 Bandeja', '#f97316'),
            ('smash', '3. 💥 Smash à plat', '#dc2626')
        ]
        
        for i, (coup_id, label, color) in enumerate(coups, 1):
            btn = tk.Button(self.main_frame, 
                           text=label,
                           command=lambda c=coup_id: self._select_coup_final(c),
                           font=("Segoe UI", 12, "bold"),
                           bg=color, fg="white",
                           relief="flat", 
                           pady=15,
                           cursor="hand2",
                           activebackground=color)
            btn.pack(fill="x", pady=8)
            # Binding numérique
            self.top.bind(str(i), lambda e, c=coup_id: self._select_coup_final(c))
        
        # Bouton retour
        tk.Button(self.main_frame, 
                 text="← Retour [Retour Arrière]",
                 command=lambda: self._show_step_3(),
                 font=("Segoe UI", 10),
                 bg="#e0e0e0", fg="#555",
                 relief="flat", padx=20, pady=8,
                 cursor="hand2").pack(side="bottom", pady=20)
    
    def _select_coup_final(self, coup: str):
        """Sélectionne le coup final et termine"""
        self.state['coup_final'] = coup
        self._finalize()
    
    def _finalize(self):
        """Finalise l'annotation et construit le résultat"""
        # Construire le type_coup détaillé
        type_coup = self._build_type_coup()
        
        # Résultat selon le type d'annotation
        if self.annotation_type == 'faute_provoquee':
            self.result = {
                'attaquant': self.state['joueur'],
                'defenseur': self.state['joueur_subit'],
                'type_coup_attaquant': type_coup,
                'type_coup_defenseur': type_coup  # Par défaut le même (à améliorer si besoin)
            }
        else:
            self.result = {
                'joueur': self.state['joueur'],
                'type_coup': type_coup
            }
        
        self.top.destroy()
    
    def _build_type_coup(self) -> str:
        """Construit le type de coup détaillé basé sur l'état"""
        zone = self.state['zone']
        technique = self.state['technique']
        coup_final = self.state['coup_final']
        
        if zone == 'service':
            return 'service'
        
        # Format: zone_technique ou zone_technique_coup
        parts = [zone]
        
        if technique:
            parts.append(technique)
        
        if coup_final:
            parts.append(coup_final)
        
        return '_'.join(parts)
    
    def _cancel(self):
        """Annule le dialogue"""
        self.result = None
        self.top.destroy()


# Test du dialogue
if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    players = ["Arnaud", "Pierre", "Thomas", "Lucas"]
    
    # Test Point Gagnant
    dialog = AnnotationDialogV2(root, 'point_gagnant', players)
    root.wait_window(dialog.top)
    
    if dialog.result:
        print("Résultat Point Gagnant:", dialog.result)
    
    root.destroy()
