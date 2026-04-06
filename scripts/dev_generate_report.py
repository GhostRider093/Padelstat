import os
import sys
from datetime import datetime

# S'assurer que le répertoire racine du projet est dans sys.path
CURRENT_DIR = os.path.dirname(__file__)
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Import ciblé du générateur HTML
from app.exports.html_generator import HTMLGenerator


class DummyAnnotationManager:
    def __init__(self, data_folder):
        self.data_folder = data_folder

    def export_to_dict(self):
        # 4 joueurs, quelques points répartis dans le temps
        joueurs = ["Alice", "Bob", "Chloé", "David"]
        stats = {
            "Alice": {
                "fautes_directes": 3,
                "points_gagnants": 5,
                "fautes_provoquees_generees": 2,
                "fautes_provoquees_subies": 1,
                "points_gagnants_detail": {
                    "volee_coup_droit": 2,
                    "volee_revers": 1,
                    "smash": 1,
                    "amorti": 0,
                    "fond_de_court": 1,
                },
            },
            "Bob": {
                "fautes_directes": 4,
                "points_gagnants": 2,
                "fautes_provoquees_generees": 1,
                "fautes_provoquees_subies": 3,
                "points_gagnants_detail": {
                    "volee_coup_droit": 1,
                    "volee_revers": 0,
                    "smash": 1,
                    "amorti": 0,
                    "fond_de_court": 0,
                },
            },
            "Chloé": {
                "fautes_directes": 1,
                "points_gagnants": 4,
                "fautes_provoquees_generees": 3,
                "fautes_provoquees_subies": 0,
                "points_gagnants_detail": {
                    "volee_coup_droit": 1,
                    "volee_revers": 1,
                    "smash": 1,
                    "amorti": 0,
                    "fond_de_court": 1,
                },
            },
            "David": {
                "fautes_directes": 2,
                "points_gagnants": 3,
                "fautes_provoquees_generees": 2,
                "fautes_provoquees_subies": 2,
                "points_gagnants_detail": {
                    "volee_coup_droit": 1,
                    "volee_revers": 0,
                    "smash": 1,
                    "amorti": 0,
                    "fond_de_court": 1,
                },
            },
        }

        # Points espacés pour la chronologie et la timeline
        points = [
            {"id": 1, "type": "faute_directe", "joueur": "Alice", "timestamp": 12.3},
            {"id": 2, "type": "point_gagnant", "joueur": "Chloé", "type_coup": "smash", "timestamp": 55.0},
            {"id": 3, "type": "faute_provoquee", "attaquant": "David", "defenseur": "Bob", "timestamp": 110.0},
            {"id": 4, "type": "point_gagnant", "joueur": "Alice", "type_coup": "fond_de_court", "timestamp": 180.0},
            {"id": 5, "type": "faute_directe", "joueur": "Bob", "timestamp": 240.0},
            {"id": 6, "type": "faute_provoquee", "attaquant": "Chloé", "defenseur": "David", "timestamp": 300.0},
            {"id": 7, "type": "point_gagnant", "joueur": "David", "type_coup": "smash", "timestamp": 360.0},
            {"id": 8, "type": "faute_directe", "joueur": "David", "timestamp": 420.0},
            {"id": 9, "type": "faute_provoquee", "attaquant": "Alice", "defenseur": "Chloé", "timestamp": 470.0},
            {"id": 10, "type": "point_gagnant", "joueur": "Bob", "type_coup": "volee_coup_droit", "timestamp": 525.0},
        ]

        return {
            "match": {
                "joueurs": joueurs,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "video": "VideoTest.mp4",
            },
            "stats": stats,
            "points": points,
        }

    # Interfaces optionnelles utilisées si disponibles
    def get_diagonal_stats(self):
        return {}

    def get_fautes_provoquees_matrix(self):
        return {
            "Alice": {"Bob": 2, "Chloé": 1, "David": 0},
            "Bob": {"Alice": 1, "Chloé": 0, "David": 2},
            "Chloé": {"Alice": 0, "Bob": 3, "David": 1},
            "David": {"Alice": 2, "Bob": 1, "Chloé": 0},
        }

    def get_player_progression(self, joueur):
        # 10 points de progression (% d'efficacité) bidons
        base = {
            "Alice": [40, 45, 50, 55, 60, 58, 62, 65, 67, 70],
            "Bob": [35, 37, 39, 40, 42, 41, 43, 45, 46, 48],
            "Chloé": [50, 52, 54, 56, 58, 60, 63, 65, 67, 70],
            "David": [45, 47, 49, 50, 52, 53, 55, 56, 58, 60],
        }
        return [{"efficacite": v} for v in base.get(joueur, [50] * 10)]


def main():
    root_dir = ROOT_DIR
    data_dir = os.path.join(root_dir, "data")
    os.makedirs(data_dir, exist_ok=True)

    am = DummyAnnotationManager(data_dir)
    gen = HTMLGenerator()
    output = os.path.join(data_dir, "rapport_test.html")

    path = gen.generate_report(
        annotation_manager=am,
        output_path=output,
        video_player=None,
        fast_mode=True,
        num_frames=0,
        logger=None,
    )
    print(path)


if __name__ == "__main__":
    main()
