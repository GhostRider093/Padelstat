"""
Interface graphique moderne pour PFPADEL Video Stats
Design élégant avec Tkinter customisé
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


SAFE_MODE = _env_truthy("NANOAPPSTAT_SAFE_MODE")
SHOW_DEBUG_BANNER = _env_truthy("NANOAPPSTAT_SHOW_DEBUG_BANNER")
SHOW_VOICE_INFO_BANNER = _env_truthy("NANOAPPSTAT_SHOW_VOICE_INFO_BANNER")
SHOW_PTT_GUIDE_PANEL = _env_truthy("NANOAPPSTAT_SHOW_PTT_GUIDE_PANEL")


class _NullVideoPlayer:
    """Implémentation minimale pour permettre le démarrage sans dépendances vidéo."""

    def __init__(self):
        self.video_path = None
        self.cap = None
        self.vlc_instance = None
        self.vlc_player = None
        self.is_playing = False
        self.current_frame = 0
        self.total_frames = 0
        self.fps = 0
        self.frame_delay = 1 / 30
        self.current_image = None
        self.video_loaded = False
        self.playback_speed = 1.0
        self.rotation = 0
        self.window_id = None
        self.vlc_available = False
        self.vlc_error = "Mode safe"
        self.cv2_available = False
        self.cv2_error = "Mode safe"

    def load_video(self, _video_path):
        raise Exception("Mode safe: la vidéo est désactivée")

    def set_vlc_window(self, _window_id):
        return None

    def set_playback_speed(self, speed):
        try:
            self.playback_speed = float(speed)
        except Exception:
            self.playback_speed = 1.0

    def toggle_play_pause(self):
        self.is_playing = False
        return False

    def get_current_timestamp(self):
        return 0.0

    def seek_time(self, _seconds):
        return None

    def seek_frame(self, _frame_number):
        return None

    def next_frame(self):
        return None

    def previous_frame(self):
        return None

    def forward(self, _seconds=5):
        return None

    def rewind(self, _seconds=5):
        return None

    def sync_from_vlc(self):
        return None

    def get_vlc_position(self):
        return 0.0

    def mute_audio(self):
        return None

    def unmute_audio(self):
        return None

    def rotate_video(self):
        self.rotation = 0
        return 0


class _NullVideoCutter:
    """Stub pour éviter téléchargement/usage FFmpeg en mode safe."""

    def __init__(self):
        self.ffmpeg_path = "ffmpeg"

    def check_ffmpeg(self):
        return False

    def cut_video(self, *_args, **_kwargs):
        raise Exception("Mode safe: découpe vidéo désactivée")


if not SAFE_MODE:
    from app.video.video_player import VideoPlayer
    from app.video.video_cutter import VideoCutter
else:
    VideoPlayer = _NullVideoPlayer  # type: ignore
    VideoCutter = _NullVideoCutter  # type: ignore
from app.annotations.annotation_manager import AnnotationManager
from app.exports.json_exporter import JSONExporter
from app.exports.html_generator import HTMLGenerator
from app.exports.csv_exporter import CSVExporter
# Import IA lazy pour éviter d'embarquer des dépendances lourdes dans les builds légers.
AIStatsAnalyzer = None  # type: ignore
AgentChatWindow = None  # type: ignore
from app.ui.annotation_dialogs_v2 import AnnotationDialogV2

# Import conditionnel des commandes vocales
if SAFE_MODE:
    VOICE_AVAILABLE = False
else:
    try:
        from app.voice.voice_commander import VoiceCommander
        from app.voice.command_parser import CommandParser
        from app.voice.voice_logger import VoiceLogger
        from app.voice.voice_batch_recorder import VoiceBatchRecorder
        VOICE_AVAILABLE = True
    except ImportError:
        VOICE_AVAILABLE = False
        print("[WARN] Module vocal non disponible (installer: pip install "
              "faster-whisper pyaudio webrtcvad)")


class ModernButton(tk.Canvas):
    """Bouton personnalisé avec effet hover (placeholder stub)."""
    def __init__(self, parent, text, command, bg_color="#667eea", fg_color="#ffffff",
                 hover_color="#7b8cf5", radius=14, padding=(14, 10), font=("Segoe UI", 10, "bold")):
        super().__init__(parent, highlightthickness=0, bd=0, bg=parent.cget("bg"))
        self.command = command
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.hover_color = hover_color
        self.radius = radius
        self.padding = padding

        # Dessine un bouton simple; placeholder en attendant une version complète
        xpad, ypad = padding
        self.config(width=100 + xpad * 2, height=30 + ypad * 2)
        self._rect = self.create_rectangle(0, 0, 0, 0, outline="", fill=bg_color)
        self._text = self.create_text(0, 0, text=text, fill=fg_color, font=font)
        self._redraw()

        self.bind("<Enter>", lambda e: self._set_color(self.hover_color))
        self.bind("<Leave>", lambda e: self._set_color(self.bg_color))
        self.bind("<Button-1>", lambda e: self._on_click())

    def _redraw(self):
        # Ajuste la taille en fonction du texte
        bbox = self.bbox(self._text)
        if bbox:
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            width = text_w + self.padding[0] * 2
            height = text_h + self.padding[1] * 2
            self.config(width=width, height=height)
            self.coords(self._rect, 0, 0, width, height)
            self.coords(self._text, width / 2, height / 2)

    def _set_color(self, color: str):
        try:
            self.itemconfig(self._rect, fill=color)
        except Exception:
            pass

    def _on_click(self):
        try:
            if callable(self.command):
                self.command()
        except Exception:
            pass


def _log_ui_exception(context: str, exc: Exception) -> None:
    """Journalise proprement les erreurs UI sans dépendre d'un stderr valide."""
    logger = logging.getLogger("NanoAppStat")
    try:
        logger.error("%s: %s", context, exc, exc_info=True)
    except Exception:
        pass

    try:
        print(f"[UI ERROR] {context}: {type(exc).__name__}: {exc}")
    except Exception:
        pass


class TypeCoupDialog:
    """Dialog pour choisir le type de coup"""
    def __init__(self, parent, title_text="Type de coup"):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title(title_text)
        self.top.geometry("350x300")
        self.top.resizable(False, False)
        
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#f5f7fa")
        
        title = tk.Label(self.top, text=f"🎾 {title_text}", 
                        font=("Segoe UI", 14, "bold"),
                        bg="#f5f7fa", fg="#667eea")
        title.pack(pady=15)
        
        content_frame = tk.Frame(self.top, bg="#f5f7fa")
        content_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.type_coup_var = tk.StringVar(value="fond_de_court")
        
        coups = [
            ("🎾 Volée", "volee"),
            ("💥 Balle Haute", "balle_haute"),
            ("🎯 Amorti", "amorti"),
            ("⚡ Fond de court", "fond_de_court"),
            ("🔄 Bandeja", "bandeja")
        ]
        
        for label, value in coups:
            rb = tk.Radiobutton(content_frame, text=label, 
                               variable=self.type_coup_var,
                               value=value,
                               font=("Segoe UI", 10),
                               bg="#f5f7fa", fg="#333",
                               activebackground="#f5f7fa",
                               selectcolor="#667eea",
                               cursor="hand2")
            rb.pack(anchor="w", pady=5, padx=10)
        
        btn_frame = tk.Frame(self.top, bg="#f5f7fa")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="✓ Suivant", command=self._ok,
                 font=("Segoe UI", 10, "bold"), bg="#667eea", fg="white",
                 relief="flat", padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="✗ Annuler", command=self._cancel,
                 font=("Segoe UI", 10), bg="#e0e0e0", fg="#555",
                 relief="flat", padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
    
    def _ok(self):
        self.result = self.type_coup_var.get()
        self.top.destroy()
    
    def _cancel(self):
        self.top.destroy()


class TechniqueDialog:
    """Dialog pour les détails techniques (coup droit/revers/balle haute)"""
    def __init__(self, parent):
        self.result = None
        self.top = tk.Toplevel(parent)
        self.top.title("Détails techniques")
        self.top.geometry("350x200")
        self.top.resizable(False, False)
        
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg="#f5f7fa")
        
        title = tk.Label(self.top, text="🎾 Détails du coup", 
                        font=("Segoe UI", 14, "bold"),
                        bg="#f5f7fa", fg="#667eea")
        title.pack(pady=15)
        
        content_frame = tk.Frame(self.top, bg="#f5f7fa")
        content_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        self.technique_var = tk.StringVar(value="coup_droit")
        
        techniques = [
            ("🎾 Coup droit", "coup_droit"),
            ("🎾 Revers", "revers"),
            ("⬆️ Balle haute", "balle_haute")
        ]
        
        for label, value in techniques:
            rb = tk.Radiobutton(content_frame, text=label, 
                               variable=self.technique_var,
                               value=value,
                               font=("Segoe UI", 10),
                               bg="#f5f7fa", fg="#333",
                               activebackground="#f5f7fa",
                               selectcolor="#667eea",
                               cursor="hand2")
            rb.pack(anchor="w", pady=5, padx=10)
        
        btn_frame = tk.Frame(self.top, bg="#f5f7fa")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="✓ Valider", command=self._ok,
                 font=("Segoe UI", 10, "bold"), bg="#667eea", fg="white",
                 relief="flat", padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
    
    def _ok(self):
        self.result = self.technique_var.get()
        self.top.destroy()


class AnnotationDialog:
    """Dialog pour les annotations"""
    def __init__(self, parent, annotation_type, players):
        self.result = None
        self.top = tk.Toplevel(parent)
        
        # Ajuster la taille selon le type
        if annotation_type in ["point_gagnant", "faute_directe"]:
            self.top.geometry("400x420")
        else:
            self.top.geometry("350x250")
        
        self.top.resizable(False, False)
        
        # Centrer
        self.top.transient(parent)
        self.top.grab_set()
        
        self.top.configure(bg="#f5f7fa")
        
        # Titre selon le type
        titles = {
            "faute_directe": "âš ï¸ Faute Directe",
            "point_gagnant": "🏆 Point Gagnant",
            "faute_provoquee": "🎯 Faute Provoquée"
        }
        
        title = tk.Label(self.top, text=titles.get(annotation_type, ""), 
                        font=("Segoe UI", 14, "bold"),
                        bg="#f5f7fa", fg="#667eea")
        title.pack(pady=15)
        
        content_frame = tk.Frame(self.top, bg="#f5f7fa")
        content_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        if annotation_type in ["faute_directe", "point_gagnant"]:
            # Un seul joueur
            tk.Label(content_frame, text="Joueur :", 
                    font=("Segoe UI", 10),
                    bg="#f5f7fa", fg="#555").pack(anchor="w", pady=5)
            
            self.player_var = tk.StringVar()
            self.player_combo = ttk.Combobox(content_frame, 
                                            textvariable=self.player_var,
                                            values=players, state="readonly",
                                            font=("Segoe UI", 10), height=10)
            self.player_combo.pack(fill="x", pady=5)
            if players:
                self.player_combo.current(0)
            
            # Ajouter le type de coup pour les points gagnants ET fautes directes
            tk.Label(content_frame, text="Type de coup :", 
                    font=("Segoe UI", 10, "bold"),
                    bg="#f5f7fa", fg="#555").pack(anchor="w", pady=(15, 5))
            
            self.type_coup_var = tk.StringVar(value="fond_de_court")
            
            # Liste des types de coups
            coups = [
                ("🎾 Service", "service"),
                ("🎾 Volée", "volee"),
                ("💥 Balle Haute", "balle_haute"),
                ("🎯 Amorti", "amorti"),
                ("⚡ Fond de court", "fond_de_court"),
                ("🔥 Bandeja", "bandeja"),
                ("🐍 Vibora", "vibora")
            ]
            
            for label, value in coups:
                rb = tk.Radiobutton(content_frame, text=label, 
                                   variable=self.type_coup_var,
                                   value=value,
                                   font=("Segoe UI", 9),
                                   bg="#f5f7fa", fg="#333",
                                   activebackground="#f5f7fa",
                                   selectcolor="#667eea",
                                   cursor="hand2")
                rb.pack(anchor="w", pady=3, padx=10)
        
        else:  # faute_provoquee
            # Attaquant
            tk.Label(content_frame, text="Attaquant :", 
                    font=("Segoe UI", 10),
                    bg="#f5f7fa", fg="#555").pack(anchor="w", pady=5)
            
            self.attaquant_var = tk.StringVar()
            self.attaquant_combo = ttk.Combobox(content_frame, 
                                               textvariable=self.attaquant_var,
                                               values=players, state="readonly",
                                               font=("Segoe UI", 10), height=10)
            self.attaquant_combo.pack(fill="x", pady=5)
            if players:
                self.attaquant_combo.current(0)
            
            # Défenseur
            tk.Label(content_frame, text="Défenseur (fautif) :", 
                    font=("Segoe UI", 10),
                    bg="#f5f7fa", fg="#555").pack(anchor="w", pady=5)
            
            self.defenseur_var = tk.StringVar()
            self.defenseur_combo = ttk.Combobox(content_frame, 
                                               textvariable=self.defenseur_var,
                                               values=players, state="readonly",
                                               font=("Segoe UI", 10), height=10)
            self.defenseur_combo.pack(fill="x", pady=5)
            if len(players) > 1:
                self.defenseur_combo.current(1)
        
        # Boutons
        btn_frame = tk.Frame(self.top, bg="#f5f7fa")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="✓ Valider", command=self._ok,
                 font=("Segoe UI", 10, "bold"), bg="#667eea", fg="white",
                 relief="flat", padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="✗ Annuler", command=self._cancel,
                 font=("Segoe UI", 10), bg="#e0e0e0", fg="#555",
                 relief="flat", padx=20, pady=8, cursor="hand2").pack(side="left", padx=5)
        
        self.annotation_type = annotation_type
        self.parent = parent
    
    def _ok(self):
        if self.annotation_type in ["faute_directe", "point_gagnant"]:
            type_coup = self.type_coup_var.get()
            
            # Pour volée et fond de court, demander les détails techniques
            if type_coup in ["volee", "fond_de_court"]:
                self.top.destroy()
                # Afficher le dialogue des détails techniques
                tech_dialog = TechniqueDialog(self.parent)
                self.parent.wait_window(tech_dialog.top)
                
                if tech_dialog.result:
                    technique = tech_dialog.result
                    # Combiner type_coup et technique
                    if type_coup == "volee":
                        if technique == "coup_droit":
                            final_type = "volee_coup_droit"
                        elif technique == "revers":
                            final_type = "volee_revers"
                        else:  # balle_haute
                            final_type = "volee_balle_haute"
                    else:  # fond_de_court
                        if technique == "coup_droit":
                            final_type = "fond_de_court_coup_droit"
                        elif technique == "revers":
                            final_type = "fond_de_court_revers"
                        else:  # balle_haute
                            final_type = "fond_de_court_balle_haute"
                    
                    result = {"joueur": self.player_var.get(), "type_coup": final_type}
                    self.result = result
                else:
                    self.result = None
            else:
                # Pour les autres types (smash, amorti, bandeja), pas besoin de détails
                result = {"joueur": self.player_var.get(), "type_coup": type_coup}
                self.result = result
                self.top.destroy()
        else:  # faute_provoquee
            attaquant = self.attaquant_var.get()
            defenseur = self.defenseur_var.get()
            self.top.destroy()
            
            # Demander le type de coup de l'attaquant
            type_coup_dialog = TypeCoupDialog(self.parent, "Coup de l'attaquant")
            self.parent.wait_window(type_coup_dialog.top)
            
            if not type_coup_dialog.result:
                self.result = None
                return
            
            type_coup_att = type_coup_dialog.result
            
            # Si volée ou fond de court, demander les détails pour l'attaquant
            if type_coup_att in ["volee", "fond_de_court"]:
                tech_dialog = TechniqueDialog(self.parent)
                self.parent.wait_window(tech_dialog.top)
                
                if not tech_dialog.result:
                    self.result = None
                    return
                
                technique_att = tech_dialog.result
                final_type_att = self._combine_type_technique(type_coup_att, technique_att)
            else:
                final_type_att = type_coup_att
            
            # Demander le type de coup du défenseur
            type_coup_dialog2 = TypeCoupDialog(self.parent, "Coup du défenseur (fautif)")
            self.parent.wait_window(type_coup_dialog2.top)
            
            if not type_coup_dialog2.result:
                self.result = None
                return
            
            type_coup_def = type_coup_dialog2.result
            
            # Si volée ou fond de court, demander les détails pour le défenseur
            if type_coup_def in ["volee", "fond_de_court"]:
                tech_dialog2 = TechniqueDialog(self.parent)
                self.parent.wait_window(tech_dialog2.top)
                
                if not tech_dialog2.result:
                    self.result = None
                    return
                
                technique_def = tech_dialog2.result
                final_type_def = self._combine_type_technique(type_coup_def, technique_def)
            else:
                final_type_def = type_coup_def
            
            self.result = {
                "attaquant": attaquant,
                "defenseur": defenseur,
                "type_coup_attaquant": final_type_att,
                "type_coup_defenseur": final_type_def
            }
    
    def _combine_type_technique(self, type_coup, technique):
        """Combine type de coup et technique"""
        if type_coup == "volee":
            if technique == "coup_droit":
                return "volee_coup_droit"
            elif technique == "revers":
                return "volee_revers"
            else:
                return "volee_balle_haute"
        else:  # fond_de_court
            if technique == "coup_droit":
                return "fond_de_court_coup_droit"
            elif technique == "revers":
                return "fond_de_court_revers"
            else:
                return "fond_de_court_balle_haute"
    
    def _cancel(self):
        self.top.destroy()


class MainWindow:
    """Fenêtre principale de l'application"""
    def __init__(self, root, safe_mode: bool = False, ui_mode: str = "standard", window_title: str | None = None):
        self.root = root
        self.ui_mode = ui_mode or "standard"
        self.safe_mode = bool(safe_mode or SAFE_MODE)
        base_title = window_title or ("PFPADEL Video Simple" if self.ui_mode == "portable_video_simple" else "NanoApp Stat")
        if self.safe_mode and self.ui_mode == "standard":
            self.root.title(base_title + " [SAFE MODE]")
        else:
            self.root.title(base_title)
        
        # Démarrer le proxy Ollama local (pour le chatbot HTML)
        try:
            from app.ai_proxy import start_proxy
            start_proxy()
        except Exception:
            pass

        # Charger la configuration
        self.config = self._load_config()
        
        # Restaurer la position et taille de la fenêtre
        self._restore_window_geometry()
        
        # Couleurs du thème moderne sombre/cyan
        self.COLORS = {
            'bg_main': '#0B1220',
            'bg_sidebar': '#111827',
            'primary': '#22D3EE',
            'primary_dark': '#06B6D4',
            'secondary': '#E5E7EB',
            'text_dark': '#E5E7EB',
            'text_light': '#94A3B8',
            'border': '#1F2937',
            'success': '#34D399',
            'warning': '#F59E0B',
            'danger': '#EF4444',
            'white': '#0F172A'
        }
        
        self.root.configure(bg=self.COLORS['bg_main'])

        # Fond d'ecran (image utilisateur) + voile sombre pour lisibilite.
        self._bg_source_image = None
        self._bg_resized_photo = None
        self._bg_label = None
        self._bg_last_size = (0, 0)
        self._setup_background_image()
        
        # Instances
        # En mode safe: pas de téléchargement FFmpeg, pas de dépendances vidéo/IA/vocal.
        self.video_player = VideoPlayer()
        self.video_cutter = VideoCutter()
        self.annotation_manager = AnnotationManager(
            enable_background_ai=not self.safe_mode
        )
        self.json_exporter = JSONExporter()
        self.html_generator = HTMLGenerator()
        self.csv_exporter = CSVExporter()
        
        # Variables
        self.current_image = None
        self.playing = False
        self.players = ["Joueur 1", "Joueur 2", "Joueur 3", "Joueur 4"]
        self.fullscreen = False
        self.fullscreen_window = None
        self.quick_mode = None  # Mode rapide: 'faute_directe', 'point_gagnant', etc.
        self.ollama_window = None  # Fenêtre d'analyse IA
        self.agent_chat = None  # Fenêtre de chat agent
        self.live_monitor = None  # Fenêtre de monitoring live
        self.vocal_mode_active = False  # Mode vocal activé/désactivé
        self.horizontal_layout = False  # Layout horizontal (timeline en haut, boutons en bas)
        self.detached_video_win = None  # Fenêtre vidéo détachée
        self.vlc_frame_original_parent = None  # Parent original du vlc_frame
        self.show_ai_controls = bool(
            self.config.get("features", {}).get("show_ai_controls", False)
        )
        self.enable_handsfree_voice = bool(
            self.config.get("features", {}).get("voice_handsfree", False)
        )
        self._last_enter_shortcut_ts = 0.0
        self._last_v_key_ts = 0
        self._progress_markers_cache_key = None
        self._ai_buttons = []
        self.audio_btn = None
        self.audio_muted = False
        self._voice_recording_forced_mute = False
        self._audio_was_muted_before_voice_recording = False
        self.rec_indicator_dot = None
        self.rec_indicator_text = None
        self._rec_indicator_mode = "idle"
        self._rec_blink_after_id = None
        self._rec_blink_phase = False
        self.voice_log_text = None
        self.voice_log_entries = []
        self._voice_log_max_entries = 120

        # Popup vocal (arbre) : apparaît uniquement quand utile (PTT)
        self.voice_tree_popup = None
        self.voice_tree_popup_title = None
        self.voice_tree_popup_body = None
        self._voice_tree_popup_hide_after_id = None

        # Politique : pas de détachement vidéo (stabilise l'affichage)
        self.allow_video_detach = False

        # Logger basique pour suivre les événements de détachement
        self._log_file = "debug_detach.log"

        # Constantes UI (évite le clipping quand la timeline est recréée)
        self.PROGRESS_CANVAS_HEIGHT = 30
        self._manual_progress = 0.0  # Position de la timeline lorsque aucune vidéo n'est chargée
        
        print("[DEBUG] Variables initialisées - detached_video_win = None")
        
        # Commandes vocales (ancien système - conservé pour compatibilité)
        self.voice_commander = None
        self.command_parser = None
        self.voice_logger = None
        self.voice_enabled = False
        self.voice_errors = []  # Historique des erreurs vocales
        self.pending_incomplete_command = None  # Commande en attente de complétion
        
        # Push-to-Talk (nouveau système)
        self.voice_batch_recorder = None
        self.voice_ptt_guide_window = None
        self.voice_pause_schema_window = None
        if (not self.safe_mode) and VOICE_AVAILABLE:
            try:
                self.command_parser = CommandParser(joueurs=self.players)
                self.voice_logger = VoiceLogger(log_dir="data")
                self.voice_batch_recorder = VoiceBatchRecorder(data_dir="data")

                if self.enable_handsfree_voice:
                    self.voice_commander = VoiceCommander(callback=self._handle_voice_command)
                    print("[OK] Module vocal prêt (PTT + mains-libres)")
                else:
                    self.voice_commander = None
                    print("[OK] Module vocal prêt (PTT uniquement)")
            except Exception as e:
                print(f"[WARN] Erreur init vocal: {e}")
        
        # Charger config
        self._load_players_config()
        
        # Mettre à jour le parser avec les joueurs chargés
        if self.command_parser:
            player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
            self.command_parser.set_joueurs(player_names)
        
        # Interface
        self._create_ui()
        if self.ui_mode == "portable_video_simple":
            self._configure_portable_video_simple_ui()

        # Vérifier une éventuelle session précédente (après UI prête)
        try:
            self.root.after(150, self._check_previous_session)
        except Exception:
            pass
        
        # Sauvegarder la géométrie lors de la fermeture
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Bindings clavier
        # Raccourcis globaux robustes: évitent les conflits de focus sur les boutons.
        self.root.bind_all("<KeyPress-space>", self._on_space_play_pause)
        self.root.bind_all("<KeyPress-Return>", self._on_enter_annotation_shortcut)
        self.root.bind_all("<Right>", lambda _e: self.skip_forward(2))  # +2s
        self.root.bind_all("<Left>", lambda _e: self.skip_backward(2))  # -2s
        self.root.bind_all("<Up>", lambda _e: self.skip_forward(10))  # +10s
        self.root.bind_all("<Down>", lambda _e: self.skip_backward(10))  # -10s
        
        # Push-to-talk avec touche V (comme Vocal)
        self.root.bind_all("<KeyPress-v>", self._on_voice_key_toggle)
        try:
            self.root.unbind("<KeyRelease-v>")
        except Exception:
            pass
        self.root.bind_all("<r>", lambda _e: self.remove_last_point())  # Annuler
        self.root.bind_all("<Delete>", lambda _e: self.remove_last_point())  # Annuler (touche Suppr)
        self.root.bind_all("<s>", lambda _e: self.quick_save())  # Sauvegarder
        self.root.bind_all("<h>", lambda _e: self.show_help())  # Aide
        self.root.bind_all("<n>", lambda _e: self.next_point())  # Point suivant
        self.root.bind_all("<t>", lambda _e: self.rotate_video())  # Rotation vidéo (T pour "Turn")
        self.root.bind_all("<b>", lambda _e: self.previous_point())  # Point précédent
        self.root.bind_all("<f>", lambda _e: self.toggle_maximized_video())
        self.root.bind_all("<F11>", lambda _e: self.toggle_maximized_video())
        self.root.bind_all("<Escape>", lambda _e: self._set_immersive_video_mode(False))
        self.root.bind_all("<m>", self.toggle_audio_mute)  # Mute/Unmute audio

        # Boucle de rafraichissement vidéo/timeline
        self._update_video()

        # Boucle de surveillance: force le rattachement si une fenêtre vidéo détachée réapparaît
        self._enforce_attached_loop()

        # Empêche les boutons de capter Enter/Espace et force le focus clavier principal.
        self.root.after(120, self._apply_keyboard_focus_policy)

    def _configure_portable_video_simple_ui(self):
        """Allège l'UI principale en conservant le lecteur vidéo et le menu Entrée."""
        self.show_ai_controls = False

        try:
            if hasattr(self, "layout_toggle_btn") and self.layout_toggle_btn:
                self.layout_toggle_btn.pack_forget()
        except Exception:
            pass

        try:
            if getattr(self, "voice_log_col", None) is not None:
                self.voice_log_col.pack_forget()
        except Exception:
            pass

        try:
            if getattr(self, "voice_info_banner", None) is not None:
                self.voice_info_banner.pack_forget()
        except Exception:
            pass

        try:
            if getattr(self, "voice_error_banner", None) is not None:
                self.voice_error_banner.pack_forget()
        except Exception:
            pass

        try:
            self.root.unbind_all("<KeyPress-v>")
        except Exception:
            pass

        sidebar_content = getattr(self, "sidebar_content", None)
        if sidebar_content is not None:
            try:
                for child in list(sidebar_content.winfo_children()):
                    child.destroy()
            except Exception:
                pass

            self._create_sidebar_section(sidebar_content, "JOUEURS")
            self._create_modern_button(
                sidebar_content,
                "✏️ CHANGER NOMS JOUEURS",
                self.configure_players,
                self.COLORS['primary'],
            ).pack(pady=(0, 12), padx=20, fill="x")

            self._create_sidebar_section(sidebar_content, "FICHIERS")
            self._create_modern_button(
                sidebar_content,
                "📁 CHARGER VIDÉO",
                self.load_video,
                self.COLORS['secondary'],
            ).pack(pady=(0, 12), padx=20, fill="x")
            self._create_modern_button(
                sidebar_content,
                "⏹️ STOP VIDÉO",
                self.stop_video,
                self.COLORS['danger'],
            ).pack(pady=(0, 12), padx=20, fill="x")

            self._create_sidebar_section(sidebar_content, "EXPORTS")
            self._create_modern_button(
                sidebar_content,
                "📈 RAPPORT RAPIDE",
                self.generate_html_fast,
                self.COLORS['primary'],
            ).pack(pady=(0, 12), padx=20, fill="x")

            self.stats_label = tk.Label(
                sidebar_content,
                text="Entrée : menu d'annotation\nEspace : pause / lecture",
                font=("Segoe UI", 9),
                bg=self.COLORS['bg_sidebar'],
                fg=self.COLORS['text_light'],
                justify="left",
                anchor="w",
                padx=10,
                pady=10,
            )
            self.stats_label.pack(pady=(8, 20), padx=20, fill="x")

        try:
            self._apply_ai_buttons_visibility()
        except Exception:
            pass

        try:
            self.root.after(120, self._apply_keyboard_focus_policy)
        except Exception:
            pass
    
    def _load_config(self):
        """Charge la configuration depuis config.json"""
        import json
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Impossible de charger config.json: {e}")
            return {}

    def _log(self, message: str):
        """Petit helper de log vers stdout + fichier debug_detach.log"""
        import datetime
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        print(line)
        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
    
    def _restore_window_geometry(self):
        """Restaure la position et taille de la fenêtre depuis la config"""
        try:
            if self.ui_mode == "portable_video_simple":
                self._set_portable_video_simple_geometry()
                return

            ui_config = self.config.get('ui', {})
            window_config = ui_config.get('window', {})
            
            if window_config.get('save_position', True):
                # Restaurer l'état (maximisé ou normal)
                last_state = window_config.get('last_state', 'zoomed')
                last_geometry = window_config.get('last_geometry')
                
                if last_state == 'zoomed':
                    self.root.state('zoomed')
                elif last_geometry:
                    # Restaurer la géométrie (widthxheight+x+y)
                    # Si la géométrie pointe hors écran (ex: ancien 2e écran), recentrer.
                    try:
                        m = re.match(r"^(\d+)x(\d+)\+(-?\d+)\+(-?\d+)$", str(last_geometry).strip())
                        if m:
                            w, h, x, y = (int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)))
                            sw = int(self.root.winfo_screenwidth())
                            sh = int(self.root.winfo_screenheight())
                            # Seuil de tolérance: si l'angle haut-gauche est trop loin, on recadre.
                            if x > sw - 50 or y > sh - 50 or x < -w + 50 or y < -h + 50:
                                x = max(0, (sw - w) // 2)
                                y = max(0, (sh - h) // 2)
                                last_geometry = f"{w}x{h}+{x}+{y}"
                    except Exception:
                        pass

                    self.root.geometry(last_geometry)
                    print(f"[INFO] Fenêtre restaurée: {last_geometry}")
                else:
                    # Utiliser les dimensions par défaut
                    width = window_config.get('width', 1400)
                    height = window_config.get('height', 900)
                    self.root.geometry(f"{width}x{height}")
            else:
                # Maximiser par défaut
                self.root.state('zoomed')

            # Forcer l'affichage au premier plan (Windows peut laisser la fenêtre minimisée/hors focus)
            try:
                self.root.update_idletasks()
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                # Toggle topmost brièvement pour être sûr qu'elle apparaît.
                self.root.attributes('-topmost', True)
                self.root.after(250, lambda: self.root.attributes('-topmost', False))
            except Exception:
                pass
        except Exception as e:
            print(f"[WARN] Erreur lors de la restauration de la géométrie: {e}")
            self.root.state('zoomed')

    def _set_portable_video_simple_geometry(self):
        """Positionne la version vidéo simple en mode normal, ratio 16:9, environ 70% de l'écran."""
        screen_width = int(self.root.winfo_screenwidth())
        screen_height = int(self.root.winfo_screenheight())

        target_width = max(1200, int(screen_width * 0.70))
        target_height = int(target_width * 9 / 16)

        max_height = max(720, int(screen_height * 0.70))
        if target_height > max_height:
            target_height = max_height
            target_width = int(target_height * 16 / 9)

        target_width = min(target_width, max(screen_width - 80, 1200))
        target_height = min(target_height, max(screen_height - 120, 720))

        x_pos = max((screen_width - target_width) // 2, 0)
        y_pos = max((screen_height - target_height) // 2, 0)

        self.root.state('normal')
        self.root.geometry(f"{target_width}x{target_height}+{x_pos}+{y_pos}")
        self.root.minsize(1100, 700)

        try:
            self.root.update_idletasks()
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
    
    def _save_window_geometry(self):
        """Sauvegarde la position et taille actuelle de la fenêtre"""
        import json
        try:
            # Récupérer l'état actuel de la fenêtre
            state = self.root.state()
            geometry = self.root.geometry() if state == 'normal' else None
            
            # Charger la config actuelle
            try:
                with open('config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
            except:
                config = self.config or {}
            
            # Mettre à jour les paramètres de fenêtre
            if 'ui' not in config:
                config['ui'] = {}
            if 'window' not in config['ui']:
                config['ui']['window'] = {}
            
            config['ui']['window']['last_state'] = state
            config['ui']['window']['last_geometry'] = geometry
            
            # Sauvegarder
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            print(f"[INFO] Géométrie sauvegardée: state={state}, geometry={geometry}")
        except Exception as e:
            print(f"[ERROR] Erreur lors de la sauvegarde de la géométrie: {e}")

    def _resolve_background_path(self):
        """Trouve un fond d'ecran valide (chemin utilisateur puis fallbacks)."""
        candidates = [
            r"C:\Users\icc34\Downloads\_Nano Stat_  Au logo de l'application Application destinée à effectuer des statistiques Sur le sport, notamment le PAdel.jpg",
            os.path.join("assets", "background.jpg"),
            os.path.join("assets", "background.png"),
            os.path.join("assets", "logo_nanoapp.png"),
        ]
        for path in candidates:
            try:
                if path and os.path.exists(path):
                    return path
            except Exception:
                continue
        return None

    def _setup_background_image(self):
        """Installe l'image de fond sur la fenetre principale sans casser le layout existant."""
        bg_path = self._resolve_background_path()
        if not bg_path:
            return

        try:
            self._bg_source_image = Image.open(bg_path).convert("RGBA")
            self._bg_label = tk.Label(self.root, bd=0, highlightthickness=0)
            self._bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            self._bg_label.lower()
            self.root.bind("<Configure>", self._refresh_background_image, add="+")
            self._refresh_background_image()
            print(f"[INFO] Fond d'ecran charge: {bg_path}")
        except Exception as e:
            self._bg_source_image = None
            self._bg_label = None
            print(f"[WARN] Impossible de charger le fond d'ecran: {e}")

    def _refresh_background_image(self, _event=None):
        """Recadre l'image en mode cover et applique un voile sombre pour la lisibilite."""
        if self._bg_source_image is None or self._bg_label is None:
            return

        w = max(1, int(self.root.winfo_width()))
        h = max(1, int(self.root.winfo_height()))
        if (w, h) == self._bg_last_size:
            return

        self._bg_last_size = (w, h)
        src = self._bg_source_image
        src_w, src_h = src.size
        if src_w <= 0 or src_h <= 0:
            return

        src_ratio = src_w / src_h
        dst_ratio = w / h
        if src_ratio > dst_ratio:
            new_h = h
            new_w = int(h * src_ratio)
        else:
            new_w = w
            new_h = int(w / src_ratio)

        resized = src.resize((max(1, new_w), max(1, new_h)), Image.LANCZOS)
        left = max(0, (new_w - w) // 2)
        top = max(0, (new_h - h) // 2)
        cropped = resized.crop((left, top, left + w, top + h))

        # Voile sombre: conserve le style "premium" tout en gardant du contraste texte/boutons.
        overlay = Image.new("RGBA", (w, h), (6, 10, 20, 125))
        composed = Image.alpha_composite(cropped, overlay)

        self._bg_resized_photo = ImageTk.PhotoImage(composed)
        self._bg_label.configure(image=self._bg_resized_photo)
    
    def _on_closing(self):
        """Appelé lors de la fermeture de l'application"""
        # Sauvegarder la géométrie de la fenêtre
        self._save_window_geometry()

        try:
            if self._rec_blink_after_id:
                self.root.after_cancel(self._rec_blink_after_id)
                self._rec_blink_after_id = None
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

    def _create_tooltip(self, widget, text):
        """Crée une infobulle simple pour un widget.
        Sécurisé: n'échoue pas si le widget est détruit.
        """
        if widget is None or not hasattr(widget, 'winfo_exists'):
            return

        tooltip = {'win': None}

        def show_tooltip(event=None):
            try:
                if not widget.winfo_exists():
                    return
                # Créer la fenêtre d'infobulle
                tw = tk.Toplevel(widget)
                tw.wm_overrideredirect(True)
                tw.wm_attributes("-topmost", True)
                # Positionner près du widget
                x = widget.winfo_rootx() + widget.winfo_width() // 2
                y = widget.winfo_rooty() + widget.winfo_height() + 10
                tw.wm_geometry(f"+{x}+{y}")
                # Contenu
                label = tk.Label(
                    tw, text=text,
                    bg="#333333", fg="white",
                    font=("Segoe UI", 9),
                    padx=8, pady=4,
                    relief="solid", borderwidth=1
                )
                label.pack()
                tooltip['win'] = tw
            except Exception:
                pass

        def hide_tooltip(event=None):
            try:
                win = tooltip.get('win')
                if win is not None and win.winfo_exists():
                    win.destroy()
                tooltip['win'] = None
            except Exception:
                tooltip['win'] = None

        # Bindings souris
        try:
            widget.bind("<Enter>", show_tooltip)
            widget.bind("<Leave>", hide_tooltip)
        except Exception:
            pass
    
    def _load_players_config(self):
        """Charge la config des joueurs"""
        import json
        config_path = "app/config/players.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    joueurs_data = data.get("joueurs", self.players)
                    # Extraire juste les noms si c'est un dict
                    if joueurs_data and isinstance(joueurs_data[0], dict):
                        self.players = [j.get("nom", j) if isinstance(j, dict) else j for j in joueurs_data]
                    else:
                        self.players = joueurs_data
            except:
                pass
        self.annotation_manager.set_players(self.players)
        
        # Mettre à jour le parser vocal avec les nouveaux noms
        if self.command_parser:
            self.command_parser.set_joueurs(self.players)
    
    def _save_players_config(self):
        """Sauvegarde la config des joueurs"""
        import json
        config_path = "app/config/players.json"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({"joueurs": self.players}, f, indent=2, ensure_ascii=False)
    
    def _check_previous_session(self):
        """Vérifie et propose de restaurer une session précédente"""
        latest_autosave = self.annotation_manager.find_latest_autosave()
        
        if latest_autosave:
            info = self.annotation_manager.get_autosave_info(latest_autosave)
            
            if info and info["nb_points"] > 0:
                # Créer une fenêtre de confirmation élégante
                response = messagebox.askyesno(
                    "📁 Session précédente détectée",
                    (
                        "Une session a été trouvée :\n\n"
                        f"🎥 Vidéo : {info['video']}\n"
                        f"📅 Date : {info['date']}\n"
                        f"👥 Joueurs : {', '.join(self._format_player_names(info))}\n"
                        f"📊 Points enregistrés : {info['nb_points']}\n"
                        f"🕒 Modifié : {info['modified']}\n\n"
                        "Voulez-vous reprendre cette session ?"
                    ),
                    icon='question',
                    parent=self.root
                )
                
                if response:
                    self._restore_session(latest_autosave, info)
    
    def _restore_session(self, autosave_path, info):
        """Restaure une session précédente"""
        try:
            # Charger l'autosave
            if self.annotation_manager.load_autosave(autosave_path):
                # Normaliser le format des joueurs (dict ou chaîne)
                raw_players = info.get("joueurs", [])
                self.players = [
                    (p if isinstance(p, dict) else {"nom": str(p)})
                    for p in raw_players
                ]
                self.annotation_manager.set_players(self.players)
                
                # Mettre à jour le parser vocal
                if self.command_parser:
                    player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                    self.command_parser.set_joueurs(player_names)

                # Chercher la vidéo (priorité au chemin complet stocké)
                video_name = info.get("video")
                video_path = None

                candidate_paths = [
                    info.get("video_path"),
                    self.annotation_manager.match_info.get("video_path"),
                ]
                for candidate in candidate_paths:
                    if candidate and os.path.exists(candidate):
                        video_path = candidate
                        break

                # Fallback: recherche limitée par nom de fichier (évite les faux positifs)
                if not video_path and video_name:
                    search_paths = [".", "data", "videos"]
                    for search_path in search_paths:
                        candidate = os.path.join(search_path, video_name)
                        if os.path.exists(candidate):
                            video_path = candidate
                            break

                # Si vidéo trouvée, la charger avec attachement VLC/UI complet
                if video_path and os.path.exists(video_path):
                    if not self._load_video_from_session_path(video_path):
                        video_path = None
                else:
                    # Pas de vidéo: placer la timeline sur le dernier point
                    self._sync_manual_position_from_annotations()

                # Rafraîchir immédiatement temps + barre (utile si aucune vidéo)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass
                self._update_info_labels()
                self._update_progress_bar()

                if video_path and os.path.exists(video_path):
                    messagebox.showinfo(
                        "✓ Session restaurée",
                        f"Session chargée avec succès !\n\n"
                        f"{info['nb_points']} points restaurés\n"
                        f"Vidéo : {video_name}",
                        parent=self.root
                    )
                else:
                    # Proposer de sélectionner manuellement la vidéo
                    response = messagebox.askyesno(
                        "🎥 Vidéo introuvable",
                        f"La vidéo '{video_name}' n'a pas été trouvée.\n\n"
                        f"Voulez-vous la sélectionner manuellement ?",
                        icon='warning',
                        parent=self.root
                    )
                    
                    if response:
                        video_path = filedialog.askopenfilename(
                            title=f"Sélectionner '{video_name}'",
                            filetypes=[
                                ("Vidéos", "*.mp4 *.avi *.mov *.mkv"),
                                ("Tous", "*.*")
                            ],
                            parent=self.root
                        )
                        
                        if video_path:
                            if not self._load_video_from_session_path(video_path):
                                messagebox.showerror(
                                    "Erreur",
                                    "La vidéo a été sélectionnée, mais le chargement a échoué.",
                                    parent=self.root
                                )
                                return
                            # Une fois la vidéo chargée, l'UI se recalera sur la vidéo via _update_video.
                            messagebox.showinfo(
                                "✓ Session restaurée",
                                f"{info['nb_points']} points restaurés",
                                parent=self.root
                            )
                
                # Mettre à jour l'interface
                try:
                    self._update_stats()
                except Exception:
                    pass
                
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible de restaurer la session :\n{str(e)}",
                parent=self.root
            )

    def _load_video_from_session_path(self, video_path: str) -> bool:
        """Charge une vidéo pour reprise de session avec synchronisation UI/VLC complète."""
        try:
            frame = self.video_player.load_video(video_path)
            self.current_video = video_path
            self.annotation_manager.set_video(video_path)

            if hasattr(self, "vlc_frame") and self.vlc_frame and self.vlc_frame.winfo_exists():
                self.vlc_frame.update_idletasks()
                self.vlc_frame.update()
                window_id = self.vlc_frame.winfo_id()
                self.video_player.set_vlc_window(window_id)
                self._set_audio_muted(self.audio_muted)

            if frame is not None:
                self._display_frame(frame)

            self.playing = False
            if hasattr(self, "play_btn") and self.play_btn and self.play_btn.winfo_exists():
                self.play_btn.config(text="▶")
            return True
        except Exception as e:
            print(f"[WARN] _load_video_from_session_path échec: {e}")
            return False
    
    def _format_player_names(self, info):
        joueurs = info.get("joueurs", [])
        names = []
        for j in joueurs[:2]:
            if isinstance(j, dict):
                names.append(str(j.get("nom", "?")))
            else:
                names.append(str(j))
        return names
    
    def _create_ui(self):
        """Crée l'interface utilisateur moderne blanc/turquoise"""
        
        # Police: configurable via config.json (ui.font.*), sinon Orbitron/Inter/Segoe UI.
        try:
            from tkinter import font as tkfont
            families = set(tkfont.families(self.root))

            cfg_font = (
                self.config.get("ui", {}).get("font", {}).get("family")
                if isinstance(self.config, dict)
                else None
            )
            cfg_font = str(cfg_font).strip() if cfg_font else ""

            if cfg_font and cfg_font in families:
                self.ui_font_family = cfg_font
            else:
                if cfg_font:
                    print(f"[UI] Police demandée introuvable: '{cfg_font}'. Fallback auto.")

                if "Orbitron" in families:
                    self.ui_font_family = "Orbitron"
                elif "Inter" in families:
                    self.ui_font_family = "Inter"
                else:
                    self.ui_font_family = "Segoe UI"

            cfg_mono = (
                self.config.get("ui", {}).get("font", {}).get("monospace")
                if isinstance(self.config, dict)
                else None
            )
            cfg_mono = str(cfg_mono).strip() if cfg_mono else ""
            if cfg_mono and cfg_mono in families:
                self.ui_mono_font_family = cfg_mono
            elif "Cascadia Mono" in families:
                self.ui_mono_font_family = "Cascadia Mono"
            elif "Consolas" in families:
                self.ui_mono_font_family = "Consolas"
            else:
                self.ui_mono_font_family = "Courier New"

            for named_font in (
                "TkDefaultFont",
                "TkTextFont",
                "TkMenuFont",
                "TkHeadingFont",
                "TkCaptionFont",
                "TkSmallCaptionFont",
                "TkIconFont",
                "TkTooltipFont",
            ):
                try:
                    tkfont.nametofont(named_font).configure(family=self.ui_font_family)
                except Exception:
                    pass
        except Exception:
            self.ui_font_family = "Segoe UI"
            self.ui_mono_font_family = "Consolas"

        self.title_font = (self.ui_font_family, 28, "bold")
        self.heading_font = (self.ui_font_family, 18, "bold")
        self.button_font = (self.ui_font_family, 12, "bold")
        self.text_font = (self.ui_font_family, 10)
        
        # ============= HEADER (compact pour maximiser la video) =============
        header = tk.Frame(self.root, bg=self.COLORS['white'], height=44)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        self.header_frame = header

        # BANDEAU DEBUG (désactivé par défaut pour maximiser la vidéo)
        if SHOW_DEBUG_BANNER:
            debug_banner = tk.Label(
                header,
                text="🔴 VERSION TEST DEBUG 28-12-2025 04:05 🔴",
                bg="#FF0000",
                fg="#FFFFFF",
                font=(self.ui_font_family, 20, "bold"),
                pady=10,
            )
            debug_banner.pack(fill="x", side="top")
        
        # Ligne accent ultra-fine (visuelle, sans manger de hauteur)
        tk.Frame(header, bg=self.COLORS['primary'], height=2).pack(fill="x", side="top")

        # Le badge titre a ete retire pour liberer un maximum d'espace video.
        tk.Frame(header, bg=self.COLORS['white']).pack(side="left", fill="y", expand=True)
        
        # Boutons header (ttkbootstrap si dispo => look moderne)
        try:
            import ttkbootstrap as tb

            config_btn = tb.Button(
                header,
                text="âœï¸ RENOMMER JOUEURS",
                command=self.configure_players,
                bootstyle="primary",
                width=18,
            )
            config_btn.pack(side="right", padx=10, pady=6)

            layout_btn = tb.Button(
                header,
                text="⚡ LAYOUT HORIZONTAL",
                command=self.toggle_layout_mode,
                bootstyle="secondary",
                width=16,
            )
            layout_btn.pack(side="right", padx=6, pady=6)
            self.layout_toggle_btn = layout_btn
        except Exception:
            # Fallback Tk classique
            config_btn = tk.Button(header, text="âœï¸ RENOMMER JOUEURS", 
                                  command=self.configure_players,
                                  font=("Segoe UI", 9, "bold"), 
                                  bg=self.COLORS['primary'], 
                                  fg=self.COLORS['white'],
                                  relief="flat", 
                                  padx=14, pady=5, 
                                  cursor="hand2",
                                  activebackground=self.COLORS['primary_dark'],
                                  borderwidth=0)
            config_btn.pack(side="right", padx=10, pady=6)

            layout_btn = tk.Button(header, text="⚡ LAYOUT HORIZONTAL", 
                                  command=self.toggle_layout_mode,
                                  font=("Segoe UI", 9, "bold"), 
                                  bg=self.COLORS['secondary'], 
                                  fg=self.COLORS['white'],
                                  relief="flat", 
                                  padx=14, pady=5, 
                                  cursor="hand2",
                                  activebackground="#2a2d3a",
                                  borderwidth=0)
            layout_btn.pack(side="right", padx=5, pady=6)
            self.layout_toggle_btn = layout_btn

        # Ligne de séparation
        tk.Frame(header, bg=self.COLORS['border'], height=1).pack(fill="x", side="bottom")

        # ============= MAIN CONTAINER =============
        main_container = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        main_container.pack(fill="both", expand=True)
        self.main_container = main_container
        
        # ============= ZONE AGENT CHAT (gauche, initialement cachée) =============
        self.agent_chat_container = tk.Frame(main_container, bg=self.COLORS['bg_sidebar'], width=400)
        # Ne pas pack par défaut - sera affiché lors du toggle
        
        # ============= SIDEBAR DROITE =============
        sidebar = tk.Frame(main_container, bg=self.COLORS['bg_sidebar'], width=320)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)
        self.sidebar_frame = sidebar
        
        # Ligne de séparation gauche de la sidebar
        tk.Frame(sidebar, bg=self.COLORS['border'], width=1).pack(fill="y", side="left")
        
        # Contenu scrollable de la sidebar
        sidebar_canvas = tk.Canvas(sidebar, bg=self.COLORS['bg_sidebar'], 
                                    highlightthickness=0, width=318)
        sidebar_scrollbar = tk.Scrollbar(sidebar, orient="vertical", 
                                         command=sidebar_canvas.yview)
        sidebar_content = tk.Frame(sidebar_canvas, bg=self.COLORS['bg_sidebar'])
        
        sidebar_content.bind(
            "<Configure>",
            lambda e: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all"))
        )
        sidebar_canvas.create_window((0, 0), window=sidebar_content, anchor="nw", width=300)
        sidebar_canvas.configure(yscrollcommand=sidebar_scrollbar.set)
        
        sidebar_scrollbar.pack(side="right", fill="y")
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        
        # Bind molette souris sur canvas et tous les widgets enfants
        def _on_mousewheel(event):
            if sidebar_canvas.winfo_exists():
                sidebar_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Fonction pour binder récursivement tous les widgets
        def bind_mousewheel(widget):
            widget.bind("<MouseWheel>", _on_mousewheel)
            for child in widget.winfo_children():
                bind_mousewheel(child)
        
        # Binder le canvas et tout son contenu
        sidebar_canvas.bind("<MouseWheel>", _on_mousewheel)
        sidebar_content.bind("<MouseWheel>", _on_mousewheel)
        
        # Stocker la référence et la fonction de binding
        self.sidebar_canvas = sidebar_canvas
        self.sidebar_content = sidebar_content
        self._bind_sidebar_mousewheel = lambda: bind_mousewheel(sidebar_content)
        
        # ========== SIDEBAR CONTENT ==========
        self._create_sidebar_section(sidebar_content, "JOUEURS")
        self._create_modern_button(
            sidebar_content, "âœï¸ CHANGER NOMS JOUEURS",
            self.configure_players, self.COLORS['primary']
        ).pack(pady=(0, 12), padx=20, fill="x")

        # Section ANNOTATIONS
        self._create_sidebar_section(sidebar_content, "ANNOTATIONS")
        
        self._create_modern_button(
            sidebar_content, "⚠ FAUTE DIRECTE", 
            self.add_faute_directe, self.COLORS['danger']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "★ POINT GAGNANT", 
            self.add_point_gagnant, self.COLORS['success']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "⚡ FAUTE PROVOQUÉE", 
            self.add_faute_provoquee, self.COLORS['warning']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Section ANNOTATIONS V2 (Détaillée)
        self._create_sidebar_section(sidebar_content, "ANNOTATIONS V2 (DÉTAILLÉE)")
        
        self._create_modern_button(
            sidebar_content, "⚠ V2 FAUTE DIRECTE", 
            self.add_faute_directe_v2, "#dc2626"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "★ V2 POINT GAGNANT", 
            self.add_point_gagnant_v2, "#16a34a"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "⚡ V2 FAUTE PROVOQUÉE", 
            self.add_faute_provoquee_v2, "#ea580c"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Section COUPS DE CÅ’UR
        self._create_sidebar_section(sidebar_content, "COUPS DE CÅ’UR")
        
        self._create_modern_button(
            sidebar_content, "💪 DÉFENSE", 
            lambda: self.add_coup_coeur("defense"), "#9333EA"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "⚔ ATTAQUE", 
            lambda: self.add_coup_coeur("attaque"), "#DC2626"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "✨ SPECTACULAIRE", 
            lambda: self.add_coup_coeur("spectaculaire"), "#0EA5E9"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Section FICHIERS
        self._create_sidebar_section(sidebar_content, "FICHIERS")
        
        self._create_modern_button(
            sidebar_content, "📁 CHARGER VIDÉO", 
            self.load_video, self.COLORS['secondary']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "⏹️ STOP VIDÉO", 
            self.stop_video, "#ef4444"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📂 CHARGER AUTOSAVE", 
            self.load_autosave, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📥 IMPORTER JSON", 
            self.import_json, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Section EXPORTS
        self._create_sidebar_section(sidebar_content, "EXPORTS")
        
        self._create_modern_button(
            sidebar_content, "💾 EXPORTER JSON", 
            self.export_json, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📊 EXPORTER CSV", 
            self.export_csv, self.COLORS['success']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📈 RAPPORT RAPIDE", 
            self.generate_html_fast, self.COLORS['primary']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📋 RAPPORT COMPLET", 
            self.generate_html_full, self.COLORS['primary_dark']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._register_ai_button(
            self._create_modern_button(
                sidebar_content, "🧠 ANALYSE IA STATS",
                self.analyze_stats_with_ai, "#FF6B6B"
            )
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Section OUTILS
        self._create_sidebar_section(sidebar_content, "OUTILS")
        
        # Bouton activation mode vocal
        self.vocal_mode_button = self._create_modern_button(
            sidebar_content, "🎤 ACTIVER VOCAL (V)", 
            self.toggle_vocal_mode, "#6b7280"
        )
        self.vocal_mode_button.pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "📊 MONITORING LIVE", 
            self.toggle_live_monitor, "#10b981"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "🔍 REVIEW VOCAL", 
            self.show_voice_review, "#F59E0B"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "⚙ MODIFIER POSITIONS", 
            self.modify_positions, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "🎥 SAUVEGARDER CLIP", 
            self.save_video_clip, "#9333EA"
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "🗑 ANNULER DERNIER", 
            self.remove_last_point, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        self._create_modern_button(
            sidebar_content, "❓ AIDE", 
            self.show_help, self.COLORS['text_light']
        ).pack(pady=(0, 12), padx=20, fill="x")
        
        # Ancien système mains-libres (désactivé par défaut). Réactivable via config.json > features.voice_handsfree
        if getattr(self, "enable_handsfree_voice", False) and VOICE_AVAILABLE and self.voice_commander:
            self.voice_button = self._create_modern_button(
                sidebar_content, "🎤 COMMANDES VOCALES (OK)",
                self.toggle_voice_commands, "#EF4444"
            )
            self.voice_button.pack(pady=(0, 12), padx=20, fill="x")
            self._create_tooltip(self.voice_button, "Ancien mode mains-libres (OK ...)")
        
        self._register_ai_button(
            self._create_modern_button(
                sidebar_content, "💬 CHAT OLLAMA",
                self.open_ollama_chat, "#00D4FF"
            )
        ).pack(pady=(0, 12), padx=20, fill="x")

        self._register_ai_button(
            self._create_modern_button(
                sidebar_content, "🤖 ANALYSE IA LIVE",
                self.toggle_ollama_live, "#667eea"
            )
        ).pack(pady=(0, 12), padx=20, fill="x")

        self._register_ai_button(
            self._create_modern_button(
                sidebar_content, "💬 AGENT CHAT",
                self.toggle_agent_chat, "#00D4FF"
            )
        ).pack(pady=(0, 30), padx=20, fill="x")
        
        # Section STATISTIQUES
        self._create_sidebar_section(sidebar_content, "STATISTIQUES")
        
        self.stats_label = tk.Label(
            sidebar_content, 
            text="Aucun point enregistré", 
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_sidebar'],
            fg=self.COLORS['text_light'],
            justify="left",
            anchor="w",
            padx=10,
            pady=10
        )
        self.stats_label.pack(pady=(0, 20), padx=20, fill="x")

        self._apply_ai_buttons_visibility()
        
        # Appliquer le binding mousewheel sur tous les widgets créés
        self._bind_sidebar_mousewheel()

        # ============= ZONE VIDÉO =============
        video_container = tk.Frame(main_container, bg=self.COLORS['bg_main'])
        # Réduit les marges pour maximiser la hauteur/largeur vidéo
        video_container.pack(side="left", fill="both", expand=True, padx=8, pady=4)
        self.video_container = video_container

        # Colonne droite dediee au journal vocal (vertical), hors zone video.
        video_content_row = tk.Frame(video_container, bg=self.COLORS['bg_main'])
        video_content_row.pack(fill="both", expand=True)

        video_main_col = tk.Frame(video_content_row, bg=self.COLORS['bg_main'])
        video_main_col.pack(side="left", fill="both", expand=True)

        voice_log_col = tk.Frame(video_content_row, bg=self.COLORS['bg_main'], width=290)
        voice_log_col.pack(side="right", fill="y", padx=(8, 0))
        voice_log_col.pack_propagate(False)
        self.voice_log_col = voice_log_col
        
        # Bandeau d'erreur vocal (caché par défaut)
        self.voice_error_banner = tk.Frame(video_main_col, bg="#EF4444", height=0)
        self.voice_error_banner.pack(fill="x", side="top")
        self.voice_error_banner.pack_forget()  # Caché par défaut
        
        self.voice_error_label = tk.Label(
            self.voice_error_banner,
            text="",
            font=("Segoe UI", 11, "bold"),
            bg="#EF4444",
            fg="white",
            pady=12
        )
        self.voice_error_label.pack(fill="x")

        # Bandeau d'informations vocal (rappel touche + champs reconnus)
        self.voice_info_banner = tk.Frame(video_main_col, bg="#111827")
        if SHOW_VOICE_INFO_BANNER:
            self.voice_info_banner.pack(fill="x", side="top", pady=(0, 8))

        self.voice_info_title = tk.Label(
            self.voice_info_banner,
            text="",
            font=("Segoe UI", 10, "bold"),
            bg="#111827",
            fg="#E5E7EB",
            pady=6,
            padx=10,
            anchor="w",
            justify="left",
        )
        self.voice_info_title.pack(fill="x")

        self.voice_info_fields = tk.Label(
            self.voice_info_banner,
            text="",
            font=("Segoe UI", 9),
            bg="#111827",
            fg="#E5E7EB",
            pady=6,
            padx=10,
            anchor="w",
            justify="left",
        )
        self.voice_info_fields.pack(fill="x")

        # Initialiser l'affichage
        try:
            self._refresh_voice_info_banner(level="info", status="Prêt")
        except Exception:
            pass
        
        # Cadre vidéo
        video_frame = tk.Frame(video_main_col, bg="#000000", relief="flat")
        video_frame.pack(fill="both", expand=True)
        
        # Frame VLC pour la vidéo
        self.vlc_frame = tk.Frame(video_frame, bg="#000000")
        self.vlc_frame.pack(fill="both", expand=True)
        
        # Sauvegarder le parent original pour le détachement/réattachement
        self.vlc_frame_original_parent = video_frame
        print(f"[DEBUG] vlc_frame créé avec parent: {video_frame}")
        
        # Canvas OpenCV (invisible, pour captures)
        self.video_canvas = tk.Canvas(video_frame, bg="#000000", highlightthickness=0)
        
        # Variables pour le zoom de la timeline
        self.timeline_zoom_level = 1.0  # Niveau de zoom (1.0 = 100%)
        self.timeline_offset = 0  # Décalage horizontal en pixels
        
        # ============= BARRE DE PROGRESSION =============
        progress_frame = tk.Frame(video_main_col, bg=self.COLORS['bg_main'], height=42)
        progress_frame.pack(fill="x", pady=(4, 0))
        progress_frame.pack_propagate(False)
        
        # Canvas pour la barre - TEST ROUGE
        self.progress_canvas = tk.Canvas(
            progress_frame,
            bg="#0F172A",
            height=self.PROGRESS_CANVAS_HEIGHT,
            highlightthickness=0,
            cursor="hand2"
        )
        self.progress_canvas.pack(fill="x", padx=8, pady=6)
        
        # Dessiner la barre
        self.progress_bg = self.progress_canvas.create_rectangle(
            0, 0, 100, self.PROGRESS_CANVAS_HEIGHT, fill=self.COLORS['border'], outline=""
        )
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, self.PROGRESS_CANVAS_HEIGHT, fill=self.COLORS['primary'], outline=""
        )
        # Curseur plus gros et visible
        self.progress_handle = self.progress_canvas.create_oval(
            -10, 5, 10, self.PROGRESS_CANVAS_HEIGHT - 5, fill=self.COLORS['white'], 
            outline=self.COLORS['primary'], width=4,
            tags="progress_handle"
        )
        self.progress_canvas.tag_raise("progress_handle")
        
        # Bindings
        self.progress_canvas.bind("<Button-1>", self._on_progress_click)
        self.progress_canvas.bind("<B1-Motion>", self._on_progress_drag)
        self.progress_canvas.bind("<Control-MouseWheel>", self._on_timeline_zoom)
        self.progress_canvas.bind("<Button-2>", self._reset_timeline_zoom)  # Clic molette = reset zoom
        # Redessiner dès que le canvas obtient sa taille finale (utile après chargement autosave sans vidéo)
        self.progress_canvas.bind("<Configure>", lambda e: self._update_progress_bar())
        
        # ============= INFO TEMPS =============
        info_frame = tk.Frame(video_main_col, bg=self.COLORS['bg_main'], height=24)
        info_frame.pack(fill="x")
        
        self.time_label = tk.Label(
            info_frame, text="00:00 / 00:00",
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_dark']
        )
        self.time_label.pack(side="left", padx=10)
        
        self.frame_label = tk.Label(
            info_frame, text="Frame: 0 / 0",
            font=("Segoe UI", 10),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_light']
        )
        self.frame_label.pack(side="right", padx=10)
        
        # ============= CONTRÔLES VIDÉO =============
        controls_frame = tk.Frame(video_main_col, bg=self.COLORS['bg_main'], height=54)
        controls_frame.pack(fill="x", pady=(4, 0))
        controls_frame.pack_propagate(False)
        # Détachement vidéo supprimé: la vidéo reste toujours intégrée.
        
        # Container pour les boutons centrés
        btn_container = tk.Frame(controls_frame, bg=self.COLORS['bg_main'])
        btn_container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Boutons de contrôle modernes
        self._create_video_control_button(
            btn_container, "⏮", self.rewind_5s
        ).pack(side="left", padx=5)
        
        self._create_video_control_button(
            btn_container, "◀", self.previous_frame
        ).pack(side="left", padx=5)
        
        self.play_btn = self._create_video_control_button(
            btn_container, "▶", self.toggle_play_pause, is_play=True
        )
        self.play_btn.pack(side="left", padx=8)
        
        self._create_video_control_button(
            btn_container, "▶", self.next_frame
        ).pack(side="left", padx=5)
        
        self._create_video_control_button(
            btn_container, "⏭", self.forward_5s
        ).pack(side="left", padx=5)
        
        # Bouton rotation (90° horaire)
        rotate_btn = self._create_video_control_button(
            btn_container, "🔄", self.rotate_video
        )
        rotate_btn.pack(side="left", padx=10)
        self._create_tooltip(rotate_btn, "Pivoter la vidéo de 90° (Touche T)")
        
        # Sélecteur de vitesse
        self.audio_btn = self._create_audio_toggle_button(btn_container)
        self.audio_btn.pack(side="left", padx=6)
        self._create_tooltip(self.audio_btn, "Couper/Remettre le son (touche M)")
        rec_widget = self._create_rec_indicator_widget(btn_container)
        rec_widget.pack(side="left", padx=(4, 6))
        self._create_tooltip(rec_widget, "Etat enregistrement vocal (touche V)")

        speed_frame = tk.Frame(controls_frame, bg=self.COLORS['bg_main'])
        speed_frame.pack(side="right", padx=20)
        
        tk.Label(
            speed_frame, text="Vitesse:",
            font=("Segoe UI", 10),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_light']
        ).pack(side="left", padx=8)
        
        self.speed_var = tk.StringVar(value="1.0x")
        speed_options = ["0.25x", "0.5x", "0.75x", "1.0x", "1.5x", "2.0x"]
        self.speed_combo = ttk.Combobox(
            speed_frame,
            textvariable=self.speed_var,
            values=speed_options,
            state="readonly",
            width=6,
            font=("Segoe UI", 10)
        )
        self.speed_combo.pack(side="left", padx=5)
        self.speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)

        self._create_voice_log_panel(voice_log_col, height=18, vertical=True)

        # Barre flottante de secours: permet de revenir en mode normal et charger une video
        # meme si la sidebar est masquee en mode immersif.
        quickbar = tk.Frame(video_container, bg="#0F172A", highlightthickness=1, highlightbackground="#334155")
        self.immersive_quickbar = quickbar
        tk.Button(
            quickbar,
            text="↩ Mode normal",
            command=lambda: self._set_immersive_video_mode(False),
            font=("Segoe UI", 9, "bold"),
            bg="#1E293B",
            fg="#E5E7EB",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            activebackground="#334155",
            activeforeground="#FFFFFF",
        ).pack(side="left", padx=(6, 4), pady=6)
        tk.Button(
            quickbar,
            text="📁 Charger video",
            command=self.load_video,
            font=("Segoe UI", 9, "bold"),
            bg="#0EA5E9",
            fg="#001018",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
            activebackground="#38BDF8",
            activeforeground="#001018",
        ).pack(side="left", padx=(4, 6), pady=6)

        self._refresh_audio_button_state()
        is_recording = bool(self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False))
        self._set_rec_indicator_mode("recording" if is_recording else "idle")
        # Mode agressif par defaut uniquement pour l'application standard.
        self.immersive_video_mode = False
        if self.ui_mode != "portable_video_simple":
            self.root.after(220, lambda: self._set_immersive_video_mode(True))
        self.root.after_idle(self._apply_keyboard_focus_policy)
    
    def _create_sidebar_section(self, parent, title):
        """Crée une section dans la sidebar"""
        # Titre de section
        section_frame = tk.Frame(parent, bg=self.COLORS['bg_sidebar'])
        section_frame.pack(fill="x", pady=(25, 15), padx=20)
        
        tk.Label(
            section_frame,
            text=title,
            font=self.heading_font,
            bg=self.COLORS['bg_sidebar'],
            fg=self.COLORS['secondary']
        ).pack(anchor="w")
        
        # Ligne sous le titre
        tk.Frame(
            section_frame,
            bg=self.COLORS['primary'],
            height=3
        ).pack(fill="x", pady=(5, 0))
    
    def _create_modern_button(self, parent, text, command, color):
        """Crée un bouton moderne pour la sidebar"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.button_font,
            bg=color,
            fg=self.COLORS['white'],
            relief="flat",
            pady=14,
            cursor="hand2",
            activebackground=color,
            borderwidth=0,
            highlightthickness=0
        )
        
        # Effet hover
        def on_enter(e):
            # Assombrir légèrement au survol
            btn['bg'] = self._darken_color(color)
        
        def on_leave(e):
            btn['bg'] = color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn
    
    def _create_video_control_button(self, parent, text, command, is_play=False):
        """Crée un bouton de contrôle vidéo moderne"""
        size = 60 if is_play else 50
        bg_color = self.COLORS['primary'] if is_play else self.COLORS['text_light']
        
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 18 if is_play else 16, "bold"),
            bg=bg_color,
            fg=self.COLORS['white'],
            relief="flat",
            width=4 if is_play else 3,
            height=1,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )
        
        # Effet hover
        def on_enter(e):
            btn['bg'] = self._darken_color(bg_color)
        
        def on_leave(e):
            btn['bg'] = bg_color
        
        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        
        return btn

    def _create_audio_toggle_button(self, parent):
        """Create mute/unmute button with explicit visual state."""
        btn = tk.Button(
            parent,
            text="SON",
            command=self.toggle_audio_mute,
            font=("Segoe UI", 11, "bold"),
            bg="#10B981",
            fg=self.COLORS['white'],
            relief="flat",
            width=6,
            height=1,
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0
        )

        def on_enter(_e):
            try:
                btn['bg'] = self._darken_color(btn.cget("bg"))
            except Exception:
                pass

        def on_leave(_e):
            self._refresh_audio_button_state()

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        self.audio_btn = btn
        self._refresh_audio_button_state()
        return btn
    
    def _darken_color(self, hex_color, factor=0.15):
        """Assombrit une couleur hexadécimale"""
        try:
            # Enlever le # si présent
            hex_color = hex_color.lstrip('#')
            
            # Convertir en RGB
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            
            # Assombrir
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            
            # Reconvertir en hex
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return hex_color
    
    def _create_control_button(self, parent, text, command, bg, hover_bg):
        """Crée un bouton de contrôle (ancienne version)"""
        btn = tk.Button(parent, text=text, command=command,
                       font=("Segoe UI", 14, "bold"), bg=bg, fg="white",
                       relief="flat", width=3, height=1, cursor="hand2",
                       activebackground=hover_bg, bd=0)
        return btn

    def toggle_detach_video_OLD(self):
        """ANCIENNE VERSION - NE PLUS UTILISER - Détache ou ré-attache la zone vidéo dans une fenêtre séparée"""
        self._log("toggle_detach_video_OLD called (legacy, no-op)")
        # Cette fonction est désactivée pour éviter les conflits
        return

    def apply_functions_topmost(self):
        """Applique l'option 'toujours au premier plan' au panneau de fonctions"""
        try:
            topmost = bool(self.functions_always_on_top.get())
            # Si la vidéo est détachée, laisser le panneau au premier plan est utile
            # Appliquer au root pour garantir que l'interface reste visible
            self.root.attributes("-topmost", topmost)
        except Exception:
            pass
    
    def _create_annotation_button(self, parent, text, command, bg, hover_bg):
        """Crée un bouton d'annotation"""
        btn = tk.Button(parent, text=text, command=command,
                       font=("Segoe UI", 12, "bold"), bg=bg, fg="white",
                       relief="flat", pady=15, cursor="hand2",
                       activebackground=hover_bg)
        return btn
    
    def _update_video(self):
        """Update loop pour synchroniser les infos"""
        # Synchroniser la position depuis VLC
        if self.playing and self.video_player.video_loaded:
            if getattr(self.video_player, "vlc_player", None):
                self.video_player.sync_from_vlc()
            else:
                # Fallback sans VLC: lecture continue image par image via OpenCV.
                frame = self.video_player.next_frame()
                if frame is not None:
                    self._display_frame(frame)
                else:
                    self.playing = False
                    try:
                        if hasattr(self, "play_btn") and self.play_btn and self.play_btn.winfo_exists():
                            self.play_btn.config(text="▶")
                    except Exception:
                        pass
        
        # Mettre à jour les infos
        self._update_info_labels()
        self._update_progress_bar()
        
        # Mettre à jour le plein écran si actif
        if self.fullscreen and not self.playing:
            self._update_fullscreen_video()
        
        # Rappeler plus vite en lecture OpenCV pour garder une animation correcte.
        interval_ms = 100
        try:
            if self.playing and self.video_player.video_loaded and not getattr(self.video_player, "vlc_player", None):
                fps = float(getattr(self.video_player, "fps", 30) or 30)
                interval_ms = max(12, int(1000 / max(1.0, fps)))
        except Exception:
            interval_ms = 40
        self.root.after(interval_ms, self._update_video)

    def _update_fullscreen_video(self):
        """Compatibilite avec l'ancienne boucle: rien a redessiner ici."""
        try:
            if bool(getattr(self, "immersive_video_mode", False)):
                # Maintient la geometrie a jour quand on est en plein ecran agressif.
                self.root.update_idletasks()
        except Exception:
            pass
    
    def _display_frame(self, frame):
        """Affiche une frame dans le canvas avec overlay de stats"""
        if frame is None:
            return
        
        # Convertir en PIL Image
        img = Image.fromarray(frame)
        
        # Redimensionner pour s'adapter au canvas
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width > 1 and canvas_height > 1:
            img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
        
        # Convertir en PhotoImage
        photo = ImageTk.PhotoImage(img)
        
        # Afficher
        self.video_canvas.delete("all")
        self.video_canvas.create_image(canvas_width//2, canvas_height//2, 
                                       image=photo, anchor="center")

        # Cadre néon (effet glow) autour de la zone vidéo
        try:
            # Plusieurs rectangles pour simuler un halo
            pad = 8
            colors = [
                (self.COLORS.get('primary', '#00bcd4'), 6),
                (self.COLORS.get('secondary', '#111827'), 3),
                (self.COLORS.get('white', '#ffffff'), 1),
            ]
            x1, y1 = pad, pad
            x2, y2 = max(pad + 1, canvas_width - pad), max(pad + 1, canvas_height - pad)
            for outline, width in colors:
                self.video_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=outline,
                    width=width,
                )
                x1 += 2
                y1 += 2
                x2 -= 2
                y2 -= 2
        except Exception:
            pass
        
        # Overlay: compteur de points
        self._draw_stats_overlay()
        
        self.video_canvas.image = photo
        self.current_image = photo
    
    def _draw_stats_overlay(self):
        """Dessine un overlay avec les stats en temps réel"""
        if not self.video_player.video_loaded:
            return
        
        canvas_width = self.video_canvas.winfo_width()
        
        # Compter les points
        total_points = len(self.annotation_manager.annotations)
        
        # Compteur en haut à droite
        overlay_text = f"📊 Points: {total_points}"
        
        # Rectangle de fond semi-transparent
        self.video_canvas.create_rectangle(
            canvas_width - 180, 10,
            canvas_width - 10, 60,
            fill="#1a1a2e", outline="#667eea", width=2
        )
        
        # Texte
        self.video_canvas.create_text(
            canvas_width - 95, 35,
            text=overlay_text,
            fill="#ffffff",
            font=("Segoe UI", 14, "bold")
        )
        
        # Dernier point enregistré
        if self.annotation_manager.annotations:
            last_point = self.annotation_manager.annotations[-1]
            point_type = last_point.get('type', '')
            
            type_labels = {
                'faute_directe': 'âš ï¸ Faute',
                'point_gagnant': '🏆 Gagnant',
                'faute_provoquee': '🎯 Provoquée'
            }
            
            last_text = f"Dernier: {type_labels.get(point_type, '')}"
            
            self.video_canvas.create_rectangle(
                canvas_width - 180, 70,
                canvas_width - 10, 110,
                fill="#2a2a3e", outline="#667eea", width=2
            )
            
            self.video_canvas.create_text(
                canvas_width - 95, 90,
                text=last_text,
                fill="#cccccc",
                font=("Segoe UI", 11)
            )
    
    def _update_info_labels(self):
        """Met à jour les labels d'information"""
        total_time = self._get_total_duration_seconds()
        fps_safe = self.video_player.fps if self.video_player.fps > 0 else 25

        if self.video_player.video_loaded and self.video_player.total_frames > 0 and self.video_player.fps > 0:
            current_time = self.video_player.get_current_timestamp()
            total_time = max(total_time, self.video_player.total_frames / self.video_player.fps)
            current_frame = self.video_player.current_frame
            total_frames = self.video_player.total_frames
        else:
            # Fallback pour afficher les infos à partir des annotations
            progress = getattr(self, "_manual_progress", 0.0)
            current_time = progress * total_time if total_time else 0

            frames = [a.get("frame") for a in self.annotation_manager.annotations if a.get("frame") is not None]
            total_frames = max(frames) if frames else int(total_time * fps_safe)
            current_frame = int(progress * total_frames) if total_frames else 0

        curr_min = int(current_time // 60)
        curr_sec = int(current_time % 60)
        total_min = int(total_time // 60)
        total_sec = int(total_time % 60)

        self.time_label.config(
            text=f"{curr_min:02d}:{curr_sec:02d} / {total_min:02d}:{total_sec:02d}"
        )
        self.frame_label.config(
            text=f"Frame: {current_frame} / {total_frames}"
        )
    
    def _update_stats(self):
        """Met à jour l'affichage des statistiques"""
        stats = self.annotation_manager.get_stats()
        points = self.annotation_manager.get_all_annotations()
        
        total = len(points)
        fautes = sum(1 for p in points if p["type"] == "faute_directe")
        gagnants = sum(1 for p in points if p["type"] == "point_gagnant")
        provoquees = sum(1 for p in points if p["type"] == "faute_provoquee")
        
        text = f"Total points: {total}\n"
        text += f"Fautes directes: {fautes}\n"
        text += f"Points gagnants: {gagnants}\n"
        text += f"Fautes provoquées: {provoquees}"
        
        self.stats_label.config(text=text)
        
        # Redessiner la timeline avec les marqueurs
        self._progress_markers_cache_key = None
        self._update_progress_bar()
        
        # Notifier la fenêtre Ollama si ouverte
        self._notify_ollama_window()

    def _get_total_duration_seconds(self):
        """Durée totale de référence (vidéo ou, à défaut, max des timestamps/frames)."""
        try:
            if self.video_player.video_loaded and self.video_player.fps > 0:
                return self.video_player.total_frames / self.video_player.fps

            if self.annotation_manager.annotations:
                timestamps = [a.get("timestamp") for a in self.annotation_manager.annotations if a.get("timestamp") is not None]
                max_ts = max(timestamps) if timestamps else 0

                frames = [a.get("frame") for a in self.annotation_manager.annotations if a.get("frame") is not None]
                if frames:
                    fps_guess = self.video_player.fps if self.video_player.fps > 0 else 25
                    max_ts = max(max_ts, max(frames) / fps_guess)

                return max_ts
        except Exception:
            pass
        return 0

    def _sync_manual_position_from_annotations(self):
        """Sans vidéo: place le curseur/temps sur le dernier point connu."""
        try:
            if self.video_player.video_loaded:
                return

            annotations = getattr(self.annotation_manager, "annotations", None) or []
            if not annotations:
                return

            total_duration = self._get_total_duration_seconds()
            if total_duration <= 0:
                return

            fps_guess = self.video_player.fps if self.video_player.fps > 0 else 25

            max_ts = 0.0
            for a in annotations:
                ts = a.get("timestamp", None)
                if ts is None:
                    fr = a.get("frame", None)
                    if fr is not None:
                        try:
                            ts = float(fr) / float(fps_guess)
                        except Exception:
                            ts = None
                try:
                    ts = float(ts)
                except Exception:
                    continue
                if ts > max_ts:
                    max_ts = ts

            progress = max_ts / total_duration if total_duration else 0.0
            self._manual_progress = max(0.0, min(1.0, progress))
        except Exception:
            pass
    
    def _update_progress_bar(self):
        """Met à jour la barre de progression avec markers et zoom."""
        # Si aucune vidéo et aucune annotation, ne rien dessiner
        has_annotations = bool(self.annotation_manager.annotations)
        if not self.video_player.video_loaded and not has_annotations:
            return

        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width <= 1:
            return

        # Calculer la largeur virtuelle avec le zoom
        virtual_width = canvas_width * self.timeline_zoom_level

        # Calculer la position de lecture (0 -> 1). Si vidéo absente, on reste à 0.
        progress = 0.0
        if self.video_player.video_loaded and self.video_player.total_frames > 0:
            progress = self.video_player.current_frame / self.video_player.total_frames
        else:
            progress = getattr(self, "_manual_progress", 0.0)

        # Position avec zoom et offset
        bar_width = (virtual_width * progress) - self.timeline_offset
        
        # Clamp dans les bornes pour éviter qu'il disparaisse visuellement
        if bar_width < 0:
            bar_width = 0
        if bar_width > canvas_width:
            bar_width = canvas_width
        
        track_h = getattr(self, "PROGRESS_CANVAS_HEIGHT", 30)
        y_pad = 5 if track_h >= 20 else 2

        # Mettre à jour la barre
        self.progress_canvas.coords(self.progress_bg, 0, 0, canvas_width, track_h)
        self.progress_canvas.coords(self.progress_bar, 0, 0, bar_width, track_h)

        # Dessiner les markers pour les points annotés
        self._draw_progress_markers()

        # Curseur agrandi et bien visible (au-dessus des markers)
        self.progress_canvas.coords(
            self.progress_handle,
            bar_width - 10, y_pad, bar_width + 10, track_h - y_pad
        )
        self.progress_canvas.tag_raise("progress_handle")
    
    def _draw_progress_markers(self):
        """Dessine des marqueurs sur la barre de progression pour chaque point avec support du zoom"""
        if not self.annotation_manager.annotations:
            self.progress_canvas.delete("marker")
            self._progress_markers_cache_key = ("empty",)
            return
        
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width <= 1:
            return
        
        # Largeur virtuelle avec zoom
        virtual_width = canvas_width * self.timeline_zoom_level

        total_duration = self._get_total_duration_seconds()
        if total_duration <= 0:
            return

        first_ann = self.annotation_manager.annotations[0]
        last_ann = self.annotation_manager.annotations[-1]
        cache_key = (
            len(self.annotation_manager.annotations),
            canvas_width,
            round(float(total_duration), 3),
            round(float(self.timeline_zoom_level), 3),
            int(self.timeline_offset),
            first_ann.get("id"),
            first_ann.get("timestamp"),
            last_ann.get("id"),
            last_ann.get("timestamp"),
            last_ann.get("type"),
        )
        if cache_key == self._progress_markers_cache_key:
            return
        self._progress_markers_cache_key = cache_key

        # Effacer les anciens markers uniquement si un redraw est nécessaire
        self.progress_canvas.delete("marker")
        
        # Couleurs par type
        marker_colors = {
            'faute_directe': '#ff6b6b',
            'point_gagnant': '#51cf66',
            'faute_provoquee': '#ffd43b'
        }
        
        for annotation in self.annotation_manager.annotations:
            timestamp = annotation.get('timestamp', None)
            if timestamp is None:
                frame = annotation.get('frame', None)
                if frame is not None:
                    fps_guess = self.video_player.fps if self.video_player.fps > 0 else 25
                    try:
                        timestamp = float(frame) / float(fps_guess)
                    except Exception:
                        timestamp = None

            try:
                timestamp = float(timestamp)
            except Exception:
                continue

            if timestamp < 0:
                continue
            point_type = annotation.get('type', '')
            
            # Position X sur la barre virtuelle
            x_pos = (timestamp / total_duration) * virtual_width if total_duration > 0 else 0
            
            # Appliquer l'offset du zoom
            x_pos -= self.timeline_offset
            
            # Ne dessiner que si visible
            if x_pos < -2 or x_pos > canvas_width + 2:
                continue
            
            color = marker_colors.get(point_type, '#ffffff')
            
            # Dessiner un petit rectangle vertical
            track_h = getattr(self, "PROGRESS_CANVAS_HEIGHT", 30)
            self.progress_canvas.create_rectangle(
                x_pos - 2, 0,
                x_pos + 2, track_h,
                fill=color, outline=color,
                tags="marker"
            )

        # Marqueurs supplémentaires: captures vocales non reconnues (violet)
        try:
            voice_timestamps = []

            # Cache simple (évite de relire le JSON à chaque refresh)
            if not hasattr(self, "_voice_unrecognized_cache"):
                self._voice_unrecognized_cache = {"mtime": None, "timestamps": []}

            from pathlib import Path
            data_dir = Path("data")
            voice_sessions = list(data_dir.glob("voice_session_*.json"))
            if voice_sessions:
                latest_session = max(voice_sessions, key=lambda p: p.stat().st_mtime)
                mtime = latest_session.stat().st_mtime

                if self._voice_unrecognized_cache.get("mtime") != mtime:
                    import json
                    with open(latest_session, "r", encoding="utf-8") as f:
                        session_data = json.load(f)
                    unrec = session_data.get("unrecognized", []) or []
                    ts_list = []
                    for c in unrec:
                        try:
                            ts_list.append(float(c.get("video_timestamp", 0.0) or 0.0))
                        except Exception:
                            continue
                    self._voice_unrecognized_cache = {"mtime": mtime, "timestamps": ts_list}

                voice_timestamps = list(self._voice_unrecognized_cache.get("timestamps") or [])

            if voice_timestamps:
                vcolor = "#a855f7"  # violet
                track_h = getattr(self, "PROGRESS_CANVAS_HEIGHT", 30)
                for ts in voice_timestamps:
                    if ts < 0:
                        continue
                    x_pos = (ts / total_duration) * virtual_width if total_duration > 0 else 0
                    x_pos -= self.timeline_offset
                    if x_pos < -3 or x_pos > canvas_width + 3:
                        continue
                    # Petit triangle en haut
                    self.progress_canvas.create_polygon(
                        x_pos, 0,
                        x_pos - 5, 10,
                        x_pos + 5, 10,
                        fill=vcolor,
                        outline=vcolor,
                        tags="marker",
                    )
        except Exception:
            pass
    
    def _on_progress_click(self, event):
        """Gère le clic sur la barre de progression avec support du zoom"""
        canvas_width = self.progress_canvas.winfo_width()
        if canvas_width <= 1:
            return

        has_annotations = bool(self.annotation_manager.annotations)
        has_video = self.video_player.video_loaded and self.video_player.total_frames > 0
        if not has_video and not has_annotations:
            return
        
        # Largeur virtuelle avec zoom
        virtual_width = canvas_width * self.timeline_zoom_level
        
        # Position virtuelle du clic (en tenant compte de l'offset)
        virtual_x = event.x + self.timeline_offset
        
        # Calculer la progression clamped
        progress = virtual_x / virtual_width if virtual_width else 0
        progress = max(0, min(1, progress))  # Clamp entre 0 et 1

        if has_video:
            target_frame = int(progress * self.video_player.total_frames)
            frame = self.video_player.seek_frame(target_frame)
            self._display_frame(frame)
        else:
            # Pas de vidéo: on mémorise la position pour afficher le handle/infos
            self._manual_progress = progress
            self._update_progress_bar()
            self._update_info_labels()
    
    def _on_progress_drag(self, event):
        """Gère le drag sur la barre de progression"""
        self._on_progress_click(event)
    
    def _on_timeline_zoom(self, event):
        """Gère le zoom de la timeline avec Ctrl + molette"""
        has_video = self.video_player.video_loaded and self.video_player.total_frames > 0
        has_annotations = bool(self.annotation_manager.annotations)
        if not has_video and not has_annotations:
            return
        
        # Incrément de zoom
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        
        # Calculer le nouveau niveau de zoom (limité entre 1.0 et 10.0)
        new_zoom = self.timeline_zoom_level * zoom_factor
        new_zoom = max(1.0, min(10.0, new_zoom))
        
        if new_zoom != self.timeline_zoom_level:
            # Position relative de la souris sur la timeline
            canvas_width = self.progress_canvas.winfo_width()
            mouse_rel_pos = event.x / canvas_width if canvas_width > 0 else 0.5
            
            # Calculer le nouveau offset pour garder la position sous la souris
            old_total_width = canvas_width * self.timeline_zoom_level
            new_total_width = canvas_width * new_zoom
            
            # Ajuster l'offset pour garder le point sous la souris fixe
            old_mouse_pos = self.timeline_offset + (mouse_rel_pos * canvas_width)
            new_offset = old_mouse_pos - (mouse_rel_pos * canvas_width)
            
            # Limiter l'offset
            max_offset = max(0, new_total_width - canvas_width)
            new_offset = max(0, min(max_offset, new_offset))
            
            self.timeline_zoom_level = new_zoom
            self.timeline_offset = new_offset
            
            # Redessiner la barre de progression
            self._update_progress_bar()
    
    def _reset_timeline_zoom(self, event=None):
        """Réinitialise le zoom de la timeline (clic molette)"""
        self.timeline_zoom_level = 1.0
        self.timeline_offset = 0
        self._update_progress_bar()
    
    def _on_speed_change(self, event=None):
        """Gère le changement de vitesse"""
        speed_text = self.speed_var.get()
        speed_value = float(speed_text.replace("x", ""))
        self.video_player.set_playback_speed(speed_value)

    def _has_vlc_audio_output(self) -> bool:
        """Indique si un backend audio VLC est disponible pour mute/unmute."""
        try:
            return bool(self.video_player and getattr(self.video_player, "vlc_player", None))
        except Exception:
            return False

    def _refresh_audio_button_state(self):
        """Met a jour l'apparence du bouton audio selon l'etat mute/unmute."""
        btn = getattr(self, "audio_btn", None)
        if btn is None:
            return
        try:
            if not btn.winfo_exists():
                return
        except Exception:
            return

        muted = bool(getattr(self, "audio_muted", False))
        has_audio = self._has_vlc_audio_output()

        if muted:
            text = "MUTE"
            bg = "#EF4444" if has_audio else "#9CA3AF"
            active_bg = "#DC2626" if has_audio else "#6B7280"
        else:
            text = "SON"
            bg = "#10B981" if has_audio else "#9CA3AF"
            active_bg = "#059669" if has_audio else "#6B7280"

        try:
            btn.config(text=text, bg=bg, activebackground=active_bg)
        except Exception:
            pass

    def _set_audio_muted(self, muted: bool):
        """Applique l'etat audio et met a jour le bouton."""
        muted = bool(muted)
        self.audio_muted = muted

        try:
            if self._has_vlc_audio_output():
                if muted:
                    self.video_player.mute_audio()
                else:
                    self.video_player.unmute_audio()
        except Exception as e:
            print(f"[WARN] Impossible de changer l'etat audio: {e}")

        self._refresh_audio_button_state()

    def toggle_audio_mute(self, event=None):
        """Bascule mute/unmute avec un bouton dedie ou la touche M."""
        if event is not None and not self._should_process_main_shortcuts(event):
            return

        # Si l'utilisateur agit manuellement pendant le PTT, on respecte son choix.
        try:
            if self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False):
                self._voice_recording_forced_mute = False
        except Exception:
            pass

        self._set_audio_muted(not bool(getattr(self, "audio_muted", False)))

        if hasattr(self, "_update_voice_status_label"):
            self._update_voice_status_label("Son coupe" if self.audio_muted else "Son actif")
            self.root.after(1200, lambda: self._update_voice_status_label(""))

        return "break" if event is not None else None

    def _create_rec_indicator_widget(self, parent):
        """Create REC widget displayed near playback controls."""
        rec_frame = tk.Frame(parent, bg=self.COLORS['bg_main'])

        dot = tk.Label(
            rec_frame,
            text="●",
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS['bg_main'],
            fg="#9CA3AF",
            width=2
        )
        dot.pack(side="left")

        text = tk.Label(
            rec_frame,
            text="REC OFF",
            font=("Segoe UI", 9, "bold"),
            bg=self.COLORS['bg_main'],
            fg="#6B7280"
        )
        text.pack(side="left", padx=(0, 2))

        self.rec_indicator_dot = dot
        self.rec_indicator_text = text
        self._set_rec_indicator_mode("idle")
        return rec_frame

    def _set_rec_indicator_mode(self, mode: str):
        """Update recording indicator mode: idle, recording, transcribing, error."""
        self._rec_indicator_mode = str(mode or "idle")

        if self._rec_blink_after_id:
            try:
                self.root.after_cancel(self._rec_blink_after_id)
            except Exception:
                pass
            self._rec_blink_after_id = None

        dot = getattr(self, "rec_indicator_dot", None)
        text = getattr(self, "rec_indicator_text", None)
        if dot is None or text is None:
            return

        try:
            if self._rec_indicator_mode == "recording":
                text.config(text="REC ON", fg="#B91C1C")
                self._rec_blink_phase = False
                self._schedule_rec_blink()
                return
            if self._rec_indicator_mode == "transcribing":
                dot.config(fg="#F59E0B")
                text.config(text="ANALYSE...", fg="#92400E")
                return
            if self._rec_indicator_mode == "error":
                dot.config(fg="#EF4444")
                text.config(text="REC ERR", fg="#991B1B")
                return

            dot.config(fg="#9CA3AF")
            text.config(text="REC OFF", fg="#6B7280")
        except Exception:
            pass

    def _schedule_rec_blink(self):
        """Blink REC dot while recording is active."""
        if getattr(self, "_rec_indicator_mode", "idle") != "recording":
            return

        dot = getattr(self, "rec_indicator_dot", None)
        if dot is None:
            return
        try:
            if not dot.winfo_exists():
                return
        except Exception:
            return

        self._rec_blink_phase = not bool(getattr(self, "_rec_blink_phase", False))
        try:
            dot.config(fg="#EF4444" if self._rec_blink_phase else "#FCA5A5")
        except Exception:
            pass

        try:
            self._rec_blink_after_id = self.root.after(320, self._schedule_rec_blink)
        except Exception:
            self._rec_blink_after_id = None

    def _create_voice_log_panel(self, parent, height=5, vertical=False):
        """Create on-screen log for voice events with timestamps."""
        panel_bg = "#111827" if vertical else "#F8FAFB"
        panel_border = "#1F2937" if vertical else "#E5E7EB"
        title_fg = "#E5E7EB" if vertical else "#1F2937"
        subtitle_fg = "#94A3B8" if vertical else "#6B7280"
        text_bg = "#0F172A" if vertical else "#FFFFFF"
        text_fg = "#E5E7EB" if vertical else "#111827"

        panel = tk.Frame(parent, bg=panel_bg, highlightthickness=1, highlightbackground=panel_border)
        if vertical:
            panel.pack(fill="both", expand=True, pady=(0, 0))
        else:
            panel.pack(fill="x", pady=(8, 0))

        header = tk.Frame(panel, bg=panel_bg)
        header.pack(fill="x", padx=8, pady=(6, 2))
        tk.Label(
            header,
            text="Journal vocal",
            font=("Segoe UI", 9, "bold"),
            bg=panel_bg,
            fg=title_fg
        ).pack(side="left")
        tk.Label(
            header,
            text="(heure + statut)",
            font=("Segoe UI", 8),
            bg=panel_bg,
            fg=subtitle_fg
        ).pack(side="left", padx=(6, 0))

        body = tk.Frame(panel, bg=panel_bg)
        if vertical:
            body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        else:
            body.pack(fill="x", padx=8, pady=(0, 8))

        text = tk.Text(
            body,
            height=height,
            wrap="word",
            font=("Consolas", 9),
            bg=text_bg,
            fg=text_fg,
            relief="solid",
            bd=1
        )
        text.pack(side="left", fill="both", expand=True)
        text.config(state="disabled")

        scrollbar = tk.Scrollbar(body, orient="vertical", command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)

        self.voice_log_text = text
        self._render_voice_log_entries()
        return panel

    def _render_voice_log_entries(self):
        """Render buffered voice log entries into text widget."""
        text = getattr(self, "voice_log_text", None)
        if text is None:
            return
        try:
            if not text.winfo_exists():
                return
            text.config(state="normal")
            text.delete("1.0", "end")
            for line in getattr(self, "voice_log_entries", []):
                text.insert("end", line + "\n")
            text.see("end")
            text.config(state="disabled")
        except Exception:
            pass

    def _append_voice_log(self, message: str):
        """Append one timestamped line to the on-screen voice log."""
        msg = " ".join(str(message or "").split()).strip()
        if not msg:
            return
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.voice_log_entries.append(line)
        max_items = int(getattr(self, "_voice_log_max_entries", 120) or 120)
        if len(self.voice_log_entries) > max_items:
            self.voice_log_entries = self.voice_log_entries[-max_items:]
        self._render_voice_log_entries()
    
    # === Méthodes de contrôle vidéo ===
    
    def load_video(self):
        """Charge une vidéo"""
        if getattr(self, "safe_mode", False):
            messagebox.showinfo(
                "Mode safe",
                "Le mode safe est activé.\n\n"
                "La vidéo est désactivée (pour démarrer sur PC moyen).\n"
                "Lancez sans --safe pour réactiver la vidéo."
            )
            return

        # Arrêter la vidéo en cours si elle existe
        if self.video_player.video_loaded:
            self.stop_video()
        
        print("[DEBUG] load_video appelé")
        filepath = ""
        was_immersive = bool(getattr(self, "immersive_video_mode", False))
        try:
            # Sur Windows, le file dialog peut être caché en mode fullscreen OS.
            if was_immersive:
                self._set_immersive_video_mode(False)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass

            filepath = filedialog.askopenfilename(
                parent=self.root,
                title="Sélectionner une vidéo",
                filetypes=[("Vidéos", "*.mp4 *.avi *.mov"), ("Tous", "*.*")]
            )
        finally:
            # Restaure le mode immersif automatiquement si l'utilisateur venait de ce mode.
            if was_immersive:
                try:
                    self._set_immersive_video_mode(True)
                except Exception:
                    pass
        
        if filepath:
            try:
                import traceback as _tb
                print(f"[UI:load_video] Fichier sélectionné: {filepath}")
                print(f"[UI:load_video] Taille fichier: {os.path.getsize(filepath)} octets")
                print(f"[UI:load_video] video_player type: {type(self.video_player).__name__}")
                print(f"[UI:load_video] cv2_available={self.video_player.cv2_available} | vlc_available={self.video_player.vlc_available}")

                frame = self.video_player.load_video(filepath)
                print(f"[UI:load_video] load_video retourné | frame={'OK' if frame is not None else 'None'}")

                self.current_video = filepath
                self.annotation_manager.set_video(filepath)

                # Configurer VLC pour afficher dans notre frame
                print(f"[UI:load_video] vlc_frame={self.vlc_frame} | winfo_exists={self.vlc_frame.winfo_exists()}")
                print(f"[UI:load_video] vlc_frame taille: {self.vlc_frame.winfo_width()}x{self.vlc_frame.winfo_height()}")
                self.vlc_frame.update()
                window_id = self.vlc_frame.winfo_id()
                print(f"[UI:load_video] window_id après update(): {window_id}")
                self.video_player.set_vlc_window(window_id)
                self._set_audio_muted(self.audio_muted)
                print(f"[UI:load_video] set_vlc_window OK")

                # Afficher la première frame via OpenCV si disponible
                if frame is not None:
                    self._display_frame(frame)
                    print(f"[UI:load_video] Première frame affichée")
                else:
                    print(f"[UI:load_video] Pas de première frame OpenCV")

                # Vérifier s'il existe un autosave pour cette vidéo
                self._check_existing_autosave(filepath)

                if self.video_player.vlc_player:
                    print("[UI:load_video] VLC player actif -> lecture avec son")
                    messagebox.showinfo(
                        "Succès",
                        "Vidéo chargée avec succès!\n"
                        "Lecture avec son activée via VLC."
                    )
                else:
                    print("[UI:load_video] Pas de VLC player -> lecture sans son")
                    reason_getter = getattr(self.video_player, "get_vlc_diagnostic", None)
                    reason = reason_getter() if callable(reason_getter) else (
                        getattr(self.video_player, "vlc_error", None) or "VLC indisponible"
                    )
                    messagebox.showwarning(
                        "Vidéo chargée (sans son)",
                        "Vidéo chargée avec succès.\n"
                        "Lecture sans son: VLC n'est pas opérationnel.\n\n"
                        f"Détail: {reason}\n\n"
                        "Vérifiez:\n"
                        "- python-vlc installé dans l'environnement lancé\n"
                        "- VLC de même architecture que Python/l'exe (64 bits avec Python 64 bits)\n"
                        "- le dossier vlc/ présent à côté de l'exécutable ou dans le package portable\n"
                        "- sinon, VLC Media Player installé (libvlc)"
                    )
            except Exception as e:
                print(f"[UI:load_video] EXCEPTION: {e}")
                _log_ui_exception("load_video", e)
                messagebox.showerror("Erreur", f"Impossible de charger la vidéo:\n{e}")

    def remote_open_video_dialog(self):
        self.load_video()
        return self.remote_get_state()

    def remote_load_video(self, video_path: str):
        ok = self._load_video_from_session_path(video_path)
        if not ok:
            raise RuntimeError(f"Impossible de charger la vidéo: {video_path}")
        return self.remote_get_state()
    
    def stop_video(self):
        """Arrête et décharge la vidéo en cours"""
        if not self.video_player.video_loaded:
            return  # Silencieux si appelé lors du changement de vidéo
        
        try:
            # Arrêter la lecture
            if self.playing:
                self.playing = False
            
            # Nettoyer VLC proprement
            if self.video_player.vlc_player:
                try:
                    self.video_player.vlc_player.stop()
                    self.video_player.vlc_player.release()
                    self.video_player.vlc_player = None
                except:
                    pass
            
            # Nettoyer OpenCV
            if self.video_player.cap:
                try:
                    self.video_player.cap.release()
                    self.video_player.cap = None
                except:
                    pass
            
            # Réinitialiser l'état
            self.video_player.video_loaded = False
            self.current_video = None
            self._refresh_audio_button_state()
            
            # Nettoyer le frame VLC
            try:
                for widget in self.vlc_frame.winfo_children():
                    widget.destroy()
            except:
                pass
            
            print("[INFO] Vidéo arrêtée et déchargée")
            
        except Exception as e:
            print(f"[ERROR] Erreur stop vidéo: {e}")
    
    def _check_existing_autosave(self, video_path):
        """Vérifie s'il existe un autosave pour cette vidéo"""
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        data_folder = self.annotation_manager.data_folder
        
        # Chercher les autosaves pour cette vidéo
        autosaves = []
        if os.path.exists(data_folder):
            for file in os.listdir(data_folder):
                if file.startswith(f"autosave_{video_name}") and file.endswith(".json"):
                    autosaves.append(os.path.join(data_folder, file))
        
        if autosaves:
            # Trier par date (le plus récent en premier)
            autosaves.sort(key=os.path.getmtime, reverse=True)
            latest = autosaves[0]
            
            response = messagebox.askyesno(
                "Autosave détecté",
                f"Un autosave existe pour cette vidéo.\n\n"
                f"Fichier: {os.path.basename(latest)}\n"
                f"Date: {self._format_file_time(latest)}\n\n"
                f"Voulez-vous charger cet autosave ?",
                icon='question'
            )
            
            if response:
                if self.annotation_manager.load_autosave(latest):
                    self._update_stats()
                    # Si on est finalement sans vidéo (ou non chargée), afficher temps + curseur via les annotations
                    self._sync_manual_position_from_annotations()
                    self._update_info_labels()
                    self._update_progress_bar()
                    messagebox.showinfo("✓", 
                                      f"Autosave chargé avec succès!\n"
                                      f"{len(self.annotation_manager.annotations)} points restaurés")
    
    def _format_file_time(self, filepath):
        """Formate la date de modification d'un fichier"""
        import time
        timestamp = os.path.getmtime(filepath)
        return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(timestamp))
    
    def load_autosave(self):
        """Charge manuellement un fichier autosave"""
        filepath = filedialog.askopenfilename(
            title="Charger un autosave",
            initialdir=self.annotation_manager.data_folder,
            filetypes=[("JSON Autosave", "autosave_*.json"), 
                      ("Tous JSON", "*.json"), 
                      ("Tous", "*.*")]
        )
        
        if filepath:
            try:
                if self.annotation_manager.load_autosave(filepath):
                    self._update_stats()

                    # Pas de vidéo: se placer sur le dernier point (curseur + temps)
                    self._sync_manual_position_from_annotations()
                    self._update_info_labels()
                    
                    # Forcer la mise à jour de l'interface puis dessiner les marqueurs
                    self.root.update_idletasks()
                    self._update_progress_bar()
                    # Redessiner après 100ms pour être sûr que le canvas a sa taille finale
                    self.root.after(100, self._update_progress_bar)
                    
                    # Afficher le résumé
                    nb_points = len(self.annotation_manager.annotations)
                    video_name = self.annotation_manager.match_info.get("video", "N/A")
                    
                    messagebox.showinfo(
                        "Autosave chargé",
                        f"✓ Données restaurées avec succès!\n\n"
                        f"Vidéo: {video_name}\n"
                        f"Points: {nb_points}\n"
                        f"Joueurs: {', '.join(self.annotation_manager.match_info['joueurs'])}"
                    )
                else:
                    messagebox.showerror("Erreur", "Impossible de charger l'autosave")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur de chargement:\n{e}")
    
    def import_json(self):
        """Importe un fichier JSON (ancien ou nouveau format)"""
        filepath = filedialog.askopenfilename(
            title="Importer un fichier JSON",
            initialdir=self.annotation_manager.data_folder,
            filetypes=[("Fichiers JSON", "*.json"), ("Tous", "*.*")]
        )
        
        if filepath:
            try:
                import json
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Détecter le format
                if self._is_new_format(data):
                    # Nouveau format (avec match/points/stats)
                    converted_data = data
                elif self._is_old_format(data):
                    # Ancien format - convertir
                    converted_data = self._convert_old_to_new_format(data)
                else:
                    messagebox.showerror("Format non reconnu", 
                                       "Le format JSON n'est pas reconnu.\n"
                                       "Formats supportés:\n"
                                       "- Nouveau format (match/points/stats)\n"
                                       "- Ancien format (joueurs/annotations)")
                    return
                
                # Charger les données converties
                self.annotation_manager.load_from_dict(converted_data)
                
                # Mettre à jour les joueurs dans l'interface
                joueurs = self.annotation_manager.match_info.get("joueurs", [])
                self.players = joueurs
                
                # Mettre à jour le parser vocal
                if self.command_parser:
                    player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                    self.command_parser.set_joueurs(player_names)
                
                # Charger la vidéo si possible
                video_path = self.annotation_manager.match_info.get("video")
                if video_path and os.path.exists(video_path):
                    self.video_player.load_video(video_path)
                
                self._update_stats()

                # Pas de vidéo: se placer sur le dernier point (curseur + temps)
                self._sync_manual_position_from_annotations()
                self._update_info_labels()
                
                # Forcer la mise à jour de l'interface puis dessiner les marqueurs
                self.root.update_idletasks()
                self._update_progress_bar()
                # Redessiner après 100ms pour être sûr que le canvas a sa taille finale
                self.root.after(100, self._update_progress_bar)
                
                nb_points = len(self.annotation_manager.annotations)
                messagebox.showinfo(
                    "Import réussi",
                    f"✓ Fichier JSON importé avec succès!\n\n"
                    f"Points importés: {nb_points}\n"
                    f"Joueurs: {len(joueurs)}\n\n"
                    f"Vous pouvez continuer l'analyse."
                )
            
            except Exception as e:
                messagebox.showerror("Erreur d'import", 
                                   f"Impossible d'importer le fichier:\n{e}")
    
    def _is_new_format(self, data):
        """Vérifie si c'est le nouveau format"""
        return "match" in data and "points" in data
    
    def _is_old_format(self, data):
        """Vérifie si c'est l'ancien format"""
        # Ancien format peut avoir: joueurs, annotations, date, etc.
        return ("joueurs" in data or "annotations" in data or 
                "points" in data and "match" not in data)
    
    def _convert_old_to_new_format(self, old_data):
        """Convertit ancien format vers nouveau format"""
        new_data = {
            "match": {
                "date": old_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                "joueurs": old_data.get("joueurs", []),
                "video": old_data.get("video", None)
            },
            "points": [],
            "stats": {}
        }
        
        # Convertir les annotations/points
        points = old_data.get("points", old_data.get("annotations", []))
        for point in points:
            # Vérifier et adapter les champs
            converted_point = {
                "id": point.get("id", 0),
                "type": point.get("type", "faute_directe"),
                "timestamp": point.get("timestamp", 0),
                "frame": point.get("frame", 0),
                "datetime": point.get("datetime", datetime.now().isoformat())
            }
            
            # Ajouter champs spécifiques selon le type
            if point.get("type") == "faute_directe":
                converted_point["joueur"] = point.get("joueur", "")
                converted_point["capture"] = point.get("capture", "")
            
            elif point.get("type") == "point_gagnant":
                converted_point["joueur"] = point.get("joueur", "")
                converted_point["type_coup"] = point.get("type_coup", "autre")
                converted_point["capture"] = point.get("capture", "")
            
            elif point.get("type") == "faute_provoquee":
                converted_point["attaquant"] = point.get("attaquant", "")
                converted_point["defenseur"] = point.get("defenseur", "")
                converted_point["capture"] = point.get("capture", "")
            
            # Ajouter screenshots si présents
            if "screenshots" in point:
                converted_point["screenshots"] = point["screenshots"]
            
            new_data["points"].append(converted_point)
        
        return new_data
    
    def toggle_play_pause(self):
        """Toggle lecture/pause"""
        if not self.video_player.video_loaded:
            print("[UI:toggle_play_pause] Ignoré: video_loaded=False")
            return

        print(f"[UI:toggle_play_pause] is_playing={self.video_player.is_playing} | vlc_player={self.video_player.vlc_player} | window_id={self.video_player.window_id}")
        self._log(f"toggle_play_pause called | allow_video_detach={self.allow_video_detach} | detached={self.detached_video_win is not None}")

        # Si jamais une fenêtre détachée existe, on la rattache avant de jouer
        if getattr(self, "detached_video_win", None) is not None and not getattr(self, "allow_video_detach", True):
            self._log("Forcing reattach before play")
            self.reattach_video_window()

        self.playing = self.video_player.toggle_play_pause()
        print(f"[UI:toggle_play_pause] après toggle: playing={self.playing}")
        # Vérifier que le bouton existe avant de le modifier
        if hasattr(self, 'play_btn') and self.play_btn.winfo_exists():
            self.play_btn.config(text="⏸" if self.playing else "▶")

    def remote_toggle_play_pause(self):
        self.toggle_play_pause()
        return self.remote_get_state()

    def remote_play(self):
        if not self.video_player.video_loaded:
            raise RuntimeError("Aucune vidéo chargée")
        if not bool(getattr(self, "playing", False)):
            self.toggle_play_pause()
        return self.remote_get_state()

    def remote_pause(self):
        if not self.video_player.video_loaded:
            raise RuntimeError("Aucune vidéo chargée")
        if bool(getattr(self, "playing", False)):
            self.toggle_play_pause()
        return self.remote_get_state()

    def _is_text_input_widget(self, widget) -> bool:
        """Retourne True si le widget focus est une zone de saisie."""
        if widget is None:
            return False
        try:
            widget_class = str(widget.winfo_class())
        except Exception:
            return False
        return widget_class in {
            "Entry",
            "TEntry",
            "Text",
            "Spinbox",
            "TCombobox",
            "Listbox",
            "Treeview",
        }

    def _should_process_main_shortcuts(self, event=None) -> bool:
        """Autorise les raccourcis globaux uniquement sur la fenêtre principale."""
        focused = getattr(event, "widget", None) if event is not None else None
        if focused is None:
            try:
                focused = self.root.focus_get()
            except Exception:
                focused = None

        if focused is not None:
            try:
                if focused.winfo_toplevel() is not self.root:
                    return False
            except Exception:
                return False
            if self._is_text_input_widget(focused):
                return False

        try:
            grabbed = self.root.grab_current()
            if grabbed is not None and grabbed.winfo_toplevel() is not self.root:
                return False
        except Exception:
            pass
        return True

    def _on_space_play_pause(self, event=None):
        """Gère la barre espace: play/pause + affichage schéma vocal quand passage en pause."""
        if not self._should_process_main_shortcuts(event):
            return
        if not self.video_player.video_loaded:
            return "break"

        was_playing = bool(getattr(self, "playing", False))
        self.toggle_play_pause()

        # Afficher le schéma uniquement lors du passage lecture -> pause
        if was_playing and not bool(getattr(self, "playing", False)):
            self._show_pause_voice_schema_panel()
        return "break"

    def _show_pause_voice_schema_panel(self):
        """Affiche un panneau compact à droite avec le schéma des commandes vocales PTT."""
        try:
            if getattr(self, "voice_pause_schema_window", None) and self.voice_pause_schema_window.winfo_exists():
                self.voice_pause_schema_window.lift()
                self.voice_pause_schema_window.focus_force()
                return

            win = tk.Toplevel(self.root)
            win.title("🎤 Schéma vocal")
            win.geometry("500x320")
            win.configure(bg="#0B1220")

            try:
                root_x = self.root.winfo_rootx()
                root_y = self.root.winfo_rooty()
                root_w = self.root.winfo_width()
                x = root_x + max(20, root_w - 530)
                y = root_y + 120
                win.geometry(f"500x320+{x}+{y}")
            except Exception:
                pass

            container = tk.Frame(win, bg="#0B1220")
            container.pack(fill="both", expand=True, padx=14, pady=14)

            tk.Label(
                container,
                text="Que dire en vocal (PTT)",
                font=("Segoe UI", 12, "bold"),
                bg="#0B1220",
                fg="#E5E7EB",
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=(0, 8))

            schema = (
                "1) Faute directe\n"
                "   • faute directe [Prénom]\n\n"
                "2) Point gagnant\n"
                "   • point gagnant [Prénom] [Type de coup]\n\n"
                "3) Faute provoquée\n"
                "   • faute provoquée [Attaquant] [Type de coup] [Défenseur]"
            )
            tk.Label(
                container,
                text=schema,
                font=("Segoe UI", 10),
                bg="#0B1220",
                fg="#D1D5DB",
                anchor="w",
                justify="left",
            ).pack(fill="x", pady=(0, 8))

            hint = "PTT : activer 'Vocal (V)' puis appuyer V, parler, rappuyer V."
            tk.Label(
                container,
                text=hint,
                font=("Segoe UI", 9, "italic"),
                bg="#0B1220",
                fg="#93C5FD",
                anchor="w",
                justify="left",
            ).pack(fill="x")

            tk.Button(
                container,
                text="Fermer",
                command=win.destroy,
                bg="#334155",
                fg="#E5E7EB",
                activebackground="#475569",
                activeforeground="#FFFFFF",
                relief="flat",
                padx=12,
                pady=6,
            ).pack(anchor="e", pady=(14, 0))

            self.voice_pause_schema_window = win
            win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, "voice_pause_schema_window", None), win.destroy()))
        except Exception as e:
            print(f"[WARN] Impossible d'afficher le schéma vocal pause: {e}")

    def _enforce_attached_loop(self):
        """Surveille et force le rattachement si une fenêtre vidéo détachée existe alors que c'est interdit."""
        try:
            # Si la fenêtre principale est déjà détruite, ne rien faire
            if not self.root or not self.root.winfo_exists():
                return
            if not getattr(self, "allow_video_detach", True) and getattr(self, "detached_video_win", None) is not None:
                self._log("Watcher: detached window detected while forbidden -> reattach")
                self.reattach_video_window()
        except Exception as e:
            self._log(f"Watcher error: {e}")
        finally:
            # Replanifier la vérification toutes les 700ms
            if self.root and self.root.winfo_exists():
                self.root.after(700, self._enforce_attached_loop)
    
    def next_frame(self):
        """Frame suivante"""
        if self.video_player.video_loaded:
            frame = self.video_player.next_frame()
            self._display_frame(frame)
    
    def previous_frame(self):
        """Frame précédente"""
        if self.video_player.video_loaded:
            frame = self.video_player.previous_frame()
            self._display_frame(frame)
    
    def forward_5s(self):
        """Avance de 5 secondes"""
        if self.video_player.video_loaded:
            frame = self.video_player.forward(5)
            self._display_frame(frame)
    
    def rewind_5s(self):
        """Recule de 5 secondes"""
        if self.video_player.video_loaded:
            frame = self.video_player.rewind(5)
            self._display_frame(frame)
    
    def rotate_video(self):
        """Pivote la vidéo de 90° dans le sens horaire"""
        if self.video_player.video_loaded:
            rotation = self.video_player.rotate_video()
            print(f"[Video] Rotation appliquée: {rotation}°")
            # Afficher un message temporaire
            if hasattr(self, '_update_voice_status_label'):
                self._update_voice_status_label(f"🔄 Rotation: {rotation}°")
                # Effacer le message après 2 secondes
                self.root.after(2000, lambda: self._update_voice_status_label(""))

    def remote_seek_relative(self, seconds: float):
        if not self.video_player.video_loaded:
            raise RuntimeError("Aucune vidéo chargée")
        if seconds < 0:
            self.video_player.rewind(abs(seconds))
        else:
            self.video_player.forward(seconds)
        return self.remote_get_state()

    def remote_seek_to(self, seconds: float):
        if not self.video_player.video_loaded:
            raise RuntimeError("Aucune vidéo chargée")
        self.video_player.seek_time(seconds)
        return self.remote_get_state()

    def remote_set_speed(self, speed: float):
        speed_value = max(0.25, min(2.0, float(speed)))
        self.video_player.set_playback_speed(speed_value)
        if hasattr(self, "speed_var") and self.speed_var is not None:
            try:
                self.speed_var.set(f"{speed_value:.2f}x".replace(".00", ".0"))
            except Exception:
                pass
        return self.remote_get_state()

    def remote_rotate_video(self):
        if not self.video_player.video_loaded:
            raise RuntimeError("Aucune vidéo chargée")
        self.rotate_video()
        return self.remote_get_state()

    def remote_generate_quick_report(self):
        if not getattr(self.annotation_manager, "annotations", None):
            raise RuntimeError("Aucune stat a exporter")
        self.generate_html_fast()
        return self.remote_get_state()

    def remote_export_json(self):
        if not getattr(self.annotation_manager, "annotations", None):
            raise RuntimeError("Aucune annotation à exporter")
        filepath = self.json_exporter.export(self.annotation_manager)
        return {"filepath": filepath}

    def remote_undo_last(self):
        self.annotation_manager.remove_last_annotation()
        return self.remote_get_state()

    def remote_get_state(self):
        return {
            "video_loaded": bool(getattr(self.video_player, "video_loaded", False)),
            "video_path": getattr(self.video_player, "video_path", None),
            "is_playing": bool(getattr(self, "playing", False)),
            "current_time": float(self.video_player.get_current_timestamp()) if getattr(self.video_player, "video_loaded", False) else 0.0,
            "speed": float(getattr(self.video_player, "playback_speed", 1.0) or 1.0),
            "rotation": int(getattr(self.video_player, "rotation", 0) or 0),
        }
    
    def toggle_maximized_video(self):
        """Bascule le mode video immersive plein ecran."""
        self._set_immersive_video_mode(not bool(getattr(self, "immersive_video_mode", False)))
    
    def toggle_fullscreen(self):
        """Alias pour compatibilité"""
        self.toggle_maximized_video()
    
    def enter_maximized_video(self):
        """Compatibilite: active le mode immersive."""
        self._set_immersive_video_mode(True)
    
    def exit_maximized_video(self):
        """Compatibilite: quitte le mode immersive."""
        self._set_immersive_video_mode(False)

    def _set_immersive_video_mode(self, enabled: bool):
        """Mode agressif: plein ecran + suppression des panneaux non essentiels."""
        enabled = bool(enabled)
        self.immersive_video_mode = enabled
        self.fullscreen = enabled

        # Plein ecran fenetre OS (barre des taches masquee). Esc/F11 pour sortir.
        try:
            self.root.attributes("-fullscreen", enabled)
        except Exception:
            pass

        header = getattr(self, "header_frame", None)
        sidebar = getattr(self, "sidebar_frame", None)
        video = getattr(self, "video_container", None)
        quickbar = getattr(self, "immersive_quickbar", None)

        if enabled:
            try:
                if header is not None and header.winfo_manager():
                    header.pack_forget()
            except Exception:
                pass
            try:
                if sidebar is not None and sidebar.winfo_manager():
                    sidebar.pack_forget()
            except Exception:
                pass
            try:
                if video is not None:
                    video.pack_configure(padx=0, pady=0)
            except Exception:
                pass
            try:
                if quickbar is not None:
                    quickbar.place(relx=1.0, rely=0.0, x=-14, y=14, anchor="ne")
            except Exception:
                pass
        else:
            try:
                if header is not None and not header.winfo_manager():
                    header.pack(fill="x", side="top", before=self.main_container)
            except Exception:
                pass
            try:
                if sidebar is not None and not sidebar.winfo_manager():
                    sidebar.pack(side="right", fill="y")
            except Exception:
                pass
            try:
                if video is not None:
                    video.pack_configure(padx=8, pady=4)
            except Exception:
                pass
            try:
                if quickbar is not None:
                    quickbar.place_forget()
            except Exception:
                pass

        try:
            self.root.update_idletasks()
            self.root.after(120, self._apply_keyboard_focus_policy)
        except Exception:
            pass

    def cycle_enlargement_mode(self):
        """Cycle entre plusieurs modes d'agrandissement."""
        if not hasattr(self, 'enlarge_mode'):
            self.enlarge_mode = 'normal'
        modes = ['normal', 'large', 'video_only']
        idx = modes.index(self.enlarge_mode)
        next_mode = modes[(idx + 1) % len(modes)]
        self.set_enlargement_mode(next_mode)

    def set_enlargement_mode(self, mode):
        """Ajuste la disposition pour différents agrandissements.
        - normal: position initiale
        - large: réduire panneau droit
        - video_only: cacher quasi totalement le panneau droit
        """
        if not hasattr(self, 'saved_paned_position'):
            # sauvegarder position actuelle
            try:
                self.saved_paned_position = self.paned_window.sashpos(0)
            except Exception:
                self.saved_paned_position = None
        self.enlarge_mode = mode
        try:
            width = self.root.winfo_width()
            if mode == 'normal' and self.saved_paned_position is not None:
                self.paned_window.sashpos(0, self.saved_paned_position)
            elif mode == 'large':
                self.paned_window.sashpos(0, int(width * 0.78))
            elif mode == 'video_only':
                self.paned_window.sashpos(0, width - 10)
        except Exception:
            pass
    
    # Alias pour compatibilité
    def exit_fullscreen(self):
        self.exit_maximized_video()
    
    def toggle_detach_video(self):
        """Bascule entre fenêtre vidéo détachée et attachée"""
        # Détachement désactivé : no-op
        self._log("toggle_detach_video called but detachment is disabled -> no-op")
        return
    
    def detach_video_window(self):
        """Détache la fenêtre vidéo dans une fenêtre séparée (désactivé)."""
        self._log("detach_video_window called but detachment is disabled -> no-op")
        try:
            if getattr(self, "detached_video_win", None) is not None:
                self.detached_video_win.destroy()
        except Exception:
            pass
        self.detached_video_win = None

    def reattach_video_window(self):
        """Réattache la fenêtre vidéo si détachée (désactivé)."""
        self._log("reattach_video_window called (cleanup only, detachment disabled)")
        try:
            if getattr(self, "detached_video_win", None) is not None:
                self.detached_video_win.destroy()
        except Exception:
            pass
        self.detached_video_win = None
        try:
            if hasattr(self, 'vlc_frame') and hasattr(self, 'vlc_frame_original_parent') and self.vlc_frame_original_parent:
                self.vlc_frame.pack_forget()
                self.vlc_frame.master = self.vlc_frame_original_parent
                self.vlc_frame.pack(fill="both", expand=True)
        except Exception:
            pass
        if hasattr(self, 'detach_btn'):
            try:
                self.detach_btn.config(text="📎 Vidéo attachée", state="disabled")
            except Exception:
                pass
    
    def skip_forward(self, seconds=2):
        """Avance de X secondes (sans pause)"""
        if self.video_player.video_loaded:
            self.video_player.forward(seconds)
    
    def skip_backward(self, seconds=2):
        """Recule de X secondes (sans pause)"""
        if self.video_player.video_loaded:
            self.video_player.rewind(seconds)

    def _on_enter_annotation_shortcut(self, _event=None):
        """Raccourci Entrée robuste: évite les déclenchements parasites."""
        if not self._should_process_main_shortcuts(_event):
            return

        now = time.monotonic()
        if (now - self._last_enter_shortcut_ts) < 0.20:
            return "break"
        self._last_enter_shortcut_ts = now
        self.show_annotation_menu()
        return "break"

    def _apply_keyboard_focus_policy(self):
        """Désactive le focus des boutons de la fenêtre principale pour fiabiliser Entrée/Espace."""
        try:
            if not self.root or not self.root.winfo_exists():
                return
        except Exception:
            return

        def _visit(widget):
            for child in widget.winfo_children():
                try:
                    widget_class = str(child.winfo_class())
                    if widget_class in {"Button", "TButton"}:
                        try:
                            child.configure(takefocus=0)
                        except Exception:
                            pass
                        # Le bind widget est prioritaire sur les binds de classe Button.
                        child.bind("<KeyPress-space>", self._on_space_play_pause)
                        child.bind("<KeyPress-Return>", self._on_enter_annotation_shortcut)
                except Exception:
                    pass
                _visit(child)

        try:
            _visit(self.root)
        except Exception:
            pass

        try:
            self.root.focus_set()
        except Exception:
            pass

    def _register_ai_button(self, button_widget):
        """Conserve les boutons IA pour pouvoir les masquer/afficher sans suppression."""
        self._ai_buttons.append(button_widget)
        return button_widget

    def _apply_ai_buttons_visibility(self):
        """Masque/affiche les contrôles IA selon la configuration."""
        for btn in getattr(self, "_ai_buttons", []):
            try:
                if self.show_ai_controls:
                    if not btn.winfo_manager():
                        btn.pack(pady=(0, 12), padx=20, fill="x")
                else:
                    btn.pack_forget()
            except Exception:
                pass

    
    def show_annotation_menu(self):
        """Affiche menu contextuel avec navigation clavier (Entrée)"""
        if not self.video_player.video_loaded:
            return
        
        # Pause si en lecture
        if self.playing:
            self.toggle_play_pause()
        
        # Créer menu contextuel
        menu = tk.Toplevel(self.root)
        menu.overrideredirect(True)
        menu.attributes('-topmost', True)
        menu.grab_set()
        
        # Positionner au centre
        w, h = 480, 580
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        menu.geometry(f"{w}x{h}+{x}+{y}")

        # --- Palette (thème clair si ttkbootstrap est actif) ---
        # Objectif: éviter un menu dark hardcodé quand l'app est en thème light.
        bg = "#ffffff"
        fg = "#111827"
        fg_muted = "#6b7280"
        panel = "#f3f4f6"
        highlight = "#2563eb"

        try:
            import ttkbootstrap as tb  # noqa: F401
            try:
                style = tb.Style()
                colors = style.colors
                bg = colors.bg
                fg = colors.fg
                panel = colors.light
                highlight = colors.primary
                fg_muted = colors.secondary
            except Exception:
                pass
        except Exception:
            pass

        menu.configure(bg=bg)
        
        # Container principal pour tout le contenu
        main_container = tk.Frame(menu, bg=bg)
        main_container.pack(fill="both", expand=True)
        
        # Titre
        title_label = tk.Label(
            main_container,
            text="📝 Menu d'annotation",
            font=("Segoe UI", 18, "bold"),
            bg=bg,
            fg=fg,
        )
        title_label.pack(pady=25)
        
        # Frame pour le contenu changeant
        content_frame = tk.Frame(main_container, bg=bg)
        content_frame.pack(fill="both", expand=True)
        
        # Variables pour stocker l'état
        state = {
            'step': 'action',  # 'action', 'player', 'confirmation'
            'selected_action': None,
            'selected_player': None,
            'result': {}
        }
        
        # Liste des options d'actions
        actions = [
            ("1", "âš ï¸ Faute Directe", "faute_directe", "#ef4444"),
            ("2", "🏆 Point Gagnant", "point_gagnant", "#22c55e"),
            ("3", "🎯 Faute Provoquée", "faute_provoquee", "#f59e0b"),
            ("4", "💪 Coup de Cœur - Défense", "coup_coeur_defense", "#a855f7"),
            ("5", "⚡ Coup de Cœur - Attaque", "coup_coeur_attaque", "#0ea5e9"),
            ("6", "✨ Coup de Cœur - Spectaculaire", "coup_coeur_spectaculaire", "#14b8a6"),
        ]
        
        selected_idx = [0]
        
        def clear_content():
            """Efface le contenu actuel"""
            for widget in content_frame.winfo_children():
                widget.destroy()
        
        def safe_destroy_menu():
            """Détruit le menu en nettoyant les événements"""
            try:
                # Unbind tous les événements clavier
                menu.unbind('<Key>')
                menu.unbind('<Escape>')
                menu.unbind('<Return>')
                menu.unbind('<Up>')
                menu.unbind('<Down>')
            except:
                pass
            finally:
                menu.destroy()
        
        def show_confirmation(message):
            """Affiche la confirmation dans le même menu"""
            clear_content()
            title_label.config(text="✓ Confirmation")
            
            tk.Label(
                content_frame,
                text=message,
                font=("Segoe UI", 14, "bold"),
                bg=bg,
                fg=highlight,
                wraplength=400,
            ).pack(pady=40)
            
            tk.Label(
                content_frame,
                text="Enregistré avec succès !",
                font=("Segoe UI", 12),
                bg=bg,
                fg=fg_muted,
            ).pack(pady=10)
            
            # Auto-fermeture après 1.5 secondes
            menu.after(1500, safe_destroy_menu)
        
        def process_annotation():
            """Traite l'annotation avec les données collectées"""
            action_type = state['selected_action']
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            # Ne plus capturer les frames ici - génération différée
            # Les captures seront générées lors de l'export HTML
            
            # Traiter selon le type
            if action_type == "faute_directe":
                type_coup = state['result'].get('type_coup')
                self.annotation_manager.add_faute_directe(
                    state['result']['joueur'],
                    timestamp, frame,
                    type_coup,
                    None  # capture_path sera None, généré plus tard si nécessaire
                )
                show_confirmation("âš ï¸ Faute Directe")
                
            elif action_type == "point_gagnant":
                type_coup = state['result'].get('type_coup', 'fond_de_court')
                self.annotation_manager.add_point_gagnant(
                    state['result']['joueur'],
                    timestamp, frame, type_coup,
                    None  # capture_path sera None, généré plus tard si nécessaire
                )
                show_confirmation("🏆 Point Gagnant")
                
            elif action_type == "faute_provoquee":
                type_coup_att = state['result'].get('type_coup_attaquant')
                type_coup_def = state['result'].get('type_coup_defenseur')
                self.annotation_manager.add_faute_provoquee(
                    state['result']['attaquant'],
                    state['result']['defenseur'],
                    timestamp, frame,
                    type_coup_att,
                    type_coup_def,
                    None  # capture_path sera None, généré plus tard si nécessaire
                )
                show_confirmation("🎯 Faute Provoquée")
                
            elif action_type.startswith("coup_coeur"):
                # Coup de cœur - ajouter comme annotation spéciale
                type_coeur = action_type.replace("coup_coeur_", "")
                self.annotation_manager.add_coup_de_coeur(
                    state['result']['joueur'],
                    type_coeur,
                    timestamp, frame,
                    None  # capture_path sera None, généré plus tard
                )
                show_confirmation(f"✨ Coup de Cœur - {type_coeur.capitalize()}")
            
            self._update_stats()
        
        def show_player_selection():
            """Affiche la sélection des joueurs"""
            clear_content()
            action_type = state['selected_action']
            
            # Titre selon l'action
            if action_type == "faute_directe":
                title_label.config(text="âš ï¸ Faute Directe - Joueur")
                tk.Label(content_frame, text="Qui a fait la faute ?",
                        font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)
                
            elif action_type == "point_gagnant":
                title_label.config(text="🏆 Point Gagnant - Joueur")
                tk.Label(content_frame, text="Qui a marqué le point ?",
                        font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)
                
            elif action_type == "faute_provoquee":
                if 'attaquant' not in state['result']:
                    title_label.config(text="🎯 Faute Provoquée - Attaquant")
                    tk.Label(content_frame, text="Qui a provoqué la faute ?",
                            font=("Segoe UI", 13, "bold"),
                            bg=bg, fg=fg).pack(pady=20)
                else:
                    title_label.config(text="🎯 Faute Provoquée - Défenseur")
                    tk.Label(content_frame, text="Qui a fait la faute ?",
                            font=("Segoe UI", 13, "bold"),
                            bg=bg, fg=fg).pack(pady=20)
                
            elif action_type.startswith("coup_coeur"):
                title_label.config(text="✨ Coup de Cœur - Joueur")
                tk.Label(content_frame, text="Quel joueur ?",
                        font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)
            
            player_labels = []
            
            # Afficher les joueurs
            for i, player in enumerate(self.players):
                player_name = player if isinstance(player, str) else player.get('nom', f'Joueur {i+1}')
                
                lbl = tk.Label(content_frame, text=f"[{i+1}] {player_name}",
                              font=("Segoe UI", 12, "bold"),
                              bg=highlight if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=20, pady=12, cursor="hand2")
                lbl.pack(pady=5, padx=20, fill="x")
                player_labels.append((lbl, player_name))
            
            selected_idx[0] = 0
            
            def on_player_key(e):
                # Navigation avec flèches + chiffres + Entrée
                nonlocal player_labels
                if e.keysym in ("Up", "Down"):
                    # mettre à jour l'index
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(player_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(player_labels)
                    # rafraîchir styles
                    for i, (lbl, _) in enumerate(player_labels):
                        lbl.configure(bg=panel, fg=fg)
                    player_labels[selected_idx[0]][0].configure(bg=highlight, fg="#ffffff")
                    return
                if e.keysym == "Return":
                    player_name = player_labels[selected_idx[0]][1]
                    
                    if action_type == "faute_provoquee":
                        # Pour faute provoquée: 2 joueurs + 2 types de coup (attaquant puis défenseur)
                        if 'attaquant' not in state['result']:
                            state['result']['attaquant'] = player_name
                            show_coup_type_selection_faute_provoquee(role="attaquant")
                        else:
                            state['result']['defenseur'] = player_name
                            show_coup_type_selection_faute_provoquee(role="defenseur")
                    else:
                        state['result']['joueur'] = player_name
                        
                        # Si point gagnant ou faute directe, demander le type de coup
                        if action_type in ["point_gagnant", "faute_directe"]:
                            show_coup_type_selection()
                        else:
                            process_annotation()
                    
                elif e.char.isdigit():
                    idx = int(e.char) - 1
                    if 0 <= idx < len(player_labels):
                        player_name = player_labels[idx][1]
                        
                        if action_type == "faute_provoquee":
                            if 'attaquant' not in state['result']:
                                state['result']['attaquant'] = player_name
                                show_coup_type_selection_faute_provoquee(role="attaquant")
                            else:
                                state['result']['defenseur'] = player_name
                                show_coup_type_selection_faute_provoquee(role="defenseur")
                        else:
                            state['result']['joueur'] = player_name
                            
                            if action_type in ["point_gagnant", "faute_directe"]:
                                show_coup_type_selection()
                            else:
                                process_annotation()
            
            # Click handlers
            for i, (lbl, player_name) in enumerate(player_labels):
                def make_click(pname):
                    def handler(e):
                        if action_type == "faute_provoquee":
                            if 'attaquant' not in state['result']:
                                state['result']['attaquant'] = pname
                                show_coup_type_selection_faute_provoquee(role="attaquant")
                            else:
                                state['result']['defenseur'] = pname
                                show_coup_type_selection_faute_provoquee(role="defenseur")
                        else:
                            state['result']['joueur'] = pname
                            if action_type in ["point_gagnant", "faute_directe"]:
                                show_coup_type_selection()
                            else:
                                process_annotation()
                    return handler
                lbl.bind("<Button-1>", make_click(player_name))
            
            # Instructions
                tk.Label(content_frame, text="↓↑ Navigation | Entrée Valider | Echap Annuler",
                    font=("Segoe UI", 9, "bold"),
                    bg=bg, fg=fg_muted).pack(pady=15)
            
            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_player_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())
        
        def show_coup_type_selection():
            """Affiche la sélection du type de coup pour point gagnant"""
            clear_content()
            title_label.config(text="🏆 Type de coup")
            
            tk.Label(content_frame, text="Quel type de coup ?",
                    font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)
            
            coup_types = [
                ("1", "Service", "service"),
                ("2", "Volée coup droit", "volee_coup_droit"),
                ("3", "Volée revers", "volee_revers"),
                ("4", "Volée balle haute", "volee_balle_haute"),
                ("5", "Fond de court coup droit", "fond_de_court_coup_droit"),
                ("6", "Fond de court revers", "fond_de_court_revers"),
                ("7", "Fond de court balle haute", "fond_de_court_balle_haute"),
                ("8", "Balle Haute", "balle_haute"),
                ("9", "Amorti", "amorti"),
                ("A", "Autre", "autre"),
            ]
            
            type_labels = []
            
            for i, (key, text, value) in enumerate(coup_types):
                lbl = tk.Label(content_frame, text=f"[{key}] {text}",
                              font=("Segoe UI", 11, "bold"),
                              bg=highlight if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=15, pady=10, cursor="hand2")
                lbl.pack(pady=4, padx=20, fill="x")
                type_labels.append((lbl, value))
            
            selected_idx[0] = 0
            
            def on_type_key(e):
                # Navigation avec flèches + chiffres + Entrée
                nonlocal type_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(type_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(type_labels)
                    for i, (lbl, _) in enumerate(type_labels):
                        lbl.configure(bg=panel, fg=fg)
                    type_labels[selected_idx[0]][0].configure(bg=highlight, fg="#ffffff")
                    return
                if e.keysym == "Return":
                    val = type_labels[selected_idx[0]][1]
                    if val == "balle_haute":
                        show_balle_haute_subselection()
                    else:
                        state['result']['type_coup'] = val
                        process_annotation()
                    
                elif e.char in "123456789":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(type_labels):
                        val = type_labels[idx][1]
                        if val == "balle_haute":
                            show_balle_haute_subselection()
                        else:
                            state['result']['type_coup'] = val
                            process_annotation()
                elif e.char.lower() == 'a':
                    # Autre est le 10ème (index 9)
                    state['result']['type_coup'] = type_labels[9][1]
                    process_annotation()
            
            # Click handlers
            for lbl, value in type_labels:
                def make_click(v):
                    def handler(e):
                        if v == "balle_haute":
                            show_balle_haute_subselection()
                        else:
                            state['result']['type_coup'] = v
                            process_annotation()
                    return handler
                lbl.bind("<Button-1>", make_click(value))
            
            tk.Label(content_frame, text="↓↑ Navigation | Entrée Valider | Echap Annuler",
                    font=("Segoe UI", 9, "bold"),
                    bg=bg, fg=fg_muted).pack(pady=15)
            
            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_type_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())

        def show_balle_haute_subselection():
            """Affiche la sélection du coup final pour balle haute"""
            clear_content()
            title_label.config(text="⬆️ Balle Haute")
            
            tk.Label(content_frame, text="Quel type de balle haute ?",
                    font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)
            
            bh_types = [
                ("1", "Smash à plat", "smash"),
                ("2", "Víbora", "vibora"),
                ("3", "Bandeja", "bandeja"),
            ]
            
            bh_labels = []
            for i, (key, text, value) in enumerate(bh_types):
                lbl = tk.Label(content_frame, text=f"[{key}] {text}",
                              font=("Segoe UI", 11, "bold"),
                              bg=highlight if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=15, pady=10, cursor="hand2")
                lbl.pack(pady=4, padx=20, fill="x")
                bh_labels.append((lbl, value))
            
            selected_idx[0] = 0
            
            def on_bh_key(e):
                nonlocal bh_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(bh_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(bh_labels)
                    for i, (lbl, _) in enumerate(bh_labels):
                        lbl.configure(bg=panel, fg=fg)
                    bh_labels[selected_idx[0]][0].configure(bg=highlight, fg="#ffffff")
                    return
                if e.keysym == "Return":
                    state['result']['type_coup'] = bh_labels[selected_idx[0]][1]
                    process_annotation()
                elif e.char in "123":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(bh_labels):
                        state['result']['type_coup'] = bh_labels[idx][1]
                        process_annotation()
                elif e.keysym == "BackSpace":
                    show_coup_type_selection()
            
            # Click handlers
            for lbl, value in bh_labels:
                def make_click(v):
                    def handler(e):
                        state['result']['type_coup'] = v
                        process_annotation()
                    return handler
                lbl.bind("<Button-1>", make_click(value))
            
            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_bh_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())

        def show_coup_type_selection_faute_provoquee(role: str):
            """Sélection du type de coup pour la faute provoquée (attaquant puis défenseur)."""
            clear_content()

            if role == "attaquant":
                title_label.config(text="🎯 Faute Provoquée - Coup attaquant")
                target_key = "type_coup_attaquant"
                next_step = "defenseur"
            else:
                title_label.config(text="🎯 Faute Provoquée - Coup défenseur")
                target_key = "type_coup_defenseur"
                next_step = None

            tk.Label(content_frame, text="Quel type de coup ?",
                    font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)

            coup_types = [
                ("1", "Service", "service"),
                ("2", "Volée coup droit", "volee_coup_droit"),
                ("3", "Volée revers", "volee_revers"),
                ("4", "Volée balle haute", "volee_balle_haute"),
                ("5", "Fond de court coup droit", "fond_de_court_coup_droit"),
                ("6", "Fond de court revers", "fond_de_court_revers"),
                ("7", "Fond de court balle haute", "fond_de_court_balle_haute"),
                ("8", "Balle Haute", "balle_haute"),
                ("9", "Amorti", "amorti"),
                ("A", "Autre", "autre"),
            ]

            type_labels = []
            for i, (key, text, value) in enumerate(coup_types):
                lbl = tk.Label(content_frame, text=f"[{key}] {text}",
                              font=("Segoe UI", 11, "bold"),
                              bg=highlight if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=15, pady=10, cursor="hand2")
                lbl.pack(pady=4, padx=20, fill="x")
                type_labels.append((lbl, value))

            selected_idx[0] = 0

            def _finalize_selection(val: str):
                if val == "balle_haute":
                    show_balle_haute_subselection_faute_provoquee(target_key, next_step)
                    return
                state['result'][target_key] = val
                if next_step == "defenseur":
                    show_player_selection()
                else:
                    process_annotation()

            def on_type_key(e):
                nonlocal type_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(type_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(type_labels)
                    for i, (lbl, _) in enumerate(type_labels):
                        lbl.configure(bg=panel, fg=fg)
                    type_labels[selected_idx[0]][0].configure(bg=highlight, fg="#ffffff")
                    return
                if e.keysym == "Return":
                    _finalize_selection(type_labels[selected_idx[0]][1])
                elif e.char in "123456789":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(type_labels):
                        _finalize_selection(type_labels[idx][1])
                elif e.char.lower() == 'a':
                    _finalize_selection(type_labels[9][1])
                elif e.keysym == "BackSpace":
                    show_player_selection()

            for lbl, value in type_labels:
                def make_click(v):
                    def handler(e):
                        _finalize_selection(v)
                    return handler
                lbl.bind("<Button-1>", make_click(value))

            tk.Label(content_frame, text="↓↑ Navigation | Entrée Valider | Echap Annuler",
                    font=("Segoe UI", 9, "bold"),
                    bg=bg, fg=fg_muted).pack(pady=15)

            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_type_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())

        def show_balle_haute_subselection_faute_provoquee(target_key: str, next_step: str | None):
            """Sous-sélection pour Balle Haute dans le flux faute provoquée."""
            clear_content()
            title_label.config(text="⬆️ Balle Haute")

            tk.Label(content_frame, text="Quel type de balle haute ?",
                    font=("Segoe UI", 13, "bold"),
                    bg=bg, fg=fg).pack(pady=20)

            bh_types = [
                ("1", "Smash à plat", "smash"),
                ("2", "Víbora", "vibora"),
                ("3", "Bandeja", "bandeja"),
            ]

            bh_labels = []
            for i, (key, text, value) in enumerate(bh_types):
                lbl = tk.Label(content_frame, text=f"[{key}] {text}",
                              font=("Segoe UI", 11, "bold"),
                              bg=highlight if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=15, pady=10, cursor="hand2")
                lbl.pack(pady=4, padx=20, fill="x")
                bh_labels.append((lbl, value))

            selected_idx[0] = 0

            def _finalize_bh(val: str):
                state['result'][target_key] = val
                if next_step == "defenseur":
                    show_player_selection()
                else:
                    process_annotation()

            def on_bh_key(e):
                nonlocal bh_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(bh_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(bh_labels)
                    for i, (lbl, _) in enumerate(bh_labels):
                        lbl.configure(bg=panel, fg=fg)
                    bh_labels[selected_idx[0]][0].configure(bg=highlight, fg="#ffffff")
                    return
                if e.keysym == "Return":
                    _finalize_bh(bh_labels[selected_idx[0]][1])
                elif e.char in "123":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(bh_labels):
                        _finalize_bh(bh_labels[idx][1])
                elif e.keysym == "BackSpace":
                    show_coup_type_selection_faute_provoquee(role="attaquant" if next_step == "defenseur" else "defenseur")

            for lbl, value in bh_labels:
                def make_click(v):
                    def handler(e):
                        _finalize_bh(v)
                    return handler
                lbl.bind("<Button-1>", make_click(value))

            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_bh_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())
        
        def show_technique_selection():
            """Affiche la sélection de la technique (coup droit/revers/balle haute)"""
            clear_content()
            action_type = state['selected_action']
            
            # Titre selon l'action
            if action_type == "faute_directe":
                title_label.config(text="âš ï¸ Faute Directe - Technique")
                tk.Label(content_frame, text="Quelle technique ?",
                        font=("Segoe UI", 13, "bold"),
                        bg="#2a2a3e", fg="#ffffff").pack(pady=20)
            elif action_type == "point_gagnant":
                title_label.config(text="🏆 Point Gagnant - Technique")
                tk.Label(content_frame, text="Quelle technique ?",
                        font=("Segoe UI", 13, "bold"),
                        bg="#2a2a3e", fg="#ffffff").pack(pady=20)
            
            # Options de technique
            technique_options = [
                ("🎾 Coup droit", "coup_droit"),
                ("🔄 Revers", "revers"),
                ("🎯 Balle haute", "balle_haute")
            ]
            
            technique_labels = []
            for i, (label, value) in enumerate(technique_options):
                lbl = tk.Label(content_frame, text=f"[{i+1}] {label}",
                              font=("Segoe UI", 12, "bold"),
                              bg="#51cf66" if i == 0 else "#3a3a4e",
                              fg="white" if i == 0 else "#aaaaaa",
                              padx=20, pady=12, cursor="hand2")
                lbl.pack(pady=5, padx=20, fill="x")
                technique_labels.append((lbl, value))
            
            selected_idx[0] = 0
            
            def on_technique_key(e):
                nonlocal technique_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(technique_labels)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(technique_labels)
                    for i, (lbl, _) in enumerate(technique_labels):
                        lbl.configure(bg="#3a3a4e", fg="#aaaaaa")
                    technique_labels[selected_idx[0]][0].configure(bg="#51cf66", fg="#ffffff")
                    return
                if e.keysym == "Return":
                    state['result']['technique'] = technique_labels[selected_idx[0]][1]
                    process_annotation()
                    
                elif e.char in "123":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(technique_labels):
                        state['result']['technique'] = technique_labels[idx][1]
                        process_annotation()
            
            # Click handlers
            for lbl, value in technique_labels:
                def make_click(v):
                    def handler(e):
                        state['result']['technique'] = v
                        process_annotation()
                    return handler
                lbl.bind("<Button-1>", make_click(value))
            
            tk.Label(content_frame, text="↓↑ Navigation | Entrée Valider | Echap Annuler",
                    font=("Segoe UI", 9, "bold"),
                    bg="#2a2a3e", fg="#888888").pack(pady=15)
            
            menu.unbind("<KeyPress>")
            menu.bind("<KeyPress>", on_technique_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())
        
        def show_actions():
            """Affiche les options d'actions"""
            option_labels = []
            
            for i, (key, text, action_type, color) in enumerate(actions):
                lbl = tk.Label(content_frame, text=f"[{key}] {text}",
                              font=("Segoe UI", 13, "bold"),
                              bg=color if i == 0 else panel,
                              fg="white" if i == 0 else fg,
                              padx=20, pady=15, cursor="hand2")
                lbl.pack(pady=8, padx=20, fill="x")
                option_labels.append(lbl)
                
                # Click handler
                def make_handler(atype):
                    def handler(e):
                        state['selected_action'] = atype
                        show_player_selection()
                    return handler
                lbl.bind("<Button-1>", make_handler(action_type))
            
            # Instructions
            tk.Label(content_frame, text="↓↑ Navigation | Entrée Valider | Echap Annuler",
                    font=("Segoe UI", 10, "bold"),
                    bg=bg, fg=fg_muted).pack(pady=20)
            
            # Navigation clavier
            def on_action_key(e):
                # Navigation avec flèches + chiffres + Entrée
                nonlocal option_labels
                if e.keysym in ("Up", "Down"):
                    if e.keysym == "Up":
                        selected_idx[0] = (selected_idx[0] - 1) % len(actions)
                    else:
                        selected_idx[0] = (selected_idx[0] + 1) % len(actions)
                    for i, lbl in enumerate(option_labels):
                        lbl.configure(bg=panel, fg=fg)
                    option_labels[selected_idx[0]].configure(bg=actions[selected_idx[0]][3], fg="#ffffff")
                    return
                if e.keysym == "Return":
                    _, _, action_type, _ = actions[selected_idx[0]]
                    state['selected_action'] = action_type
                    show_player_selection()
                    
                elif e.char in "123456":
                    idx = int(e.char) - 1
                    if 0 <= idx < len(actions):
                        _, _, action_type, _ = actions[idx]
                        state['selected_action'] = action_type
                        show_player_selection()
            
            menu.bind("<KeyPress>", on_action_key)
            menu.bind("<Escape>", lambda e: safe_destroy_menu())
        
        # Afficher les actions au démarrage
        show_actions()
        menu.focus_set()
    
    def pause_and_annotate(self):
        """Met en pause et affiche le menu d'annotation au centre"""
        if not self.video_player.video_loaded:
            return
        
        # Pause la vidéo
        if self.playing:
            self.toggle_play_pause()
        
        # Afficher le pop-up de choix d'annotation au centre
        self._show_annotation_menu()
    
    def _show_annotation_menu(self):
        """Affiche le menu de sélection d'annotation au centre"""
        # Créer un overlay transparent
        overlay = tk.Toplevel(self.root)
        overlay.overrideredirect(True)
        overlay.attributes('-topmost', True)
        overlay.attributes('-alpha', 0.95)
        overlay.grab_set()  # Capturer le focus clavier
        
        # Centrer sur l'écran
        window_width = 450
        window_height = 350
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        overlay.geometry(f"{window_width}x{window_height}+{x}+{y}")
        overlay.configure(bg="#1a1a2e")
        
        # Titre
        title = tk.Label(overlay, text="Type d'action",
                        font=("Segoe UI", 18, "bold"),
                        bg="#1a1a2e", fg="#ffffff")
        title.pack(pady=30)
        
        # Instructions clavier
        instructions = tk.Label(overlay,
                               text="Utilisez les touches du clavier :",
                               font=("Segoe UI", 10),
                               bg="#1a1a2e", fg="#aaaaaa")
        instructions.pack(pady=(0, 15))
        
        # Boutons d'action avec raccourcis
        btn_frame = tk.Frame(overlay, bg="#1a1a2e")
        btn_frame.pack(expand=True)
        
        # Faute directe
        tk.Label(btn_frame, text="[F] âš ï¸ Faute Directe",
                font=("Segoe UI", 14, "bold"), bg="#ff6b6b", fg="white",
                padx=30, pady=15).pack(pady=8, fill="x")
        
        # Point gagnant
        tk.Label(btn_frame, text="[P] 🏆 Point Gagnant",
                font=("Segoe UI", 14, "bold"), bg="#51cf66", fg="white",
                padx=30, pady=15).pack(pady=8, fill="x")
        
        # Faute provoquée
        tk.Label(btn_frame, text="[E] 🎯 Faute Provoquée",
                font=("Segoe UI", 14, "bold"), bg="#ffd43b", fg="#333",
                padx=30, pady=15).pack(pady=8, fill="x")
        
        # Annuler
        cancel_label = tk.Label(btn_frame, text="[Echap] ✕ Annuler",
                               font=("Segoe UI", 11), bg="#555555",
                               fg="white", padx=20, pady=10)
        cancel_label.pack(pady=15)
        
        # Bindings clavier pour le menu
        def on_key(event):
            key = event.char.lower()
            if key == 'f':
                self._quick_annotate(overlay, "faute_directe")
            elif key == 'p':
                self._quick_annotate(overlay, "point_gagnant")
            elif key == 'e':
                self._quick_annotate(overlay, "faute_provoquee")
        
        overlay.bind('<KeyPress>', on_key)
        overlay.bind('<Escape>', lambda e: overlay.destroy())
        overlay.focus_set()
    
    def _quick_annotate(self, menu_window, annotation_type):
        """Annotation rapide depuis le menu"""
        menu_window.destroy()
        
        # Afficher le formulaire au centre
        self._show_annotation_form(annotation_type)
    
    def _show_annotation_form(self, annotation_type):
        """Affiche le formulaire d'annotation au centre avec navigation clavier"""
        # IMPORTANT : Capturer timestamp et frame ICI (au moment de l'action)
        # Pas au moment de la validation pour avoir timestamps chronologiques précis
        captured_timestamp = self.video_player.get_current_timestamp()
        captured_frame = self.video_player.current_frame
        
        form = tk.Toplevel(self.root)
        form.overrideredirect(True)
        form.attributes('-topmost', True)
        form.attributes('-alpha', 0.95)
        form.grab_set()
        
        # Taille selon le type
        if annotation_type == "point_gagnant":
            window_width = 500
            window_height = 520
        elif annotation_type == "faute_provoquee":
            window_width = 500
            window_height = 400
        else:
            window_width = 450
            window_height = 320
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        form.geometry(f"{window_width}x{window_height}+{x}+{y}")
        form.configure(bg="#1a1a2e")
        
        # Titres
        titles = {
            "faute_directe": "âš ï¸ Faute Directe",
            "point_gagnant": "🏆 Point Gagnant",
            "faute_provoquee": "🎯 Faute Provoquée"
        }
        
        title = tk.Label(form, text=titles.get(annotation_type, ""),
                        font=("Segoe UI", 18, "bold"),
                        bg="#1a1a2e", fg="#ffffff")
        title.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(form,
                               text="Utilisez 1-2-3-4 puis [Entrée] pour valider",
                               font=("Segoe UI", 10),
                               bg="#1a1a2e", fg="#aaaaaa")
        instructions.pack(pady=(0, 10))
        
        content = tk.Frame(form, bg="#1a1a2e")
        content.pack(pady=10, padx=30, fill="both", expand=True)
        
        # Variables pour stocker les choix + timestamp/frame capturés
        result_data = {
            'selected_player_idx': 0,
            'captured_timestamp': captured_timestamp,
            'captured_frame': captured_frame
        }
        
        if annotation_type in ["faute_directe", "point_gagnant"]:
            # Sélection joueur avec numéros
            tk.Label(content, text="Sélectionnez le joueur :",
                    font=("Segoe UI", 12, "bold"),
                    bg="#1a1a2e", fg="#ffffff").pack(anchor="w", pady=10)
            
            player_labels = []
            for i, player in enumerate(self.players):
                lbl = tk.Label(content,
                              text=f"[{i+1}] {player}",
                              font=("Segoe UI", 12),
                              bg="#2a2a3e", fg="#aaaaaa",
                              padx=20, pady=12, anchor="w")
                lbl.pack(fill="x", pady=3)
                player_labels.append(lbl)
            
            # Highlight le premier par défaut
            player_labels[0].configure(bg="#667eea", fg="#ffffff")
            
            result_data['player_labels'] = player_labels
            
            # Si point gagnant, ajouter type de coup
            if annotation_type == "point_gagnant":
                tk.Label(content, text="Type de coup :",
                        font=("Segoe UI", 12, "bold"),
                        bg="#1a1a2e", fg="#ffffff").pack(anchor="w",
                                                         pady=(20, 10))
                
                result_data['selected_coup_idx'] = 0
                result_data['coups'] = [
                    ("🎾 Service", "service"),
                    ("🎾 Volée coup droit", "volee_coup_droit"),
                    ("🎾 Volée revers", "volee_revers"),
                    ("🎾 Volée balle haute", "volee_balle_haute"),
                    ("⚡ Fond de court coup droit", "fond_de_court_coup_droit"),
                    ("⚡ Fond de court revers", "fond_de_court_revers"),
                    ("⚡ Fond de court balle haute", "fond_de_court_balle_haute"),
                    ("💥 Balle Haute", "balle_haute"),
                    ("ï¿½ Lobe", "lobe"),
                    ("�🎯 Amorti", "amorti"),
                    ("➕ Autre", "autre")
                ]
                
                coup_labels = []
                for i, (label, value) in enumerate(result_data['coups']):
                    lbl = tk.Label(content, text=f"[{i+1}] {label}",
                                  font=("Segoe UI", 11),
                                  bg="#2a2a3e", fg="#aaaaaa",
                                  padx=15, pady=8, anchor="w")
                    lbl.pack(fill="x", pady=2)
                    coup_labels.append(lbl)
                
                coup_labels[0].configure(bg="#51cf66", fg="#ffffff")
                result_data['coup_labels'] = coup_labels
        
        else:  # faute_provoquee
            result_data['selected_attaquant_idx'] = 0
            result_data['selected_defenseur_idx'] = 1 if len(self.players) > 1 else 0
            result_data['mode'] = 'attaquant'
            
            # Attaquant
            tk.Label(content, text="Attaquant (1-2-3-4) :",
                    font=("Segoe UI", 12, "bold"),
                    bg="#1a1a2e", fg="#ffffff").pack(anchor="w", pady=5)
            
            attaquant_labels = []
            for i, player in enumerate(self.players):
                lbl = tk.Label(content, text=f"[{i+1}] {player}",
                              font=("Segoe UI", 11),
                              bg="#2a2a3e", fg="#aaaaaa",
                              padx=15, pady=10, anchor="w")
                lbl.pack(fill="x", pady=2)
                attaquant_labels.append(lbl)
            
            attaquant_labels[0].configure(bg="#667eea", fg="#ffffff")
            result_data['attaquant_labels'] = attaquant_labels
            
            # Défenseur
            tk.Label(content, text="Défenseur/Fautif (1-2-3-4) :",
                    font=("Segoe UI", 12, "bold"),
                    bg="#1a1a2e", fg="#ffffff").pack(anchor="w",
                                                     pady=(15, 5))
            
            defenseur_labels = []
            for i, player in enumerate(self.players):
                lbl = tk.Label(content, text=f"[{i+1}] {player}",
                              font=("Segoe UI", 11),
                              bg="#2a2a3e", fg="#aaaaaa",
                              padx=15, pady=10, anchor="w")
                lbl.pack(fill="x", pady=2)
                defenseur_labels.append(lbl)
            
            if len(self.players) > 1:
                defenseur_labels[1].configure(bg="#ffd43b", fg="#333333")
            result_data['defenseur_labels'] = defenseur_labels
        
        # Footer avec instructions
        footer = tk.Label(form,
                         text="[Entrée] Valider  |  [Echap] Annuler",
                         font=("Segoe UI", 11, "bold"),
                         bg="#667eea", fg="#ffffff", pady=15)
        footer.pack(side="bottom", fill="x")
        
        # Gestion clavier
        def on_key(event):
            if annotation_type in ["faute_directe", "point_gagnant"]:
                if event.char and event.char in '1234':
                    idx = int(event.char) - 1
                    if idx < len(self.players):
                        # Reset tous les labels joueur
                        for lbl in result_data['player_labels']:
                            lbl.configure(bg="#2a2a3e", fg="#aaaaaa")
                        # Highlight le sélectionné
                        result_data['player_labels'][idx].configure(
                            bg="#667eea", fg="#ffffff"
                        )
                        result_data['selected_player_idx'] = idx
                
                # Pour point gagnant, chiffres pour type de coup aussi
                if annotation_type == "point_gagnant" and event.char in '1234567890':
                    if event.char == '0':
                        idx = 9  # 0 = 10ème choix
                    else:
                        idx = int(event.char) - 1
                    if idx < len(result_data['coups']):
                        for lbl in result_data['coup_labels']:
                            lbl.configure(bg="#2a2a3e", fg="#aaaaaa")
                        result_data['coup_labels'][idx].configure(
                            bg="#51cf66", fg="#ffffff"
                        )
                        result_data['selected_coup_idx'] = idx
            
            else:  # faute_provoquee
                if event.char in '1234':
                    idx = int(event.char) - 1
                    if idx < len(self.players):
                        # Mettre à jour attaquant et défenseur
                        for lbl in result_data['attaquant_labels']:
                            lbl.configure(bg="#2a2a3e", fg="#aaaaaa")
                        result_data['attaquant_labels'][idx].configure(
                            bg="#667eea", fg="#ffffff"
                        )
                        result_data['selected_attaquant_idx'] = idx
                        
                        # Auto-sélectionner défenseur différent
                        def_idx = (idx + 1) % len(self.players)
                        for lbl in result_data['defenseur_labels']:
                            lbl.configure(bg="#2a2a3e", fg="#aaaaaa")
                        result_data['defenseur_labels'][def_idx].configure(
                            bg="#ffd43b", fg="#333333"
                        )
                        result_data['selected_defenseur_idx'] = def_idx
            
            # Entrée pour valider
            if event.keysym == 'Return':
                type_coup = result_data['coups'][result_data['selected_coup_idx']][1]
                if type_coup == "balle_haute":
                    self._show_balle_haute_subselection_quick(form, result_data)
                else:
                    self._save_quick_annotation(form, annotation_type, result_data)
        
        form.bind('<KeyPress>', on_key)
        form.bind('<Escape>', lambda e: form.destroy())
        form.focus_set()
    
    def _save_quick_annotation(self, form, annotation_type, result_data):
        """Sauvegarde l'annotation sans confirmation"""
        # Utiliser le timestamp/frame capturé à l'ouverture du dialog
        timestamp = result_data.get('captured_timestamp')
        frame = result_data.get('captured_frame')
        
        # Fallback si pas capturé (ancien code)
        if timestamp is None or frame is None:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
        
        point_id = self.annotation_manager.current_point_id
        capture_folder = self.annotation_manager.get_capture_path(point_id)
        self.video_player.capture_frames_before(capture_folder, num_frames=10)
        
        if annotation_type == "faute_directe":
            joueur = self.players[result_data['selected_player_idx']]
            self.annotation_manager.add_faute_directe(
                joueur, timestamp, frame,
                None,  # type_coup non géré dans le mode rapide simplifié
                f"screens/point_{point_id:03d}"
            )
        
        elif annotation_type == "point_gagnant":
            joueur = self.players[result_data['selected_player_idx']]
            type_coup = result_data['coups'][result_data['selected_coup_idx']][1]
            self.annotation_manager.add_point_gagnant(
                joueur, timestamp, frame, type_coup,
                f"screens/point_{point_id:03d}"
            )
        
        elif annotation_type == "faute_provoquee":
            attaquant = self.players[result_data['selected_attaquant_idx']]
            defenseur = self.players[result_data['selected_defenseur_idx']]
            self.annotation_manager.add_faute_provoquee(
                attaquant, defenseur, timestamp, frame,
                None, None,  # type_coup non géré dans le mode rapide simplifié
                f"screens/point_{point_id:03d}"
            )
        
        # Mettre à jour les stats
        self._update_stats()
        
        # Mettre à jour monitoring live
        self._update_live_monitor()
        
        # Fermer le formulaire (pas de pop-up de confirmation)
        form.destroy()
        
        # Reprendre la lecture automatiquement
        if not self.playing:
            self.toggle_play_pause()

    def _show_balle_haute_subselection_quick(self, form, result_data):
        """Affiche la sous-sélection pour balle haute dans le mode rapide"""
        # Nettoyer le contenu actuel
        for widget in form.winfo_children():
            widget.destroy()
            
        title = tk.Label(form, text="💥 Balle Haute",
                        font=("Segoe UI", 18, "bold"),
                        bg="#1a1a2e", fg="#ffffff")
        title.pack(pady=20)
        
        content = tk.Frame(form, bg="#1a1a2e")
        content.pack(pady=10, padx=30, fill="both", expand=True)
        
        tk.Label(content, text="Quel type de balle haute ?",
                font=("Segoe UI", 12, "bold"),
                bg="#1a1a2e", fg="#ffffff").pack(anchor="w", pady=10)
        
        bh_types = [
            ("1", "Smash à plat", "smash"),
            ("2", "Víbora", "vibora"),
            ("3", "Bandeja", "bandeja"),
        ]
        
        bh_labels = []
        for i, (key, text, value) in enumerate(bh_types):
            lbl = tk.Label(content, text=f"[{key}] {text}",
                          font=("Segoe UI", 12),
                          bg="#2a2a3e", fg="#aaaaaa",
                          padx=20, pady=12, anchor="w")
            lbl.pack(fill="x", pady=3)
            bh_labels.append(lbl)
            
        # Highlight le premier
        bh_labels[0].configure(bg="#51cf66", fg="#ffffff")
        selected_bh_idx = [0]
        
        def on_bh_key(event):
            if event.char and event.char in '123':
                idx = int(event.char) - 1
                for lbl in bh_labels:
                    lbl.configure(bg="#2a2a3e", fg="#aaaaaa")
                bh_labels[idx].configure(bg="#51cf66", fg="#ffffff")
                selected_bh_idx[0] = idx
            
            if event.keysym == 'Return':
                # Mettre à jour le type de coup dans result_data
                final_type = bh_types[selected_bh_idx[0]][2]
                # On triche un peu en modifiant la liste des coups pour que _save_quick_annotation fonctionne
                result_data['coups'] = [("", final_type)]
                result_data['selected_coup_idx'] = 0
                self._save_quick_annotation(form, "point_gagnant", result_data)
            
            if event.keysym == 'BackSpace':
                # Retour au menu précédent (pas implémenté ici pour simplifier, on ferme juste)
                form.destroy()
                
        form.bind('<KeyPress>', on_bh_key)
    
    # === Méthodes d'annotation (anciennes, gardées pour compatibilité) ===

    def _open_builtin_player_rename_dialog(self):
        """Fallback local: renommage des joueurs sans dépendance externe."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Renommer les joueurs")
        dialog.geometry("520x340")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.COLORS['bg_main'])

        tk.Label(
            dialog,
            text="Renommer les joueurs",
            font=(self.ui_font_family, 16, "bold"),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_dark']
        ).pack(pady=(18, 8))

        tk.Label(
            dialog,
            text="Les changements sont sauvegardés automatiquement.",
            font=(self.ui_font_family, 10),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_light']
        ).pack(pady=(0, 14))

        form = tk.Frame(dialog, bg=self.COLORS['bg_main'])
        form.pack(fill="both", expand=True, padx=20)

        entries = []
        for i in range(4):
            if i < len(self.players):
                player = self.players[i]
                current_name = player if isinstance(player, str) else player.get("nom", f"Joueur {i+1}")
            else:
                current_name = f"Joueur {i+1}"

            row = tk.Frame(form, bg=self.COLORS['bg_main'])
            row.pack(fill="x", pady=6)
            tk.Label(
                row,
                text=f"Joueur {i+1}",
                width=10,
                anchor="w",
                font=(self.ui_font_family, 11, "bold"),
                bg=self.COLORS['bg_main'],
                fg=self.COLORS['text_dark']
            ).pack(side="left")
            ent = tk.Entry(
                row,
                font=(self.ui_font_family, 11),
                relief="solid",
                bd=1
            )
            ent.insert(0, str(current_name))
            ent.pack(side="left", fill="x", expand=True, padx=(8, 0))
            entries.append(ent)

        result = {"players": None}

        def _save():
            names = [e.get().strip() for e in entries]
            if any(not n for n in names):
                messagebox.showwarning("Champs vides", "Merci de renseigner les 4 noms.")
                return

            new_players = []
            for i, name in enumerate(names):
                if i < len(self.players) and isinstance(self.players[i], dict):
                    p = dict(self.players[i])
                    p["nom"] = name
                    new_players.append(p)
                else:
                    new_players.append(name)

            result["players"] = new_players
            dialog.destroy()

        btns = tk.Frame(dialog, bg=self.COLORS['bg_main'])
        btns.pack(fill="x", padx=20, pady=(8, 18))
        tk.Button(
            btns,
            text="Enregistrer",
            command=_save,
            font=(self.ui_font_family, 11, "bold"),
            bg=self.COLORS['primary'],
            fg=self.COLORS['white'],
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2"
        ).pack(side="left")
        tk.Button(
            btns,
            text="Annuler",
            command=dialog.destroy,
            font=(self.ui_font_family, 11),
            bg=self.COLORS['border'],
            fg=self.COLORS['text_dark'],
            relief="flat",
            padx=16,
            pady=8,
            cursor="hand2"
        ).pack(side="right")

        entries[0].focus_set()
        dialog.bind("<Return>", lambda _e: _save())
        dialog.bind("<Escape>", lambda _e: dialog.destroy())
        self.root.wait_window(dialog)
        return result["players"]
    
    def configure_players(self):
        """Configure les joueurs"""
        try:
            from app.ui.player_selection_dialog import PlayerSelectionDialog
            dialog = PlayerSelectionDialog(self.root, self.players)
            self.root.wait_window(dialog.top)
            updated_players = dialog.result
        except Exception:
            updated_players = self._open_builtin_player_rename_dialog()

        if updated_players:
            self.players = updated_players
            self.annotation_manager.set_players(self.players)
            self._save_players_config()
            self.annotation_manager.autosave()
            
            # Mettre à jour le parser vocal
            if self.command_parser:
                player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                self.command_parser.set_joueurs(player_names)
            
            messagebox.showinfo("Succès", "Joueurs configurés!")
    
    def toggle_layout_mode(self):
        """Bascule entre layout vertical et horizontal"""
        self.horizontal_layout = not self.horizontal_layout
        
        if self.horizontal_layout:
            self.layout_toggle_btn.config(text="⚡ LAYOUT VERTICAL")
            messagebox.showinfo(
                "Layout Horizontal",
                "L'interface va se réorganiser en mode horizontal.\n\n"
                "⬆ Timeline en haut sur toute la largeur\n"
                "⬇ Boutons alignés horizontalement en bas\n\n"
                "Redémarrage de l'interface..."
            )
        else:
            self.layout_toggle_btn.config(text="⚡ LAYOUT HORIZONTAL")
            messagebox.showinfo(
                "Layout Vertical",
                "Retour au layout vertical classique.\n\n"
                "Redémarrage de l'interface..."
            )
        
        # Reconstruire l'interface
        self._rebuild_interface()
    
    def _rebuild_interface(self):
        """Reconstruit l'interface avec le nouveau layout"""
        # Sauvegarder l'état de la vidéo
        video_path = self.video_player.video_path if self.video_player.video_loaded else None
        current_frame = self.video_player.current_frame if self.video_player.video_loaded else 0
        was_playing = self.playing
        
        # Réinitialiser les références aux widgets qui vont être détruits
        self.play_btn = None
        self.audio_btn = None
        self.rec_indicator_dot = None
        self.rec_indicator_text = None
        self.voice_log_text = None
        self.sidebar_canvas = None
        
        # Détruire le container principal
        if hasattr(self, 'main_container'):
            for widget in self.main_container.winfo_children():
                widget.destroy()
            self.main_container.destroy()
        
        # Recréer l'interface avec le bon layout
        if self.horizontal_layout:
            self._create_horizontal_ui()
        else:
            # Recréer uniquement la partie main_container (header reste intact)
            main_container = tk.Frame(self.root, bg=self.COLORS['bg_main'])
            main_container.pack(fill="both", expand=True)
            self.main_container = main_container
            self._create_vertical_layout(main_container)
        
        # Restaurer la vidéo si elle était chargée
        if video_path:
            try:
                self.video_player.load_video(video_path)
                self.video_player.seek_frame(current_frame)
                
                # Reconfigurer VLC
                if hasattr(self, 'vlc_frame'):
                    self.vlc_frame.update()
                    window_id = self.vlc_frame.winfo_id()
                    self.video_player.set_vlc_window(window_id)
                    self._set_audio_muted(self.audio_muted)
                
                if was_playing:
                    self.video_player.play()
                    self.playing = True
            except Exception as e:
                print(f"Erreur restauration vidéo: {e}")
        self._refresh_audio_button_state()
        self.root.after_idle(self._apply_keyboard_focus_policy)
    
    def _create_horizontal_ui(self):
        """Crée l'interface en mode horizontal (timeline en haut, boutons en bas)"""
        main_container = tk.Frame(self.root, bg=self.COLORS['bg_main'])
        main_container.pack(fill="both", expand=True)
        self.main_container = main_container
        
        # ============= ZONE VIDÉO EN HAUT =============
        video_section = tk.Frame(main_container, bg=self.COLORS['bg_main'])
        video_section.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        # Frame VLC pour la vidéo
        video_frame = tk.Frame(video_section, bg="#000000", relief="flat")
        video_frame.pack(fill="both", expand=True)
        
        self.vlc_frame = tk.Frame(video_frame, bg="#000000")
        self.vlc_frame.pack(fill="both", expand=True)
        
        # Sauvegarder le parent original pour le détachement/réattachement
        self.vlc_frame_original_parent = video_frame
        print(f"[DEBUG] vlc_frame créé (layout horizontal) avec parent: {video_frame}")
        
        # Canvas OpenCV (invisible)
        self.video_canvas = tk.Canvas(video_frame, bg="#000000", highlightthickness=0)
        
        # ============= TIMELINE SUR TOUTE LA LARGEUR =============
        timeline_section = tk.Frame(main_container, bg=self.COLORS['bg_main'], height=100)
        timeline_section.pack(fill="x", padx=20, pady=10)
        timeline_section.pack_propagate(False)
        
        # Barre de progression
        progress_frame = tk.Frame(timeline_section, bg=self.COLORS['bg_main'], height=50)
        progress_frame.pack(fill="x", pady=(0, 5))
        progress_frame.pack_propagate(False)
        
        self.progress_canvas = tk.Canvas(
            progress_frame,
            bg=self.COLORS['border'],
            height=self.PROGRESS_CANVAS_HEIGHT,
            highlightthickness=0,
            cursor="hand2"
        )
        self.progress_canvas.pack(fill="x", padx=10, pady=15)
        
        self.progress_bg = self.progress_canvas.create_rectangle(
            0, 0, 100, self.PROGRESS_CANVAS_HEIGHT, fill=self.COLORS['border'], outline=""
        )
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, self.PROGRESS_CANVAS_HEIGHT, fill=self.COLORS['primary'], outline=""
        )
        self.progress_handle = self.progress_canvas.create_oval(
            -10, 5, 10, self.PROGRESS_CANVAS_HEIGHT - 5, fill=self.COLORS['white'], 
            outline=self.COLORS['primary'], width=4,
            tags="progress_handle"
        )
        
        self.progress_canvas.bind("<Button-1>", self._on_progress_click)
        self.progress_canvas.bind("<B1-Motion>", self._on_progress_drag)
        
        # Info temps
        info_frame = tk.Frame(timeline_section, bg=self.COLORS['bg_main'])
        info_frame.pack(fill="x")
        
        self.time_label = tk.Label(
            info_frame, text="00:00 / 00:00",
            font=("Segoe UI", 12, "bold"),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_dark']
        )
        self.time_label.pack(side="left", padx=10)
        
        self.frame_label = tk.Label(
            info_frame, text="Frame: 0 / 0",
            font=("Segoe UI", 10),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_light']
        )
        self.frame_label.pack(side="right", padx=10)
        
        # ============= BOUTONS HORIZONTAUX EN BAS =============
        buttons_section = tk.Frame(main_container, bg=self.COLORS['bg_main'], height=230)
        buttons_section.pack(fill="x", padx=20, pady=(0, 15))
        buttons_section.pack_propagate(False)
        
        # Ligne 1: Contrôles vidéo
        controls_row = tk.Frame(buttons_section, bg=self.COLORS['bg_main'])
        controls_row.pack(fill="x", pady=5)
        # Détachement vidéo supprimé: la vidéo reste toujours intégrée.
        
        # Contrôles vidéo
        self._create_video_control_button(
            controls_row, "⏮", self.rewind_5s
        ).pack(side="left", padx=3)
        
        self._create_video_control_button(
            controls_row, "◀", self.previous_frame
        ).pack(side="left", padx=3)
        
        self.play_btn = self._create_video_control_button(
            controls_row, "▶", self.toggle_play_pause, is_play=True
        )
        self.play_btn.pack(side="left", padx=8)
        
        self._create_video_control_button(
            controls_row, "▶", self.next_frame
        ).pack(side="left", padx=3)
        
        self._create_video_control_button(
            controls_row, "⏭", self.forward_5s
        ).pack(side="left", padx=3)
        
        # Vitesse
        self.audio_btn = self._create_audio_toggle_button(controls_row)
        self.audio_btn.pack(side="left", padx=(8, 3))
        self._create_tooltip(self.audio_btn, "Couper/Remettre le son (touche M)")
        rec_widget = self._create_rec_indicator_widget(controls_row)
        rec_widget.pack(side="left", padx=(4, 3))
        self._create_tooltip(rec_widget, "Etat enregistrement vocal (touche V)")

        tk.Label(
            controls_row, text="Vitesse:",
            font=("Segoe UI", 9),
            bg=self.COLORS['bg_main'],
            fg=self.COLORS['text_light']
        ).pack(side="left", padx=(15, 5))
        
        self.speed_var = tk.StringVar(value="1.0x")
        self.speed_combo = ttk.Combobox(
            controls_row,
            textvariable=self.speed_var,
            values=["0.25x", "0.5x", "0.75x", "1.0x", "1.5x", "2.0x"],
            state="readonly",
            width=6,
            font=("Segoe UI", 9)
        )
        self.speed_combo.pack(side="left", padx=3)
        self.speed_combo.bind("<<ComboboxSelected>>", self._on_speed_change)
        
        # Ligne 2: Boutons d'annotation
        annotation_row = tk.Frame(buttons_section, bg=self.COLORS['bg_main'])
        annotation_row.pack(fill="x", pady=5)
        
        tk.Button(
            annotation_row,
            text="⚠ FAUTE DIRECTE",
            command=self.add_faute_directe,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['danger'],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)
        
        tk.Button(
            annotation_row,
            text="★ POINT GAGNANT",
            command=self.add_point_gagnant,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['success'],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)
        
        tk.Button(
            annotation_row,
            text="⚡ FAUTE PROVOQUÉE",
            command=self.add_faute_provoquee,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['warning'],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)
        
        tk.Button(
            annotation_row,
            text="🎬 CHARGER VIDÉO",
            command=self.load_video,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['secondary'],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)
        
        tk.Button(
            annotation_row,
            text="💾 EXPORTER",
            command=self.export_csv,
            font=("Segoe UI", 10, "bold"),
            bg=self.COLORS['primary'],
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)
        
        tk.Button(
            annotation_row,
            text="📊 STATS",
            command=self.show_stats,
            font=("Segoe UI", 10, "bold"),
            bg="#9333ea",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(side="left", padx=3)

        self._create_voice_log_panel(buttons_section, height=4)
        
        # Variables pour le zoom
        self.timeline_zoom_level = 1.0
        self.timeline_offset = 0
        self._refresh_audio_button_state()
        is_recording = bool(self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False))
        self._set_rec_indicator_mode("recording" if is_recording else "idle")
        self.root.after_idle(self._apply_keyboard_focus_policy)
    
    def _create_vertical_layout(self, main_container):
        """Reconstruit l'interface verticale complète (mode par défaut)."""
        # Le layout vertical placeholder cassait l'UI après bascule.
        # On reconstruit toute l'interface standard.
        try:
            for widget in self.root.winfo_children():
                widget.destroy()
            self._create_ui()
        except Exception as e:
            print(f"[WARN] Impossible de reconstruire l'interface verticale: {e}")
            fallback = tk.Label(
                main_container,
                text="Impossible de restaurer l'interface.\nRedémarrez l'application.",
                font=("Segoe UI", 14),
                bg=self.COLORS['bg_main'],
                fg=self.COLORS['text_dark']
            )
            fallback.pack(expand=True)

    def add_faute_directe(self):
        """Ajoute une faute directe"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialog(self.root, "faute_directe", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            # Sauvegarder capture
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer le type de coup si disponible
            type_coup = dialog.result.get("type_coup")
            
            self.annotation_manager.add_faute_directe(
                dialog.result["joueur"],
                timestamp,
                frame,
                type_coup,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", "Faute directe enregistrée!")
    
    def add_point_gagnant(self):
        """Ajoute un point gagnant"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialog(self.root, "point_gagnant", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer le type de coup
            type_coup = dialog.result.get("type_coup", "fond_de_court")
            
            self.annotation_manager.add_point_gagnant(
                dialog.result["joueur"],
                timestamp,
                frame,
                type_coup,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", "Point gagnant enregistré!")
    
    def add_faute_provoquee(self):
        """Ajoute une faute provoquée"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialog(self.root, "faute_provoquee", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer les types de coups si disponibles
            type_coup_att = dialog.result.get("type_coup_attaquant")
            type_coup_def = dialog.result.get("type_coup_defenseur")
            
            self.annotation_manager.add_faute_provoquee(
                dialog.result["attaquant"],
                dialog.result["defenseur"],
                timestamp,
                frame,
                type_coup_att,
                type_coup_def,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", "Faute provoquée enregistrée!")
    
    # ============= ANNOTATIONS V2 (Structure détaillée complète) =============
    
    def add_faute_directe_v2(self):
        """Ajoute une faute directe avec structure V2 détaillée"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialogV2(self.root, "faute_directe", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            # Sauvegarder capture
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer le type de coup détaillé
            type_coup = dialog.result.get("type_coup")
            
            self.annotation_manager.add_faute_directe(
                dialog.result["joueur"],
                timestamp,
                frame,
                type_coup,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", f"Faute directe enregistrée!\nCoup: {type_coup}")
    
    def add_point_gagnant_v2(self):
        """Ajoute un point gagnant avec structure V2 détaillée"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialogV2(self.root, "point_gagnant", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer le type de coup détaillé
            type_coup = dialog.result.get("type_coup")
            
            self.annotation_manager.add_point_gagnant(
                dialog.result["joueur"],
                timestamp,
                frame,
                type_coup,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", f"Point gagnant enregistré!\nCoup: {type_coup}")
    
    def add_faute_provoquee_v2(self):
        """Ajoute une faute provoquée avec structure V2 détaillée"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        dialog = AnnotationDialogV2(self.root, "faute_provoquee", self.players)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Récupérer les types de coups détaillés
            type_coup_att = dialog.result.get("type_coup_attaquant")
            type_coup_def = dialog.result.get("type_coup_defenseur")
            
            self.annotation_manager.add_faute_provoquee(
                dialog.result["attaquant"],
                dialog.result["defenseur"],
                timestamp,
                frame,
                type_coup_att,
                type_coup_def,
                f"screens/point_{point_id:03d}"
            )
            
            self._update_stats()
            messagebox.showinfo("✓", f"Faute provoquée enregistrée!\nAttaquant: {type_coup_att}")
    
    # ============= FIN ANNOTATIONS V2 =============
    
    def add_coup_coeur(self, type_coeur):
        """Ajoute un coup de cÅ“ur (moment spectaculaire)"""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Veuillez charger une vidéo d'abord")
            return
        
        # Mettre en pause
        if self.video_player.is_playing():
            self.video_player.pause()
        
        # Dialog pour sélectionner le joueur concerné
        dialog_types = {
            "defense": "💪 Superbe Défense",
            "attaque": "⚡ Superbe Attaque",
            "spectaculaire": "✨ Point Spectaculaire"
        }
        
        # Créer un dialog simple pour sélectionner le joueur
        form = tk.Toplevel(self.root)
        form.title(dialog_types.get(type_coeur, "Coup de CÅ“ur"))
        form.geometry("400x300")
        form.configure(bg="#f5f7fa")
        form.transient(self.root)
        form.grab_set()
        
        result = {'player': None}
        
        tk.Label(form, text=dialog_types.get(type_coeur, "Coup de CÅ“ur"),
                font=("Segoe UI", 16, "bold"),
                bg="#f5f7fa", fg="#667eea").pack(pady=20)
        
        tk.Label(form, text="Sélectionnez le joueur concerné:",
                font=("Segoe UI", 11),
                bg="#f5f7fa", fg="#555").pack(pady=10)
        
        players_frame = tk.Frame(form, bg="#f5f7fa")
        players_frame.pack(pady=20)
        
        def select_player(player):
            result['player'] = player
            form.destroy()
        
        for i, player in enumerate(self.players):
            player_name = player if isinstance(player, str) else player.get('nom', f'Joueur {i+1}')
            btn = tk.Button(players_frame, text=f"{i+1}. {player_name}",
                          command=lambda p=player_name: select_player(p),
                          font=("Segoe UI", 11, "bold"),
                          bg="#667eea", fg="white",
                          relief="flat", padx=20, pady=10,
                          cursor="hand2", activebackground="#5568d3")
            btn.pack(pady=5, fill="x")
        
        self.root.wait_window(form)
        
        if result['player']:
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame
            
            # Ajouter comme annotation spéciale
            point_id = self.annotation_manager.current_point_id
            capture_folder = self.annotation_manager.get_capture_path(point_id)
            self.video_player.capture_frames_before(capture_folder, num_frames=10)
            
            # Stocker le coup de cÅ“ur dans les annotations
            self.annotation_manager.annotations.append({
                "id": point_id,
                "type": "coup_coeur",
                "coup_coeur_type": type_coeur,
                "player": result['player'],
                "timestamp": timestamp,
                "frame": frame,
                "screenshots": capture_folder,
                "datetime": self.annotation_manager._get_timestamp()
            })
            
            self.annotation_manager.current_point_id += 1
            self.annotation_manager.autosave()
            self._update_stats()
            
            emoji_map = {
                "defense": "💪",
                "attaque": "⚡",
                "spectaculaire": "✨"
            }
            messagebox.showinfo(f"{emoji_map.get(type_coeur, '❤️')} Coup de CÅ“ur",
                              f"{dialog_types.get(type_coeur)} enregistré !")
    
    def remove_last(self):
        """Supprime la dernière annotation"""
        removed = self.annotation_manager.remove_last()
        if removed:
            self._update_stats()
            point_type = removed.get('type', '')
            type_labels = {
                'faute_directe': 'Faute directe',
                'point_gagnant': 'Point gagnant',
                'faute_provoquee': 'Faute provoquée',
                'coup_coeur': 'Coup de cÅ“ur'
            }
            label = type_labels.get(point_type, 'Point')
            messagebox.showinfo("✓ Annulé", f"{label} supprimé")
        else:
            messagebox.showwarning("Attention", "Aucune annotation à supprimer")
    
    def remove_last_point(self):
        """Raccourci clavier pour supprimer le dernier point"""
        self.remove_last()
    
    def quick_save(self):
        """Sauvegarde rapide sans dialog"""
        try:
            self.json_exporter.export(self.annotation_manager)
            messagebox.showinfo("💾 Sauvegardé", "Session sauvegardée")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de sauvegarde:\n{e}")
    
    def next_point(self):
        """Navigue vers le point annoté suivant"""
        if not self.annotation_manager.annotations:
            return
        
        current_time = self.video_player.get_current_timestamp()
        
        # Trouver le point suivant
        next_annotation = None
        for annotation in self.annotation_manager.annotations:
            if annotation.get('timestamp', 0) > current_time:
                next_annotation = annotation
                break
        
        if next_annotation:
            timestamp = next_annotation.get('timestamp', 0)
            self.video_player.seek_time(timestamp)
    
    def previous_point(self):
        """Navigue vers le point annoté précédent"""
        if not self.annotation_manager.annotations:
            return
        
        current_time = self.video_player.get_current_timestamp()
        
        # Trouver le point précédent
        prev_annotation = None
        for annotation in reversed(self.annotation_manager.annotations):
            if annotation.get('timestamp', 0) < current_time - 1:
                prev_annotation = annotation
                break
        
        if prev_annotation:
            timestamp = prev_annotation.get('timestamp', 0)
            self.video_player.seek_time(timestamp)
    
    def show_help(self):
        """Affiche l'aide des raccourcis clavier"""
        help_window = tk.Toplevel(self.root)
        help_window.title("âŒ¨ï¸ Raccourcis clavier")
        help_window.geometry("600x700")
        help_window.configure(bg="#1a1a2e")
        help_window.resizable(False, False)
        
        # Titre
        title = tk.Label(help_window, text="âŒ¨ï¸ Raccourcis clavier",
                        font=("Segoe UI", 20, "bold"),
                        bg="#1a1a2e", fg="#ffffff")
        title.pack(pady=20)
        
        # Frame pour le contenu
        content = tk.Frame(help_window, bg="#1a1a2e")
        content.pack(fill="both", expand=True, padx=30, pady=10)
        
        shortcuts = [
            ("NAVIGATION VIDÉO", ""),
            ("→ Flèche droite", "Avancer de 2 secondes"),
            ("â† Flèche gauche", "Reculer de 2 secondes"),
            ("↑ Flèche haut", "Avancer de 10 secondes"),
            ("↓ Flèche bas", "Reculer de 10 secondes"),
            ("T", "Pivoter la vidéo de 90°"),
            ("", ""),
            ("ANNOTATION", ""),
            ("ESPACE", "Pause + Menu d'annotation"),
            ("F", "Faute directe (dans menu)"),
            ("P", "Point gagnant (dans menu)"),
            ("E", "Faute provoquée (dans menu)"),
            ("1-2-3-4", "Sélectionner joueur"),
            ("ENTRÉE", "Valider annotation"),
            ("ECHAP", "Annuler/Fermer"),
            ("", ""),
            ("GESTION", ""),
            ("R", "Annuler le dernier point"),
            ("S", "Sauvegarder rapidement"),
            ("N", "Aller au point suivant"),
            ("B", "Aller au point précédent"),
            ("H", "Afficher cette aide"),
            ("", ""),
            ("AFFICHAGE", ""),
            ("F / F11", "Mode plein écran"),
        ]
        
        for key, description in shortcuts:
            if key == "" and description == "":
                tk.Frame(content, bg="#667eea", height=2).pack(fill="x", pady=10)
            elif description == "":
                tk.Label(content, text=key, font=("Segoe UI", 12, "bold"),
                        bg="#1a1a2e", fg="#667eea").pack(anchor="w", pady=(10, 5))
            else:
                row = tk.Frame(content, bg="#2a2a3e")
                row.pack(fill="x", pady=3)
                
                tk.Label(row, text=key, font=("Segoe UI", 11, "bold"),
                        bg="#667eea", fg="white",
                        padx=15, pady=8, width=20, anchor="w").pack(side="left")
                
                tk.Label(row, text=description, font=("Segoe UI", 10),
                        bg="#2a2a3e", fg="#cccccc",
                        padx=15, pady=8, anchor="w").pack(side="left", fill="x", expand=True)
        
        # Bouton fermer
        tk.Button(help_window, text="Fermer", command=help_window.destroy,
                 font=("Segoe UI", 12, "bold"), bg="#667eea", fg="white",
                 relief="flat", padx=40, pady=12, cursor="hand2").pack(pady=20)
        
        help_window.transient(self.root)
        help_window.grab_set()
    
    def open_ollama_chat(self):
        """Ouvre le chat Ollama dans une nouvelle fenêtre"""
        import subprocess
        import sys
        
        try:
            # Lancer ollama_chat.py dans un nouveau terminal
            if sys.platform == "win32":
                # Windows
                subprocess.Popen(
                    ["start", "cmd", "/k", "python", "ollama_chat.py"],
                    shell=True,
                    cwd=os.path.dirname(os.path.abspath(__file__)) + "/../.."
                )
            else:
                # Linux/Mac
                subprocess.Popen(
                    ["python", "ollama_chat.py"],
                    cwd=os.path.dirname(os.path.abspath(__file__)) + "/../.."
                )
            
            messagebox.showinfo(
                "Chat Ollama", 
                "💬 Le chat Ollama s'ouvre dans une nouvelle fenêtre terminal.\n\n"
                "Assurez-vous qu'Ollama est installé et en cours d'exécution."
            )
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible d'ouvrir le chat Ollama:\n{str(e)}\n\n"
                "Vérifiez qu'Ollama est installé et que ollama_chat.py existe."
            )
    
    # === Exports ===
    
    def export_json(self):
        """Exporte en JSON"""
        try:
            filepath = self.json_exporter.export(self.annotation_manager)
            messagebox.showinfo("Succès", f"JSON exporté:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'export:\n{e}")
    
    def export_csv(self):
        """Exporte en CSV pour Excel"""
        try:
            filepath = self.csv_exporter.export(self.annotation_manager)
            messagebox.showinfo("Succès", f"CSV exporté:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'export CSV:\n{e}")

    def modify_positions(self):
        """Permet de modifier les positions des joueurs à partir du temps courant."""
        try:
            dialog = PlayerSelectionDialog(self.root, self.players)
            self.root.wait_window(dialog.top)
            if dialog.result:
                # Extraire les positions choisies
                positions = [p.get("position", "gauche") for p in dialog.result]
                # Timestamp courant de la vidéo (0 si pas de vidéo)
                ts = 0.0
                if self.video_player and self.video_player.video_loaded:
                    ts = self.video_player.get_current_timestamp()
                ok = self.annotation_manager.add_position_change(ts, positions)
                if ok:
                    # Mettre à jour les joueurs localement et sauvegarder
                    self.players = dialog.result
                    self.annotation_manager.set_players(self.players)
                    self._save_players_config()
                    
                    # Mettre à jour le parser vocal
                    if self.command_parser:
                        player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                        self.command_parser.set_joueurs(player_names)
                    mm = int(ts // 60)
                    ss = int(ts % 60)
                    messagebox.showinfo(
                        "Positions mises à jour",
                        f"Positions appliquées à partir de {mm}:{ss:02d}"
                    )
                else:
                    messagebox.showerror("Erreur", "Impossible d'enregistrer les positions")
        except Exception as e:
            messagebox.showerror("Erreur", f"Modification impossible:\n{e}")
    
    def generate_html(self):
        """Génère le rapport HTML"""
        try:
            # Passer le video_player pour générer les captures à la demande
            filepath = self.html_generator.generate_report(
                self.annotation_manager,
                video_player=self.video_player,
                fast_mode=False,
                num_frames=6
            )
            messagebox.showinfo("Succès", f"Rapport généré:\n{filepath}")
            
            # Ouvrir dans le navigateur
            import webbrowser
            webbrowser.open('file://' + os.path.abspath(filepath))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de génération:\n{e}")

    def generate_html_fast(self):
        """Rapport sans génération de captures (très rapide) + parsing des captures vocales"""
        try:
            # NOUVEAU : Parser les captures vocales avant de générer le rapport
            if self.voice_batch_recorder and self.voice_batch_recorder.session_data:
                self._parse_voice_captures_batch()
            
            print("[DEBUG] Début génération rapport rapide...")
            print(f"[DEBUG] Annotation manager: {self.annotation_manager}")
            print(f"[DEBUG] Nombre d'annotations: {len(self.annotation_manager.annotations) if self.annotation_manager else 0}")
            
            # Exporter les données pour debug
            data = self.annotation_manager.export_to_dict()
            stats = data.get("stats", {})
            print(f"[DEBUG] Stats exportées: {list(stats.keys())}")
            
            # Vérifier les données de lobe pour chaque joueur
            for joueur, joueur_stats in stats.items():
                if joueur == "match":
                    continue
                print(f"\n[DEBUG] Joueur {joueur}:")
                print(f"  - fautes_directes_detail: {joueur_stats.get('fautes_directes_detail', {})}")
                print(f"  - points_gagnants_detail: {joueur_stats.get('points_gagnants_detail', {})}")
                print(f"  - coups_techniques: {joueur_stats.get('coups_techniques', {})}")
                
                # Vérifier spécifiquement le lobe
                fd_detail = joueur_stats.get('fautes_directes_detail', {})
                pg_detail = joueur_stats.get('points_gagnants_detail', {})
                coups_tech = joueur_stats.get('coups_techniques', {})
                
                print(f"  - LOBE dans fautes_directes_detail: {'lobe' in fd_detail}")
                print(f"  - LOBE dans points_gagnants_detail: {'lobe' in pg_detail}")
                print(f"  - LOBE dans coups_techniques: {'lobe' in coups_tech}")
                if 'lobe' in coups_tech:
                    print(f"  - Données lobe: {coups_tech['lobe']}")
            
            # Demander si l'utilisateur veut une analyse IA
            want_ai = messagebox.askyesno(
                "Analyse IA",
                "Voulez-vous lancer une analyse IA du match ?\n\n"
                "Oui → Analyse par le modèle IA (30-60 sec)\n"
                "Non → Rapport rapide uniquement"
            )

            filepath = self.html_generator.generate_report(
                self.annotation_manager,
                video_player=self.video_player,
                fast_mode=True
            )
            print(f"[DEBUG] Rapport généré avec succès: {filepath}")
            try:
                os.startfile(os.path.abspath(filepath))
            except Exception:
                import webbrowser
                webbrowser.open('file://' + os.path.abspath(filepath))

            if want_ai:
                self.analyze_stats_with_ai(skip_confirm=True)

        except Exception as e:
            print(f"[DEBUG ERROR] Exception complète: {type(e).__name__}: {e}")
            _log_ui_exception("generate_html_fast", e)
            messagebox.showerror("Erreur", f"Erreur de génération (rapide):\n{e}")

    def generate_html_full(self):
        """Rapport complet avec captures (plus lent, optimisé)"""
        try:
            # Demander confirmation pour les opérations lourdes
            consent = messagebox.askyesno(
                "Rapport complet",
                "Générer les captures d'écran en parcourant la vidéo ?\n"
                "Cette opération peut être longue."
            )
            # En mode EXE (frozen) sans vidéo chargée, forcer rapide pour éviter erreurs
            import sys
            fast = not consent or (getattr(sys, 'frozen', False) and not (self.video_player and self.video_player.video_loaded))
            filepath = self.html_generator.generate_report(
                self.annotation_manager,
                video_player=self.video_player,
                fast_mode=fast,
                num_frames=6
            )
            messagebox.showinfo(
                "Succès",
                f"Rapport généré (complet):\n{filepath}"
            )
            try:
                os.startfile(os.path.abspath(filepath))
            except Exception:
                import webbrowser
                webbrowser.open('file://' + os.path.abspath(filepath))
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Erreur de génération (complet):\n{e}"
            )
    
    def analyze_stats_with_ai(self, skip_confirm: bool = False):
        """Analyse complète des statistiques avec IA et RAG"""
        if getattr(self, "safe_mode", False):
            messagebox.showinfo(
                "Mode safe",
                "Le mode safe est activé.\n\n"
                "L'analyse IA est désactivée."
            )
            return

        analyzer_cls = AIStatsAnalyzer
        if analyzer_cls is None:
            try:
                from app.exports.ai_analyzer import AIStatsAnalyzer as analyzer_cls
            except Exception as e:
                messagebox.showwarning(
                    "IA non disponible",
                    "Le module d'analyse IA n'est pas disponible dans cette version.\n\n"
                    f"Détail: {e}"
                )
                return

        try:
            # Vérifier qu'il y a des données
            if not self.annotation_manager or not self.annotation_manager.annotations:
                messagebox.showwarning(
                    "Attention",
                    "Aucune donnée à analyser.\n"
                    "Annotez d'abord quelques points du match."
                )
                return
            
            # Confirmation (sauf si déjà confirmé par l'appelant)
            if not skip_confirm:
                confirm = messagebox.askyesno(
                    "Analyse IA",
                    "Lancer une analyse IA complète des statistiques ?\n\n"
                    "L'IA va analyser TOUS les chiffres du match\n"
                    "et les comparer aux connaissances des livres de padel.\n\n"
                    "⏱️ Cela peut prendre 1-2 minutes..."
                )
                if not confirm:
                    return
            
            # Message de progression
            progress_window = tk.Toplevel(self.root)
            progress_window.title("Analyse en cours...")
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            progress_window.configure(bg="#f5f7fa")
            
            # Centrer la fenêtre
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            label = tk.Label(
                progress_window,
                text="🧠 Analyse IA en cours...\n\n"
                     "L'IA analyse vos statistiques\n"
                     "et consulte les livres de padel.\n\n"
                     "⏳ Veuillez patienter...",
                font=("Segoe UI", 11),
                bg="#f5f7fa",
                fg="#667eea",
                justify="center"
            )
            label.pack(expand=True)
            
            progress_window.update()
            
            # Créer l'analyseur
            analyzer = analyzer_cls()
            
            # Lancer l'analyse
            filepath = analyzer.analyze_match_stats(self.annotation_manager)
            
            # Fermer la fenêtre de progression
            progress_window.destroy()
            
            # Succès
            messagebox.showinfo(
                "Analyse terminée",
                f"Analyse IA générée avec succès !\n\n"
                f"Fichier: {os.path.basename(filepath)}\n\n"
                f"Le rapport va s'ouvrir dans votre navigateur."
            )
            
            # Ouvrir le fichier
            try:
                os.startfile(os.path.abspath(filepath))
            except Exception:
                import webbrowser
                webbrowser.open('file://' + os.path.abspath(filepath))
            
        except Exception as e:
            try:
                progress_window.destroy()
            except:
                pass
            
            error_msg = str(e)
            
            # Messages d'erreur personnalisés
            if "Impossible de se connecter à Ollama" in error_msg:
                messagebox.showerror(
                    "Serveur IA non disponible",
                    "Impossible de se connecter au serveur IA.\n\n"
                    "Vérifiez que le serveur est accessible\n"
                    "et que la connexion internet est active."
                )
            elif "Timeout" in error_msg:
                messagebox.showerror(
                    "Timeout",
                    "L'analyse prend trop de temps.\n\n"
                    "Le serveur est peut-être surchargé,\n"
                    "réessayez dans quelques instants."
                )
            else:
                messagebox.showerror(
                    "Erreur d'analyse",
                    f"Erreur lors de l'analyse IA:\n\n{error_msg}"
                )
    
    def save_video_clip(self):
        """Dialogue (overlay) pour sauvegarder un clip vidéo, style Entrée."""
        if not self.video_player.video_loaded:
            messagebox.showwarning("Attention", "Chargez d'abord une vidéo")
            return
        # Vérifier ffmpeg
        if not self.video_cutter.check_ffmpeg():
            messagebox.showerror(
                "FFmpeg requis",
                "FFmpeg n'est pas installé.\n\n"
                "Téléchargez-le sur: https://ffmpeg.org/download.html\n"
                "Puis ajoutez-le au PATH système."
            )
            return

        # Overlay centré, focus et grab (comme menu Entrée)
        clip_dialog = tk.Toplevel(self.root)
        clip_dialog.overrideredirect(True)
        clip_dialog.attributes('-topmost', True)
        clip_dialog.attributes('-alpha', 0.95)
        clip_dialog.grab_set()
        
        # Centrer sur l'écran
        window_width = 600
        window_height = 320
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        clip_dialog.geometry(f"{window_width}x{window_height}+{x}+{y}")
        clip_dialog.configure(bg="#1a1a2e")
        clip_dialog.resizable(False, False)
        
        # Variables
        current = self.video_player.get_current_timestamp()
        start_time = tk.DoubleVar(value=max(0, current - 10))
        end_time = tk.DoubleVar(value=current)
        clip_saved_path = [None]
        
        # Titre
        title = tk.Label(clip_dialog, text="🎥 Définir le segment vidéo",
                 font=("Segoe UI", 16, "bold"),
                 bg="#1a1a2e", fg="#ffffff")
        title.pack(pady=20)
        
        # Instructions
        instructions = tk.Label(
            clip_dialog,
            text="â† → ajuster | ↑ ↓ basculer Début/Fin | Entrée sauvegarder",
            font=("Segoe UI", 10),
            bg="#1a1a2e", fg="#aaaaaa"
        )
        instructions.pack(pady=(0, 20))
        
        # Frame info
        info_frame = tk.Frame(clip_dialog, bg="#2a2a3e")
        info_frame.pack(fill="x", padx=30, pady=10)
        
        # Labels temps
        start_label = tk.Label(info_frame, text="Début:",
                              font=("Segoe UI", 11, "bold"),
                              bg="#2a2a3e", fg="#51cf66")
        start_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        start_value = tk.Label(info_frame, text="0:00",
                              font=("Segoe UI", 11),
                              bg="#2a2a3e", fg="#ffffff")
        start_value.grid(row=0, column=1, sticky="w", pady=5)
        
        end_label = tk.Label(info_frame, text="Fin:",
                            font=("Segoe UI", 11, "bold"),
                            bg="#2a2a3e", fg="#ff6b6b")
        end_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        end_value = tk.Label(info_frame, text="0:00",
                            font=("Segoe UI", 11),
                            bg="#2a2a3e", fg="#ffffff")
        end_value.grid(row=1, column=1, sticky="w", pady=5)
        
        duration_label = tk.Label(info_frame, text="Durée:",
                                 font=("Segoe UI", 11, "bold"),
                                 bg="#2a2a3e", fg="#667eea")
        duration_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)
        
        duration_value = tk.Label(info_frame, text="0s",
                                 font=("Segoe UI", 11),
                                 bg="#2a2a3e", fg="#ffffff")
        duration_value.grid(row=2, column=1, sticky="w", pady=5)
        
        # Mode initial: Début (on est à la fin du point et on recule le début)
        mode = ["start"]
        
        def format_time(seconds):
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}:{secs:02d}"
        
        def update_labels():
            start_value.config(text=format_time(start_time.get()))
            end_value.config(text=format_time(end_time.get()))
            dur = max(0, int(end_time.get() - start_time.get()))
            duration_value.config(text=f"{dur}s")
        
        def on_key(event):
            max_dur = self.video_player.total_frames / self.video_player.fps
            if event.keysym == "Right":
                if mode[0] == "end":
                    end_time.set(min(max_dur, end_time.get() + 1))
                    self.video_player.seek_time(end_time.get())
                else:
                    # début avance sans dépasser fin-1
                    start_time.set(min(end_time.get() - 1, start_time.get() + 1))
                    self.video_player.seek_time(start_time.get())
            elif event.keysym == "Left":
                if mode[0] == "end":
                    end_time.set(max(start_time.get() + 1, end_time.get() - 1))
                    self.video_player.seek_time(end_time.get())
                else:
                    start_time.set(max(0, start_time.get() - 1))
                    self.video_player.seek_time(start_time.get())
            elif event.keysym == "Up":
                mode[0] = "start"
                start_label.config(fg="#ffd43b")
                end_label.config(fg="#ff6b6b")
            elif event.keysym == "Down":
                mode[0] = "end"
                start_label.config(fg="#51cf66")
                end_label.config(fg="#ffd43b")
            elif event.keysym == "Return":
                save_clip()
                return
            update_labels()
        
        def save_clip():
            try:
                video_path = self.video_player.video_path
                clip_path = self.video_cutter.cut_video(
                    video_path,
                    start_time.get(),
                    end_time.get()
                )
                clip_saved_path[0] = clip_path
                messagebox.showinfo("✓ Clip sauvegardé", f"Clip:\n{clip_path}")
                clip_dialog.destroy()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur clip:\n{e}")
        
        # Boutons
        btn_frame = tk.Frame(clip_dialog, bg="#1a1a2e")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="💾 Sauvegarder Clip",
                 command=save_clip,
                 font=("Segoe UI", 12, "bold"), bg="#667eea", fg="white",
                 relief="flat", padx=30, pady=12, cursor="hand2").pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="✕ Annuler",
                 command=clip_dialog.destroy,
                 font=("Segoe UI", 12), bg="#e74c3c", fg="white",
                 relief="flat", padx=20, pady=12, cursor="hand2").pack(side="left", padx=5)
        
        # Bindings
        clip_dialog.bind("<KeyPress>", on_key)
        clip_dialog.focus_set()
        # Positionner la vidéo sur le début par défaut pour régler immédiatement
        self.video_player.seek_time(start_time.get())
        update_labels()
    
    def toggle_ollama_live(self):
        """Génère et ouvre le rapport HTML live dans le navigateur"""
        if getattr(self, "safe_mode", False):
            messagebox.showinfo(
                "Mode safe",
                "Le mode safe est activé.\n\n"
                "L'analyse IA live est désactivée."
            )
            return

        from pathlib import Path
        import webbrowser
        from app.exports.live_html_generator import generate_live_report
        
        # Récupérer les données en mémoire
        match_data = self.annotation_manager.export_to_dict()
        
        if not match_data or not match_data.get('points'):
            messagebox.showwarning(
                "Aucun match",
                "Aucun match en cours.\nAnnotez des points pour démarrer l'analyse live."
            )
            return
        
        # Générer le rapport HTML
        print(f"[MainWindow] Génération du rapport HTML live...")
        if generate_live_report(match_data, force_analyze=True):
            # Ouvrir dans le navigateur
            html_path = Path("data/live_analysis.html").absolute()
            webbrowser.open(f"file:///{html_path}")
            print(f"[MainWindow] Rapport ouvert dans le navigateur")
            
            messagebox.showinfo(
                "Analyse Live",
                "📊 Rapport HTML ouvert dans votre navigateur!\n\n"
                "✨ Il se rafraîchit automatiquement toutes les 5 secondes.\n"
                "🤖 L'analyse IA se met à jour tous les 3 points."
            )
        else:
            messagebox.showerror("Erreur", "Impossible de générer le rapport HTML")
    
    def _notify_ollama_window(self):
        """Régénère le rapport HTML après chaque annotation"""
        if getattr(self, "safe_mode", False):
            return

        from app.exports.live_html_generator import generate_live_report
        
        # Mettre à jour le HTML en arrière-plan avec les données en mémoire
        match_data = self.annotation_manager.export_to_dict()
        
        # Ajouter les erreurs vocales dans les données
        if hasattr(self, 'voice_errors') and self.voice_errors:
            match_data['voice_errors'] = self.voice_errors
        
        if match_data and match_data.get('points'):
            # Générer en arrière-plan (pas de force_analyze, uniquement tous les 3 points)
            generate_live_report(match_data, force_analyze=False)
        
        # Mettre à jour le contexte de l'agent chat si ouvert
        if self.agent_chat:
            match_data = self.annotation_manager.get_match_data()
            self.agent_chat.update_context(match_data=match_data)
    
    def toggle_agent_chat(self):
        """Ouvre/ferme la zone de chat avec l'agent IA"""
        if getattr(self, "safe_mode", False):
            messagebox.showinfo(
                "Mode safe",
                "Le mode safe est activé.\n\n"
                "Le chat IA est désactivé."
            )
            return

        chat_cls = AgentChatWindow
        if chat_cls is None:
            try:
                from app.ui.agent_chat_tk import AgentChatWindow as chat_cls
            except Exception as e:
                messagebox.showwarning(
                    "Chat IA non disponible",
                    "Le module de chat IA n'est pas disponible dans cette version.\n\n"
                    f"Détail: {e}"
                )
                return

        if not self.agent_chat:
            # Créer le widget agent en mode intégré
            self.agent_chat = chat_cls(
                self, 
                container=self.agent_chat_container,
                action_callback=self.handle_agent_action
            )
            
            # Mettre à jour le contexte initial
            match_data = self.annotation_manager.get_match_data()
            self.agent_chat.update_context(match_data=match_data)
        
        # Toggle l'affichage du container
        if self.agent_chat_container.winfo_ismapped():
            self.agent_chat_container.pack_forget()
        else:
            self.agent_chat_container.pack(side="left", fill="both", before=self.agent_chat_container.master.winfo_children()[0] if self.agent_chat_container.master.winfo_children() else None)
            self.agent_chat.window.pack(fill="both", expand=True)
    
    def handle_agent_action(self, action_type, params):
        """Gère les actions déclenchées par l'agent"""
        # Code existant...
        pass
    
    # ============= COMMANDES VOCALES =============
    
    # --- PUSH-TO-TALK (Nouveau système) ---
    
    def _instant_voice_annotation(self, audio_text: str, video_timestamp: float) -> bool:
        """
        Callback pour créer instantanément une annotation depuis la transcription vocale
        
        Args:
            audio_text: Texte transcrit
            video_timestamp: Timestamp vidéo en secondes
            
        Returns:
            True si commande reconnue et annotation créée, False sinon
        """
        # IMPORTANT: appelé depuis un thread (transcription). Ne pas toucher à Tkinter ici.
        try:
            result = self.command_parser.parse(audio_text) if self.command_parser else None

            recognized = False
            if result and self.command_parser:
                try:
                    is_valid, _msg = self.command_parser.validate_command(result)
                    # "Reconnu" au sens "stat exploitable" => commande valide + nouveau point
                    recognized = bool(is_valid and result.get("action") == "nouveau_point")
                except Exception:
                    recognized = False

            try:
                self.root.after(
                    0,
                    lambda: self._handle_instant_voice_result(
                        audio_text=audio_text,
                        video_timestamp=video_timestamp,
                        parsed_result=result,
                        recognized=recognized,
                    ),
                )
            except Exception:
                pass

            return recognized
        except Exception as e:
            print(f"[ERROR] Parsing vocal instantané: {e}")
            return False

    def _handle_instant_voice_result(self, audio_text: str, video_timestamp: float, parsed_result: dict, recognized: bool):
        """Applique le résultat d'une capture push-to-talk (thread UI)."""
        try:
            if recognized and parsed_result:
                self._refresh_voice_info_banner(
                    raw_text=audio_text,
                    parsed=parsed_result,
                    level="ok",
                    status="Commande reconnue (PTT)",
                )

                # Popup arbre: mise à jour puis auto-hide
                self._show_voice_tree_popup(level="ok", status="Commande reconnue (PTT)", raw_text=audio_text, parsed=parsed_result)
                try:
                    if self._voice_tree_popup_hide_after_id:
                        self.root.after_cancel(self._voice_tree_popup_hide_after_id)
                    self._voice_tree_popup_hide_after_id = self.root.after(2500, self._hide_voice_tree_popup)
                except Exception:
                    pass

                self._create_annotation_from_voice(parsed_result, video_timestamp)

                self._update_voice_status_label(f"✅ {audio_text}")
                self.root.after(2000, lambda: self._update_voice_status_label(""))
                self._set_rec_indicator_mode("idle")
                self._append_voice_log(f"OK commande reconnue: {audio_text}")
            else:
                print(f"[VOICE] ✗ Commande non reconnue: {audio_text}")
                self._refresh_voice_info_banner(
                    raw_text=audio_text,
                    parsed=parsed_result,
                    level="warn",
                    status="Non reconnu (PTT)",
                )

                # Popup arbre: mise à jour puis auto-hide
                self._show_voice_tree_popup(level="warn", status="Non reconnu (PTT)", raw_text=audio_text, parsed=parsed_result)
                try:
                    if self._voice_tree_popup_hide_after_id:
                        self.root.after_cancel(self._voice_tree_popup_hide_after_id)
                    self._voice_tree_popup_hide_after_id = self.root.after(3500, self._hide_voice_tree_popup)
                except Exception:
                    pass
                self._update_voice_status_label(f"❌ Non reconnu: {audio_text}")
                self.root.after(3000, lambda: self._update_voice_status_label(""))
                self._set_rec_indicator_mode("idle")
                self._append_voice_log(f"ECHEC commande non reconnue: {audio_text}")
        except Exception as e:
            print(f"[ERROR] _handle_instant_voice_result: {e}")
            self._set_rec_indicator_mode("error")
            self._append_voice_log(f"Erreur traitement vocal: {e}")
    
    def _on_voice_key_press(self, event):
        """Wrapper pour KeyPress touche V (push-to-talk)"""
        if getattr(self, "safe_mode", False):
            return
        if not self.vocal_mode_active:
            return  # Mode vocal désactivé, ignorer
        print(f"[DEBUG] Touche V appuyée (mode vocal actif)")
        self._refresh_voice_info_banner(level="info", status="PTT: maintenir V pour parler")
        self._start_voice_recording()
    
    def _on_voice_key_release(self, event):
        """Wrapper pour KeyRelease touche V (push-to-talk)"""
        if getattr(self, "safe_mode", False):
            return
        if not self.vocal_mode_active:
            return  # Mode vocal désactivé, ignorer
        print(f"[DEBUG] Touche V relâchée (mode vocal actif)")
        self._refresh_voice_info_banner(level="info", status="PTT: relâcher = transcription")
        self._stop_voice_recording()

    def _on_voice_key_toggle(self, event):
        """Mode toggle: appuyer sur V = démarrer/arrêter l'enregistrement."""
        if getattr(self, "safe_mode", False):
            return
        if not getattr(self, "vocal_mode_active", False):
            return

        # Anti-repeat clavier (Windows peut répéter KeyPress)
        try:
            now = int(getattr(event, "time", 0) or 0)
        except Exception:
            now = 0
        if now and self._last_v_key_ts and (now - self._last_v_key_ts) < 250:
            return
        if now:
            self._last_v_key_ts = now

        is_recording = bool(self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False))
        if is_recording:
            # Garder le popup arbre visible et mettre à jour le statut
            self._show_voice_tree_popup(level="info", status="PTT: arrêt (transcription)")
            self._refresh_voice_info_banner(level="info", status="PTT: arrêt (transcription)")
            self._append_voice_log("V stop enregistrement, lancement analyse")
            self._stop_voice_recording()
        else:
            # Afficher uniquement le popup "arbre" léger (pas le gros bandeau/guide)
            self._show_voice_tree_popup(level="info", status="PTT: démarrage (parlez puis rappuyez V)")
            self._refresh_voice_info_banner(level="info", status="PTT: démarrage (parlez puis rappuyez V)")
            self._append_voice_log("V start enregistrement")
            self._start_voice_recording()

    def _show_voice_ptt_guide_panel(self):
        """Affiche un panneau guide (ordre chronologique) à chaque démarrage du PTT."""
        try:
            if not SHOW_PTT_GUIDE_PANEL:
                return
            if getattr(self, "voice_ptt_guide_window", None) and self.voice_ptt_guide_window.winfo_exists():
                self.voice_ptt_guide_window.lift()
                self.voice_ptt_guide_window.focus_force()
                return

            win = tk.Toplevel(self.root)
            win.title("🎤 Guide vocal (V)")
            win.geometry("520x360")
            win.configure(bg="#0B1220")
            win.attributes("-topmost", True)

            body = tk.Frame(win, bg="#0B1220")
            body.pack(fill="both", expand=True, padx=14, pady=14)

            steps = (
                "1) Appuyer sur V → démarre l'enregistrement (timestamp capturé)\n"
                "2) Parler la commande (ex: 'faute directe Arnaud', 'point gagnant Pierre smash')\n"
                "3) Rappuyer sur V → stop + transcription\n"
                "4) Parsing/validation → ajout du point si reconnu\n"
                "5) Si non reconnu → bouton 'REVIEW VOCAL' pour revenir dessus"
            )
            tk.Label(
                body,
                text=steps,
                font=("Segoe UI", 10),
                bg="#0B1220",
                fg="#D1D5DB",
                justify="left",
                anchor="w",
            ).pack(fill="x", pady=(0, 10))

            examples = (
                "Exemples courts (sans 'OK' requis en PTT) :\n"
                "• point gagnant Arnaud smash\n"
                "• faute directe Pierre\n"
                "• faute provoquée Thomas service Lucas\n"
                "Champs extraits : Point / Joueur / Défenseur / Coup / Zone / Diagonale / Label"
            )
            tk.Label(
                body,
                text=examples,
                font=("Segoe UI", 9),
                bg="#0B1220",
                fg="#9CA3AF",
                justify="left",
                anchor="w",
            ).pack(fill="x")

            btns = tk.Frame(win, bg="#0B1220")
            btns.pack(fill="x", padx=14, pady=12)
            tk.Button(
                btns,
                text="Fermer",
                command=win.destroy,
                bg="#374151",
                fg="white",
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
            ).pack(side="right")

            self.voice_ptt_guide_window = win
        except Exception:
            pass

    def _ensure_voice_tree_popup(self):
        """Crée le popup vocal (arbre) si nécessaire."""
        try:
            if getattr(self, "voice_tree_popup", None) and self.voice_tree_popup.winfo_exists():
                return

            win = tk.Toplevel(self.root)
            win.title("🎤 Vocal (PTT)")
            win.configure(bg="#0B1220")
            win.resizable(False, False)
            win.attributes("-topmost", True)

            # Petit popup non intrusif (on évite focus_force)
            try:
                win.transient(self.root)
            except Exception:
                pass

            title = tk.Label(
                win,
                text="",
                font=(getattr(self, "ui_font_family", "Segoe UI"), 10, "bold"),
                bg="#0B1220",
                fg="#E5E7EB",
                anchor="w",
                justify="left",
                padx=12,
                pady=8,
            )
            title.pack(fill="x")

            body = tk.Label(
                win,
                text="",
                font=(getattr(self, "ui_mono_font_family", "Consolas"), 9),
                bg="#0B1220",
                fg="#D1D5DB",
                anchor="w",
                justify="left",
                padx=12,
                pady=10,
            )
            body.pack(fill="both", expand=True)

            # Fermeture manuelle possible
            win.bind("<Escape>", lambda _e: self._hide_voice_tree_popup())

            self.voice_tree_popup = win
            self.voice_tree_popup_title = title
            self.voice_tree_popup_body = body

            def _on_destroy(_evt=None):
                self.voice_tree_popup = None
                self.voice_tree_popup_title = None
                self.voice_tree_popup_body = None
                self._voice_tree_popup_hide_after_id = None

            win.bind("<Destroy>", _on_destroy)
        except Exception:
            pass

    def _place_voice_tree_popup(self):
        """Positionne le popup sur le côté gauche de la fenêtre principale."""
        try:
            if not (self.voice_tree_popup and self.voice_tree_popup.winfo_exists()):
                return

            self.root.update_idletasks()

            root_x = int(self.root.winfo_rootx())
            root_y = int(self.root.winfo_rooty())
            root_h = int(self.root.winfo_height())

            popup_w, popup_h = 520, 430
            x = root_x + 14
            y = root_y + max(90, int((root_h - popup_h) / 2))

            self.voice_tree_popup.geometry(f"{popup_w}x{popup_h}+{x}+{y}")
        except Exception:
            pass

    def _hide_voice_tree_popup(self):
        try:
            if self._voice_tree_popup_hide_after_id:
                try:
                    self.root.after_cancel(self._voice_tree_popup_hide_after_id)
                except Exception:
                    pass
                self._voice_tree_popup_hide_after_id = None

            if self.voice_tree_popup and self.voice_tree_popup.winfo_exists():
                self.voice_tree_popup.withdraw()
        except Exception:
            pass

    def _show_voice_tree_popup(self, level: str = "info", status: str = None, raw_text: str = None, parsed: dict = None):
        try:
            self._ensure_voice_tree_popup()
            if not (self.voice_tree_popup and self.voice_tree_popup.winfo_exists()):
                return

            # Évite qu'un auto-hide précédent ferme le popup juste après une nouvelle commande.
            if self._voice_tree_popup_hide_after_id:
                try:
                    self.root.after_cancel(self._voice_tree_popup_hide_after_id)
                except Exception:
                    pass
                self._voice_tree_popup_hide_after_id = None

            self._place_voice_tree_popup()
            self.voice_tree_popup.deiconify()
            self.voice_tree_popup.lift()
            self._update_voice_tree_popup(level=level, status=status, raw_text=raw_text, parsed=parsed)
        except Exception:
            pass

    def _update_voice_tree_popup(self, level: str = "info", status: str = None, raw_text: str = None, parsed: dict = None):
        try:
            if not (self.voice_tree_popup and self.voice_tree_popup.winfo_exists()):
                return
            if not (self.voice_tree_popup_title and self.voice_tree_popup_body):
                return

            colors = {
                "info": ("#0B1220", "#E5E7EB", "#D1D5DB"),
                "ok": ("#052e1a", "#ECFDF5", "#D1FAE5"),
                "warn": ("#2a1a05", "#FFFBEB", "#FDE68A"),
                "error": ("#2a0505", "#FEF2F2", "#FCA5A5"),
            }
            bg, fg_title, fg_body = colors.get(level, colors["info"])

            # Titre compact (pas de gros bandeau)
            parts = []
            if status:
                parts.append(str(status))
            if raw_text:
                rt = " ".join(str(raw_text).split())
                if len(rt) > 60:
                    rt = rt[:57] + "…"
                parts.append(f"\"{rt}\"")
            title_text = "  ·  ".join(parts) if parts else "PTT"

            heard_text = ""
            if raw_text:
                raw_clean = " ".join(str(raw_text).split())
                if len(raw_clean) > 180:
                    raw_clean = raw_clean[:177] + "…"
                heard_text = f"🗣 Entendu: {raw_clean}\n\n"

            tree_text = heard_text + self._build_voice_tree_text(parsed or {})

            self.voice_tree_popup.configure(bg=bg)
            self.voice_tree_popup_title.configure(text=title_text, bg=bg, fg=fg_title)
            self.voice_tree_popup_body.configure(text=tree_text, bg=bg, fg=fg_body)
        except Exception:
            pass

    def _build_voice_tree_text(self, parsed: dict) -> str:
        """Arbre vocal complet: schéma attendu + valeurs reconnues."""
        def humanize(field: str, value):
            if value is None:
                return None
            if field == "type_point":
                return {
                    "point_gagnant": "Point gagnant",
                    "faute_directe": "Faute directe",
                    "faute_provoquee": "Faute provoquée",
                }.get(value, value)
            if field == "type_coup":
                return {
                    "service": "Service",
                    "smash": "Smash",
                    "vollee": "Volée",
                    "bandeja": "Bandeja",
                    "vibora": "Víbora",
                    "coup_droit": "Coup droit",
                    "revers": "Revers",
                    "lob": "Lob",
                    "chiquita": "Chiquita",
                    "amorti": "Amorti",
                    "sortie_vitre": "Sortie de vitre",
                    "contre_vitre": "Contre-vitre",
                    "fond_de_court": "Fond de court",
                    "balle_haute": "Balle haute",
                }.get(value, value)
            return value

        recognized_flag = None
        if parsed and getattr(self, "command_parser", None):
            try:
                is_valid, _msg = self.command_parser.validate_command(parsed)
                recognized_flag = bool(is_valid and parsed.get("action") == "nouveau_point")
            except Exception:
                recognized_flag = None

        if recognized_flag is True:
            flag_text = "🟩 STAT RECONNUE"
        elif recognized_flag is False:
            flag_text = "🟥 STAT NON RECONNUE"
        else:
            flag_text = "⬜ STAT: —"

        stat_label = humanize("type_point", parsed.get("type_point"))
        head = f"{flag_text}" + (f"  ·  {stat_label}" if stat_label else "")

        def _fmt(value, required=False):
            if value in (None, ""):
                return "— (obligatoire)" if required else "—"
            return str(value)

        joueur = parsed.get("joueur")
        defenseur = parsed.get("defenseur")
        type_point = parsed.get("type_point")
        type_coup = humanize("type_coup", parsed.get("type_coup"))
        zone = parsed.get("zone")
        diagonale = parsed.get("diagonale")
        label = parsed.get("label")

        lines = [
            head,
            "",
            "🌳 Schéma vocal complet (PTT avec V)",
            "1) Faute directe",
            "   ├─ Type point: faute directe (obligatoire)",
            "   ├─ Joueur: [Prénom] (obligatoire)",
            "   └─ Type de coup: [optionnel]",
            "",
            "2) Point gagnant",
            "   ├─ Type point: point gagnant (obligatoire)",
            "   ├─ Joueur: [Prénom] (obligatoire)",
            "   ├─ Type de coup: [obligatoire]",
            "   └─ Label: [optionnel, ex balle haute: smash/bandeja/víbora]",
            "",
            "3) Faute provoquée",
            "   ├─ Type point: faute provoquée (obligatoire)",
            "   ├─ Attaquant: [Prénom] (obligatoire)",
            "   ├─ Défenseur/Fautif: [Prénom] (obligatoire)",
            "   └─ Type de coup: [recommandé]",
            "",
            "🧩 Valeurs reconnues sur ta phrase",
            f"├─ Type point: {_fmt(humanize('type_point', type_point), required=True)}",
            f"├─ Joueur / Attaquant: {_fmt(joueur, required=True)}",
            f"├─ Défenseur: {_fmt(defenseur, required=(type_point == 'faute_provoquee'))}",
            f"├─ Type de coup: {_fmt(type_coup, required=(type_point == 'point_gagnant'))}",
            f"├─ Zone: {_fmt(zone)}",
            f"├─ Diagonale: {_fmt(diagonale)}",
            f"└─ Label: {_fmt(label)}",
        ]

        return "\n".join(lines)
    
    def _start_voice_recording(self):
        """Démarre l'enregistrement vocal (PTT: appui touche V)"""
        print("[DEBUG] _start_voice_recording appelé")
        
        if not self.voice_batch_recorder:
            print("[WARN] VoiceBatchRecorder non disponible")
            self._set_rec_indicator_mode("error")
            self._append_voice_log("Erreur: module enregistrement vocal indisponible")
            return
        
        # Vérifier qu'une vidéo est chargée
        if not self.video_player.video_loaded:
            print("[WARN] Aucune vidéo chargée")
            self._set_rec_indicator_mode("error")
            self._append_voice_log("Erreur: impossible de lancer REC sans video")
            return
        
        # Obtenir timestamp vidéo actuel (en secondes, comme annotation manuelle)
        video_timestamp = self.video_player.get_current_timestamp()
        
        # Démarrer session si première utilisation
        if not self.voice_batch_recorder.session_data:
            video_path = getattr(self, 'current_video', None) or self.annotation_manager.video_path
            self.voice_batch_recorder.start_session(
                video_path,
                ui_callback=self._voice_batch_callback,
                create_annotation_callback=self._instant_voice_annotation
            )
        
        # Demarrer enregistrement d'abord. Si le micro echoue, ne pas forcer le mute.
        self._audio_was_muted_before_voice_recording = bool(getattr(self, "audio_muted", False))
        self.voice_batch_recorder.start_recording(video_timestamp)

        is_recording = bool(getattr(self.voice_batch_recorder, "is_recording", False))
        if not is_recording:
            self._voice_recording_forced_mute = False
            self._audio_was_muted_before_voice_recording = False
            self._update_voice_status_label("Micro indisponible")
            self._refresh_voice_info_banner(level="warn", status="Impossible de demarrer l'enregistrement")
            self._set_rec_indicator_mode("error")
            self._append_voice_log("Erreur micro: enregistrement non demarre")
            return

        # Couper le son seulement si l'utilisateur ne l'avait pas deja coupe.
        if not self._audio_was_muted_before_voice_recording:
            self._voice_recording_forced_mute = True
            self._set_audio_muted(True)
        else:
            self._voice_recording_forced_mute = False

        # Feedback visuel
        self._update_voice_status_label("Enregistrement...")
        self._refresh_voice_info_banner(level="info", status="Enregistrement...")
        self._set_rec_indicator_mode("recording")
        self._append_voice_log(f"Enregistrement demarre a {video_timestamp:.2f}s")
    
    def _stop_voice_recording(self):
        """Arrête l'enregistrement vocal (PTT: relâche touche V)"""
        print("[DEBUG] _stop_voice_recording appelé")
        
        if not self.voice_batch_recorder:
            self._voice_recording_forced_mute = False
            self._audio_was_muted_before_voice_recording = False
            self._set_rec_indicator_mode("idle")
            return
        
        # Arreter enregistrement
        self.voice_batch_recorder.stop_recording()

        # Restaurer le son uniquement si le mute a ete force par le PTT.
        if self._voice_recording_forced_mute and not self._audio_was_muted_before_voice_recording:
            self._set_audio_muted(False)

        self._voice_recording_forced_mute = False
        self._audio_was_muted_before_voice_recording = False

        # Feedback visuel
        self._update_voice_status_label("Transcription...")
        self._refresh_voice_info_banner(level="info", status="Transcription...")
        self._set_rec_indicator_mode("transcribing")
    
    def _voice_batch_callback(self, event_type: str, data: dict):
        """Callback pour les événements du batch recorder"""
        if event_type == "recording_started":
            print(f"[VOICE] Enregistrement démarré à {data['timestamp']}")
            try:
                self._append_voice_log(f"Capture audio en cours (t={float(data.get('timestamp', 0.0)):.2f}s)")
            except Exception:
                self._append_voice_log("Capture audio en cours")
        
        elif event_type == "capture_added":
            print(f"[VOICE] Capture #{data['id']} ajoutée: {data['audio_text']}")
            self._update_voice_status_label(f"✓ Capture #{data['id']}: {data['audio_text'][:30]}...")
            preview = " ".join(str(data.get("audio_text", "")).split())
            if len(preview) > 60:
                preview = preview[:57] + "..."
            self._append_voice_log(f"Capture #{data.get('id')} recue: {preview}")
            self._set_rec_indicator_mode("idle")
            try:
                self.root.after(
                    0,
                    lambda: self._show_voice_tree_popup(
                        level="info",
                        status=f"Capture vocale #{data.get('id')}",
                        raw_text=data.get("audio_text"),
                        parsed={},
                    ),
                )
            except Exception:
                pass
            
            # Retour à l'état normal après 2 secondes
            self.root.after(2000, lambda: self._update_voice_status_label(""))
    
    def _parse_voice_captures_batch(self):
        """Parse toutes les captures vocales en attente et affiche popup de review si nécessaire"""
        if not self.voice_batch_recorder or not self.command_parser:
            return
        
        pending = self.voice_batch_recorder.get_pending_captures()
        if not pending:
            print("[VOICE] Aucune capture à parser")
            return
        
        print(f"[VOICE] Parsing de {len(pending)} captures...")
        recognized_count = 0
        unrecognized = []
        
        for capture in pending:
            audio_text = capture["audio_text"]
            
            # Parser la commande
            try:
                result = self.command_parser.parse(audio_text)

                is_recognized = False
                if result:
                    try:
                        is_valid, _msg = self.command_parser.validate_command(result)
                        is_recognized = bool(is_valid and result.get("action") == "nouveau_point")
                    except Exception:
                        is_recognized = False

                if is_recognized:
                    # Commande reconnue → créer annotation
                    self._create_annotation_from_voice(result, capture["video_timestamp"])
                    self.voice_batch_recorder.mark_as_processed(capture["id"], success=True)
                    recognized_count += 1
                    print(f"[VOICE] ✓ Capture #{capture['id']} reconnue: {result}")
                else:
                    # Non reconnue
                    self.voice_batch_recorder.mark_as_processed(capture["id"], success=False)
                    unrecognized.append(capture)
                    print(f"[VOICE] ✗ Capture #{capture['id']} non reconnue: {audio_text}")
                    
            except Exception as e:
                print(f"[ERROR] Parsing capture #{capture['id']}: {e}")
                self.voice_batch_recorder.mark_as_processed(capture["id"], success=False)
                unrecognized.append(capture)
        
        # Afficher résumé
        print(f"[VOICE] Résultat parsing: {recognized_count} reconnues, {len(unrecognized)} non reconnues")
        
        # Si des commandes non reconnues, afficher popup de review
        if unrecognized:
            self.root.after(100, lambda: self._show_voice_review_popup(unrecognized))
    
    def _create_annotation_from_voice(self, parsed_result: dict, video_timestamp: float):
        """Crée une annotation à partir d'une commande vocale parsée
        
        Args:
            parsed_result: Résultat du parsing vocal
            video_timestamp: Timestamp en secondes (float) - même format qu'annotations manuelles
        """
        try:
            # Extraire les infos du parsing
            joueur = parsed_result.get("joueur")
            type_point = parsed_result.get("type_point")
            type_coup = parsed_result.get("type_coup")
            frame = int(video_timestamp * 30)  # Approximation 30 FPS
            
            # Utiliser les méthodes appropriées selon le type de point
            if type_point == 'faute_directe':
                self.annotation_manager.add_faute_directe(
                    joueur=joueur,
                    timestamp=video_timestamp,
                    frame=frame,
                    type_coup=type_coup
                )
                print(f"[VOICE] Faute directe créée: {joueur} - {type_coup}")
            elif type_point == 'point_gagnant':
                self.annotation_manager.add_point_gagnant(
                    joueur=joueur,
                    timestamp=video_timestamp,
                    frame=frame,
                    type_coup=type_coup
                )
                print(f"[VOICE] Point gagnant créé: {joueur} - {type_coup}")
            elif type_point == 'faute_provoquee':
                defenseur = parsed_result.get("defenseur")
                self.annotation_manager.add_faute_provoquee(
                    attaquant=joueur,
                    defenseur=defenseur,
                    timestamp=video_timestamp,
                    frame=frame,
                    type_coup_attaquant=type_coup
                )
                print(f"[VOICE] Faute provoquee creee: {joueur} -> {defenseur}")
            else:
                print(f"[WARN] Type de point inconnu: {type_point}")
                self._append_voice_log(f"ECHEC type de point inconnu: {type_point}")
                return
            
            # Mise à jour UI
            self._update_annotations_display()
            
            # Mise à jour monitoring live
            self._update_live_monitor()
            if type_point == 'faute_provoquee':
                self._append_voice_log(f"STAT ajoutee: {type_point} {joueur}->{defenseur}")
            else:
                self._append_voice_log(f"STAT ajoutee: {type_point} {joueur}")
            
        except Exception as e:
            print(f"[ERROR] Création annotation depuis vocal: {e}")
            self._append_voice_log(f"ECHEC ajout stat: {e}")
            _log_ui_exception("_create_annotation_from_voice", e)
    
    def _show_voice_review_popup(self, unrecognized_captures: list, session_file: str = None):
        """Affiche un popup pour review les commandes vocales non reconnues (vidéo + audio WAV + correction)."""
        print(f"[DEBUG] Popup avec {len(unrecognized_captures)} captures")
        
        popup = tk.Toplevel(self.root)
        popup.title("📝 Review des commandes vocales")
        popup.geometry("1000x700")
        popup.resizable(True, True)
        popup.configure(bg="#f5f7fa")
        
        # Empêcher la fermeture automatique du popup
        popup.protocol("WM_DELETE_WINDOW", popup.destroy)
        
        # Header
        header = tk.Frame(popup, bg="#667eea", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text=f"📊 {len(unrecognized_captures)} commandes à corriger",
            font=("Segoe UI", 14, "bold"),
            bg="#667eea",
            fg="white"
        ).pack(pady=15)
        
        # Instructions
        info_frame = tk.Frame(popup, bg="#fff3cd", height=50)
        info_frame.pack(fill="x", pady=(10, 0))
        info_frame.pack_propagate(False)
        
        tk.Label(
            info_frame,
            text="💡 Sélectionnez une commande pour rejouer la vidéo au bon moment et corriger manuellement",
            font=("Segoe UI", 10),
            bg="#fff3cd",
            fg="#856404"
        ).pack(pady=12)
        
        # Conteneur principal
        main_container = tk.Frame(popup, bg="#f5f7fa")
        main_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Liste des commandes (gauche)
        list_frame = tk.Frame(main_container, bg="white", relief="solid", bd=1)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(
            list_frame,
            text="📋 Commandes non reconnues",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#333"
        ).pack(pady=10)
        
        # Scrollbar + Listbox
        scroll_frame = tk.Frame(list_frame, bg="white")
        scroll_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(scroll_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = tk.Listbox(
            scroll_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            bg="white",
            fg="#333",
            selectbackground="#667eea",
            selectforeground="white",
            relief="flat",
            highlightthickness=0
        )
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        # Remplir la liste (non reconnues uniquement)
        for capture in unrecognized_captures:
            timestamp = capture["video_timestamp"]
            text = capture["audio_text"]
            listbox.insert(tk.END, f"❌ [{float(timestamp):.1f}s] {text}")
        
        # Actions (droite)
        actions_frame = tk.Frame(main_container, bg="white", relief="solid", bd=1)
        actions_frame.pack(side="right", fill="both", padx=(10, 0))
        actions_frame.config(width=250)
        actions_frame.pack_propagate(False)
        
        tk.Label(
            actions_frame,
            text="🎬 Actions",
            font=("Segoe UI", 12, "bold"),
            bg="white",
            fg="#333"
        ).pack(pady=10)
        
        # Label détails
        details_label = tk.Label(
            actions_frame,
            text="Sélectionnez une commande",
            font=("Segoe UI", 9),
            bg="white",
            fg="#666",
            wraplength=220,
            justify="left"
        )
        details_label.pack(pady=10, padx=10)
        
        # Champ de correction
        tk.Label(
            actions_frame,
            text="âœï¸ Correction:",
            font=("Segoe UI", 9, "bold"),
            bg="white",
            fg="#333"
        ).pack(pady=(10, 2), padx=10, anchor="w")
        
        correction_entry = tk.Entry(
            actions_frame,
            font=("Segoe UI", 10),
            bg="#f8f9fa",
            fg="#333",
            relief="solid",
            bd=1
        )
        correction_entry.pack(pady=(0, 10), padx=10, fill="x")
        
        # Boutons d'action
        def _update_session_file_capture(session_path: str, capture_id: int, new_status: str):
            """Met à jour le fichier voice_session_*.json pour refléter une correction / ignore."""
            if not session_path:
                return
            try:
                import json
                from pathlib import Path

                p = Path(session_path)
                if not p.exists():
                    return

                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Mettre à jour la capture dans captures
                captures = data.get("captures", []) or []
                for c in captures:
                    if int(c.get("id", -1)) == int(capture_id):
                        c["status"] = str(new_status)
                        c["processed"] = True
                        break

                # Retirer de unrecognized si présent
                unrec = data.get("unrecognized", []) or []
                data["unrecognized"] = [c for c in unrec if int(c.get("id", -1)) != int(capture_id)]

                with open(p, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"[WARN] Impossible de mettre à jour la session vocale: {e}")

        def _seek_video_to_timestamp(timestamp_s: float, autoplay: bool = True):
            try:
                if not self.video_player or not self.video_player.video_loaded:
                    messagebox.showwarning("Vidéo", "Aucune vidéo chargée")
                    return
                self.video_player.seek_time(float(timestamp_s))
                # Laisser le loop UI rafraîchir, mais on peut démarrer la lecture.
                if autoplay and not getattr(self, "playing", False):
                    self.toggle_play_pause()
            except Exception as e:
                print(f"[ERROR] Seek vidéo: {e}")

        def _play_wav(wav_path: str):
            """Lecture asynchrone du WAV (Windows)."""
            if not wav_path:
                messagebox.showwarning("Audio", "Aucun fichier audio associé à cette capture")
                return
            try:
                import os
                if not os.path.exists(wav_path):
                    messagebox.showwarning("Audio", f"Fichier introuvable:\n{wav_path}")
                    return
                try:
                    import winsound  # Windows only
                    winsound.PlaySound(None, winsound.SND_PURGE)
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    messagebox.showinfo("Audio", f"Lecture audio non disponible sur cette configuration.\n\nFichier:\n{wav_path}")
            except Exception as e:
                messagebox.showerror("Audio", f"Impossible de lire l'audio:\n{e}")

        def replay_selected():
            """Rejoue la vidéo au timestamp sélectionné"""
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une commande")
                return
            
            idx = selection[0]
            capture = unrecognized_captures[idx]
            timestamp = float(capture.get("video_timestamp", 0.0) or 0.0)
            _seek_video_to_timestamp(timestamp_s=timestamp, autoplay=True)
            print(f"[VOICE] Replay à {timestamp:.1f}s")

        def play_audio_selected():
            """Joue le WAV de la capture sélectionnée"""
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une commande")
                return
            idx = selection[0]
            capture = unrecognized_captures[idx]
            _play_wav(str(capture.get("audio_wav") or ""))
        
        def correct_manually():
            """Applique la correction et crée l'annotation"""
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Sélection", "Veuillez sélectionner une commande")
                return
            
            idx = selection[0]
            capture = unrecognized_captures[idx]
            
            # Récupérer la correction saisie
            corrected_text = correction_entry.get().strip()
            if not corrected_text:
                messagebox.showwarning("Correction", "Veuillez saisir une commande corrigée")
                return
            
            # Parser la commande corrigée
            parsed = self.command_parser.parse(corrected_text)

            if not parsed or not self.command_parser:
                messagebox.showerror(
                    "Erreur",
                    f"Commande non reconnue:\n'{corrected_text}'",
                )
                return

            is_valid, validation_message = self.command_parser.validate_command(parsed)
            if not (is_valid and parsed.get("action") == "nouveau_point"):
                messagebox.showerror(
                    "Erreur",
                    f"Commande incomplète / invalide:\n'{corrected_text}'\n\n{validation_message}",
                )
                return
            
            # Créer l'annotation avec le timestamp de la capture
            timestamp = capture["video_timestamp"]
            
            try:
                self._create_annotation_from_voice(parsed, timestamp)

                # Marquer la capture comme résolue dans le JSON de session
                _update_session_file_capture(session_file, int(capture.get("id", -1)), "recognized")
                
                # Retirer de la liste
                listbox.delete(idx)
                unrecognized_captures.pop(idx)
                correction_entry.delete(0, tk.END)
                
                # Message de succès
                messagebox.showinfo("✅ Succès", 
                                  f"Annotation créée:\n"
                                  f"{parsed.get('joueur')} - {parsed.get('type_point')}\n"
                                  f"{parsed.get('type_coup')}")
                
                print(f"[VOICE] Annotation créée, reste {len(unrecognized_captures)} commandes")
                    
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de créer l'annotation:\n{e}")
        
        def ignore_selected():
            """Ignore la commande sélectionnée"""
            selection = listbox.curselection()
            if not selection:
                return
            
            idx = selection[0]
            capture = unrecognized_captures[idx]
            listbox.delete(idx)
            unrecognized_captures.pop(idx)
            try:
                _update_session_file_capture(session_file, int(capture.get("id", -1)), "ignored")
            except Exception:
                pass
            print(f"[VOICE] Commande ignorée, reste {len(unrecognized_captures)} commandes")
        
        def update_details(event):
            """Met à jour les détails de la sélection"""
            selection = listbox.curselection()
            if not selection:
                return
            
            idx = selection[0]
            capture = unrecognized_captures[idx]
            timestamp = capture['video_timestamp']
            
            # Formater le timestamp en HH:MM:SS
            hours = int(timestamp // 3600)
            minutes = int((timestamp % 3600) // 60)
            seconds = timestamp % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:05.2f}"
            
            details_label.config(
                text=f"Timestamp: {time_str}\n\n"
                     f"Texte: {capture['audio_text']}\n\n"
                     f"Statut: {capture.get('status', 'unknown')}\n\n"
                     f"Capturé: {capture.get('capture_time', 'N/A')[:19]}\n\n"
                     f"Audio: {capture.get('audio_wav', '—')}"
            )
            
            # Pré-remplir le champ de correction avec le texte original
            correction_entry.delete(0, tk.END)
            correction_entry.insert(0, capture['audio_text'])
        
        listbox.bind("<<ListboxSelect>>", update_details)
        
        # Boutons
        tk.Button(
            actions_frame,
            text="â–¶ï¸ Rejouer vidéo",
            command=replay_selected,
            font=("Segoe UI", 10, "bold"),
            bg="#667eea",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(pady=5, padx=10, fill="x")

        tk.Button(
            actions_frame,
            text="🔊 Écouter audio (WAV)",
            command=play_audio_selected,
            font=("Segoe UI", 10, "bold"),
            bg="#0ea5e9",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(pady=5, padx=10, fill="x")
        
        tk.Button(
            actions_frame,
            text="âœï¸ Corriger manuellement",
            command=correct_manually,
            font=("Segoe UI", 10, "bold"),
            bg="#22c55e",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(pady=5, padx=10, fill="x")
        
        tk.Button(
            actions_frame,
            text="🗑️ Ignorer",
            command=ignore_selected,
            font=("Segoe UI", 10),
            bg="#ef4444",
            fg="white",
            relief="flat",
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(pady=5, padx=10, fill="x")
        
        # Bouton fermer (bas)
        btn_frame = tk.Frame(popup, bg="#f5f7fa")
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(
            btn_frame,
            text="✓ Terminé",
            command=popup.destroy,
            font=("Segoe UI", 11, "bold"),
            bg="#10b981",
            fg="white",
            relief="flat",
            padx=30,
            pady=10,
            cursor="hand2"
        ).pack()
        
        # Centrer le popup
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")
        
        # Focus
        popup.focus_set()
        if unrecognized_captures:
            listbox.selection_set(0)
            listbox.event_generate("<<ListboxSelect>>")
    
    def _update_voice_status_label(self, text: str):
        """Met à jour le label de statut vocal"""
        # Chercher ou créer le label de statut
        if not hasattr(self, 'voice_status_label'):
            # Le créer si nécessaire (sera fait dans _create_ui plus tard)
            return
        
        try:
            self.voice_status_label.config(text=text)
        except:
            pass
    
    # --- ANCIEN SYSTÈME (conservé) ---
    
    def toggle_voice_commands(self):
        """Active/désactive les commandes vocales"""
        if not getattr(self, "enable_handsfree_voice", False):
            messagebox.showinfo(
                "Commandes vocales",
                "Le mode 'mains-libres' est désactivé.\n\n"
                "Utilisez le nouveau mode PTT : bouton 'ACTIVER VOCAL (V)' puis V pour enregistrer.",
            )
            return
        if getattr(self, "safe_mode", False):
            messagebox.showinfo(
                "Mode safe",
                "Le mode safe est activé.\n\n"
                "Les commandes vocales sont désactivées."
            )
            return

        if not self.voice_commander:
            messagebox.showwarning(
                "Module vocal indisponible",
                "Le module vocal n'est pas installé.\n\n"
                "Installation:\n"
                "pip install SpeechRecognition pyaudio"
            )
            return
        
        if not self.voice_enabled:
            # Éviter conflit micro: si le push-to-talk est actif, le couper.
            if getattr(self, "vocal_mode_active", False):
                try:
                    # Stopper un enregistrement en cours si besoin
                    if self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False):
                        self._stop_voice_recording()
                except Exception:
                    pass

                self.vocal_mode_active = False
                if hasattr(self, "vocal_mode_button") and self.vocal_mode_button:
                    try:
                        self.vocal_mode_button.config(
                            text="🎤 ACTIVER VOCAL (V)",
                            bg="#6b7280",
                        )
                    except Exception:
                        pass

                self._refresh_voice_info_banner(level="warn", status="PTT désactivé (conflit micro avec mains-libres)")

            # Démarrer l'écoute
            if self.voice_commander.start():
                self.voice_enabled = True
                self.voice_button.config(bg="#22C55E", text="🎤 VOCAL ACTIF")
                self._update_voice_status_label("🎤 Écoute active...")
                self._refresh_voice_info_banner(level="ok", status="Mains-libres activé (format: 'stat ... à toi')")
                print(
                    "[VOICE] Mains-libres activé. Format: 'stat [commande] à toi' "
                    "(lecture, pause, annuler, sauvegarder, rapport)."
                )
            else:
                messagebox.showerror("Erreur", "Impossible de démarrer l'écoute vocale")
        else:
            # Arrêter l'écoute
            self.voice_commander.stop()
            self.voice_enabled = False
            self.voice_button.config(bg="#EF4444", text="🎤 COMMANDES VOCALES")
            self._update_voice_status_label("")
            self._refresh_voice_info_banner(level="info", status="Mains-libres désactivé")
    
    def _handle_voice_command(self, text: str):
        """
        Callback appelé quand Whisper transcrit une commande
        S'exécute dans le thread audio, on utilise after() pour la GUI
        """
        # Passer au thread principal
        self.root.after(0, lambda: self._process_voice_command(text))
    
    def _process_voice_command(self, text: str):
        """
        Traite une commande vocale - VERSION SIMPLIFIÉE QUI MARCHE
        Format requis : "stat [commande] à toi".
        Exemple : "stat faute directe arnaud à toi".
        """
        print(f"[Voice] Commande reçue: '{text}'")

        # Feedback visuel immédiat: afficher ce qui a été entendu.
        self._show_voice_tree_popup(level="info", status="Transcription vocale", raw_text=text, parsed={})
        
        # === VARIABLES POUR LE LOGGING ===
        raw_text = text
        text_clean = text.lower().strip()
        wake_word = None
        command_text = None
        parsed_result = None
        validation_result = (False, "Non validé")
        action_taken = "IGNORÉ"
        error_msg = None
        
        try:
            import re

            # Normaliser espaces pour rendre la détection robuste
            text_clean = " ".join(text_clean.split())

            def _strip_accents(s: str) -> str:
                import unicodedata
                return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

            def _normalize_voice(s: str) -> str:
                s = _strip_accents((s or "").lower().strip())
                s = re.sub(r"[^a-z0-9\s]", " ", s)
                s = re.sub(r"\s+", " ", s).strip()
                return s

            normalized = _normalize_voice(text_clean)
            
            # === VÉRIFIER SI ON ATTEND UNE COMPLÉTION ===
            # En mode complétion, on accepte soit "[réponse]", soit "stat [réponse] à toi"
            if self.pending_incomplete_command:
                completion_norm = normalized
                completion_text = text_clean
                m_completion = re.match(r"^(?:stat|statistique(?:s)?)\b\s*(.*?)\s*a\s*toi$", completion_norm)
                if m_completion:
                    completion_norm = (m_completion.group(1) or "").strip()
                    completion_text = completion_norm

                # Si phrase vide ou juste mots de contrôle du protocole, on attend
                if completion_norm in ("", "stat", "a toi", "a", "toi"):
                    self._update_voice_status_label("🎤 Compléter puis dire 'à toi'")
                    action_taken = "⏳ EN ATTENTE COMPLÉTION"
                    return

                return self._complete_pending_command(completion_text)

            def _show_common_commands_banner():
                hint = "Commandes courantes: point gagnant [joueur] [coup], faute directe [joueur], faute provoquée [attaquant] [coup] [défenseur], lecture"
                self._refresh_voice_info_banner(level="info", status=hint)
                self._show_voice_tree_popup(level="info", status="Raccourcis vocaux", raw_text=hint, parsed={})
                try:
                    if self._voice_tree_popup_hide_after_id:
                        self.root.after_cancel(self._voice_tree_popup_hide_after_id)
                    self._voice_tree_popup_hide_after_id = self.root.after(7000, self._hide_voice_tree_popup)
                except Exception:
                    pass

            # 1) Commandes directes lecture/pause (sans protocole)
            if normalized in {"pause", "pose", "stop", "arrete", "silence", "lecture", "play", "reprend", "reprends"}:
                wake_word = "DIRECT"
                if normalized in {"lecture", "play", "reprend", "reprends"}:
                    command_text = "lecture"
                else:
                    command_text = "pause"
            else:
                # 2a) "statistique [commande]" — mot déclencheur Wispr Flow, exécution directe sans "à toi"
                stat_trigger_match = re.match(r"^(?:stat|statistique(?:s)?)\s+(.+)$", normalized)
                if stat_trigger_match:
                    wake_word = "STATISTIQUE"
                    command_text = stat_trigger_match.group(1).strip()
                    # Retire "à toi" si l'utilisateur l'a quand même dit
                    command_text = re.sub(r"\s*a\s*toi\s*$", "", command_text).strip()
                else:
                # 2b) Stats directes: si la phrase commence par point gagnant / faute directe / faute provoquée
                    direct_stat_match = re.match(r"^(point gagnant|faute directe|faute provoquee)\b", normalized)
                    if direct_stat_match:
                        wake_word = "DIRECT_STAT"
                        command_text = text_clean
                    else:
                    # 3) Protocole stat/statistique ... à toi (conservé)
                    m = re.match(r"^(?:stat|statistique(?:s)?)\b\s*(.*?)\s*a\s*toi$", normalized)
                    if not m:
                        if re.match(r"^(?:stat|statistique(?:s)?)", normalized) and not re.search(r"a\s*toi$", normalized):
                            self._update_voice_status_label("🎤 Terminez par 'à toi'")
                            action_taken = "IGNORÉ (manque mot de validation 'à toi')"
                        else:
                            action_taken = "IGNORÉ (format attendu: stat/statistique ... à toi ou commande directe: pause/lecture/point gagnant/faute directe)"
                        return

                    wake_word = "STAT"
                    command_text = (m.group(1) or "").strip()

                    if not command_text:
                        self._update_voice_status_label("🎤 Dire la commande entre 'stat' et 'à toi'")
                        action_taken = "⏳ STAT seul (en attente)"
                        return
            
            # === COMMANDES SIMPLES (pas besoin de parser) ===
            
            if "pause" in command_text or "stop" in command_text:
                if self.playing:
                    self.toggle_play_pause()
                    self._update_voice_status_label("⏸️ Pause")
                    _show_common_commands_banner()
                    action_taken = "✅ EXÉCUTÉ: Pause"
                else:
                    self._update_voice_status_label("â„¹ï¸ Déjà en pause")
                    _show_common_commands_banner()
                    action_taken = "â„¹ï¸ IGNORÉ: Déjà en pause"
                validation_result = (True, "Commande simple")
                return
            
            if "lecture" in command_text or "play" in command_text:
                if not self.playing:
                    self.toggle_play_pause()
                    self._update_voice_status_label("â–¶ï¸ Lecture")
                    action_taken = "✅ EXÉCUTÉ: Lecture"
                else:
                    self._update_voice_status_label("â„¹ï¸ Déjà en lecture")
                    action_taken = "â„¹ï¸ IGNORÉ: Déjà en lecture"
                validation_result = (True, "Commande simple")
                return
            
            if "supprimer" in command_text or "supprime" in command_text:
                self.remove_last_point()
                self._hide_voice_error_banner()
                self._update_voice_status_label("🗑️ Point supprimé")
                action_taken = "✅ EXÉCUTÉ: Suppression"
                validation_result = (True, "Commande simple")
                return
            
            if "sauvegarder" in command_text or "sauver" in command_text:
                self.save_annotations()
                self._update_voice_status_label("💾 Sauvegardé")
                action_taken = "✅ EXÉCUTÉ: Sauvegarde"
                validation_result = (True, "Commande simple")
                return
            
            if "rapport" in command_text:
                self.generate_html_fast()
                self._update_voice_status_label("📊 Rapport généré")
                action_taken = "✅ EXÉCUTÉ: Rapport"
                validation_result = (True, "Commande simple")
                return
            
            # === ANNOTATIONS COMPLEXES ===
            
            if not self.command_parser:
                error_msg = "Parser non disponible"
                self._show_voice_error("âš ï¸ Parser non disponible")
                action_taken = "❌ ERREUR: Parser non disponible"
                return
            
            # Parser
            parsed_result = self.command_parser.parse(command_text)

            # Bandeau info: afficher les champs reconnus même si incomplets
            self._refresh_voice_info_banner(
                raw_text=command_text,
                parsed=parsed_result,
                level="info",
                status="Commande reçue (mains-libres)",
            )
            
            if not parsed_result:
                error_msg = f"Commande non reconnue: '{command_text}'"
                self._show_voice_error("❌ Commande non reconnue")
                action_taken = "❌ REJETÉ: Pattern non reconnu"
                return
            
            # Valider
            validation_result = self.command_parser.validate_command(parsed_result)
            is_valid, validation_message = validation_result
            
            if not is_valid:
                # === COMMANDE INCOMPLÈTE : DEMANDER CE QUI MANQUE ===
                missing_fields = self.command_parser.get_missing_fields(parsed_result)
                
                if missing_fields:
                    # 🎬 PAUSE VIDÉO AUTOMATIQUE quand info manquante
                    was_playing = self.playing
                    if was_playing:
                        self.toggle_play_pause()
                        print("[Voice] 🎬 VIDÉO EN PAUSE - En attente de complément")
                    
                    # Sauvegarder la commande incomplète
                    self.pending_incomplete_command = {
                        'parsed': parsed_result,
                        'raw': command_text,
                        'missing': missing_fields,
                        'was_playing': was_playing  # Mémoriser si la vidéo était en lecture
                    }
                    
                    # Demander le premier champ manquant
                    first_missing = missing_fields[0]
                    
                    # Messages personnalisés selon le champ
                    if first_missing == "Type de point":
                        question = "⏸️ Quel type de point ? (point gagnant / faute directe / faute provoquée)"
                    elif first_missing == "Joueur":
                        player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                        question = f"⏸️ Quel joueur ? ({' / '.join(player_names)})"
                    elif first_missing == "Défenseur":
                        player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                        question = f"⏸️ Quel défenseur/fautif ? ({' / '.join(player_names)})"
                    elif first_missing == "Type de coup":
                        question = "⏸️ Quel type de coup ? (service / volée / fond de court / smash / lob)"
                    else:
                        question = f"⏸️ {first_missing} ?"
                    
                    self._update_voice_status_label(question)

                    self._refresh_voice_info_banner(
                        raw_text=command_text,
                        parsed=parsed_result,
                        missing=missing_fields,
                        level="warn",
                        status="Champs manquants",
                    )
                    
                    action_taken = f"⏸️ PAUSE + EN ATTENTE: {first_missing}"
                    return
                else:
                    # Erreur sans détection de champs manquants
                    error_entry = {
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "command": command_text,
                        "error": validation_message
                    }
                    self.voice_errors.append(error_entry)
                    
                    if len(self.voice_errors) > 10:
                        self.voice_errors.pop(0)
                    
                    self._show_voice_error(validation_message)
                    
                    if self.playing:
                        self.toggle_play_pause()
                    
                    self._update_voice_status_label("❌ COMMANDE INCOMPLÈTE")
                    self._refresh_voice_info_banner(
                        raw_text=command_text,
                        parsed=parsed_result,
                        level="error",
                        status="Commande incomplète",
                    )
                    self._notify_ollama_window()
                    
                    action_taken = f"❌ REJETÉ: {validation_message}"
                    error_msg = validation_message
                    return
            
            # === ENREGISTRER ===
            self._hide_voice_error_banner()
            
            joueur = parsed_result.get('joueur')
            defenseur = parsed_result.get('defenseur')
            type_point = parsed_result.get('type_point')
            type_coup = parsed_result.get('type_coup')
            zone = parsed_result.get('zone')
            diagonale = parsed_result.get('diagonale')
            label = parsed_result.get('label')
            
            print(f"[Voice] ✅ Commande COMPLÈTE validée - Enregistrement en cours...")

            self._refresh_voice_info_banner(
                raw_text=command_text,
                parsed=parsed_result,
                level="ok",
                status="Commande validée",
            )
            
            self._add_voice_annotation(
                joueur=joueur,
                type_point=type_point,
                type_coup=type_coup,
                zone=zone,
                diagonale=diagonale,
                label=label,
                defenseur=defenseur
            )
            
            if defenseur:
                self._update_voice_status_label(f"✅ {joueur} → {defenseur} - {type_coup or type_point}")
                action_taken = f"✅ ENREGISTRÉ: {type_point} - {joueur} → {defenseur} - {type_coup or 'N/A'}"
            else:
                self._update_voice_status_label(f"✅ {joueur} - {type_coup or type_point}")
                action_taken = f"✅ ENREGISTRÉ: {type_point} - {joueur} - {type_coup or 'N/A'}"
            
        finally:
            # === LOGGING ===
            if self.voice_logger:
                try:
                    self.voice_logger.log_command(
                        raw_text=raw_text,
                        cleaned_text=text_clean,
                        wake_word=wake_word,
                        command_text=command_text or "",
                        parsed_result=parsed_result,
                        validation_result=validation_result,
                        action_taken=action_taken,
                        error=error_msg
                    )
                except Exception as log_error:
                    print(f"[VoiceLogger] Erreur logging: {log_error}")
    
    def _process_voice_command_OLD(self, text: str):
        """
        Traite une commande vocale avec système de DOUBLE CONFIRMATION
        NOUVEAU FORMAT : "OK [commande] OK"
        Exemple : "OK point Arnaud service OK"
        
        Flow :
        1. Premier "OK" → Démarrer l'écoute
        2. Capturer la commande
        3. Second "OK" → Valider et exécuter
        """
        print(f"[Voice] Commande reçue: '{text}'")
        
        # === VARIABLES POUR LE LOGGING ===
        raw_text = text
        text_clean = text.lower().strip()
        wake_word = None
        command_text = None
        parsed_result = None
        validation_result = (False, "Non validé")
        action_taken = "IGNORÉ"
        error_msg = None
        
        try:
            import time
            
            # === CAS 1 : JUSTE "OK" (confirmation ou démarrage) ===
            if text_clean == "ok":
                # Vérifier s'il y a une commande en attente
                if self.pending_command:
                    # C'est le OK de validation !
                    wake_word = "OK"
                    command_text = self.pending_command['text']
                    parsed_result = self.pending_command['parsed']
                    
                    # Valider et exécuter
                    is_valid, validation_message = self.command_parser.validate_command(parsed_result)
                    validation_result = (is_valid, validation_message)
                    
                    if is_valid:
                        # Exécuter la commande
                        joueur = parsed_result.get('joueur')
                        type_point = parsed_result.get('type_point')
                        type_coup = parsed_result.get('type_coup')
                        zone = parsed_result.get('zone')
                        diagonale = parsed_result.get('diagonale')
                        label = parsed_result.get('label')
                        
                        self._add_voice_annotation(
                            joueur=joueur,
                            type_point=type_point,
                            type_coup=type_coup,
                            zone=zone,
                            diagonale=diagonale,
                            label=label
                        )
                        
                        self._hide_voice_error_banner()
                        self._update_voice_status_label(f"✅ Point enregistré : {joueur} - {type_coup or 'N/A'}")
                        action_taken = f"✅ VALIDÉ ET ENREGISTRÉ: {type_point} - {joueur} - {type_coup or 'N/A'}"
                    else:
                        error_msg = validation_message
                        self._show_voice_error(validation_message)
                        self._update_voice_status_label("❌ COMMANDE INCOMPLÈTE")
                        action_taken = f"❌ REJETÉ: {validation_message}"
                    
                    # Effacer la commande en attente
                    self.pending_command = None
                    self.pending_command_time = None
                    return
                else:
                    # Premier OK sans commande → attendre la suite
                    wake_word = "OK"
                    self._update_voice_status_label("🎤 Dites votre commande puis 'OK'")
                    action_taken = "⏳ EN ATTENTE de commande"
                    return
            
            # === CAS 2 : COMMANDE COMMENÇANT PAR "OK" ===
            if text_clean.startswith("ok "):
                wake_word = "OK"
                command_text = text_clean[3:].strip()  # Enlever "ok "
                
                # Vérifier si la commande se termine par "ok"
                if command_text.endswith(" ok"):
                    # Format complet : "OK point Arnaud service OK"
                    command_text = command_text[:-3].strip()  # Enlever " ok"
                    
                    # Parser immédiatement
                    if not self.command_parser:
                        error_msg = "Parser non disponible"
                        self._show_voice_error("âš ï¸ Parseur non disponible")
                        action_taken = "❌ ERREUR: Parser non disponible"
                        return
                    
                    parsed_result = self.command_parser.parse(command_text)
                    
                    if not parsed_result:
                        error_msg = f"Commande non reconnue: '{command_text}'"
                        self._show_voice_error(f"❌ Commande non reconnue")
                        action_taken = "❌ REJETÉ: Aucun pattern reconnu"
                        return
                    
                    # === COMMANDES SIMPLES (pas de validation) ===
                    # Supprimer
                    if "supprimer" in command_text or "supprime" in command_text:
                        self.remove_last_point()
                        self._hide_voice_error_banner()
                        self._update_voice_status_label("🗑️ Point supprimé")
                        action_taken = "✅ EXÉCUTÉ: Suppression du dernier point"
                        validation_result = (True, "Commande simple")
                        return
                    
                    # Pause
                    if "pause" in command_text or "arrête" in command_text or "stop" in command_text:
                        if self.playing:
                            self.toggle_play_pause()
                            self._update_voice_status_label("⏸️ Pause")
                            action_taken = "✅ EXÉCUTÉ: Pause activée"
                        else:
                            self._update_voice_status_label("â„¹ï¸ Déjà en pause")
                            action_taken = "â„¹ï¸ IGNORÉ: Déjà en pause"
                        validation_result = (True, "Commande simple")
                        return
                    
                    # Lecture
                    if "lecture" in command_text or "play" in command_text or "joue" in command_text:
                        if not self.playing:
                            self.toggle_play_pause()
                            self._update_voice_status_label("â–¶ï¸ Lecture démarrée")
                            action_taken = "✅ EXÉCUTÉ: Lecture démarrée"
                        else:
                            self._update_voice_status_label("â„¹ï¸ Déjà en lecture")
                            action_taken = "â„¹ï¸ IGNORÉ: Déjà en lecture"
                        validation_result = (True, "Commande simple")
                        return
                    
                    # Sauvegarder
                    if "sauvegarder" in command_text or "sauver" in command_text or "sauvegarde" in command_text:
                        self.save_annotations()
                        self._update_voice_status_label("💾 Sauvegardé")
                        action_taken = "✅ EXÉCUTÉ: Annotations sauvegardées"
                        validation_result = (True, "Commande simple")
                        return
                    
                    # Rapport
                    if "rapport" in command_text or "générer rapport" in command_text:
                        self.generate_html_fast()
                        self._update_voice_status_label("📊 Rapport rapide généré")
                        action_taken = "✅ EXÉCUTÉ: Rapport généré"
                        validation_result = (True, "Commande simple")
                        return
                    
                    # === ANNOTATIONS COMPLEXES : VALIDER ET EXÉCUTER ===
                    validation_result = self.command_parser.validate_command(parsed_result)
                    is_valid, validation_message = validation_result
                    
                    if is_valid:
                        # Exécuter immédiatement
                        joueur = parsed_result.get('joueur')
                        type_point = parsed_result.get('type_point')
                        type_coup = parsed_result.get('type_coup')
                        zone = parsed_result.get('zone')
                        diagonale = parsed_result.get('diagonale')
                        label = parsed_result.get('label')
                        
                        self._add_voice_annotation(
                            joueur=joueur,
                            type_point=type_point,
                            type_coup=type_coup,
                            zone=zone,
                            diagonale=diagonale,
                            label=label
                        )
                        
                        self._hide_voice_error_banner()
                        self._update_voice_status_label(f"✅ Point enregistré : {joueur} - {type_coup or 'N/A'}")
                        action_taken = f"✅ VALIDÉ ET ENREGISTRÉ: {type_point} - {joueur} - {type_coup or 'N/A'}"
                    else:
                        error_msg = validation_message
                        self._show_voice_error(validation_message)
                        self._update_voice_status_label("❌ COMMANDE INCOMPLÈTE")
                        action_taken = f"❌ REJETÉ: {validation_message}"
                    
                    return
                
                else:
                    # Format incomplet : "OK point Arnaud service" (sans OK final)
                    # Mettre en attente de confirmation
                    
                    if not self.command_parser:
                        error_msg = "Parser non disponible"
                        self._show_voice_error("âš ï¸ Parseur non disponible")
                        action_taken = "❌ ERREUR: Parser non disponible"
                        return
                    
                    parsed_result = self.command_parser.parse(command_text)
                    
                    if not parsed_result:
                        error_msg = f"Commande non reconnue: '{command_text}'"
                        self._show_voice_error(f"❌ Commande non reconnue")
                        action_taken = "❌ REJETÉ: Aucun pattern reconnu"
                        return
                    
                    # Stocker en attente
                    self.pending_command = {
                        'text': command_text,
                        'parsed': parsed_result,
                        'raw': raw_text
                    }
                    self.pending_command_time = time.time()
                    
                    # Afficher ce qui a été compris
                    joueur = parsed_result.get('joueur', 'N/A')
                    type_coup = parsed_result.get('type_coup', 'N/A')
                    self._update_voice_status_label(f"⏳ EN ATTENTE : {joueur} - {type_coup} → Dites 'OK' pour valider")
                    action_taken = f"⏳ EN ATTENTE DE VALIDATION: {joueur} - {type_coup}"
                    validation_result = (False, "En attente de confirmation OK")
                    return
            
            else:
                # Pas de "OK" au début → ignorer
                action_taken = "IGNORÉ (pas de mot de réveil OK)"
                return
            
        finally:
            # === LOGGING COMPLET ===
            if self.voice_logger:
                try:
                    self.voice_logger.log_command(
                        raw_text=raw_text,
                        cleaned_text=text_clean,
                        wake_word=wake_word,
                        command_text=command_text or "",
                        parsed_result=parsed_result,
                        validation_result=validation_result,
                        action_taken=action_taken,
                        error=error_msg
                    )
                except Exception as log_error:
                    print(f"[VoiceLogger] Erreur logging: {log_error}")
    
    def _add_voice_annotation(self, joueur=None, type_point=None, type_coup=None, 
                              zone=None, diagonale=None, label=None, defenseur=None):
        """Ajoute une annotation depuis une commande vocale - HYBRIDE avec pause/reprise"""
        # Récupérer timestamp et frame
        timestamp = self.video_player.get_vlc_position()
        frame = int(timestamp * 30)  # Approximation 30 FPS
        
        # Joueur par défaut
        if not joueur:
            joueur = self.players[0] if self.players else "Joueur 1"
        
        # Type de point par défaut
        if not type_point:
            type_point = 'point_gagnant'
        
        # Appeler la méthode appropriée selon le type de point
        if type_point == 'faute_directe':
            self.annotation_manager.add_faute_directe(
                joueur=joueur,
                timestamp=timestamp,
                frame=frame,
                type_coup=type_coup
            )
        elif type_point == 'point_gagnant':
            self.annotation_manager.add_point_gagnant(
                joueur=joueur,
                timestamp=timestamp,
                frame=frame,
                type_coup=type_coup
            )
        elif type_point == 'faute_provoquee':
            # Pour faute provoquée, utiliser defenseur fourni ou fallback
            if not defenseur:
                defenseur = zone if zone else (self.players[1] if len(self.players) > 1 else "Adversaire")
            self.annotation_manager.add_faute_provoquee(
                attaquant=joueur,
                defenseur=defenseur,
                timestamp=timestamp,
                frame=frame,
                type_coup_attaquant=type_coup
            )
        
        # Construire le message de feedback
        parts = []
        if joueur:
            parts.append(joueur)
        if type_coup:
            parts.append(type_coup.replace('_', ' '))
        if type_point:
            parts.append(type_point.replace('_', ' '))
        if defenseur and type_point == 'faute_provoquee':
            parts.append(f"→ {defenseur}")
        
        feedback = " - ".join(parts) if parts else "Point ajouté"
        
        # Feedback visuel
        self._update_voice_status_label(f"✅ {feedback}")
        self._notify_ollama_window()
    
    def _complete_pending_command(self, response_text: str):
        """
        Complète une commande incomplète avec la réponse de l'utilisateur
        HYBRIDE: Reprend automatiquement la vidéo une fois la commande validée
        """
        if not self.pending_incomplete_command:
            return
        
        pending = self.pending_incomplete_command
        parsed = pending['parsed']
        missing = pending['missing']
        was_playing = pending.get('was_playing', False)  # Récupérer si la vidéo était en lecture
        
        # Normaliser la réponse
        response_normalized = self.command_parser.normaliser_texte(response_text) if hasattr(self.command_parser, 'normaliser_texte') else response_text.lower()

        # Mettre à jour le bandeau avec la réponse brute (utile en mode “question/réponseâ€)
        self._refresh_voice_info_banner(
            raw_text=response_text,
            parsed=parsed,
            missing=missing,
            level="info",
            status="Réponse reçue",
        )
        
        # Parser la réponse pour extraire l'information manquante
        first_missing = missing[0]
        
        if first_missing == "Joueur":
            # Extraire le joueur de la réponse
            joueur = self.command_parser._extract_joueur(response_normalized)
            if joueur:
                parsed['joueur'] = joueur
                self._update_voice_status_label(f"✅ Joueur: {joueur}")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status=f"Joueur: {joueur}")
            else:
                self._update_voice_status_label(f"❌ Joueur non reconnu. Dites le nom clairement.")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="warn", status="Joueur non reconnu")
                return
        
        elif first_missing == "Défenseur":
            # Extraire le défenseur/fautif de la réponse
            defenseur = self.command_parser._extract_joueur(response_normalized)
            if defenseur:
                parsed['defenseur'] = defenseur
                self._update_voice_status_label(f"✅ Défenseur: {defenseur}")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status=f"Défenseur: {defenseur}")
            else:
                self._update_voice_status_label(f"❌ Défenseur non reconnu. Dites le nom clairement.")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="warn", status="Défenseur non reconnu")
                return
        
        elif first_missing == "Type de point":
            # Extraire le type de point avec normalisation
            if "faute provoquée" in response_normalized or "faute provoquer" in response_normalized:
                parsed['type_point'] = 'faute_provoquee'
                self._update_voice_status_label("✅ Type: Faute provoquée")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status="Type: Faute provoquée")
            elif "faute directe" in response_normalized or ("faute" in response_normalized and "provoqu" not in response_normalized):
                parsed['type_point'] = 'faute_directe'
                self._update_voice_status_label("✅ Type: Faute directe")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status="Type: Faute directe")
            elif "point" in response_normalized or "gagnant" in response_normalized:
                parsed['type_point'] = 'point_gagnant'
                self._update_voice_status_label("✅ Type: Point gagnant")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status="Type: Point gagnant")
            else:
                self._update_voice_status_label("❌ Type non reconnu. Dites 'point gagnant', 'faute directe' ou 'faute provoquée'")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="warn", status="Type de point non reconnu")
                return
        
        elif first_missing == "Type de coup":
            # Extraire le type de coup avec normalisation
            type_coup_detected = None
            for action, pattern in self.command_parser.patterns.items():
                if action in ['service', 'smash', 'vollee', 'bandeja', 'vibora', 'coup_droit',
                             'revers', 'lob', 'chiquita', 'amorti', 'sortie_vitre', 'contre_vitre',
                             'fond_de_court', 'balle_haute']:
                    if re.search(pattern, response_normalized, re.IGNORECASE):
                        type_coup_detected = action
                        break
            
            if type_coup_detected:
                parsed['type_coup'] = type_coup_detected
                self._update_voice_status_label(f"✅ Coup: {type_coup_detected}")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="ok", status=f"Coup: {type_coup_detected}")
            else:
                self._update_voice_status_label("❌ Type de coup non reconnu. Répétez clairement.")
                self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="warn", status="Type de coup non reconnu")
                return
        
        # Retirer le champ de la liste des manquants
        missing.pop(0)

        self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="info")
        
        # S'il reste des champs manquants, demander le suivant
        if missing:
            next_missing = missing[0]
            
            if next_missing == "Type de point":
                question = "⏸️ Quel type de point ? (point gagnant / faute directe / faute provoquée)"
            elif next_missing == "Joueur":
                player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                question = f"⏸️ Quel joueur ? ({' / '.join(player_names)})"
            elif next_missing == "Défenseur":
                player_names = [p.get("nom") if isinstance(p, dict) else p for p in self.players]
                question = f"⏸️ Quel défenseur/fautif ? ({' / '.join(player_names)})"
            elif next_missing == "Type de coup":
                question = "⏸️ Quel type de coup ? (service / volée / fond de court / smash / lob)"
            else:
                question = f"⏸️ {next_missing} ?"
            
            self._update_voice_status_label(question)
            self._refresh_voice_info_banner(parsed=parsed, missing=missing, level="warn", status=question)
            return
        
        # Tous les champs sont remplis : valider et enregistrer
        validation_result = self.command_parser.validate_command(parsed)
        is_valid, validation_message = validation_result
        
        if is_valid:
            # Enregistrer
            self._add_voice_annotation(
                joueur=parsed.get('joueur'),
                type_point=parsed.get('type_point'),
                type_coup=parsed.get('type_coup'),
                zone=parsed.get('zone'),
                diagonale=parsed.get('diagonale'),
                label=parsed.get('label'),
                defenseur=parsed.get('defenseur')
            )
            
            self._update_voice_status_label(f"✅ VALIDÉ + ENREGISTRÉ")
            self._refresh_voice_info_banner(parsed=parsed, missing=None, level="ok", status="VALIDÉ + ENREGISTRÉ")
            
            # 🎬 REPRENDRE LA VIDÉO AUTOMATIQUEMENT si elle était en lecture
            if was_playing and not self.playing:
                self.root.after(500, self.toggle_play_pause)  # Petit délai pour laisser le temps à l'utilisateur de voir la validation
                print("[Voice] 🎬 REPRISE AUTOMATIQUE DE LA VIDÉO")
            
            # Effacer la commande en attente
            self.pending_incomplete_command = None
        else:
            self._update_voice_status_label(f"❌ {validation_message}")
            self._refresh_voice_info_banner(parsed=parsed, missing=None, level="error", status=validation_message)
            
            # Reprendre la vidéo même en cas d'erreur
            if was_playing and not self.playing:
                self.root.after(1000, self.toggle_play_pause)
            
            self.pending_incomplete_command = None
    
    def _update_voice_status_label(self, text: str):
        """Met à jour le label de statut vocal"""
        if hasattr(self, 'voice_status_label') and self.voice_status_label:
            self.voice_status_label.config(text=text)
        else:
            # Fallback: afficher dans la console
            if text:
                safe_text = text.replace("🗣️", "[VOICE]").replace("🎤", "[MIC]").replace("❌", "[ERR]").replace("âš ï¸", "[WARN]").replace("✅", "[OK]").replace("â†©ï¸", "[UNDO]").replace("💾", "[SAVE]").replace("📊", "[REPORT]").replace("⏸️", "[PAUSE]").replace("â–¶ï¸", "[PLAY]")
                print(f"[Voice Status] {safe_text}")
    
    def _show_voice_error(self, error_message: str):
        """Affiche le bandeau d'erreur rouge avec le message"""
        if hasattr(self, 'voice_error_banner') and hasattr(self, 'voice_error_label'):
            self.voice_error_label.config(text=f"âš ï¸ {error_message}")
            self.voice_error_banner.pack(fill="x", side="top", before=self.vlc_frame.master)
            
            # Auto-cacher après 10 secondes
            self.root.after(10000, self._hide_voice_error_banner)

        # Synchroniser aussi le bandeau d'infos
        self._refresh_voice_info_banner(level="error", status=error_message)
    
    def _hide_voice_error_banner(self):
        """Cache le bandeau d'erreur"""
        if hasattr(self, 'voice_error_banner'):
            self.voice_error_banner.pack_forget()

    def _refresh_voice_info_banner(
        self,
        raw_text: str = None,
        parsed: dict = None,
        missing: list = None,
        level: str = "info",
        status: str = None,
    ):
        """Met à jour le bandeau d'informations vocales (touche + champs reconnus)."""
        if not hasattr(self, "voice_info_banner"):
            return

        try:
            colors = {
                "info": ("#111827", "#E5E7EB"),
                "ok": ("#065F46", "#ECFDF5"),
                "warn": ("#92400E", "#FFFBEB"),
                "error": ("#7F1D1D", "#FEF2F2"),
            }
            bg, fg = colors.get(level, colors["info"])

            ptt_key = "V"
            ptt_state = "ACTIF" if getattr(self, "vocal_mode_active", False) else "INACTIF"
            handsfree_state = "ACTIF" if getattr(self, "voice_enabled", False) else "INACTIF"
            is_recording = bool(self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False))
            rec_state = "EN COURS" if is_recording else "—"
            hint = f"PTT: appuyer {ptt_key} = start/stop"

            title_parts = [f"🎤 PTT: {ptt_state}", f"REC: {rec_state}", f"Mains-libres: {handsfree_state}", hint]
            if status:
                title_parts.append(str(status))
            if raw_text:
                rt = " ".join(str(raw_text).split())
                if len(rt) > 80:
                    rt = rt[:77] + "…"
                title_parts.append(f"🗣️ \"{rt}\"")

            def fmt(label: str, value) -> str:
                if value is None or value == "":
                    return f"{label}: —"
                return f"{label}: {value}"

            def humanize(field: str, value):
                if value is None:
                    return None
                if field == "type_point":
                    return {
                        "point_gagnant": "Point gagnant",
                        "faute_directe": "Faute directe",
                        "faute_provoquee": "Faute provoquée",
                    }.get(value, value)
                if field == "type_coup":
                    return {
                        "service": "Service",
                        "smash": "Smash",
                        "vollee": "Volée",
                        "bandeja": "Bandeja",
                        "vibora": "Víbora",
                        "coup_droit": "Coup droit",
                        "revers": "Revers",
                        "lob": "Lob",
                        "chiquita": "Chiquita",
                        "amorti": "Amorti",
                        "sortie_vitre": "Sortie de vitre",
                        "contre_vitre": "Contre-vitre",
                        "fond_de_court": "Fond de court",
                        "balle_haute": "Balle haute",
                    }.get(value, value)
                return value

            # Drapeau vert/rouge: "stat reconnue" = commande valide + nouveau point
            recognized_flag = None
            if parsed and self.command_parser:
                try:
                    is_valid, _msg = self.command_parser.validate_command(parsed)
                    recognized_flag = bool(is_valid and parsed.get("action") == "nouveau_point")
                except Exception:
                    recognized_flag = None

            if recognized_flag is True:
                flag_text = "🟩 STAT RECONNUE"
            elif recognized_flag is False:
                flag_text = "🟥 STAT NON RECONNUE"
            else:
                flag_text = "⬜ STAT: —"

            # Affichage en arbre (multiligne)
            if parsed:
                stat_label = humanize("type_point", parsed.get("type_point"))
                fields_lines = [
                    f"{flag_text}",
                    fmt("Stat", stat_label),
                    f"  ├─ {fmt('Joueur', parsed.get('joueur'))}",
                    f"  ├─ {fmt('Défenseur', parsed.get('defenseur'))}",
                    f"  ├─ {fmt('Coup', humanize('type_coup', parsed.get('type_coup')))}",
                    f"  ├─ {fmt('Zone', parsed.get('zone'))}",
                    f"  ├─ {fmt('Diagonale', parsed.get('diagonale'))}",
                    f"  └─ {fmt('Label', parsed.get('label'))}",
                ]
            else:
                fields_lines = [
                    f"{flag_text}",
                    "Stat: —",
                    "  ├─ Joueur: —",
                    "  ├─ Défenseur: —",
                    "  ├─ Coup: —",
                    "  ├─ Zone: —",
                    "  ├─ Diagonale: —",
                    "  └─ Label: —",
                ]

            if missing:
                miss = ", ".join([str(m) for m in missing])
                fields_lines.append(f"Manque: {miss}")

            self.voice_info_banner.configure(bg=bg)
            self.voice_info_title.configure(text="  |  ".join(title_parts), bg=bg, fg=fg)
            self.voice_info_fields.configure(text="\n".join(fields_lines), bg=bg, fg=fg)

            # Si le bandeau n'est pas affiché, on évite qu'il prenne de la place.
            # (Il est masqué par défaut: popup arbre uniquement lors de l'appui sur V.)
            if not SHOW_VOICE_INFO_BANNER:
                try:
                    self.voice_info_banner.pack_forget()
                except Exception:
                    pass
        except Exception:
            pass
    
    # ============= MONITORING LIVE =============
    
    def toggle_live_monitor(self):
        """Ouvre/ferme la fenêtre de monitoring live"""
        if self.live_monitor and self.live_monitor.winfo_exists():
            self.live_monitor.destroy()
            self.live_monitor = None
        else:
            self._create_live_monitor()
    
    def _create_live_monitor(self):
        """Crée la fenêtre de monitoring en temps réel"""
        self.live_monitor = tk.Toplevel(self.root)
        self.live_monitor.title("📊 Monitoring Live")
        self.live_monitor.geometry("400x300")
        self.live_monitor.configure(bg="#1a1a1a")
        
        # Toujours en premier plan
        self.live_monitor.attributes('-topmost', True)
        
        # Header
        header = tk.Label(
            self.live_monitor,
            text="📊 STATS LIVE",
            font=("Helvetica", 14, "bold"),
            bg="#1a1a1a",
            fg="#10b981"
        )
        header.pack(pady=10)
        
        # Container pour les stats
        stats_frame = tk.Frame(self.live_monitor, bg="#1a1a1a")
        stats_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        # Stocker les labels pour mise à jour
        self.live_monitor_labels = {}
        
        # Créer une ligne pour chaque joueur
        for i, joueur in enumerate(self.players, 1):
            # Frame joueur
            player_frame = tk.Frame(stats_frame, bg="#262626", relief="solid", borderwidth=1)
            player_frame.pack(fill="x", pady=5)
            
            # Nom joueur
            name_label = tk.Label(
                player_frame,
                text=f"🎾 {joueur}",
                font=("Helvetica", 10, "bold"),
                bg="#262626",
                fg="#ffffff",
                anchor="w"
            )
            name_label.pack(fill="x", padx=8, pady=(5, 2))
            
            # Stats frame
            stats_container = tk.Frame(player_frame, bg="#262626")
            stats_container.pack(fill="x", padx=8, pady=(0, 5))
            
            # Créer les 4 labels de stats
            stats_labels = {}
            stat_names = [
                ("PG", "Points Gagnants", "#10b981"),
                ("FD", "Fautes Directes", "#ef4444"),
                ("FP", "Fautes Provoquées", "#f59e0b"),
                ("FS", "Fautes Subies", "#3b82f6")
            ]
            
            for short, full, color in stat_names:
                stat_frame = tk.Frame(stats_container, bg="#262626")
                stat_frame.pack(side="left", expand=True, fill="x")
                
                label = tk.Label(
                    stat_frame,
                    text=f"{short}: 0",
                    font=("Helvetica", 9),
                    bg="#262626",
                    fg=color
                )
                label.pack()
                stats_labels[short] = label
            
            self.live_monitor_labels[f"J{i}"] = stats_labels
        
        # Bouton fermer
        close_btn = tk.Button(
            self.live_monitor,
            text="✖ Fermer",
            command=self.toggle_live_monitor,
            bg="#ef4444",
            fg="white",
            font=("Helvetica", 9, "bold"),
            relief="flat",
            cursor="hand2"
        )
        close_btn.pack(pady=10)
        
        # Première mise à jour
        self._update_live_monitor()
    
    def _update_live_monitor(self):
        """Met à jour les stats du monitoring"""
        if not self.live_monitor or not self.live_monitor.winfo_exists():
            return
        
        # Récupérer les stats actuelles
        match_data = self.annotation_manager.get_match_data()
        
        # Mettre à jour chaque joueur
        for i in range(1, 5):
            joueur_key = f"J{i}"
            if joueur_key in self.live_monitor_labels:
                labels = self.live_monitor_labels[joueur_key]
                
                # Compter les stats
                pg = sum(1 for p in match_data.get('points', []) 
                        if p.get('joueur') == i and p.get('type') == 'point_gagnant')
                fd = sum(1 for p in match_data.get('points', []) 
                        if p.get('joueur') == i and p.get('type') == 'faute_directe')
                fp = sum(1 for p in match_data.get('points', []) 
                        if p.get('defenseur') == i and p.get('type') == 'point_gagnant')
                fs = sum(1 for p in match_data.get('points', []) 
                        if p.get('defenseur') == i and p.get('type') == 'faute_directe')
                
                # Mettre à jour les labels
                labels['PG'].config(text=f"PG: {pg}")
                labels['FD'].config(text=f"FD: {fd}")
                labels['FP'].config(text=f"FP: {fp}")
                labels['FS'].config(text=f"FS: {fs}")
    
    def toggle_vocal_mode(self):
        """Active/désactive le mode vocal (touche V pour push-to-talk)"""
        self.vocal_mode_active = not self.vocal_mode_active
        
        if self.vocal_mode_active:
            # Éviter conflit micro: si les commandes vocales mains-libres sont actives, les arrêter.
            if getattr(self, "voice_enabled", False) and self.voice_commander:
                try:
                    self.voice_commander.stop()
                except Exception:
                    pass

                self.voice_enabled = False
                if hasattr(self, "voice_button") and self.voice_button:
                    try:
                        self.voice_button.config(bg="#EF4444", text="🎤 COMMANDES VOCALES")
                    except Exception:
                        pass

            # Mode activé - bouton vert
            self.vocal_mode_button.config(
                text="🎤 VOCAL ACTIF ✓",
                bg="#10b981"
            )
            print("[VOCAL] Mode vocal ACTIVÉ - Utilisez la touche V pour parler")
            self._refresh_voice_info_banner(level="ok", status="PTT activé (mains-libres désactivé si besoin)")
            self._set_rec_indicator_mode("idle")
            self._append_voice_log("Mode vocal active (PTT V)")
        else:
            # Si un enregistrement est en cours, on stoppe proprement.
            try:
                if self.voice_batch_recorder and getattr(self.voice_batch_recorder, "is_recording", False):
                    self._stop_voice_recording()
            except Exception:
                pass

            # Mode désactivé - bouton gris
            self.vocal_mode_button.config(
                text="🎤 ACTIVER VOCAL (V)",
                bg="#6b7280"
            )
            print("[VOCAL] Mode vocal DÉSACTIVÉ")
            self._refresh_voice_info_banner(level="info", status="PTT désactivé")
            self._hide_voice_tree_popup()
            self._set_rec_indicator_mode("idle")
            self._append_voice_log("Mode vocal desactive")
    
    def show_voice_review(self):
        """Affiche le popup de review des commandes vocales non reconnues"""
        import json
        from pathlib import Path
        
        # Chercher le dernier fichier de session vocale
        data_dir = Path("data")
        voice_sessions = list(data_dir.glob("voice_session_*.json"))
        
        if not voice_sessions:
            messagebox.showinfo("Review Vocal", "Aucune session vocale trouvée.")
            return
        
        # Prendre la plus récente
        latest_session = max(voice_sessions, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest_session, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            unrecognized = session_data.get("unrecognized", []) or []

            if not unrecognized:
                messagebox.showinfo(
                    "Review Vocal",
                    "Aucune commande à corriger dans cette session (tout est reconnu / déjà corrigé).",
                )
                return

            self._show_voice_review_popup(unrecognized, session_file=str(latest_session))
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de charger la session:\n{e}")
            _log_ui_exception("open_voice_review", e)


def main():
    """Lance l'application"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
