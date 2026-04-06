"""
Boîte de dialogue pour sélectionner un layout d'interface
"""

import tkinter as tk
from tkinter import messagebox
from app.config.layout_manager import LayoutManager


class LayoutSelectionDialog:
    """Dialog pour choisir un layout d'interface"""
    
    def __init__(self, parent, layout_manager: LayoutManager, callback=None):
        self.parent = parent
        self.layout_manager = layout_manager
        self.callback = callback
        self.result = None
        
        # Créer la fenêtre
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("🎨 Configuration de l'interface")
        self.dialog.geometry("700x600")
        self.dialog.resizable(False, False)
        self.dialog.configure(bg="#f5f7fa")
        
        # Centrer
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
    
    def _create_ui(self):
        """Crée l'interface du dialog"""
        
        # En-tête
        header = tk.Frame(self.dialog, bg="#667eea", height=80)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text="🎨 Choisissez votre disposition d'interface",
            font=("Segoe UI", 18, "bold"),
            bg="#667eea",
            fg="white"
        ).pack(pady=25)
        
        # Container principal avec scroll
        main_container = tk.Frame(self.dialog, bg="#f5f7fa")
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Canvas avec scrollbar
        canvas = tk.Canvas(main_container, bg="#f5f7fa", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#f5f7fa")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=640)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # Bind molette
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Récupérer les layouts
        layouts = self.layout_manager.get_available_layouts()
        current = self.layout_manager.current_layout
        
        # Créer une carte pour chaque layout
        self.selected_var = tk.StringVar(value=current)
        
        for layout_id, layout_config in layouts.items():
            self._create_layout_card(
                scrollable_frame,
                layout_id,
                layout_config
            )
        
        # Boutons en bas
        button_frame = tk.Frame(self.dialog, bg="#f5f7fa")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        tk.Button(
            button_frame,
            text="✓ Appliquer",
            command=self._apply,
            font=("Segoe UI", 11, "bold"),
            bg="#667eea",
            fg="white",
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack(side="right", padx=5)
        
        tk.Button(
            button_frame,
            text="✗ Annuler",
            command=self._cancel,
            font=("Segoe UI", 11),
            bg="#e0e0e0",
            fg="#555",
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack(side="right", padx=5)
    
    def _create_layout_card(self, parent, layout_id, config):
        """Crée une carte pour un layout"""
        
        is_current = layout_id == self.layout_manager.current_layout
        
        # Frame principale de la carte
        card = tk.Frame(
            parent,
            bg="white" if not is_current else "#e0f2ff",
            relief="solid",
            borderwidth=2 if is_current else 1,
            bd=2 if is_current else 1,
            highlightbackground="#667eea" if is_current else "#ddd",
            highlightthickness=2 if is_current else 0
        )
        card.pack(fill="x", pady=8)
        
        # Radio button et contenu
        content = tk.Frame(card, bg=card["bg"])
        content.pack(fill="both", expand=True, padx=15, pady=12)
        
        # Header avec radio et nom
        header_frame = tk.Frame(content, bg=content["bg"])
        header_frame.pack(fill="x", anchor="w")
        
        radio = tk.Radiobutton(
            header_frame,
            text=config["nom"],
            variable=self.selected_var,
            value=layout_id,
            font=("Segoe UI", 13, "bold"),
            bg=content["bg"],
            fg="#1a1d29",
            activebackground=content["bg"],
            selectcolor=content["bg"],
            cursor="hand2"
        )
        radio.pack(side="left")
        
        # Badge "Actuel" si c'est le layout actuel
        if is_current:
            badge = tk.Label(
                header_frame,
                text="✓ ACTUEL",
                font=("Segoe UI", 8, "bold"),
                bg="#667eea",
                fg="white",
                padx=8,
                pady=2
            )
            badge.pack(side="left", padx=10)
        
        # Description
        desc = tk.Label(
            content,
            text=config["description"],
            font=("Segoe UI", 10),
            bg=content["bg"],
            fg="#666",
            justify="left",
            anchor="w"
        )
        desc.pack(fill="x", pady=(5, 8))
        
        # Détails de configuration
        details_frame = tk.Frame(content, bg=content["bg"])
        details_frame.pack(fill="x")
        
        # Créer des badges pour les caractéristiques principales
        characteristics = []
        
        if config.get("sidebar_width"):
            w = config["sidebar_width"]
            size = "Petit" if w < 300 else "Large" if w > 350 else "Moyen"
            characteristics.append(f"📐 Panneau: {size}")
        
        if config.get("button_size"):
            characteristics.append(f"🔘 Boutons: {config['button_size'].capitalize()}")
        
        if config.get("show_ai_section"):
            characteristics.append("🤖 IA activé")
        
        if config.get("show_voice_controls"):
            characteristics.append("🎤 Vocal activé")
        
        if config.get("spacing"):
            characteristics.append(f"↔ Espacement: {config['spacing']}")
        
        # Afficher les caractéristiques
        for char in characteristics:
            label = tk.Label(
                details_frame,
                text=char,
                font=("Segoe UI", 9),
                bg="#f0f0f0",
                fg="#555",
                padx=8,
                pady=3
            )
            label.pack(side="left", padx=3)
        
        # Rendre toute la carte cliquable
        def select_layout(e=None):
            self.selected_var.set(layout_id)
        
        card.bind("<Button-1>", select_layout)
        for widget in card.winfo_children():
            widget.bind("<Button-1>", select_layout)
            for child in widget.winfo_children():
                child.bind("<Button-1>", select_layout)
    
    def _apply(self):
        """Applique le layout sélectionné"""
        selected = self.selected_var.get()
        
        if selected != self.layout_manager.current_layout:
            # Changer le layout
            self.layout_manager.set_layout(selected)
            self.result = selected
            
            # Callback
            if self.callback:
                self.callback(selected)
            
            messagebox.showinfo(
                "✓ Layout appliqué",
                f"Le layout '{self.layout_manager.LAYOUTS[selected]['nom']}' a été appliqué.\n\n"
                "Certains changements peuvent nécessiter un redémarrage de l'application.",
                parent=self.dialog
            )
        
        self.dialog.destroy()
    
    def _cancel(self):
        """Annule la sélection"""
        self.dialog.destroy()
