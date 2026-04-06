"""
Test de l'export des données pour vérifier ce qui est envoyé à l'IA
"""

import json
import os
from app.annotations.annotation_manager import AnnotationManager

# Charger un fichier de match existant
match_file = "data/autosave_VID_20251217_120454_20251219_232206.json"

if not os.path.exists(match_file):
    print(f"ERREUR - Fichier non trouvé: {match_file}")
    exit(1)

# Créer un annotation manager
manager = AnnotationManager(data_folder="data")

# Charger les données
with open(match_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

manager.load_from_dict(data)

# Exporter pour voir ce qui serait envoyé à l'IA
exported = manager.export_to_dict()

print("="*80)
print("DONNÉES EXPORTÉES POUR L'IA")
print("="*80)
print(json.dumps(exported, ensure_ascii=False, indent=2))
print("="*80)
print(f"\nNombre de points: {len(exported.get('points', []))}")
print(f"Joueurs: {exported.get('match', {}).get('joueurs', [])}")
print(f"Stats disponibles: {list(exported.get('stats', {}).keys())}")
