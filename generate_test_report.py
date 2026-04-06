"""
Générer un rapport HTML de test avec les nouvelles stats agrégées
"""

from app.annotations.annotation_manager import AnnotationManager
from app.exports.html_generator import HTMLGenerator

# Créer un gestionnaire d'annotations
manager = AnnotationManager()

# Définir des joueurs
manager.set_players(["Alice", "Bob", "Charlie", "David"])
manager.set_video("test_stats_agregees.mp4")

# Ajouter des annotations variées pour tester toutes les stats
# Alice - Joueuse agressive au filet
manager.add_point_gagnant("Alice", 10.0, 300, "volee_coup_droit")
manager.add_point_gagnant("Alice", 20.0, 600, "volee_coup_droit")
manager.add_point_gagnant("Alice", 30.0, 900, "volee_revers")
manager.add_point_gagnant("Alice", 40.0, 1200, "smash")
manager.add_faute_directe("Alice", 50.0, 1500, "volee_coup_droit")
manager.add_faute_directe("Alice", 60.0, 1800, "amorti")

# Bob - Joueur de fond de court
manager.add_point_gagnant("Bob", 15.0, 450, "fond_de_court_revers")
manager.add_point_gagnant("Bob", 25.0, 750, "fond_de_court_coup_droit")
manager.add_point_gagnant("Bob", 35.0, 1050, "fond_de_court_revers")
manager.add_faute_directe("Bob", 45.0, 1350, "fond_de_court_coup_droit")
manager.add_faute_directe("Bob", 55.0, 1650, "fond_de_court_balle_haute")

# Charlie - Joueur équilibré
manager.add_point_gagnant("Charlie", 12.0, 360, "smash")
manager.add_point_gagnant("Charlie", 22.0, 660, "bandeja")
manager.add_faute_provoquee("Charlie", "David", 32.0, 960, "volee_coup_droit", "fond_de_court_revers")
manager.add_faute_provoquee("Charlie", "David", 42.0, 1260, "smash", "fond_de_court_coup_droit")
manager.add_faute_directe("Charlie", 52.0, 1560, "volee_revers")

# David - Joueur sous pression
manager.add_point_gagnant("David", 18.0, 540, "fond_de_court_coup_droit")
manager.add_faute_directe("David", 28.0, 840, "fond_de_court_revers")
manager.add_faute_directe("David", 38.0, 1140, "volee_coup_droit")
# David a déjà 2 fautes provoquées subies (par Charlie)

# Générer le rapport HTML
print("\n🔄 Génération du rapport HTML...")
generator = HTMLGenerator()
output_path = generator.generate_report(manager, "data/rapport_test_stats_agregees.html")

print(f"\n✅ Rapport généré avec succès!")
print(f"📄 Fichier: {output_path}")
print(f"\n💡 Ouvrez le fichier dans un navigateur pour voir les nouvelles statistiques agrégées")
print("   incluant l'analyse détaillée par type de coup (coup droit, revers, etc.)")
