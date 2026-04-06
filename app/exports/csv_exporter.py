"""
Export des données en format CSV pour Excel
"""

import csv
import os
from datetime import datetime


class CSVExporter:
    def __init__(self):
        pass
    
    def export(self, annotation_manager, output_path=None):
        """
        Exporte les données en CSV
        
        Args:
            annotation_manager: Instance de AnnotationManager
            output_path: Chemin du fichier de sortie (optionnel)
        
        Returns:
            str: Chemin du fichier créé
        """
        data = annotation_manager.export_to_dict()
        match_info = data.get("match", {})
        points = data.get("points", [])
        
        # Générer un nom de fichier si non fourni
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                annotation_manager.data_folder,
                f"export_{timestamp}.csv"
            )
        
        # Écrire le CSV
        with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';')
            
            # En-tête
            writer.writerow(['ID', 'Type', 'Joueur', 'Timestamp', 'Frame',
                           'Type_Coup', 'Attaquant', 'Defenseur', 
                           'Type_Coup_Attaquant', 'Type_Coup_Defenseur', 'Capture'])
            
            # Données
            for point in points:
                row = [
                    point.get('id', ''),
                    point.get('type', ''),
                    point.get('joueur', ''),
                    point.get('timestamp', ''),
                    point.get('frame', ''),
                    point.get('type_coup', ''),
                    point.get('attaquant', ''),
                    point.get('defenseur', ''),
                    point.get('type_coup_attaquant', ''),
                    point.get('type_coup_defenseur', ''),
                    point.get('capture', '')
                ]
                writer.writerow(row)
        
        return output_path
