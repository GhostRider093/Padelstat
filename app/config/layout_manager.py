"""
Gestionnaire de layouts pour l'interface
Permet de créer et gérer différentes configurations d'agencement
"""

import json
import os
from typing import Dict, Any


class LayoutManager:
    """Gère les différents layouts de l'interface"""
    
    # Définition des layouts prédéfinis
    LAYOUTS = {
        "compact": {
            "nom": "Compact",
            "description": "Interface compacte avec boutons essentiels",
            "sidebar_width": 280,
            "video_controls_height": 60,
            "button_size": "small",
            "show_stats": True,
            "show_voice_controls": False,
            "show_ai_section": False,
            "button_layout": "vertical",
            "font_size": "small",
            "spacing": "tight"
        },
        "standard": {
            "nom": "Standard",
            "description": "Configuration par défaut équilibrée",
            "sidebar_width": 320,
            "video_controls_height": 70,
            "button_size": "medium",
            "show_stats": True,
            "show_voice_controls": True,
            "show_ai_section": True,
            "button_layout": "vertical",
            "font_size": "medium",
            "spacing": "normal"
        },
        "etendu": {
            "nom": "Étendu",
            "description": "Maximum de fonctionnalités visibles",
            "sidebar_width": 380,
            "video_controls_height": 80,
            "button_size": "large",
            "show_stats": True,
            "show_voice_controls": True,
            "show_ai_section": True,
            "button_layout": "vertical",
            "font_size": "large",
            "spacing": "comfortable"
        },
        "professionnel": {
            "nom": "Professionnel",
            "description": "Interface épurée pour analyse pro",
            "sidebar_width": 340,
            "video_controls_height": 70,
            "button_size": "medium",
            "show_stats": True,
            "show_voice_controls": False,
            "show_ai_section": True,
            "button_layout": "vertical",
            "font_size": "medium",
            "spacing": "normal",
            "theme": "dark"
        },
        "minimaliste": {
            "nom": "Minimaliste",
            "description": "Seulement l'essentiel, focus sur la vidéo",
            "sidebar_width": 250,
            "video_controls_height": 60,
            "button_size": "small",
            "show_stats": False,
            "show_voice_controls": False,
            "show_ai_section": False,
            "button_layout": "horizontal",
            "font_size": "small",
            "spacing": "tight"
        },
        "analyse": {
            "nom": "Analyse IA",
            "description": "Optimisé pour l'analyse avec IA",
            "sidebar_width": 400,
            "video_controls_height": 70,
            "button_size": "medium",
            "show_stats": True,
            "show_voice_controls": True,
            "show_ai_section": True,
            "button_layout": "vertical",
            "font_size": "medium",
            "spacing": "normal",
            "ai_panel_expanded": True
        },
        "coaching": {
            "nom": "Coaching",
            "description": "Interface adaptée pour les coachs",
            "sidebar_width": 360,
            "video_controls_height": 80,
            "button_size": "large",
            "show_stats": True,
            "show_voice_controls": True,
            "show_ai_section": True,
            "button_layout": "vertical",
            "font_size": "large",
            "spacing": "comfortable",
            "show_quick_annotations": True
        }
    }
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.current_layout = "standard"
        self.custom_layout = None
        self._load_preferences()
    
    def _load_preferences(self):
        """Charge les préférences de layout depuis config.json"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_layout = config.get("layout", "standard")
                    self.custom_layout = config.get("custom_layout", None)
            except Exception as e:
                print(f"[WARN] Erreur chargement layout: {e}")
    
    def save_preferences(self):
        """Sauvegarde les préférences de layout"""
        try:
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config["layout"] = self.current_layout
            if self.custom_layout:
                config["custom_layout"] = self.custom_layout
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ERROR] Erreur sauvegarde layout: {e}")
    
    def get_current_layout(self) -> Dict[str, Any]:
        """Retourne la configuration du layout actuel"""
        if self.current_layout == "custom" and self.custom_layout:
            return self.custom_layout
        return self.LAYOUTS.get(self.current_layout, self.LAYOUTS["standard"])
    
    def set_layout(self, layout_name: str):
        """Change le layout actuel"""
        if layout_name in self.LAYOUTS or layout_name == "custom":
            self.current_layout = layout_name
            self.save_preferences()
            return True
        return False
    
    def get_available_layouts(self) -> Dict[str, Dict[str, Any]]:
        """Retourne tous les layouts disponibles"""
        return self.LAYOUTS.copy()
    
    def create_custom_layout(self, config: Dict[str, Any]) -> bool:
        """Crée un layout personnalisé"""
        try:
            self.custom_layout = config
            self.current_layout = "custom"
            self.save_preferences()
            return True
        except Exception as e:
            print(f"[ERROR] Erreur création layout custom: {e}")
            return False
    
    def get_layout_property(self, property_name: str, default=None):
        """Récupère une propriété du layout actuel"""
        layout = self.get_current_layout()
        return layout.get(property_name, default)
    
    def get_button_padding(self) -> tuple:
        """Retourne le padding des boutons selon le spacing"""
        spacing = self.get_layout_property("spacing", "normal")
        if spacing == "tight":
            return (8, 8)
        elif spacing == "comfortable":
            return (15, 15)
        else:  # normal
            return (12, 12)
    
    def get_button_font_size(self) -> int:
        """Retourne la taille de police des boutons"""
        size = self.get_layout_property("font_size", "medium")
        if size == "small":
            return 9
        elif size == "large":
            return 12
        else:  # medium
            return 10
    
    def get_section_spacing(self) -> int:
        """Retourne l'espacement entre sections"""
        spacing = self.get_layout_property("spacing", "normal")
        if spacing == "tight":
            return 10
        elif spacing == "comfortable":
            return 20
        else:  # normal
            return 15
