"""
Test rapide pour vérifier que les commandes vocales fonctionnent
"""

from app.voice.command_parser import CommandParser

def test_commandes():
    parser = CommandParser()
    parser.set_joueurs(["Arnaud", "Pierre", "Thomas", "Lucas"])
    
    test_cases = [
        # Format simple : "OK point Arnaud service"
        "point arnaud service",
        "point pierre volée",
        "point gagnant thomas smash",
        "faute lucas service",
        
        # Format avec OK final (sera enlevé) : "OK point Arnaud service OK"
        "point arnaud service",  # Le OK final sera enlevé avant le parsing
        "point pierre coup droit",
        
        # Commandes simples
        "pause",
        "lecture",
        "rapport",
    ]
    
    print("=" * 70)
    print("TEST DES COMMANDES VOCALES - APRÈS RÉPARATION")
    print("=" * 70)
    
    for i, cmd in enumerate(test_cases, 1):
        print(f"\n[TEST {i}] Commande : \"{cmd}\"")
        
        # Simuler le nettoyage fait dans _process_voice_command
        text_clean = cmd.lower().strip()
        if text_clean.endswith(" ok"):
            text_clean = text_clean[:-3].strip()
        
        # Test commandes simples
        if any(word in text_clean for word in ["pause", "lecture", "rapport", "sauvegarder", "supprimer"]):
            print(f"  → Type : COMMANDE SIMPLE")
            print(f"  → Résultat : ✅ Sera exécutée directement")
            continue
        
        # Parser les annotations
        result = parser.parse(text_clean)
        
        if not result:
            print(f"  → ❌ ÉCHEC PARSING")
            continue
        
        # Valider
        is_valid, message = parser.validate_command(result)
        
        print(f"  → Parsing : {result}")
        print(f"  → Validation : {'✅ VALIDE' if is_valid else '❌ INVALIDE'}")
        print(f"  → Message : {message}")
        
        if is_valid:
            print(f"  → Action : ✅ SERA ENREGISTRÉ")
        else:
            print(f"  → Action : ❌ SERA REJETÉ")
    
    print("\n" + "=" * 70)
    print("FIN DES TESTS")
    print("=" * 70)

if __name__ == "__main__":
    test_commandes()
