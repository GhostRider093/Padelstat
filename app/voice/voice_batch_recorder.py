"""
Module Push-to-Talk pour enregistrement vocal instantané
Capture rapide : timestamp vidéo + audio → transcription Google Speech → création annotation immédiate
"""

import os
import json
import wave
import threading
import time
from datetime import datetime
from typing import Optional, Callable, Dict, List
import pyaudio

# Windows Speech Recognition
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except ImportError:
    SPEECH_AVAILABLE = False
    print("[WARN] speech_recognition non disponible pour push-to-talk")


class VoiceBatchRecorder:
    """Enregistreur vocal push-to-talk avec création annotation instantanée"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Args:
            data_dir: Dossier pour stocker les sessions JSON
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        # Dossier de stockage des fichiers audio (WAV) pour relecture / debug
        self.audio_dir = os.path.join(self.data_dir, "voice_audio")
        os.makedirs(self.audio_dir, exist_ok=True)
        
        # Session courante
        self.session_file = None
        self.session_data = None
        self.video_path = None

        self._capture_counter = 0
        
        # Enregistrement audio
        self.is_recording = False
        self.audio_frames = []
        self.audio = None
        self.stream = None
        self.current_timestamp = 0.0
        self.recording_started_at = None
        
        # Windows Speech Recognition
        self.recognizer = None
        if SPEECH_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                print("[VOICE] ✓ Google Speech Recognition prêt")
            except Exception as e:
                print(f"[WARN] Speech Recognition non initialisé: {e}")
        
        # Configuration audio
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        
        # Callback pour mise à jour UI et création annotation
        self.ui_callback = None
        self.create_annotation_callback = None
    
    def start_session(self, video_path: str, ui_callback: Optional[Callable] = None, create_annotation_callback: Optional[Callable] = None):
        """
        Démarre une nouvelle session d'enregistrement vocal
        
        Args:
            video_path: Chemin de la vidéo en cours
            ui_callback: Callback pour notifier l'UI (capture, transcription)
            create_annotation_callback: Callback pour créer l'annotation instantanément
        """
        self.video_path = video_path
        self.ui_callback = ui_callback
        self.create_annotation_callback = create_annotation_callback
        
        # Créer fichier de session
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(self.data_dir, f"voice_session_{session_id}.json")
        
        self.session_data = {
            "session_id": session_id,
            "video_path": video_path,
            "start_time": datetime.now().isoformat(),
            "captures": [],
            "unrecognized": []
        }

        self._capture_counter = 0
        
        self._save_session()
        print(f"[VOICE] Session démarrée: {session_id}")
        
        # Initialiser PyAudio
        try:
            self.audio = pyaudio.PyAudio()
        except Exception as e:
            print(f"[ERROR] PyAudio init failed: {e}")
    
    def start_recording(self, video_timestamp: float):
        """
        Démarre l'enregistrement audio (appui touche)
        
        Args:
            video_timestamp: Timestamp vidéo en secondes (float) - même format que annotations manuelles
        """
        if self.is_recording:
            print("[WARN] Enregistrement déjà en cours")
            return
        
        if not self.audio:
            print("[ERROR] PyAudio non initialisé")
            return
        
        self.is_recording = True
        self.audio_frames = []
        self.current_timestamp = video_timestamp
        self.recording_started_at = time.time()
        
        try:
            self.stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            
            # Thread d'enregistrement
            def record():
                print("[VOICE] 🎤 Enregistrement...")
                while self.is_recording:
                    try:
                        data = self.stream.read(self.CHUNK, exception_on_overflow=False)
                        self.audio_frames.append(data)
                    except Exception as e:
                        print(f"[ERROR] Erreur enregistrement: {e}")
                        break
            
            threading.Thread(target=record, daemon=True).start()
            
            # Notifier UI
            if self.ui_callback:
                self.ui_callback("recording_started", {"timestamp": video_timestamp})
                
        except Exception as e:
            print(f"[ERROR] Démarrage enregistrement: {e}")
            self.is_recording = False
    
    def stop_recording(self):
        """
        Arrête l'enregistrement et lance la transcription (relâche touche)
        """
        if not self.is_recording:
            return
        
        self.is_recording = False
        
        # Fermer stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        print("[VOICE] ⏹️ Enregistrement arrêté")

        # Snapshot des données pour éviter les races (on peut relancer un enregistrement pendant la transcription)
        frames_bytes = b"".join(self.audio_frames)
        capture_timestamp = float(self.current_timestamp)
        capture_started_at = self.recording_started_at
        capture_stopped_at = time.time()

        self._capture_counter += 1
        capture_id = self._capture_counter

        # Transcription en background
        threading.Thread(
            target=self._transcribe_and_save,
            args=(frames_bytes, capture_timestamp, capture_id, capture_started_at, capture_stopped_at),
            daemon=True,
        ).start()
    
    def _transcribe_and_save(self, frames_bytes: bytes, video_timestamp: float, capture_id: int, started_at: Optional[float], stopped_at: Optional[float]):
        """Transcrit l'audio (Google Speech) et crée l'annotation. Sauvegarde aussi le .wav pour relecture."""
        if not frames_bytes:
            print("[WARN] Pas de données audio")
            return
        
        try:
            # Sauvegarder audio en WAV (persistant)
            session_id = (self.session_data or {}).get("session_id") or "no_session"
            safe_ts = int(max(0.0, float(video_timestamp)) * 1000)
            wav_filename = f"voice_{session_id}_{capture_id:04d}_{safe_ts}ms.wav"
            wav_path = os.path.join(self.audio_dir, wav_filename)

            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(frames_bytes)
            
            # Transcription Google Speech API
            audio_text = ""
            if self.recognizer and SPEECH_AVAILABLE:
                print("[VOICE] Transcription Google Speech API...")
                start_time = time.time()
                
                try:
                    with sr.AudioFile(wav_path) as source:
                        # Ajuster pour le bruit ambiant
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.2)
                        audio_data = self.recognizer.record(source)
                        
                        # Utiliser Google Speech API (gratuit, rapide, bon français)
                        audio_text = self.recognizer.recognize_google(audio_data, language="fr-FR")
                        duration = time.time() - start_time
                        print(f"[VOICE] ✓ Transcription ({duration:.2f}s): '{audio_text}'")
                except sr.UnknownValueError:
                    audio_text = ""
                    print("[VOICE] ⚠️ Parole non comprise")
                except sr.RequestError as e:
                    # Erreur API (pas de connexion internet par exemple)
                    print(f"[ERROR] Google Speech API échoué: {e}")
                    audio_text = ""
            else:
                audio_text = "[Speech Recognition non disponible]"

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
            
            # Créer l'annotation après transcription
            success = False
            if audio_text and self.create_annotation_callback:
                success = bool(self.create_annotation_callback(audio_text, float(video_timestamp)))
            else:
                if not audio_text:
                    print("[WARN] Texte vide (rien à parser)")
                if not self.create_annotation_callback:
                    print("[WARN] Callback manquant (create_annotation_callback)")

            capture["processed"] = True
            capture["status"] = "recognized" if success else "unrecognized"

            if not success:
                self.session_data["unrecognized"].append(capture)

            self.session_data["captures"].append(capture)
            self._save_session()

            if success:
                print(f"[VOICE] ✓ Annotation créée: {audio_text}")
            else:
                print(f"[VOICE] ⚠️ Non reconnu: {audio_text}")
            
        except Exception as e:
            print(f"[ERROR] Transcription: {e}")
            import traceback
            traceback.print_exc()
    
    def _save_session(self):
        """Sauvegarde la session JSON"""
        if not self.session_file or not self.session_data:
            return
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.session_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[ERROR] Sauvegarde session: {e}")
    
    def get_pending_captures(self) -> List[Dict]:
        """Retourne les captures non traitées"""
        if not self.session_data:
            return []
        return [c for c in self.session_data["captures"] if not c["processed"]]
    
    def mark_as_processed(self, capture_id: int, success: bool):
        """
        Marque une capture comme traitée
        
        Args:
            capture_id: ID de la capture
            success: True si reconnue, False si non reconnue
        """
        if not self.session_data:
            return
        
        for capture in self.session_data["captures"]:
            if capture["id"] == capture_id:
                capture["processed"] = True
                capture["status"] = "recognized" if success else "unrecognized"
                
                # Si non reconnue, ajouter à la liste de review
                if not success:
                    self.session_data["unrecognized"].append(capture)
                
                self._save_session()
                break
    
    def get_unrecognized(self) -> List[Dict]:
        """Retourne les captures non reconnues pour review"""
        if not self.session_data:
            return []
        return self.session_data.get("unrecognized", [])
    
    def cleanup(self):
        """Nettoie les ressources"""
        self.is_recording = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        
        if self.audio:
            try:
                self.audio.terminate()
            except:
                pass
        
        print("[VOICE] Cleanup terminé")
