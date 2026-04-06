"""
TEST EN DIRECT : Reconnaissance vocale + Parsing
Affiche CE QUI A ÉTÉ ENTENDU et CE QUI N'A PAS ÉTÉ ENTENDU

Commande cible : "OK point gagnant joueur1 service"
"""

import sys
import os
import threading
import time

# Ajouter le répertoire parent au path pour importer app
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import conditionnel
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[WARN] speech_recognition non disponible")

from app.voice.command_parser import CommandParser


class TestVoiceLive:
    """Teste la reconnaissance vocale en direct - AFFICHE TOUT"""
    
    def __init__(self):
        # Parser avec des PRÉNOMS (plus facile à dire et reconnaître)
        self.parser = CommandParser(joueurs=['Arnaud', 'Pierre', 'Thomas', 'Lucas'])
        
        # Recognizer
        self.recognizer = None
        self.microphone = None
        self.running = False
        
        # Compteurs
        self.count_heard = 0
        self.count_not_heard = 0
        
        print("\n" + "="*70)
        print("🎤 TEST VOCAL : 'OK point gagnant Arnaud service'")
        print("="*70)
        print("\n📊 Le test affiche :")
        print("   ✅ Ce qui A ÉTÉ ENTENDU (transcrit correctement)")
        print("   ❌ Ce qui N'A PAS ÉTÉ ENTENDU (silence/erreur)")
        print("\n💬 Exemples à dire :")
        print("   • 'OK point gagnant Arnaud service'")
        print("   • 'OK point gagnant Pierre volée'")
        print("   • 'OK faute directe Thomas'")
        print("\nArrêt : Dites 'stop' ou Ctrl+C")
        print("="*70 + "\n")
    
    def on_voice_heard(self, text):
        """Callback : Audio capturé ET transcrit avec succès"""
        self.count_heard += 1
        
        print("\n" + "="*70)
        print(f"✅ ENTENDU #{self.count_heard} : '{text}'")
        print("="*70)
        
        # Vérifier si c'est une commande d'arrêt
        if 'stop' in text.lower() or 'arrêt' in text.lower():
            print("\n✋ Arrêt demandé")
            self.running = False
            return
        
        # Parser la commande
        result = self.parser.parse(text)
        
        print("\n📊 PARSING :")
        for key, value in result.items():
            if value is not None:
                symbol = "✓" if value else "✗"
                print(f"   {symbol} {key:15s} = {value}")
        
        # Validation
        is_valid, missing = self.parser.validate_command(result)
        
        print("\n🔍 RÉSULTAT :")
        if is_valid:
            print("   ✅ COMMANDE VALIDE ET COMPLÈTE")
        else:
            print(f"   ⚠️  COMMANDE INCOMPLÈTE")
            print(f"      {missing}")
        
        print("="*70)
    
    def on_voice_not_heard(self, reason="Rien compris"):
        """Callback : Audio capté MAIS pas transcrit (silence/erreur)"""
        self.count_not_heard += 1
        
        print(f"\n❌ NON ENTENDU #{self.count_not_heard} : {reason}")
    
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
            
            print("✅ Microphone prêt\n")
            return True
            
        except Exception as e:
            print(f"❌ Erreur init : {e}")
            return False
    
    def listen_once(self):
        """Écoute UNE SEULE commande vocale"""
        try:
            print("🎤 Parlez maintenant...")
            
            with self.microphone as source:
                # Écoute une phrase (max 5 secondes)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
            
            # Tentative de transcription
            try:
                text = self.recognizer.recognize_google(audio, language="fr-FR")
                
                if text:
                    self.on_voice_heard(text)
                    return True
            
            except sr.UnknownValueError:
                self.on_voice_not_heard("Google n'a pas compris l'audio")
            except sr.RequestError as e:
                self.on_voice_not_heard(f"Erreur Google API: {e}")
            
        except sr.WaitTimeoutError:
            self.on_voice_not_heard("Timeout - aucun son détecté")
        except Exception as e:
            self.on_voice_not_heard(f"Erreur: {e}")
        
        return False
    
    def start(self):
        """Lance l'écoute MANUELLE (appuyer sur ENTRÉE à chaque fois)"""
        if not self.initialize():
            return False
        
        print("✅ Prêt ! Appuyez sur ENTRÉE pour chaque commande vocale\n")
        
        # Boucle manuelle
        try:
            while True:
                # Attendre ENTRÉE
                user_input = input(">>> Appuyez sur [ENTRÉE] pour parler (ou tapez 'stop' pour quitter) : ")
                
                if user_input.lower() in ['stop', 'quit', 'exit']:
                    print("\n✋ Arrêt demandé")
                    break
                
                # Écouter UNE commande
                self.listen_once()
                
                print()  # Ligne vide pour clarté
        
        except KeyboardInterrupt:
            print("\n\n✋ Arrêt par Ctrl+C")
        
        # Résumé
        print("\n" + "="*70)
        print("📊 RÉSUMÉ DU TEST")
        print("="*70)
        print(f"✅ Phrases entendues    : {self.count_heard}")
        print(f"❌ Phrases non entendues : {self.count_not_heard}")
        print("="*70 + "\n")


if __name__ == '__main__':
    test = TestVoiceLive()
    test.start()
