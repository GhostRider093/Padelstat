"""Commandes vocales mains-libres (STT) avec fallback.

Ordre de priorité (Windows):
- Windows SAPI via pywin32
- SpeechRecognition (Google) (nécessite internet)
- Whisper (optionnel; désactivé par défaut ici)

Ce module est volontairement "UI-agnostique": il ne fait que remonter le texte reconnu via callback.
"""

import threading
import time
import io
import wave
from typing import Callable, Optional

from .voice_logger import VoiceLogger

try:
    from .voice_commander_windows import WindowsVoiceCommander, WINDOWS_SAPI_AVAILABLE
except Exception:
    WindowsVoiceCommander = None  # type: ignore
    WINDOWS_SAPI_AVAILABLE = False

try:
    import speech_recognition as sr

    SPEECH_RECOGNITION_AVAILABLE = True
except Exception:
    sr = None  # type: ignore
    SPEECH_RECOGNITION_AVAILABLE = False


class VoiceCommander:
    """Gestionnaire de reconnaissance vocale"""

    def __init__(
        self,
        callback: Optional[Callable[[str], None]] = None,
        language: str = "fr-FR",
        enable_whisper: bool = False,
        log_dir: str = "data",
    ):
        self.callback = callback
        self.language = language
        self.logger = VoiceLogger(log_dir=log_dir)

        self.running = False
        self.thread = None

        self.windows_commander = None
        self.recognizer = None
        self.microphone = None

        self.enable_whisper = bool(enable_whisper)
        self.whisper_model = None
        self.audio = None
        self.vad = None

        self.mode = None
        if WINDOWS_SAPI_AVAILABLE:
            self.mode = "windows"
            print("[VOICE] Utilisation: Windows Speech Recognition (API native)")
        elif SPEECH_RECOGNITION_AVAILABLE:
            self.mode = "google"
            print("[VOICE] Utilisation: SpeechRecognition/Google (fallback)")
        elif self.enable_whisper:
            self.mode = "whisper"
            print("[VOICE] Utilisation: Whisper (dernier recours)")
        else:
            print("[ERROR] Aucun système de reconnaissance vocale disponible")

        self.logger.log_event(
            "voice_commander_init",
            {
                "mode": self.mode,
                "language": self.language,
                "enable_whisper": self.enable_whisper,
                "windows_sapi_available": WINDOWS_SAPI_AVAILABLE,
                "speech_recognition_available": SPEECH_RECOGNITION_AVAILABLE,
                "log_file": self.logger.log_file,
            },
        )

    def initialize(self) -> bool:
        if self.mode == "windows":
            return self._initialize_windows()
        if self.mode == "google":
            return self._initialize_google()
        if self.mode == "whisper":
            return self._initialize_whisper()
        return False

    def _initialize_windows(self) -> bool:
        if WindowsVoiceCommander is None:
            self.logger.log_event("init_windows_unavailable", {})
            self.mode = "google"
            return self._initialize_google()
        try:
            self.windows_commander = WindowsVoiceCommander(callback=self.callback, language=self.language)
            if self.windows_commander.initialize():
                print("[OK] Windows Speech prêt")
                self.logger.log_event("init_windows_ok", {"mode": self.mode})
                return True
            print("[WARN] Échec init Windows Speech, fallback Google...")
            self.logger.log_event("init_windows_failed_fallback_google", {})
            self.mode = "google"
            return self._initialize_google()
        except Exception as e:
            print(f"[WARN] Erreur init Windows Speech: {e}")
            self.logger.log_exception("initialize_windows", e)
            self.mode = "google"
            return self._initialize_google()

    def _initialize_google(self) -> bool:
        if not SPEECH_RECOGNITION_AVAILABLE or sr is None:
            self.logger.log_event("init_google_unavailable", {})
            return False
        try:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            print("[GOOGLE] Calibrage du microphone...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

            print("[OK] SpeechRecognition prêt")
            self.logger.log_event("init_google_ok", {"language": self.language})
            return True
        except Exception as e:
            print(f"[ERROR] Erreur init SpeechRecognition: {e}")
            self.logger.log_exception("initialize_google", e)
            return False

    def _initialize_whisper(self) -> bool:
        if not self.enable_whisper:
            self.logger.log_event("init_whisper_disabled", {})
            return False
        try:
            from faster_whisper import WhisperModel
            import pyaudio
            webrtcvad = __import__("webrtcvad")

            print("[WHISPER] Chargement du modèle...")
            self.whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            self.audio = pyaudio.PyAudio()
            self.vad = webrtcvad.Vad(2)
            print("[OK] Whisper prêt")
            self.logger.log_event("init_whisper_ok", {"language": self.language})
            return True
        except Exception as e:
            print(f"[WARN] Erreur init Whisper: {e}")
            self.logger.log_exception("initialize_whisper", e)
            return False

    def start(self) -> bool:
        if self.mode == "windows":
            if not self.windows_commander:
                if not self.initialize():
                    self.logger.log_event("start_failed_initialize", {"mode": self.mode})
                    return False
            if not self.windows_commander:
                self.logger.log_event("start_windows_missing_commander", {})
                return False
            ok = bool(self.windows_commander.start())
            self.logger.log_event("start_windows", {"ok": ok})
            return ok

        if not self.recognizer and not self.whisper_model:
            if not self.initialize():
                self.logger.log_event("start_failed_initialize", {"mode": self.mode})
                return False

        if self.running:
            self.logger.log_event("start_already_running", {"mode": self.mode})
            return True

        self.running = True
        if self.mode == "whisper":
            self.thread = threading.Thread(target=self._listen_loop_whisper, daemon=True)
        else:
            self.thread = threading.Thread(target=self._listen_loop_google, daemon=True)
        self.thread.start()

        print(f"[VOICE] Écoute démarrée ({self.mode})")
        self.logger.log_event("start_ok", {"mode": self.mode, "thread": str(self.thread)})
        return True

    def stop(self):
        if self.mode == "windows" and self.windows_commander:
            self.windows_commander.stop()
            self.logger.log_event("stop_windows", {})
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        print("[VOICE] Écoute arrêtée")
        self.logger.log_event("stop_ok", {"mode": self.mode})

    def _listen_loop_whisper(self):
        import pyaudio

        if self.audio is None or self.vad is None or self.whisper_model is None:
            self.logger.log_event("whisper_loop_missing_components", {})
            return

        RATE = 16000
        CHUNK_DURATION_MS = 30
        CHUNK_SIZE = int(RATE * CHUNK_DURATION_MS / 1000)

        stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        frames = []
        silence_chunks = 0
        MAX_SILENCE_CHUNKS = 20

        print("[WHISPER] En écoute...")
        while self.running:
            try:
                chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                is_speech = self.vad.is_speech(chunk, RATE)

                if is_speech:
                    frames.append(chunk)
                    silence_chunks = 0
                elif frames:
                    silence_chunks += 1
                    frames.append(chunk)

                    if silence_chunks > MAX_SILENCE_CHUNKS:
                        audio_data = b"".join(frames)
                        try:
                            wav_io = io.BytesIO()
                            with wave.open(wav_io, "wb") as wav:
                                wav.setnchannels(1)
                                wav.setsampwidth(2)
                                wav.setframerate(RATE)
                                wav.writeframes(audio_data)

                            wav_io.seek(0)
                            segments, _info = self.whisper_model.transcribe(
                                wav_io,
                                language=self.language,
                                beam_size=5,
                                vad_filter=False,
                            )
                            text = " ".join([seg.text for seg in segments]).strip()
                            if text and self.callback:
                                self.logger.log_event("whisper_text", {"text": text, "length": len(text)})
                                self.callback(text)
                        except Exception as e:
                            print(f"[WARN] Erreur transcription Whisper: {e}")
                            self.logger.log_exception("listen_loop_whisper_transcribe", e)

                        frames = []
                        silence_chunks = 0

            except Exception as e:
                print(f"[WARN] Erreur écoute Whisper: {e}")
                self.logger.log_exception("listen_loop_whisper", e)
                time.sleep(0.5)

        stream.stop_stream()
        stream.close()

    def _listen_loop_google(self):
        if self.microphone is None or self.recognizer is None or sr is None:
            self.logger.log_event("google_loop_missing_components", {})
            return

        while self.running:
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=3)

                try:
                    recognize_google = getattr(self.recognizer, "recognize_google", None)
                    if not callable(recognize_google):
                        self.logger.log_event("google_recognize_unavailable", {})
                        time.sleep(1)
                        continue
                    raw_text = recognize_google(audio, language=self.language)
                    text = str(raw_text).strip()
                    if text and self.callback:
                        self.logger.log_event("google_text", {"text": text, "length": len(text)})
                        self.callback(text)
                except sr.UnknownValueError:
                    self.logger.log_event("google_unknown_value", {})
                    pass
                except sr.RequestError as e:
                    print(f"[WARN] Erreur Google API: {e}")
                    self.logger.log_exception("google_request_error", e)
                    time.sleep(2)

            except sr.WaitTimeoutError:
                self.logger.log_event("google_wait_timeout", {})
                pass
            except Exception as e:
                print(f"[WARN] Erreur écoute: {e}")
                self.logger.log_exception("listen_loop_google", e)
                time.sleep(0.5)
