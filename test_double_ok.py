"""
Test du nouveau système de commandes vocales
Format : "OK [commande] OK"
Exemple : "OK point Arnaud service OK"
"""

from app.voice.command_parser import CommandParser

# Créer le parser avec des joueurs
parser = CommandParser(joueurs=["Arnaud", "Pierre", "Thomas", "Lucas"])

print("=" * 80)
print("🎤 TEST DU NOUVEAU SYSTÈME DE COMMANDES VOCALES")
print("=" * 80)
print("\nFormat: 'OK [commande] OK'")
print("Exemple: 'OK point Arnaud service OK'\n")
print("=" * 80)

# Tests avec le nouveau format
tests = [
    "OK point Arnaud service OK",
    "OK point Pierre volée OK",
    "OK faute directe Thomas OK",
    "OK point Lucas smash OK",
    "point Arnaud service",  # Simplification : juste "point"
    "point gagnant Pierre volée",  # Ancien format
]

for i, test_cmd in enumerate(tests, 1):
    print(f"\n{'=' * 80}")
    print(f"TEST {i}: '{test_cmd}'")
    print("=" * 80)
    
    # Simuler le traitement
    text_clean = test_cmd.lower().strip()
    
    # Détecter le format OK...OK
    if text_clean.startswith("ok ") and text_clean.endswith(" ok"):
        # Extraire la commande du milieu
        command_text = text_clean[3:-3].strip()
        print(f"✅ Format détecté: OK...OK")
        print(f"   Commande extraite: '{command_text}'")
    elif text_clean.startswith("ok "):
        command_text = text_clean[3:].strip()
        print(f"⚠️  Format incomplet: OK... (sans OK final)")
        print(f"   Commande extraite: '{command_text}'")
        print(f"   → EN ATTENTE DE CONFIRMATION")
    else:
        command_text = text_clean
        print(f"❌ Pas de mot de réveil OK")
        print(f"   → IGNORÉ")
        continue
    
    # Parser
    result = parser.parse(command_text)
    
    if result:
        print(f"\n📊 Résultat du parsing:")
        for key, value in result.items():
            if value is not None and key != 'raw_text':
                print(f"   • {key}: {value}")
        
        # Valider
        is_valid, message = parser.validate_command(result)
        if is_valid:
            print(f"\n✅ VALIDATION: {message}")
        else:
            print(f"\n❌ VALIDATION: {message}")
    else:
        print(f"\n❌ Parsing échoué - Aucun pattern reconnu")

print("\n" + "=" * 80)
print("✅ Tests terminés")
print("=" * 80)
