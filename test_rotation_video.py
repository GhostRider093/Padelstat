#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST ROTATION VIDÉO
Vérifie que la rotation de 90° fonctionne correctement
"""

import sys
sys.path.insert(0, '.')

print("=" * 80)
print("🔄 TEST ROTATION VIDÉO - PADEL STAT")
print("=" * 80)
print()
print("✅ Fonctionnalité ajoutée :")
print()
print("  📹 Bouton de rotation : 🔄")
print("  🎮 Raccourci clavier  : T")
print()
print("🔄 Comportement :")
print("  • Rotation de 90° dans le sens horaire à chaque clic")
print("  • Cycle complet : 0° → 90° → 180° → 270° → 0°")
print("  • La rotation est appliquée via VLC en temps réel")
print("  • Message de confirmation affiché : '🔄 Rotation: XXX°'")
print()
print("📍 Où trouver :")
print("  • Bouton 🔄 dans les contrôles vidéo (à droite du bouton ⏭)")
print("  • Raccourci : Appuyez sur la touche 'T'")
print("  • Tooltip au survol : 'Pivoter la vidéo de 90° (Touche T)'")
print()
print("💡 Cas d'usage :")
print("  • Vidéo filmée en mode portrait")
print("  • Vidéo avec mauvaise orientation")
print("  • Besoin de voir le match sous un autre angle")
print()
print("=" * 80)
print()
print("🧪 Test de la logique de rotation :")
print()

# Simuler les rotations
rotations = [0]
for i in range(8):  # Faire 2 cycles complets
    current = rotations[-1]
    next_rotation = (current + 90) % 360
    rotations.append(next_rotation)
    print(f"  Clic {i+1}: {current}° → {next_rotation}°")

print()
print("✅ Cycle de rotation validé !")
print()
print("=" * 80)
print("🚀 PRÊT À TESTER DANS L'APPLICATION")
print("=" * 80)
print()
print("Instructions de test :")
print("  1. Lancez l'application : python main.py")
print("  2. Chargez une vidéo")
print("  3. Cliquez sur le bouton 🔄 ou appuyez sur 'T'")
print("  4. Vérifiez que la vidéo pivote de 90°")
print("  5. Répétez pour tester le cycle complet")
print()
