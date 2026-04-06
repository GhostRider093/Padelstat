import os
import json
import webbrowser
from datetime import datetime


class SimpleAnnotationManager:
    def __init__(self, data_path):
        self.data_path = data_path
        self.data_folder = os.path.dirname(data_path)
        with open(data_path, 'r', encoding='utf-8') as f:
            self._data = json.load(f)

    def export_to_dict(self):
        return self._data

    def get_player_progression(self, player_name):
        # Fallback: return empty progression if not present
        match = self._data.get('match', {})
        prog = (match.get('progression', {}) or {}).get(player_name)
        return prog or []


def main(json_filename):
    base = os.path.abspath(os.path.dirname(__file__))
    root = os.path.normpath(os.path.join(base, '..'))
    json_path = os.path.join(root, 'data', json_filename)
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"Fichier introuvable: {json_path}")

    am = SimpleAnnotationManager(json_path)

    from app.exports.html_generator2 import HTMLGenerator2
    gen = HTMLGenerator2()
    output_path = gen.generate_report(am, output_path=None)
    print(f"Rapport généré: {output_path}")
    try:
        webbrowser.open(f"file:///{output_path}")
    except Exception:
        pass


if __name__ == '__main__':
    # Par défaut, utiliser le match du 06/12 identifié "000612"
    default_json = 'match_20251206_000612.json'
    main(default_json)
