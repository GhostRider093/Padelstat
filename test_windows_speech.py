"""
Test rapide du nouveau système Windows Speech Recognition
"""

import sys
import time

print("\n" + "=" * 70)
print("🎤 TEST WINDOWS SPEECH RECOGNITION - API NATIVE")
print("=" * 70 + "\n")

try:
    from app.voice.voice_commander_windows import WindowsVoiceCommander
    
    def on_recognized(text):
        print(f"\n✅ RECONNU: '{text}'")
        print("-" * 70)
    
    print("📋 Initialisation du système Windows Speech...\n")
    
    commander = WindowsVoiceCommander(callback=on_recognized, language="fr-FR")
    
    if commander.initialize():
        print("\n" + "=" * 70)
        print("✅ SYSTÈME PRÊT - Parlez maintenant !")
        print("=" * 70)
        print("\n💡 Exemples de commandes à tester:")
        print("   • OK point Pierre service OK")
        print("   • OK faute directe Arnaud OK")
        print("   • OK pause OK")
        print("\n⏹ Appuyez sur Ctrl+C pour arrêter\n")
        
        commander.start()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n⏹ Arrêt en cours...")
            commander.stop()
            print("✅ Test terminé\n")
    else:
        print("\n❌ ERREUR: Impossible d'initialiser Windows Speech Recognition")
        print("\n🔧 Vérifications:")
        print("   1. Windows Speech Recognition est-il activé dans Windows ?")
        print("   2. Un microphone est-il connecté et configuré ?")
        print("   3. pywin32 est-il installé ? (pip install pywin32)")
        sys.exit(1)

except ImportError as e:
    print(f"\n❌ ERREUR D'IMPORT: {e}")
    print("\n📦 Installation requise:")
    print("   pip install pywin32")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERREUR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
