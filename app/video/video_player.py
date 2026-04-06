"""Gestionnaire de lecture vidéo avec VLC et OpenCV.

Important: l'application doit pouvoir démarrer même si OpenCV n'est pas
disponible sur la machine (dépendances natives / VC++ runtime manquant).
Dans ce cas, la partie vidéo sera simplement indisponible.
"""

import importlib
import os
import struct
import sys
import traceback
from pathlib import Path

from PIL import Image, ImageTk

_CV2_IMPORT_ERROR = None
_VLC_IMPORT_ERROR = None
vlc = None

try:
    import cv2  # type: ignore
    print(f"[VideoPlayer] cv2 importé OK: {cv2.__version__}")
except Exception as _e:
    cv2 = None
    _CV2_IMPORT_ERROR = _e
    print(f"[VideoPlayer] cv2 INDISPONIBLE: {_e}")


class VideoPlayer:
    def __init__(self):
        self.video_path = None
        self.cap = None  # OpenCV pour captures
        self.vlc_instance = None
        self.vlc_player = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 30
        self.frame_delay = 1/30
        self.current_image = None
        self.video_loaded = False
        self.playback_speed = 1.0
        self.rotation = 0  # Rotation actuelle : 0, 90, 180, 270
        self.window_id = None  # Stocker l'ID de la fenêtre VLC
        self.vlc_runtime_dir = None
        self.vlc_runtime_issue = None
        self.vlc_search_paths = []

        self.cv2_available = cv2 is not None
        self.cv2_error = None if self.cv2_available else str(_CV2_IMPORT_ERROR)

        self._prepare_vlc_runtime()
        self._try_import_vlc()

        self.vlc_available = vlc is not None
        self.vlc_error = None if self.vlc_available else str(_VLC_IMPORT_ERROR)
        if self.vlc_runtime_issue and not self.vlc_runtime_dir and not self.vlc_available:
            self.vlc_error = self.vlc_runtime_issue

        print(f"[VideoPlayer] __init__ | cv2={self.cv2_available} | vlc={self.vlc_available}")
        if not self.cv2_available:
            print(f"[VideoPlayer] cv2_error: {self.cv2_error}")
        if not self.vlc_available:
            print(f"[VideoPlayer] vlc_error: {self.vlc_error}")

        # Initialiser VLC
        self._init_vlc()

    @staticmethod
    def _is_valid_vlc_directory(path: Path) -> bool:
        """Vrai si le dossier ressemble à un runtime VLC Windows complet."""
        return (
            path.exists()
            and path.is_dir()
            and (path / "libvlc.dll").exists()
            and (path / "plugins").exists()
        )

    @staticmethod
    def _expected_dll_architecture() -> str:
        """Architecture DLL attendue pour le processus Python courant."""
        return "64-bit" if sys.maxsize > 2**32 else "32-bit"

    @staticmethod
    def _read_pe_machine(dll_path: Path) -> int | None:
        """Lit le champ Machine d'un binaire PE Windows."""
        try:
            with dll_path.open("rb") as fh:
                if fh.read(2) != b"MZ":
                    return None
                fh.seek(0x3C)
                pe_offset = struct.unpack("<I", fh.read(4))[0]
                fh.seek(pe_offset)
                if fh.read(4) != b"PE\x00\x00":
                    return None
                return struct.unpack("<H", fh.read(2))[0]
        except Exception:
            return None

    @classmethod
    def _dll_architecture(cls, dll_path: Path) -> str | None:
        """Retourne l'architecture d'une DLL PE Windows."""
        machine = cls._read_pe_machine(dll_path)
        if machine == 0x14C:
            return "32-bit"
        if machine == 0x8664:
            return "64-bit"
        return None

    @classmethod
    def _vlc_directory_issue(cls, path: Path) -> str | None:
        """Retourne une explication si le runtime VLC est incompatible."""
        if not cls._is_valid_vlc_directory(path):
            return None

        dll_path = path / "libvlc.dll"
        dll_arch = cls._dll_architecture(dll_path)
        expected_arch = cls._expected_dll_architecture()

        if dll_arch and dll_arch != expected_arch:
            return (
                f"VLC {dll_arch} incompatible avec l'application {expected_arch} "
                f"({path})"
            )
        return None

    @staticmethod
    def _add_vlc_variants(candidates, base_path: Path) -> None:
        """Ajoute les variantes directes d'un emplacement donné."""
        candidates.extend([
            base_path,
            base_path / "vlc",
            base_path / "VLC",
        ])

    def _add_portable_search_root(self, candidates, base_path: Path) -> None:
        """Ajoute les emplacements VLC probables autour d'un dossier portable."""
        self._add_vlc_variants(candidates, base_path)
        try:
            for child in base_path.iterdir():
                if child.is_dir():
                    self._add_vlc_variants(candidates, child)
        except OSError:
            pass

    def _candidate_vlc_directories(self):
        """Retourne les chemins VLC plausibles (Windows) sans doublons."""
        project_root = Path(__file__).resolve().parents[2]
        candidates = []

        env_vlc = os.environ.get("VLC_DIR", "").strip()
        if env_vlc:
            self._add_vlc_variants(candidates, Path(env_vlc))

        portable_roots = []
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            portable_roots.append(Path(meipass))

        executable = getattr(sys, "executable", "").strip()
        if executable:
            exe_path = Path(executable).resolve()
            portable_roots.extend([
                exe_path.parent / exe_path.stem,
                exe_path.parent,
            ])

        try:
            portable_roots.append(Path.cwd())
        except OSError:
            pass

        portable_roots.append(project_root)

        for base_path in portable_roots:
            self._add_portable_search_root(candidates, base_path)

        if os.name == "nt":
            for env_name in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
                base = os.environ.get(env_name, "").strip()
                if base:
                    candidates.append(Path(base) / "VideoLAN" / "VLC")

        existing = []
        seen = set()
        incompatible_issue = None
        self.vlc_runtime_issue = None
        self.vlc_search_paths = []
        for path in candidates:
            try:
                key = str(path.resolve()).lower()
            except Exception:
                key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            self.vlc_search_paths.append(str(path))
            if self._is_valid_vlc_directory(path):
                issue = self._vlc_directory_issue(path)
                if issue:
                    self.vlc_search_paths[-1] = f"{path} [ignore: {issue}]"
                    if incompatible_issue is None:
                        incompatible_issue = issue
                    continue
                existing.append(path)
        if not existing:
            self.vlc_runtime_issue = incompatible_issue
        return existing

    def _prepare_vlc_runtime(self):
        """Prépare l'environnement VLC (DLL/plugins) sous Windows."""
        if os.name != "nt":
            return

        for vlc_dir in self._candidate_vlc_directories():
            vlc_dir_str = str(vlc_dir)
            try:
                if hasattr(os, "add_dll_directory"):
                    os.add_dll_directory(vlc_dir_str)
            except Exception as exc:
                print(f"[VideoPlayer] WARN add_dll_directory({vlc_dir_str}): {exc}")

            current_path = os.environ.get("PATH", "")
            if vlc_dir_str.lower() not in current_path.lower():
                os.environ["PATH"] = vlc_dir_str + os.pathsep + current_path

            plugins_dir = vlc_dir / "plugins"
            if plugins_dir.exists() and not os.environ.get("VLC_PLUGIN_PATH"):
                os.environ["VLC_PLUGIN_PATH"] = str(plugins_dir)

            self.vlc_runtime_dir = vlc_dir_str
            break

        if self.vlc_runtime_dir:
            print(f"[VideoPlayer] VLC runtime détecté: {self.vlc_runtime_dir}")
        elif self.vlc_runtime_issue:
            print(f"[VideoPlayer] VLC incompatible: {self.vlc_runtime_issue}")
        else:
            print("[VideoPlayer] VLC runtime introuvable. Chemins testés:")
            for candidate in self.vlc_search_paths[:20]:
                print(f"  - {candidate}")

    def _try_import_vlc(self) -> bool:
        """Tente de (re)charger le module vlc."""
        global vlc, _VLC_IMPORT_ERROR

        if vlc is not None:
            return True

        try:
            vlc = importlib.import_module("vlc")
            _VLC_IMPORT_ERROR = None
            print("[VideoPlayer] vlc importé OK")
            return True
        except Exception as exc:
            _VLC_IMPORT_ERROR = exc
            print(f"[VideoPlayer] vlc indisponible: {exc}")
            return False

    def get_vlc_diagnostic(self) -> str:
        """Retourne un diagnostic court pour l'interface."""
        if self.vlc_player:
            return "VLC actif"
        if self.vlc_runtime_issue and not self.vlc_runtime_dir:
            return self.vlc_runtime_issue
        if self.vlc_error:
            return self.vlc_error
        if self.vlc_available and self.vlc_instance is None:
            return "VLC détecté mais instance libvlc indisponible"
        if self.vlc_instance is not None and self.vlc_runtime_dir:
            return f"VLC initialisé ({self.vlc_runtime_dir})"
        if os.name == "nt" and self.vlc_runtime_dir:
            return f"VLC runtime détecté mais non initialisé ({self.vlc_runtime_dir})"
        return "VLC indisponible"

    def _bind_vlc_to_window(self) -> bool:
        """Force le rendu VLC dans la fenêtre Tkinter (aucun détachement autorisé)."""
        if not self.vlc_player:
            print("[VideoPlayer] _bind_vlc_to_window: pas de vlc_player")
            return False

        if not self.window_id:
            print("[VideoPlayer] _bind_vlc_to_window: window_id absent -> blocage lecture VLC externe")
            return False

        try:
            self.vlc_player.set_hwnd(int(self.window_id))
            print(f"[VideoPlayer] _bind_vlc_to_window OK (hwnd={self.window_id})")
            return True
        except Exception as exc:
            print(f"[VideoPlayer] _bind_vlc_to_window ERREUR: {exc}")
            traceback.print_exc()
            return False
    
    def _init_vlc(self):
        """Initialise ou réinitialise VLC avec les options de rotation"""
        print(f"[VideoPlayer] _init_vlc | rotation={self.rotation} | vlc_module={vlc}")
        if vlc is None and not self._try_import_vlc():
            self.vlc_instance = None
            self.vlc_player = None
            self.vlc_available = False
            self.vlc_error = self.vlc_runtime_issue or (
                str(_VLC_IMPORT_ERROR) if _VLC_IMPORT_ERROR else "python-vlc indisponible"
            )
            print("[VideoPlayer] _init_vlc annulé: module vlc absent")
            return

        # Déterminer les options VLC selon la rotation
        vlc_options = ['--no-xlib']
        
        if self.rotation == 90:
            vlc_options.extend(['--video-filter=transform', '--transform-type=90'])
        elif self.rotation == 180:
            vlc_options.extend(['--video-filter=transform', '--transform-type=180'])
        elif self.rotation == 270:
            vlc_options.extend(['--video-filter=transform', '--transform-type=270'])
        
        # Libérer l'instance précédente si elle existe
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()
        if self.vlc_instance:
            self.vlc_instance.release()
        
        # Créer nouvelle instance
        print(f"[VideoPlayer] _init_vlc options: {vlc_options}")
        try:
            self.vlc_instance = vlc.Instance(vlc_options)
            print(f"[VideoPlayer] VLC Instance créée: {self.vlc_instance}")
            self.vlc_available = True
            self.vlc_error = None
        except Exception as exc:
            print(f"[VideoPlayer] ERREUR création VLC Instance: {exc}")
            traceback.print_exc()
            self.vlc_instance = None
            self.vlc_available = False
            self.vlc_error = str(exc)
        self.vlc_player = None
    
    def load_video(self, video_path):
        """Charge une vidéo MP4"""
        print(f"[VideoPlayer] load_video: {video_path}")
        print(f"[VideoPlayer] load_video | cv2={cv2 is not None} | vlc_instance={self.vlc_instance}")

        if cv2 is None:
            detail = f" ({self.cv2_error})" if self.cv2_error else ""
            print(f"[VideoPlayer] ERREUR: cv2 absent{detail}")
            raise Exception(
                "OpenCV (cv2) n'est pas disponible sur cette machine. "
                "La lecture vidéo est désactivée." + detail
            )

        self.video_path = video_path

        # OpenCV pour les infos et captures
        print(f"[VideoPlayer] Ouverture cv2.VideoCapture...")
        self.cap = cv2.VideoCapture(video_path)
        print(f"[VideoPlayer] cap.isOpened() = {self.cap.isOpened()}")

        if not self.cap.isOpened():
            raise Exception(f"Impossible d'ouvrir la vidéo : {video_path}")

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_delay = 1 / self.fps if self.fps > 0 else 1/30
        self.current_frame = 0
        self.video_loaded = True
        print(f"[VideoPlayer] cv2 OK | frames={self.total_frames} | fps={self.fps:.2f} | durée={self.total_frames/self.fps:.1f}s")

        # VLC pour la lecture avec son (optionnel)
        self.vlc_player = None
        if self.vlc_instance is not None:
            print(f"[VideoPlayer] Création VLC media_player...")
            try:
                self.vlc_player = self.vlc_instance.media_player_new()
                media = self.vlc_instance.media_new(video_path)
                self.vlc_player.set_media(media)
                # Evite un volume nul persistant ou un mute residuel.
                self.vlc_player.audio_set_mute(False)
                if self.vlc_player.audio_get_volume() <= 0:
                    self.vlc_player.audio_set_volume(100)
                if self.window_id:
                    self._bind_vlc_to_window()
                print(f"[VideoPlayer] VLC player prêt: {self.vlc_player}")
            except Exception as exc:
                print(f"[VideoPlayer] ERREUR VLC player: {exc}")
                traceback.print_exc()
                self.vlc_player = None
                self.vlc_error = str(exc)
        else:
            print(f"[VideoPlayer] vlc_instance=None -> lecture sans son | reason={self.get_vlc_diagnostic()}")

        # Lire la première frame avec OpenCV
        first_frame = self.get_current_frame()
        print(f"[VideoPlayer] Première frame: {None if first_frame is None else first_frame.shape}")
        return first_frame
    
    def set_vlc_window(self, window_id):
        """Configure la fenêtre d'affichage VLC"""
        print(f"[VideoPlayer] set_vlc_window | window_id={window_id} | vlc_player={self.vlc_player}")
        try:
            self.window_id = int(window_id) if window_id is not None else None
        except Exception:
            self.window_id = window_id
        if self.vlc_player:
            self._bind_vlc_to_window()
        else:
            print("[VideoPlayer] set_vlc_window: pas de vlc_player, set_hwnd ignoré")
    
    def get_current_frame(self):
        """Récupère la frame actuelle"""
        if not self.cap or not self.video_loaded:
            return None
        
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)
        ret, frame = self.cap.read()
        
        if ret:
            # Convertir BGR (OpenCV) en RGB (Pillow/Tkinter)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.current_image = frame_rgb
            return frame_rgb
        return None
    
    def next_frame(self):
        """Avance d'une frame"""
        if self.current_frame < self.total_frames - 1:
            self.current_frame += 1
            return self.get_current_frame()
        return None
    
    def previous_frame(self):
        """Recule d'une frame"""
        if self.current_frame > 0:
            self.current_frame -= 1
            return self.get_current_frame()
        return None
    
    def seek_frame(self, frame_number):
        """Aller directement à une frame spécifique"""
        if 0 <= frame_number < self.total_frames:
            self.current_frame = frame_number
            
            # Synchroniser VLC
            if self.vlc_player and self.total_frames > 0:
                position = frame_number / self.total_frames
                self.vlc_player.set_position(position)
            
            return self.get_current_frame()
        return None
    
    def seek_time(self, seconds):
        """Aller à un timestamp spécifique (en secondes)"""
        frame_number = int(seconds * self.fps)
        return self.seek_frame(frame_number)
    
    def play(self):
        """Démarre la lecture"""
        print(f"[VideoPlayer] play() | vlc_player={self.vlc_player} | window_id={self.window_id} | video_loaded={self.video_loaded}")
        self.is_playing = True
        if self.vlc_player:
            try:
                if not self._bind_vlc_to_window():
                    self.is_playing = False
                    print("[VideoPlayer] play() bloqué: impossible de garantir l'affichage attaché")
                    return
                state_before = self.vlc_player.get_state()
                ret = self.vlc_player.play()
                state_after = self.vlc_player.get_state()
                print(f"[VideoPlayer] vlc.play() retour={ret} | etat {state_before} -> {state_after}")
            except Exception as exc:
                print(f"[VideoPlayer] ERREUR vlc.play(): {exc}")
                traceback.print_exc()
        else:
            print("[VideoPlayer] play(): pas de vlc_player")

    def pause(self):
        """Met en pause"""
        print(f"[VideoPlayer] pause() | vlc_player={self.vlc_player}")
        self.is_playing = False
        if self.vlc_player:
            try:
                self.vlc_player.pause()
                print(f"[VideoPlayer] vlc.pause() OK | état={self.vlc_player.get_state()}")
            except Exception as exc:
                print(f"[VideoPlayer] ERREUR vlc.pause(): {exc}")
                traceback.print_exc()
    
    def toggle_play_pause(self):
        """Alterne lecture/pause"""
        if self.is_playing:
            self.pause()
        else:
            self.play()
        return self.is_playing
    
    def get_vlc_position(self):
        """Retourne la position VLC (0.0 à 1.0)"""
        if self.vlc_player:
            return self.vlc_player.get_position()
        return 0.0
    
    def sync_from_vlc(self):
        """Synchronise OpenCV avec la position VLC"""
        if self.vlc_player and self.video_loaded:
            vlc_pos = self.vlc_player.get_position()
            if vlc_pos >= 0:
                self.current_frame = int(vlc_pos * self.total_frames)
                return self.get_current_frame()
        return None
    
    def forward(self, seconds=5):
        """Avance rapide de X secondes sans pause"""
        if self.vlc_player and self.video_loaded:
            current_time = self.vlc_player.get_time()
            new_time = current_time + (seconds * 1000)
            self.vlc_player.set_time(int(new_time))
    
    def rewind(self, seconds=5):
        """Retour rapide de X secondes sans pause"""
        if self.vlc_player and self.video_loaded:
            current_time = self.vlc_player.get_time()
            new_time = max(0, current_time - (seconds * 1000))
            self.vlc_player.set_time(int(new_time))
    
    def get_current_timestamp(self):
        """Retourne le timestamp actuel en secondes"""
        return self.current_frame / self.fps if self.fps > 0 else 0
    
    def set_playback_speed(self, speed):
        """Définit la vitesse de lecture (0.25x à 2x)"""
        self.playback_speed = max(0.25, min(2.0, speed))
        if self.fps > 0:
            self.frame_delay = (1 / self.fps) / self.playback_speed
        else:
            self.frame_delay = 1/30
        
        # Appliquer la vitesse à VLC
        if self.vlc_player:
            self.vlc_player.set_rate(self.playback_speed)
    
    def get_playback_speed(self):
        """Retourne la vitesse de lecture actuelle"""
        return self.playback_speed
    
    def rotate_video(self):
        """
        Pivote la vidéo de 90° dans le sens horaire
        Rotation: 0° → 90° → 180° → 270° → 0°
        Redémarre VLC avec les bonnes options
        """
        if not self.video_loaded or not self.video_path:
            return self.rotation

        # Sans VLC: ne pas planter, mais la rotation vidéo avec filtre VLC n'est pas disponible
        if self.vlc_instance is None:
            self.rotation = (self.rotation + 90) % 360
            return self.rotation
        
        # Sauvegarder l'état actuel
        current_pos = 0
        was_playing = self.is_playing
        
        try:
            if self.vlc_player:
                current_pos = self.vlc_player.get_position()
                if was_playing:
                    self.vlc_player.pause()
                    self.is_playing = False
        except:
            pass
        
        # Passer à la rotation suivante
        self.rotation = (self.rotation + 90) % 360
        
        print(f"[VideoPlayer] Application rotation: {self.rotation}°")
        
        # Réinitialiser VLC avec les nouvelles options
        self._init_vlc()

        if self.vlc_instance is None:
            return self.rotation
        
        # Recharger la vidéo
        self.vlc_player = self.vlc_instance.media_player_new()
        media = self.vlc_instance.media_new(self.video_path)
        self.vlc_player.set_media(media)
        
        # Reconfigurer la fenêtre
        if self.window_id:
            if not self._bind_vlc_to_window():
                print("[VideoPlayer] Rotation: impossible de binder VLC à la fenêtre -> lecture externe évitée")
                self.is_playing = False
                return self.rotation
        else:
            print("[VideoPlayer] Rotation: window_id absent -> lecture externe évitée")
            self.is_playing = False
            return self.rotation
        
        # Restaurer la position
        self.vlc_player.play()
        
        # Attendre que le media soit prêt
        import time
        time.sleep(0.2)
        
        # Restaurer la position
        if current_pos > 0.01:
            try:
                self.vlc_player.set_position(current_pos)
            except:
                pass
        
        # Restaurer l'état de lecture
        if not was_playing:
            time.sleep(0.1)
            self.vlc_player.pause()
            self.is_playing = False
        else:
            self.is_playing = True
        
        print(f"[VideoPlayer] Rotation {self.rotation}° appliquée avec succès")
        
        return self.rotation
    
    def get_rotation(self):
        """Retourne l'angle de rotation actuel"""
        return self.rotation
    
    def get_video_info(self):
        """Retourne les informations de la vidéo"""
        if not self.video_loaded:
            return None
        
        return {
            "path": self.video_path,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration": self.total_frames / self.fps,
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        }
    
    def capture_current_frame(self, output_path):
        """Sauvegarde la frame actuelle en PNG"""
        if self.current_image is not None:
            img = Image.fromarray(self.current_image)
            img.save(output_path)
            return True
        return False
    
    def capture_frames_before(self, output_folder, num_frames=10):
        """Capture les N frames avant la frame actuelle"""
        if not self.video_loaded or not self.cap:
            return []
        
        captured_files = []
        current_pos = self.current_frame
        
        # Calculer la frame de départ (10 frames avant)
        start_frame = max(0, current_pos - num_frames)
        
        # Sauvegarder la position actuelle
        original_frame = current_pos
        
        # Capturer chaque frame
        for i in range(num_frames):
            frame_num = start_frame + i
            if frame_num >= 0 and frame_num < self.total_frames:
                # Aller à cette frame
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
                ret, frame = self.cap.read()
                
                if ret:
                    # Convertir BGR vers RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    
                    # Sauvegarder avec numéro de séquence
                    filename = f"frame_{i+1:02d}.png"
                    filepath = os.path.join(output_folder, filename)
                    img.save(filepath)
                    captured_files.append(filepath)
        
        # Restaurer la position originale
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, original_frame)
        ret, frame = self.cap.read()
        if ret:
            self.current_frame = original_frame
            self.current_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return captured_files
    
    def mute_audio(self):
        """Coupe le son de la vidéo"""
        if self.vlc_player:
            self.vlc_player.audio_set_mute(True)
    
    def unmute_audio(self):
        """Remet le son de la vidéo"""
        if self.vlc_player:
            self.vlc_player.audio_set_mute(False)
    
    def release(self):
        """Libère les ressources"""
        self.is_playing = False
        
        # Arrêter VLC
        if self.vlc_player:
            self.vlc_player.stop()
            self.vlc_player.release()
            self.vlc_player = None
        
        # Libérer OpenCV
        if self.cap:
            self.cap.release()
        
        self.video_loaded = False
