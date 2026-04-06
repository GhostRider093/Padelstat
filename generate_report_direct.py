"""
Script pour générer directement un rapport HTML à partir d'un fichier autosave
"""
import sys
import os
import json
sys.path.insert(0, os.path.dirname(__file__))

from app.annotations.annotation_manager import AnnotationManager
from app.exports.html_generator import HTMLGenerator

# Charger le fichier autosave
autosave_path = r'e:\projet\padel stat\data\autosave_VID_20251217_120454_20251219_232206.json'

print(f"Chargement du fichier: {autosave_path}")

# Lire le JSON
with open(autosave_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Créer un AnnotationManager
annotation_manager = AnnotationManager(data_folder="data")

# Charger les données depuis le dictionnaire
annotation_manager.load_from_dict(data)

print(f"Données chargées: {len(annotation_manager.annotations)} points")

# Générer le rapport
generator = HTMLGenerator()
output_path = r'e:\projet\padel stat\data\rapport_test_direct.html'

print(f"Génération du rapport HTML...")
result = generator.generate_report(
    annotation_manager=annotation_manager,
    output_path=output_path,
    video_player=None,
    fast_mode=True  # Mode rapide sans captures
)

print(f"\n✅ Rapport généré avec succès: {result}")
print(f"\nOuvrez le fichier dans votre navigateur pour voir le résultat.")
