import json
import sys
from app.annotations.annotation_manager import AnnotationManager
from app.exports.html_generator import HTMLGenerator

# Charger le fichier autosave
autosave_path = r'e:\projet\padel stat\data\autosave_VID_20251217_120454_20251219_232206.json'

print(f"Chargement du fichier: {autosave_path}")

with open(autosave_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Créer un AnnotationManager temporaire
annotation_manager = AnnotationManager()
annotation_manager.match_info = data.get('match', {})
annotation_manager.annotations = data.get('points', [])

# Générer le rapport HTML
generator = HTMLGenerator()
output_path = r'e:\projet\padel stat\data\rapport_rapide.html'

print("Génération du rapport HTML...")
report_path = generator.generate_report(
    annotation_manager,
    output_path=output_path,
    video_player=None,
    fast_mode=True,  # Mode rapide, pas de captures d'écran
    logger=None
)

print(f"\n✅ Rapport généré avec succès !")
print(f"📄 Fichier: {report_path}")
print(f"\nOuvrez le fichier dans votre navigateur pour voir le rapport.")
