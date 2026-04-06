"""
Test rapide de toutes les commandes vocales
"""

import speech_recognition as sr

def test_command(command_name):
    """Test une commande vocale"""
    print("\n" + "=" * 60)
    print(f"🎤 TEST: {command_name}")
    print("=" * 60)
    
    r = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("📊 Calibrage rapide...")
        r.adjust_for_ambient_noise(source, duration=1)
        
        print(f"🎯 Dites: '{command_name}'")
        print("Écoute...\n")
        
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=3)
            print("🔄 Transcription... ", end='', flush=True)
            
            text = r.recognize_google(audio, language="fr-FR")
            print("✅\n")
            
            print("RÉSULTAT:")
            print(f"  Attendu: '{command_name}'")
            print(f"  Reconnu: '{text}'")
            
            # Vérifier si c'est bon
            if command_name.lower() in text.lower():
                print("  ✅ CORRECT!")
                return True
            else:
                print("  ❌ DIFFÉRENT")
                return False
                
        except sr.WaitTimeoutError:
            print("❌ Timeout")
            return False
        except sr.UnknownValueError:
            print("❌ Non compris")
            return False
        except Exception as e:
            print(f"❌ Erreur: {e}")
            return False

def main():
    print("\n" + "=" * 60)
    print("🎯 TEST DE TOUTES LES COMMANDES VOCALES")
    print("=" * 60)
    
    commands = [
        "OK lecture",
        "OK pause",
        "OK annuler",
        "OK sauvegarder",
        "OK rapport"
    ]
    
    results = {}
    
    print(f"\nVous allez tester {len(commands)} commandes")
    print("Appuyez sur Entrée pour commencer chaque test\n")
    
    for cmd in commands:
        input(f"➤ Prêt pour '{cmd}' ? [Entrée]")
        results[cmd] = test_command(cmd)
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    
    success = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nRéussite: {success}/{total} ({success/total*100:.0f}%)\n")
    
    for cmd, ok in results.items():
        status = "✅" if ok else "❌"
        print(f"{status} {cmd}")
    
    print("\n" + "=" * 60)
    
    if success == total:
        print("🎉 PARFAIT! Toutes les commandes fonctionnent!")
        print("\nVous pouvez maintenant activer les commandes vocales")
        print("dans l'application principale!")
    else:
        print("⚠️  Certaines commandes ont des problèmes")
        print("\nConseils:")
        print("• Articulez bien")
        print("• Parlez un peu plus fort")
        print("• Attendez 1 seconde après 'OK' avant la commande")
    
    print("=" * 60 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Arrêté")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
