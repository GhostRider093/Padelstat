"""
TEST : Reconnaissance avec MOT DE VALIDATION
Le mot "service" termine et valide la commande

Exemple : "OK point gagnant Arnaud service"
→ Le système écoute jusqu'à entendre "service", puis valide
"""

import sys
import os
import threading
import time

# Ajouter le répertoire parent au path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[WARN] speech_recognition non disponible")

from app.voice.command_parser import CommandParser


class TestServiceValidation:
    """Test avec mot de validation 'service'"""
    
    def __init__(self):
        self.parser = CommandParser(joueurs=['Arnaud', 'Pierre', 'Thomas', 'Lucas'])
        
        self.recognizer = None
        self.microphone = None
        self.running = False
        
        # Mots de validation (fin de commande)
        self.validation_words = ['service', 'volée', 'droit', 'revers']
        
        # Buffer de commande en cours
        self.command_buffer = []
        
        print("\n" + "="*70)
        print("🎤 TEST AVEC MOT DE VALIDATION : 'service'")
        print("="*70)
        print("\n💡 PRINCIPE :")
        print("   1. Dites 'OK point gagnant Arnaud service'")
        print("   2. Le système écoute jusqu'à entendre 'service'")
        print("   3. Quand 'service' est détecté → VALIDATION automatique")
        print("\n🎯 COMMANDE À TESTER :")
        print("   'OK point gagnant Arnaud service'")
        print("\nArrêt : Dites 'stop' ou Ctrl+C")
        print("="*70 + "\n")
    
    def contains_validation_word(self, text):
        """Vérifie si le texte contient un mot de validation"""
        text_lower = text.lower()
        for word in self.validation_words:
            if word in text_lower:
                return True, word
        return False, None
    
    def process_command(self, full_text):
        """Traite la commande complète"""
        print("\n" + "="*70)
        print(f"✅ COMMANDE VALIDÉE : '{full_text}'")
        print("="*70)
        
        # Parser
        result = self.parser.parse(full_text)
        
        print("\n📊 PARSING :")
        for key, value in result.items():
            if value is not None:
                print(f"   • {key:15s} = {value}")
        
        # Validation
        is_valid, missing = self.parser.validate_command(result)
        
        print("\n🔍 RÉSULTAT :")
        if is_valid:
            print("   ✅ COMMANDE COMPLÈTE ET VALIDE")
            print(f"\n   → Point : {result.get('type_point')}")
            print(f"   → Joueur : {result.get('joueur')}")
            print(f"   → Coup : {result.get('type_coup')}")
        else:
            print(f"   ⚠️  COMMANDE INCOMPLÈTE")
            print(f"      {missing}")
        
        print("="*70 + "\n")
        
        # Réinitialiser le buffer
        self.command_buffer = []
    
    def initialize(self):
        """Initialise le recognizer"""
        if not SPEECH_RECOGNITION_AVAILABLE:
            print("❌ speech_recognition non installé")
            return False
        
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            print("🎧 Calibrage du microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            print("✅ Microphone prêt")
            print("🎤 En écoute... (dites 'OK point gagnant Arnaud service')\n")
            return True
            
        except Exception as e:
            print(f"❌ Erreur init : {e}")
            return False
    
    def listen_loop(self):
        """Boucle d'écoute avec validation par mot-clé"""
        while self.running:
            try:
                with self.microphone as source:
                    # Écoute LONGUE (10 secondes max)
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=10)
                
                try:
                    text = self.recognizer.recognize_google(audio, language="fr-FR")
                    
                    if text:
                        print(f"🎤 Audio : '{text}'")
                        
                        # Vérifier mot d'arrêt
                        if 'stop' in text.lower():
                            print("\n✋ Arrêt demandé")
                            self.running = False
                            return
                        
                        # Ajouter au buffer
                        self.command_buffer.append(text)
                        
                        # Vérifier si un mot de validation est présent
                        has_validation, word = self.contains_validation_word(text)
                        
                        if has_validation:
                            # Assembler toute la commande
                            full_command = ' '.join(self.command_buffer)
                            print(f"✓ Mot de validation détecté : '{word}'")
                            self.process_command(full_command)
                
                except sr.UnknownValueError:
                    print("❌ Pas compris")
                except sr.RequestError as e:
                    print(f"❌ Erreur API : {e}")
                
            except sr.WaitTimeoutError:
                # Si buffer non vide après timeout, afficher
                if self.command_buffer:
                    print(f"⏱️  Timeout - Buffer : {' '.join(self.command_buffer)}")
                    print("   (Attendez le mot de validation 'service'...)")
            except Exception as e:
                print(f"❌ Erreur : {e}")
                time.sleep(0.5)
    
    def start(self):
        """Lance l'écoute"""
        if not self.initialize():
            return False
        
        self.running = True
        
        thread = threading.Thread(target=self.listen_loop, daemon=True)
        thread.start()
        
        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n✋ Arrêt par l'utilisateur")
            self.running = False


if __name__ == '__main__':
    test = TestServiceValidation()
    test.start()
