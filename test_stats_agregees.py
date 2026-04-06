"""
Test des statistiques agrégées par type de coup
"""

from app.annotations.annotation_manager import AnnotationManager

# Créer un gestionnaire d'annotations
manager = AnnotationManager()

# Définir des joueurs
manager.set_players(["Alice", "Bob", "Charlie", "David"])

# Ajouter quelques annotations de test
# Alice fait 3 coups droits gagnants en volée
manager.add_point_gagnant("Alice", 10.0, 300, "volee_coup_droit")
manager.add_point_gagnant("Alice", 20.0, 600, "volee_coup_droit")
manager.add_point_gagnant("Alice", 30.0, 900, "volee_coup_droit")

# Bob fait 2 revers gagnants au fond de court
manager.add_point_gagnant("Bob", 15.0, 450, "fond_de_court_revers")
manager.add_point_gagnant("Bob", 25.0, 750, "fond_de_court_revers")

# Alice fait 1 faute directe en coup droit
manager.add_faute_directe("Alice", 35.0, 1050, "volee_coup_droit")

# Charlie provoque une faute de David avec un smash
manager.add_faute_provoquee("Charlie", "David", 40.0, 1200, "smash", "fond_de_court_revers")

# Récupérer les stats
stats = manager.get_stats()

print("\n" + "="*60)
print("📊 STATISTIQUES AGRÉGÉES PAR TYPE DE COUP")
print("="*60)

for joueur in ["Alice", "Bob", "Charlie", "David"]:
    coups_tech = stats[joueur].get("coups_techniques", {})
    
    print(f"\n🎾 {joueur}:")
    print("-" * 40)
    
    for technique, data in coups_tech.items():
        if data["total"] > 0:
            total = data["total"]
            fautes = data["fautes"]
            gagnants = data["gagnants"]
            fp_gen = data["fp_generees"]
            fp_sub = data["fp_subies"]
            
            # Calculer le ratio
            ratio = round((gagnants + fp_gen) / max(total, 1) * 100, 1)
            
            print(f"\n  {technique.upper().replace('_', ' ')}:")
            print(f"    Total: {total}")
            print(f"    └─ Gagnants: {gagnants} ({round(gagnants/total*100, 1)}%)")
            print(f"    └─ Fautes: {fautes} ({round(fautes/total*100, 1)}%)")
            print(f"    └─ FP générées: {fp_gen} ({round(fp_gen/total*100, 1)}%)")
            print(f"    └─ FP subies: {fp_sub} ({round(fp_sub/total*100, 1)}%)")
            print(f"    💪 Efficacité: {ratio}%")

print("\n" + "="*60)
print("✅ Test terminé avec succès!")
print("="*60 + "\n")
