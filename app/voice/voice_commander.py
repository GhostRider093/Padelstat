"""
Module de commandes vocales - Priorise Windows Speech Recognition natif
Ordre de priorité: Windows SAPI > Google Speech > Whisper
"""

import threading
import time
import io
import wave
from typing import Callable, Optional

# 1. Essayer Windows Speech Recognition (API native - PRIORITAIRE)
try:
    from .voice_commander_windows import WindowsVoiceCommander, WINDOWS_SAPI_AVAILABLE
except ImportError:
    WINDOWS_SAPI_AVAILABLE = False
    print("[INFO] Module Windows Speech non disponible")

# 2. Fallback: Google Speech Recognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    print("[INFO] speech_recognition non disponible")

# 3. Dernier recours: Whisper (DÉSACTIVÉ par défaut car moins performant)
WHISPER_AVAILABLE = False  # Désactivé
WhisperModel = None  # type: ignore
pyaudio = None  # type: ignore
webrtcvad = None  # type: ignore


class VoiceCommander:
    """Gestionnaire de commandes vocales - Utilise Windows Speech en priorité"""
    
    def __init__(self, callback: Optional[Callable] = None, language: str = "fr-FR"):
        self.callback = callback
        self.language = language  # "fr-FR" pour Windows/Google
        
        self.running = False
        self.thread = None
        
        # Windows Speech (prioritaire)
        self.windows_commander = None
        
        # Fallback Google
        self.recognizer = None
        self.microphone = None
        
        # Whisper (désactivé)
        self.whisper_model = None
        self.audio = None
        self.vad = None
        
        # Déterminer quel système utiliser
        if WINDOWS_SAPI_AVAILABLE:
            self.mode = "windows"
            print("[VOICE] Utilisation: Windows Speech Recognition (API native)")
        elif SPEECH_RECOGNITION_AVAILABLE:
            self.mode = "google"
            print("[VOICE] Utilisation: Google Speech Recognition (fallback)")
        elif WHISPER_AVAILABLE:
            self.mode = "whisper"
            print("[VOICE] Utilisation: Whisper (dernier recours)")
        else:
            self.mode = None
            print("[ERROR] Aucun système de reconnaissance vocale disponible")
        
    def initialize(self) -> bool:
        """Initialise le système de reconnaissance (Windows prioritaire)"""
        if self.mode == "windows":
            return self._initialize_windows()
        elif self.mode == "google":
            return self._initialize_google()
        elif self.mode == "whisper":
            return self._initialize_whisper()
        else:
            return False
    
    def _initialize_windows(self) -> bool:
        """Initialise Windows Speech Recognition (API native)"""
        try:
            self.windows_commander = WindowsVoiceCommander(
                callback=self.callback,
                language=self.language
            )
            
            if self.windows_commander.initialize():
                print("[OK] Windows Speech Recognition prêt")
                return True
            else:
                print("[WARN] Échec init Windows Speech, fallback...")
                self.mode = "google"
                return self._initialize_google()
                
        except Exception as e:
            print(f"[WARN] Erreur init Windows Speech: {e}")
            self.mode = "google"
            return self._initialize_google()
    
    def _initialize_whisper(self) -> bool:
        """Initialise Whisper (rapide et précis)"""
        global WhisperModel, pyaudio, webrtcvad
        try:
            if WhisperModel is None or pyaudio is None or webrtcvad is None:
                from faster_whisper import WhisperModel as _WhisperModel
                import pyaudio as _pyaudio
                import webrtcvad as _webrtcvad
                WhisperModel = _WhisperModel
                pyaudio = _pyaudio
                webrtcvad = _webrtcvad

            # Charger le modèle Whisper (tiny ou base pour rapidité)
            print("[WHISPER] Chargement du modèle...")
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            
            # Initialiser PyAudio
            self.audio = pyaudio.PyAudio()
            
            # Initialiser Voice Activity Detection
            self.vad = webrtcvad.Vad(2)  # Aggressivité 2 (0-3)
            
            print("[OK] Whisper prêt (modèle base)")
            return True
            
        except Exception as e:
            print(f"[WARN] Erreur init Whisper: {e}")
            # Fallback sur Google
            self.use_whisper = False
            if SPEECH_RECOGNITION_AVAILABLE:
                return self._initialize_google()
            return False
    
    def _initialize_google(self) -> bool:
        """Initialise Google Speech Recognition"""
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            
            # Calibrer le bruit ambiant
            print("[GOOGLE] Calibrage du microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            print("[OK] Google Speech Recognition prêt")
            return True
            
        except Exception as e:
            print(f"[ERROR] Erreur init Google Speech: {e}")
            return False
    
    def start(self):
        """Démarre l'écoute"""
        # Mode Windows (prioritaire)
        if self.mode == "windows":
            if not self.windows_commander:
                if not self.initialize():
                    return False
            return self.windows_commander.start()
        
        # Modes Google/Whisper
        if not self.recognizer and not self.whisper_model:
            if not self.initialize():
                return False
        
        if self.running:
            return True
        
        self.running = True
        
        if self.mode == "whisper":
            self.thread = threading.Thread(target=self._listen_loop_whisper, daemon=True)
        else:
            self.thread = threading.Thread(target=self._listen_loop_google, daemon=True)
        
        self.thread.start()
        
        mode = "Whisper" if self.mode == "whisper" else "Google"
        print(f"[VOICE] Écoute vocale démarrée ({mode})")
        return True
    
    def stop(self):
        """Arrête l'écoute"""
        # Mode Windows
        if self.mode == "windows" and self.windows_commander:
            self.windows_commander.stop()
            return
        
        # Modes Google/Whisper
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        
        print("[VOICE] Écoute vocale arrêtée")
    
    def _listen_loop_whisper(self):
        """Boucle d'écoute avec Whisper"""
        RATE = 16000
        CHUNK_DURATION_MS = 30  # VAD frame
        CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)
        
        # Ouvrir le stream audio
        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        
        frames = []
        silence_chunks = 0
        MAX_SILENCE_CHUNKS = 20  # ~0.6s de silence
        
        print("[WHISPER] En écoute...")
        
        while self.running:
            try:
                # Lire un chunk audio
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # Vérifier si c'est de la voix
                is_speech = self.vad.is_speech(chunk, RATE)
                
                if is_speech:
                    frames.append(chunk)
                    silence_chunks = 0
                elif frames:
                    silence_chunks += 1
                    frames.append(chunk)
                    
                    # Si silence prolongé après de la voix, on transcrit
                    if silence_chunks > MAX_SILENCE_CHUNKS:
                        # Créer un fichier WAV en mémoire
                        audio_data = b''.join(frames)
                        
                        # Transcrire avec Whisper
                        try:
                            wav_io = io.BytesIO()
                            with wave.open(wav_io, 'wb') as wav:
                                wav.setnchannels(1)
                                wav.setsampwidth(2)  # 16-bit
                                wav.setframerate(RATE)
                                wav.writeframes(audio_data)
                            
                            wav_io.seek(0)
                            
                            # Transcription
                            segments, info = self.whisper_model.transcribe(
                                wav_io,
                                language=self.language,
                                beam_size=5,
                                vad_filter=False  # Déjà fait par webrtcvad
                            )
                            
                            text = " ".join([seg.text for seg in segments]).strip()
                            
                            if text:
                                print(f"[WHISPER] Reconnu: '{text}'")
                                
                                # Callback immédiat
                                if self.callback:
                                    self.callback(text)
                        
                        except Exception as e:
                            print(f"[WARN] Erreur transcription: {e}")
                        
                        # Réinitialiser
                        frames = []
                        silence_chunks = 0
            
            except Exception as e:
                print(f"[WARN] Erreur écoute Whisper: {e}")
                time.sleep(0.5)
        
        stream.stop_stream()
        stream.close()
    
    def _listen_loop_google(self):
        """Boucle d'écoute Google (fallback)"""
        while self.running:
            try:
                with self.microphone as source:
                    # Écoute courte (3 secondes max par phrase)
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)
                
                # Transcription en arrière-plan
                try:
                    text = self.recognizer.recognize_google(audio, language=self.language)
                    
                    if text:
                        print(f"[VOICE] Reconnu: '{text}'")
                        
                        # Callback immédiat
                        if self.callback:
                            self.callback(text)
                
                except sr.UnknownValueError:
                    pass  # Rien compris, on continue
                except sr.RequestError as e:
                    print(f"[WARN] Erreur Google API: {e}")
                    time.sleep(2)
                
            except sr.WaitTimeoutError:
                pass  # Timeout normal, on continue
            except Exception as e:
                print(f"[WARN] Erreur écoute: {e}")
                time.sleep(0.5)
