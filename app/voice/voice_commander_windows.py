"""app.voice.voice_commander_windows

Reconnaissance vocale via l'API Windows Speech (SAPI) avec pywin32.

Important: l'objet SAPI ne fournit pas une méthode fiable type `GetEvents()`.
La bonne approche avec pywin32 est d'attacher un handler d'événements COM
et de pomper la file de messages Windows (`pythoncom.PumpWaitingMessages()`).
"""

import threading
import time
from typing import Callable, Optional, List

# Import de l'API Windows COM
try:
    import win32com.client
    import pythoncom
    WINDOWS_SAPI_AVAILABLE = True
except ImportError:
    WINDOWS_SAPI_AVAILABLE = False
    print("[WARN] pywin32 non disponible - installer avec: pip install pywin32")


class WindowsVoiceCommander:
    """Gestionnaire de reconnaissance vocale utilisant Windows Speech Recognition API"""
    
    def __init__(self, callback: Optional[Callable] = None, language: str = "fr-FR"):
        """
        Args:
            callback: Fonction appelée avec le texte reconnu
            language: Code langue (fr-FR, en-US, etc.)
        """
        self.callback = callback
        self.language = language
        
        self.running = False
        self.thread = None
        
        # Objets SAPI
        self.recognizer = None
        self.context = None
        self.grammar = None
        
        # Grammaire personnalisée (pour vos commandes spécifiques)
        self.custom_phrases = []

        # Dernier texte reconnu (thread-safe simple)
        self._last_text: Optional[str] = None
        
    def set_custom_phrases(self, phrases: List[str]):
        """
        Définit des phrases personnalisées pour améliorer la reconnaissance
        
        Args:
            phrases: Liste des commandes attendues
        """
        self.custom_phrases = phrases
        print(f"[SAPI] {len(phrases)} phrases personnalisées configurées")
    
    def initialize(self) -> bool:
        """Initialise le système de reconnaissance Windows"""
        if not WINDOWS_SAPI_AVAILABLE:
            print("[ERROR] pywin32 requis. Installer: pip install pywin32")
            return False
        
        try:
            # Smoke-test COM + création d'un recognizer.
            pythoncom.CoInitialize()
            _recognizer = win32com.client.Dispatch("SAPI.SpInProcRecognizer")

            # S'assurer qu'une entrée audio micro est branchée.
            try:
                _recognizer.AudioInputStream = win32com.client.Dispatch("SAPI.SpMMAudioIn")
            except Exception:
                # Certaines configs exposent AudioInput au lieu de AudioInputStream
                try:
                    _recognizer.AudioInput = win32com.client.Dispatch("SAPI.SpMMAudioIn")
                except Exception:
                    pass

            _context = _recognizer.CreateRecoContext()
            _grammar = _context.CreateGrammar()
            try:
                _grammar.DictationLoad()
            except Exception:
                pass
            _grammar.DictationSetState(0)

            # Tenter de forcer fr-FR (peut échouer selon configuration Windows)
            try:
                _recognizer.SetPropertyNum("Language", 0x040C)  # fr-FR
            except Exception:
                print("[WARN] Impossible de forcer la langue française, utilisation par défaut")

            print("[OK] Windows Speech Recognition initialisé")
            print(f"[INFO] Langue: {self.language}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Erreur initialisation Windows Speech: {e}")
            return False
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    
    def start(self):
        """Démarre l'écoute en continu"""
        if self.running:
            return True
        
        self.running = True
        self.thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        
        print("[VOICE] Écoute Windows Speech démarrée")
        return True
    
    def stop(self):
        """Arrête l'écoute"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        
        print("[VOICE] Écoute Windows Speech arrêtée")
    
    def _listen_loop(self):
        """Boucle d'écoute principale (thread séparé) via événements COM."""
        pythoncom.CoInitialize()

        try:
            recognizer = win32com.client.Dispatch("SAPI.SpInProcRecognizer")

            try:
                recognizer.AudioInputStream = win32com.client.Dispatch("SAPI.SpMMAudioIn")
            except Exception:
                try:
                    recognizer.AudioInput = win32com.client.Dispatch("SAPI.SpMMAudioIn")
                except Exception:
                    pass

            context = recognizer.CreateRecoContext()
            try:
                # SRERecognition (1) suffit pour OnRecognition
                context.EventInterests = 1
            except Exception:
                pass
            grammar = context.CreateGrammar()

            # Activer la dictée libre
            try:
                grammar.DictationLoad()
            except Exception:
                pass
            grammar.DictationSetState(1)

            # Handler d'événements COM
            owner = self

            class _ContextEvents:
                def OnRecognition(self, _stream_number, _stream_position, _recognition_type, result):
                    try:
                        text = result.PhraseInfo.GetText()
                    except Exception:
                        text = None

                    if text:
                        owner._last_text = text
                        if owner.callback:
                            owner.callback(text)

            win32com.client.WithEvents(context, _ContextEvents)

            print("[SAPI] Écoute active...")
            while self.running:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.05)

            try:
                grammar.DictationSetState(0)
            except Exception:
                pass

        except Exception as e:
            if self.running:
                print(f"[ERROR] Erreur boucle écoute SAPI: {e}")
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
    
    def recognize_once(self, timeout: float = 5.0) -> Optional[str]:
        """
        Reconnaissance unique (bloquante)
        
        Args:
            timeout: Temps max d'attente en secondes
            
        Returns:
            Texte reconnu ou None
        """
        try:
            pythoncom.CoInitialize()

            recognizer = win32com.client.Dispatch("SAPI.SpInProcRecognizer")

            try:
                recognizer.AudioInputStream = win32com.client.Dispatch("SAPI.SpMMAudioIn")
            except Exception:
                try:
                    recognizer.AudioInput = win32com.client.Dispatch("SAPI.SpMMAudioIn")
                except Exception:
                    pass

            context = recognizer.CreateRecoContext()
            try:
                context.EventInterests = 1
            except Exception:
                pass
            grammar = context.CreateGrammar()

            recognized: Dict[str, Optional[str]] = {"text": None}

            class _ContextEvents:
                def OnRecognition(self, _stream_number, _stream_position, _recognition_type, result):
                    try:
                        text = result.PhraseInfo.GetText()
                    except Exception:
                        text = None
                    if text:
                        recognized["text"] = text

            win32com.client.WithEvents(context, _ContextEvents)
            try:
                grammar.DictationLoad()
            except Exception:
                pass
            grammar.DictationSetState(1)

            print("[SAPI] Écoute (one-shot)...")

            start_time = time.time()
            while time.time() - start_time < timeout:
                pythoncom.PumpWaitingMessages()
                if recognized["text"]:
                    break
                time.sleep(0.03)

            try:
                grammar.DictationSetState(0)
            except Exception:
                pass

            return recognized["text"]
            
        except Exception as e:
            print(f"[ERROR] Erreur reconnaissance SAPI: {e}")
            return None
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass


# Test simple
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🎤 TEST WINDOWS SPEECH RECOGNITION API")
    print("=" * 60 + "\n")
    
    def on_recognized(text):
        print(f"\n✅ Reconnu: '{text}'\n")
    
    commander = WindowsVoiceCommander(callback=on_recognized)
    
    if commander.initialize():
        print("\n▶ Démarrage de l'écoute continue...")
        print("▶ Parlez maintenant ! (Ctrl+C pour arrêter)\n")
        
        commander.start()
        
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n⏹ Arrêt...")
            commander.stop()
            print("👋 Terminé\n")
    else:
        print("\n❌ Impossible d'initialiser Windows Speech Recognition")
        print("📦 Installer: pip install pywin32\n")
