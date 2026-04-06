"""
Script de test pour l'analyse IA des statistiques
"""

import sys
import os

# Ajouter le dossier parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.exports.ai_analyzer import AIStatsAnalyzer
from app.annotations.annotation_manager import AnnotationManager
import json


def test_ai_analysis():
    """Test de l'analyseur IA"""
    
    # Charger un fichier de match de test
    test_files = [
        "data/autosave_VID_20251217_120454_20251219_232206.json",
        "data/match_20251218_071907.json"
    ]
    
    match_file = None
    for f in test_files:
        if os.path.exists(f):
            match_file = f
            break
    
    if not match_file:
        print("ERREUR - Aucun fichier de match trouvé pour le test")
        print("Créez d'abord quelques annotations dans l'application")
        return
    
    print(f"Chargement du match: {match_file}")
    
    # Créer un annotation manager et charger les données
    manager = AnnotationManager(data_folder="data")
    
    try:
        with open(match_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Restaurer les données
        match_info = data.get('match', {})
        points = data.get('points', [])
        
        # Configurer le manager
        manager.joueurs = match_info.get('joueurs', [])
        manager.points = points
        
        print(f"Match chargé: {len(points)} points")
        
        # Créer l'analyseur
        print("\nCréation de l'analyseur IA...")
        analyzer = AIStatsAnalyzer()
        
        print("\n" + "="*60)
        print("LANCEMENT DE L'ANALYSE IA")
        print("="*60)
        print("Cela peut prendre 1-2 minutes...")
        print("")
        
        # Lancer l'analyse
        filepath = analyzer.analyze_match_stats(manager)
        
        print("\n" + "="*60)
        print("ANALYSE TERMINÉE")
        print("="*60)
        print(f"Rapport généré: {filepath}")
        print("\nOuverture dans le navigateur...")
        
        # Ouvrir le fichier
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(filepath))
        
    except Exception as e:
        print(f"\nERREUR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_ai_analysis()
