"""
Export des annotations au format JSON
"""

import json
import os
from datetime import datetime


class JSONExporter:
    def __init__(self):
        pass
    
    def export(self, annotation_manager, output_path=None):
        """
        Exporte les annotations en JSON
        
        Args:
            annotation_manager: Instance de AnnotationManager
            output_path: Chemin du fichier de sortie (optionnel)
        
        Returns:
            str: Chemin du fichier créé
        """
        data = annotation_manager.export_to_dict()
        
        # Générer un nom de fichier si non fourni
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                annotation_manager.data_folder,
                f"match_{timestamp}.json"
            )
        
        # Écrire le JSON avec indentation
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_path
    
    def load(self, json_path):
        """
        Charge les annotations depuis un fichier JSON
        
        Args:
            json_path: Chemin du fichier JSON
        
        Returns:
            dict: Données chargées
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return data
