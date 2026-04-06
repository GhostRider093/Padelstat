#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST RAPIDE - Normalisation et Détection Hybride
Vérifie que toutes les variantes de "faute provoquée" fonctionnent
"""

import sys
sys.path.insert(0, '.')

from app.voice.command_parser import CommandParser

def test_normalisation():
    """Test de la normalisation avec toutes les variantes"""
    
    parser = CommandParser(joueurs=["Pierre", "Lucas", "Marie", "Sophie"])
    
    print("=" * 80)
    print("🧪 TEST NORMALISATION - TOUTES LES VARIANTES")
    print("=" * 80)
    print()
    
    # Test des variantes de "faute provoquée"
    variantes_faute_provoquee = [
        "faute provoqué Pierre Lucas",
        "faute provoquer Pierre Lucas",
        "faut provoquer Pierre Lucas",
        "foot provoquer Pierre Lucas",
        "ford provoquer Pierre Lucas",
        "phoque provoquer Pierre Lucas",
        "photos provoquer Pierre Lucas",
        "faute de provoquer Pierre Lucas",
        "faut te provoquer Pierre Lucas",
        "foot pro ok Pierre Lucas",
        "fort provoquer Pierre Lucas",
        "provoquer Pierre Lucas",  # Juste "provoquer"
    ]
    
    print("📋 VARIANTES 'FAUTE PROVOQUÉE':")
    print("-" * 80)
    for original in variantes_faute_provoquee:
        normalise = parser.normaliser_texte(original)
        parsed = parser.parse(original)
        
        print(f"  Original  : '{original}'")
        print(f"  Normalisé : '{normalise}'")
        
        if parsed:
            valide, msg = parser.validate_command(parsed)
            type_point = parsed.get('type_point', 'NON DÉTECTÉ')
            joueur = parsed.get('joueur', 'NON DÉTECTÉ')
            defenseur = parsed.get('defenseur', 'NON DÉTECTÉ')
            
            print(f"  Type      : {type_point}")
            print(f"  Joueur    : {joueur}")
            print(f"  Défenseur : {defenseur}")
            print(f"  Validation: {'✅ OK' if valide else f'❌ {msg}'}")
        else:
            print(f"  ❌ PARSING ÉCHOUÉ")
        
        print()
    
    print("=" * 80)
    print("📋 TEST COMMANDES COMPLÈTES EN 1 FOIS:")
    print("-" * 80)
    
    commandes_completes = [
        "point Pierre service",
        "faute Lucas volée coup droit",
        "faute provoquée Pierre Lucas smash",
        "point Marie fond de court revers",
        "faute Sophie lob",
    ]
    
    for cmd in commandes_completes:
        print(f"\n🎤 '{cmd}'")
        parsed = parser.parse(cmd)
        
        if parsed:
            valide, msg = parser.validate_command(parsed)
            print(f"  ✅ Parsé: {parser.format_command(parsed)}")
            print(f"  Validation: {'✅ COMPLET' if valide else f'⚠️ {msg}'}")
        else:
            print(f"  ❌ Non reconnu")
    
    print()
    print("=" * 80)
    print("📋 TEST COMMANDES PARTIELLES (2 ÉTAPES):")
    print("-" * 80)
    
    etapes_1 = [
        "point Pierre",
        "faute Lucas",
        "faute provoquée Pierre Lucas",
    ]
    
    for cmd in etapes_1:
        print(f"\n🎤 ÉTAPE 1: '{cmd}'")
        parsed = parser.parse(cmd)
        
        if parsed:
            valide, msg = parser.validate_command(parsed)
            missing = parser.get_missing_fields(parsed)
            
            print(f"  Parsé: {parser.format_command(parsed)}")
            
            if valide:
                print(f"  ✅ COMPLET (pas besoin d'étape 2)")
            else:
                print(f"  ⏸️ INCOMPLET - Manque: {', '.join(missing)}")
                
                # Simuler étape 2
                if missing and "Type de coup" in missing:
                    print(f"\n  🎤 ÉTAPE 2: 'service'")
                    parsed['type_coup'] = 'service'
                    valide2, msg2 = parser.validate_command(parsed)
                    print(f"  {'✅ VALIDÉ' if valide2 else f'❌ {msg2}'}")
        else:
            print(f"  ❌ Non reconnu")
    
    print()
    print("=" * 80)
    print("✅ TEST TERMINÉ")
    print("=" * 80)


if __name__ == "__main__":
    test_normalisation()
