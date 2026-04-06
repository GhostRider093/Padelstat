"""Push-to-talk (PTT): enregistre un segment audio court puis transcrit.

Ce module ne dépend pas d'une UI: il expose des callbacks.
- ui_callback(event_type, data)
- create_annotation_callback(audio_text, video_timestamp) -> bool (reconnu?)

Le stockage des captures est optionnel mais activé par défaut (JSON + WAV).
"""

import os
import json
import wave
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, List

from .voice_logger import VoiceLogger

# PyAudio est requis uniquement pour l'enregistrement (PTT).
# On le rend optionnel pour que le package soit importable même en mode "parser only".
try:
    import pyaudio  # type: ignore

    PYAUDIO_AVAILABLE = True
except Exception:
    pyaudio = None  # type: ignore
    PYAUDIO_AVAILABLE = False
    print("[WARN] pyaudio non disponible: le mode push-to-talk (PTT) sera indisponible")

try:
    import speech_recognition as sr

    SPEECH_AVAILABLE = True
except Exception:
    sr = None  # type: ignore
    SPEECH_AVAILABLE = False
    print("[WARN] speech_recognition non disponible pour push-to-talk")


class VoiceBatchRecorder:
    """Enregistreur vocal push-to-talk avec création d'évènement/annotation"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.logger = VoiceLogger(log_dir=data_dir)

        self.audio_dir = os.path.join(self.data_dir, "voice_audio")
        os.makedirs(self.audio_dir, exist_ok=True)

        self.session_file = None
        self.session_data = None
        self.video_path = None

        self._capture_counter = 0

        self.is_recording = False
        self.audio_frames: List[bytes] = []
        self.audio = None
        self.stream = None
        self.current_timestamp = 0.0
        self.recording_started_at: Optional[float] = None

        self.recognizer = None
        if SPEECH_AVAILABLE and sr is not None:
            try:
                self.recognizer = sr.Recognizer()
                print("[VOICE] ✓ SpeechRecognition prêt")
            except Exception as e:
                print(f"[WARN] SpeechRecognition non initialisé: {e}")

        self.CHUNK = 1024
        self.FORMAT = (pyaudio.paInt16 if PYAUDIO_AVAILABLE and pyaudio is not None else None)
        self.CHANNELS = 1
        self.RATE = 16000

        self.ui_callback: Optional[Callable] = None
        self.create_annotation_callback: Optional[Callable] = None

        self.logger.log_event(
            "ptt_init",
            {
                "data_dir": os.path.abspath(self.data_dir),
                "pyaudio_available": PYAUDIO_AVAILABLE,
                "speech_available": SPEECH_AVAILABLE,
                "log_file": self.logger.log_file,
            },
        )

    def start_session(
        self,
        video_path: str,
        ui_callback: Optional[Callable] = None,
        create_annotation_callback: Optional[Callable] = None,
    ):
        if not PYAUDIO_AVAILABLE or pyaudio is None:
            raise RuntimeError(
                "PyAudio est requis pour le mode push-to-talk (PTT). "
                "Installez-le (pip install pyaudio) puis réessayez."
            )

        self.video_path = video_path
        self.ui_callback = ui_callback
        self.create_annotation_callback = create_annotation_callback

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(self.data_dir, f"voice_session_{session_id}.json")
        self.session_data = {
            "session_id": session_id,
            "video_path": video_path,
            "start_time": datetime.now().isoformat(),
            "captures": [],
            "unrecognized": [],
        }
        self._capture_counter = 0
        self._save_session()

        print(f"[VOICE] Session démarrée: {session_id}")
        print(f"[VOICE-DEBUG] Log absolu: {self.logger.log_file}")
        self.logger.log_event(
            "ptt_start_session",
            {
                "session_id": session_id,
                "video_path": video_path,
                "session_file": self.session_file,
            },
        )
        try:
            self.audio = pyaudio.PyAudio()
            self.logger.log_event("ptt_audio_init_ok", {})
        except Exception as e:
            print(f"[ERROR] PyAudio init failed: {e}")
            self.logger.log_exception("ptt_audio_init", e)

    def start_recording(self, video_timestamp: float):
        if not PYAUDIO_AVAILABLE or pyaudio is None:
            print("[ERROR] PyAudio indisponible: impossible de démarrer un enregistrement PTT")
            self.logger.log_event("ptt_start_recording_rejected", {"reason": "pyaudio_unavailable"})
            return
        if self.is_recording:
            self.logger.log_event("ptt_start_recording_ignored", {"reason": "already_recording"})
            return
        if not self.audio:
            print("[ERROR] PyAudio non initialisé")
            self.logger.log_event("ptt_start_recording_rejected", {"reason": "audio_not_initialized"})
            return
        if self.FORMAT is None:
            print("[ERROR] Format audio PTT non initialisé")
            self.logger.log_event("ptt_start_recording_rejected", {"reason": "format_not_initialized"})
            return

        self.is_recording = True
        self.audio_frames = []
        self.current_timestamp = float(video_timestamp)
        self.recording_started_at = time.time()
        self.logger.log_event("ptt_recording_started", {"video_timestamp": float(video_timestamp)})

        try:
            audio_format = self.FORMAT
            if audio_format is None:
                self.logger.log_event("ptt_start_recording_rejected", {"reason": "format_none"})
                return

            self.stream = self.audio.open(
                format=audio_format,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
            )

            def record():
                while self.is_recording:
                    try:
                        stream = self.stream
                        if stream is None:
                            break
                        data = stream.read(self.CHUNK, exception_on_overflow=False)
                        self.audio_frames.append(data)
                    except Exception:
                        break

            threading.Thread(target=record, daemon=True).start()

            if self.ui_callback:
                self.ui_callback("recording_started", {"timestamp": float(video_timestamp)})

        except Exception as e:
            print(f"[ERROR] Démarrage enregistrement: {e}")
            self.logger.log_exception("ptt_start_recording", e)
            self.is_recording = False

    def stop_recording(self):
        if not self.is_recording:
            self.logger.log_event("ptt_stop_recording_ignored", {"reason": "not_recording"})
            return

        self.is_recording = False

        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

        frames_bytes = b"".join(self.audio_frames)
        capture_timestamp = float(self.current_timestamp)
        capture_started_at = self.recording_started_at
        capture_stopped_at = time.time()

        self._capture_counter += 1
        capture_id = self._capture_counter
        self.logger.log_event(
            "ptt_recording_stopped",
            {
                "capture_id": int(capture_id),
                "video_timestamp": capture_timestamp,
                "bytes": len(frames_bytes),
            },
        )

        threading.Thread(
            target=self._transcribe_and_save,
            args=(frames_bytes, capture_timestamp, capture_id, capture_started_at, capture_stopped_at),
            daemon=True,
        ).start()

    def _transcribe_and_save(
        self,
        frames_bytes: bytes,
        video_timestamp: float,
        capture_id: int,
        started_at: Optional[float],
        stopped_at: Optional[float],
    ):
        if not frames_bytes:
            self.logger.log_event("ptt_capture_empty", {"capture_id": int(capture_id)})
            return

        try:
            session_id = (self.session_data or {}).get("session_id") or "no_session"
            safe_ts = int(max(0.0, float(video_timestamp)) * 1000)
            wav_filename = f"voice_{session_id}_{capture_id:04d}_{safe_ts}ms.wav"
            wav_path = os.path.join(self.audio_dir, wav_filename)

            if self.audio is None or self.FORMAT is None:
                self.logger.log_event(
                    "ptt_transcribe_missing_audio_components",
                    {"capture_id": int(capture_id), "audio_is_none": self.audio is None, "format_is_none": self.FORMAT is None},
                )
                return

            with wave.open(wav_path, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(frames_bytes)

            self.logger.log_event(
                "ptt_wav_saved",
                {
                    "capture_id": int(capture_id),
                    "wav_path": os.path.abspath(wav_path),
                    "bytes": len(frames_bytes),
                },
            )

            audio_text: str = ""
            if self.recognizer and SPEECH_AVAILABLE and sr is not None:
                try:
                    with sr.AudioFile(wav_path) as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                        audio_data = self.recognizer.record(source)
                        recognize_google = getattr(self.recognizer, "recognize_google", None)
                        if callable(recognize_google):
                            raw_text = recognize_google(audio_data, language="fr-FR")
                            audio_text = str(raw_text).strip()
                        else:
                            self.logger.log_event("ptt_google_recognize_unavailable", {"capture_id": int(capture_id)})
                            audio_text = ""
                    self.logger.log_event(
                        "ptt_google_text",
                        {"capture_id": int(capture_id), "text": audio_text, "length": len(audio_text)},
                    )
                except sr.UnknownValueError:
                    audio_text = ""
                    self.logger.log_event("ptt_google_unknown_value", {"capture_id": int(capture_id)})
                except sr.RequestError as e:
                    print(f"[ERROR] Google Speech API échoué: {e}")
                    self.logger.log_exception("ptt_google_request_error", e)
                    audio_text = ""
            else:
                audio_text = ""
                self.logger.log_event("ptt_stt_unavailable", {"capture_id": int(capture_id)})

            capture = {
                "id": int(capture_id),
                "video_timestamp": float(video_timestamp),
                "capture_time": datetime.now().isoformat(),
                "audio_wav": wav_path,
                "recording_started_at": started_at,
                "recording_stopped_at": stopped_at,
                "recording_duration_s": (float(stopped_at - started_at) if started_at and stopped_at else None),
                "audio_text": (audio_text or "").lower().strip(),
                "processed": False,
                "status": "pending",
            }

            success = False
            if audio_text and self.create_annotation_callback:
                success = bool(self.create_annotation_callback(audio_text, float(video_timestamp)))

            self.logger.log_event(
                "ptt_annotation_result",
                {
                    "capture_id": int(capture_id),
                    "success": bool(success),
                    "audio_text": audio_text,
                },
            )

            capture["processed"] = True
            capture["status"] = "recognized" if success else "unrecognized"

            if self.session_data is not None:
                if not success:
                    self.session_data["unrecognized"].append(capture)
                self.session_data["captures"].append(capture)
                self._save_session()

            if self.ui_callback:
                self.ui_callback(
                    "capture_added",
                    {
                        "id": int(capture_id),
                        "timestamp": float(video_timestamp),
                        "audio_text": (audio_text or ""),
                        "success": bool(success),
                        "audio_wav": wav_path,
                    },
                )

        except Exception as e:
            print(f"[ERROR] Transcription: {e}")
            self.logger.log_exception("ptt_transcribe_and_save", e)

    def _save_session(self):
        if not self.session_file or not self.session_data:
            return
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=2)
            self.logger.log_event("ptt_session_saved", {"session_file": self.session_file})
        except Exception as e:
            print(f"[ERROR] Sauvegarde session: {e}")
            self.logger.log_exception("ptt_save_session", e)

    def get_pending_captures(self) -> List[Dict]:
        if not self.session_data:
            return []
        return [c for c in self.session_data.get("captures", []) if not c.get("processed")]

    def mark_as_processed(self, capture_id: int, success: bool):
        if not self.session_data:
            return
        for capture in self.session_data.get("captures", []) or []:
            if int(capture.get("id", -1)) == int(capture_id):
                capture["processed"] = True
                capture["status"] = "recognized" if success else "unrecognized"
                if not success:
                    self.session_data.setdefault("unrecognized", []).append(capture)
                self._save_session()
                break

    def get_unrecognized(self) -> List[Dict]:
        if not self.session_data:
            return []
        return self.session_data.get("unrecognized", []) or []

    def cleanup(self):
        self.is_recording = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
        self.logger.log_event("ptt_cleanup", {})
