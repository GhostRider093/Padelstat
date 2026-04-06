"""Test debug du parser"""
from app.voice.command_parser import CommandParser

# Test avec les joueurs actuels
joueurs = ["Arnaud", "Teddy", "Laurent", "Philippe"]
parser = CommandParser(joueurs=joueurs)

# Test 1: Commande complète avec OK
print("=" * 70)
print("TEST 1: 'point gagnant arnaud service'")
parsed = parser.parse("point gagnant arnaud service")
print(f"Résultat: {parsed}")
is_valid, msg = parser.validate_command(parsed)
print(f"Validation: {is_valid} - {msg}")

print("\n" + "=" * 70)
print("TEST 2: 'point gagnant Arnaud service' (avec majuscule)")
parsed = parser.parse("point gagnant Arnaud service")
print(f"Résultat: {parsed}")
is_valid, msg = parser.validate_command(parsed)
print(f"Validation: {is_valid} - {msg}")

print("\n" + "=" * 70)
print("TEST 3: 'ok point gagnant Arnaud service'")
parsed = parser.parse("ok point gagnant Arnaud service")
print(f"Résultat: {parsed}")
is_valid, msg = parser.validate_command(parsed)
print(f"Validation: {is_valid} - {msg}")

print("\n" + "=" * 70)
print("TEST 4: Ce que l'app devrait envoyer après avoir enlevé 'ok '")
# L'app fait: text_clean = "ok point gagnant Arnaud service"
#             command_text = text_clean[3:].strip()  → "point gagnant Arnaud service"
parsed = parser.parse("point gagnant Arnaud service")
print(f"Résultat: {parsed}")
is_valid, msg = parser.validate_command(parsed)
print(f"Validation: {is_valid} - {msg}")
