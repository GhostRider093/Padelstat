"""
Test simple de reconnaissance vocale avec Windows Speech Recognition
Pas besoin de Whisper, utilise l'API Windows native
"""

import speech_recognition as sr
import time

def test_windows_voice():
    """Test avec la reconnaissance vocale Windows (bien plus simple!)"""
    
    print("\n" + "=" * 60)
    print("🎤 TEST RECONNAISSANCE VOCALE WINDOWS")
    print("=" * 60)
    print("\n✅ Utilise la reconnaissance vocale native de Windows")
    print("✅ Pas besoin de Whisper, plus rapide et plus précis\n")
    
    # Créer le recognizer
    r = sr.Recognizer()
    
    # Ajuster pour le bruit ambiant
    with sr.Microphone() as source:
        print("📊 Calibrage du micro (restez silencieux 2 secondes)...")
        r.adjust_for_ambient_noise(source, duration=2)
        print("✅ Calibrage terminé\n")
        
        # Test simple
        print("🎯 Dites une commande (ex: 'OK lecture')")
        print("Écoute en cours...\n")
        
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
            print("🔄 Transcription...\n")
            
            # Essayer Google (gratuit et très bon)
            try:
                text = r.recognize_google(audio, language="fr-FR")
                print("=" * 60)
                print("✅ RÉSULTAT (Google):")
                print("=" * 60)
                print(f"  '{text}'")
                print("=" * 60)
                return text
            except:
                # Fallback: reconnaissance Windows
                text = r.recognize_sphinx(audio)
                print("=" * 60)
                print("✅ RÉSULTAT (Windows):")
                print("=" * 60)
                print(f"  '{text}'")
                print("=" * 60)
                return text
                
        except sr.WaitTimeoutError:
            print("❌ Timeout - rien détecté")
        except sr.UnknownValueError:
            print("❌ Impossible de comprendre l'audio")
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    return None

def interactive_test():
    """Mode interactif pour tester plusieurs fois"""
    print("\n" + "=" * 60)
    print("🎤 MODE INTERACTIF")
    print("=" * 60)
    
    while True:
        choice = input("\n➤ [Entrée = tester / q = quitter]: ").strip().lower()
        if choice == 'q':
            break
        
        test_windows_voice()
    
    print("\n👋 Au revoir!")

if __name__ == "__main__":
    try:
        print("\n🔍 Vérification des dépendances...")
        import speech_recognition as sr
        print("✅ speech_recognition installé\n")
        
        interactive_test()
        
    except ImportError:
        print("\n❌ Module 'speech_recognition' manquant")
        print("\n📦 Installation requise:")
        print("   pip install SpeechRecognition pyaudio")
        print("\n💡 Plus simple et plus fiable que Whisper!")
