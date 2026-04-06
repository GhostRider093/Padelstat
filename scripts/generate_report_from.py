import os
import sys
import json
from datetime import datetime

# Utilise le générateur principal pour produire un rapport complet à partir d'un fichier match_*.json fourni

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_report_from.py <chemin_du_json_match>")
        return 1
    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"Fichier introuvable: {json_path}")
        return 1

    # Charger le json et construire un AnnotationManager minimal
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, 'data')

    # Importer dynamiquement pour éviter problèmes de chemins
    sys.path.insert(0, root)
    from app.annotations.annotation_manager import AnnotationManager
    from app.exports.html_generator import HTMLGenerator

    with open(json_path, 'r', encoding='utf-8') as f:
        match_data = json.load(f)

    # Préparer un manager et lui injecter les données
    am = AnnotationManager(data_folder=data_dir)
    am.import_from_dict(match_data)

    generator = HTMLGenerator()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(data_dir, f'rapport_{ts}.html')
    generator.generate_report(annotation_manager=am, output_path=out_path, video_player=None, fast_mode=True)
    print(out_path)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
