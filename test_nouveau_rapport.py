"""
Test du nouveau format de rapport avec tableaux chronologiques
"""
import json
from app.annotations.annotation_manager import AnnotationManager
from app.exports.html_generator import HTMLGenerator

# Charger le fichier JSON de référence
json_path = r"E:\projet\padel stat\data\autosave_VID_20251217_120454_20251220_002108.json"

print(f"📂 Chargement de: {json_path}")

with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Créer le gestionnaire d'annotations et charger les données
manager = AnnotationManager()
manager.load_from_dict(data)

print(f"✅ {len(data.get('points', []))} points chargés")
joueurs_raw = data.get('match', {}).get('joueurs', [])
joueurs = [j if isinstance(j, str) else j.get('nom', 'Joueur') for j in joueurs_raw]
print(f"👥 Joueurs: {', '.join(joueurs)}")

# Générer le rapport
print("\n🔄 Génération du rapport HTML avec nouveaux tableaux chronologiques...")
generator = HTMLGenerator()
output_path = generator.generate_report(manager, "data/rapport_nouveau_format.html")

print(f"\n✅ Rapport généré avec succès!")
print(f"📄 Fichier: {output_path}")
