"""
Test unitaire pour la commande vocale SERVICE
Menu 1 : OK point gagnant [Joueur] service
"""

import sys
import os

# Ajouter le répertoire parent (racine du projet) au path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from app.voice.command_parser import CommandParser


def test_service_arnaud():
    """Test : OK point gagnant Arnaud service"""
    # Initialiser le parser avec la liste des joueurs
    parser = CommandParser(joueurs=['Arnaud', 'Pierre', 'Thomas', 'Lucas'])
    
    # Texte de la commande vocale
    text = "ok point gagnant Arnaud service"
    
    # Parser la commande
    result = parser.parse(text)
    
    # Afficher le résultat
    print(f"\n{'='*60}")
    print(f"Commande : '{text}'")
    print(f"{'='*60}")
    print(f"Résultat du parsing :")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"{'='*60}")
    
    # Vérifications
    assert result['type_point'] == 'point_gagnant', f"Type incorrect: {result['type_point']}"
    assert result['joueur'] == 'Arnaud', f"Joueur incorrect: {result['joueur']}"
    assert result['type_coup'] == 'service', f"Type de coup incorrect: {result['type_coup']}"
    
    # Vérifier la validation
    is_valid, missing = parser.validate_command(result)
    print(f"\nValidation : {'✓ VALIDE' if is_valid else '✗ INVALIDE'}")
    if not is_valid:
        print(f"Champs manquants : {missing}")
    
    assert is_valid, f"La commande devrait être valide. Champs manquants: {missing}"
    
    print("\n✓ TEST RÉUSSI !\n")


def test_service_pierre():
    """Test : OK point gagnant Pierre service"""
    # Initialiser le parser avec la liste des joueurs
    parser = CommandParser(joueurs=['Arnaud', 'Pierre', 'Thomas', 'Lucas'])
    
    text = "ok point gagnant Pierre service"
    result = parser.parse(text)
    
    print(f"\n{'='*60}")
    print(f"Commande : '{text}'")
    print(f"{'='*60}")
    print(f"Résultat du parsing :")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"{'='*60}")
    
    assert result['type_point'] == 'point_gagnant'
    assert result['joueur'] == 'Pierre'
    assert result['type_coup'] == 'service'
    
    is_valid, missing = parser.validate_command(result)
    print(f"\nValidation : {'✓ VALIDE' if is_valid else '✗ INVALIDE'}")
    if not is_valid:
        print(f"Champs manquants : {missing}")
    
    assert is_valid, f"La commande devrait être valide. Champs manquants: {missing}"
    
    print("\n✓ TEST RÉUSSI !\n")


def test_service_incomplet():
    """Test négatif : OK point gagnant service (sans joueur) - devrait échouer"""
    # Initialiser le parser avec la liste des joueurs
    parser = CommandParser(joueurs=['Arnaud', 'Pierre', 'Thomas', 'Lucas'])
    
    text = "ok point gagnant service"
    result = parser.parse(text)
    
    print(f"\n{'='*60}")
    print(f"Commande INCOMPLÈTE : '{text}'")
    print(f"{'='*60}")
    print(f"Résultat du parsing :")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"{'='*60}")
    
    is_valid, missing = parser.validate_command(result)
    print(f"\nValidation : {'✓ VALIDE' if is_valid else '✗ INVALIDE (attendu)'}")
    if not is_valid:
        print(f"Champs manquants : {missing}")
    
    # Cette commande DOIT être invalide car il manque le joueur
    assert not is_valid, "La commande devrait être INVALIDE (manque le joueur)"
    assert 'JOUEUR' in missing, "Le champ 'JOUEUR' devrait être signalé comme manquant"
    
    print("\n✓ TEST RÉUSSI (invalidité détectée correctement) !\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("TEST DE LA COMMANDE VOCALE : SERVICE")
    print("="*60)
    
    try:
        # Test 1 : Service avec Arnaud
        test_service_arnaud()
        
        # Test 2 : Service avec Pierre
        test_service_pierre()
        
        # Test 3 : Service incomplet (sans joueur)
        test_service_incomplet()
        
        print("\n" + "="*60)
        print("✓✓✓ TOUS LES TESTS SONT PASSÉS !")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗✗✗ ÉCHEC DU TEST : {e}\n")
        sys.exit(1)
