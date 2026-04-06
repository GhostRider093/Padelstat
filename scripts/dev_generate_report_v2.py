import os
from datetime import datetime
import sys

# Génère un rapport v2 à partir du dernier match_*.json trouvé

def find_latest_match(data_dir):
    files = []
    for name in os.listdir(data_dir):
        if name.startswith('match_') and name.endswith('.json'):
            path = os.path.join(data_dir, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            files.append((mtime, path))
    if not files:
        return None
    files.sort(key=lambda x: x[0], reverse=True)
    return files[0][1]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(root, 'data')
    sys.path.insert(0, root)
    from app.annotations.annotation_manager import AnnotationManager
    from app.exports.html_generator2 import HTMLGenerator2

    latest = find_latest_match(data_dir)
    if latest is None:
        print('Aucun match_*.json trouvé')
        return 1

    import json
    with open(latest, 'r', encoding='utf-8') as f:
        data = json.load(f)

    am = AnnotationManager(data_folder=data_dir)
    # Charger le dictionnaire via méthode existante
    am.load_from_dict(data)

    gen = HTMLGenerator2()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = os.path.join(data_dir, f'rapport_v2_{ts}.html')
    gen.generate_report(annotation_manager=am, output_path=out, fast_mode=True)
    print(out)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
