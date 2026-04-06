"""Portable video-first UI with minimal manual stats input."""

from __future__ import annotations

import json
import re
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.annotations.annotation_manager import AnnotationManager
from app.exports.csv_exporter import CSVExporter
from app.exports.html_generator2 import HTMLGenerator2
from app.exports.json_exporter import JSONExporter
from app.video.video_player import VideoPlayer


TYPE_OPTIONS = [
    ("Point gagnant", "point_gagnant"),
    ("Faute directe", "faute_directe"),
    ("Faute provoquee", "faute_provoquee"),
]
TYPE_LABEL_TO_CODE = dict(TYPE_OPTIONS)
TYPE_CODE_TO_LABEL = {code: label for label, code in TYPE_OPTIONS}

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _candidate_resource_paths(relative_path: str) -> list[Path]:
    runtime_base = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
    return [
        Path.cwd() / relative_path,
        runtime_base / relative_path,
        PROJECT_ROOT / relative_path,
    ]


def _first_existing_path(relative_path: str) -> Path | None:
    for path in _candidate_resource_paths(relative_path):
        if path.exists():
            return path
    return None


def _load_default_players() -> list[str]:
    players_path = _first_existing_path("app/config/players.json")
    if not players_path:
        return ["Joueur 1", "Joueur 2", "Joueur 3", "Joueur 4"]

    try:
        data = json.loads(players_path.read_text(encoding="utf-8"))
        players = [str(player).strip() for player in data.get("joueurs", []) if str(player).strip()]
        if players:
            while len(players) < 4:
                players.append(f"Joueur {len(players) + 1}")
            return players[:4]
    except Exception:
        pass
    return ["Joueur 1", "Joueur 2", "Joueur 3", "Joueur 4"]


def _safe_filename(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (value or "").strip()).strip("._")
    return cleaned or fallback


def _format_seconds(seconds: float) -> str:
    total_seconds = max(float(seconds or 0.0), 0.0)
    minutes = int(total_seconds // 60)
    remaining = total_seconds - (minutes * 60)
    return f"{minutes:02d}:{remaining:05.2f}"


class PortableVideoSimpleWindow:
    """Compact video player plus minimal stat entry workflow."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PFPADEL Video Simple")
        self.fullscreen = False
        self.immersive_video_mode = False
        self.sidebar_visible = True
        self.sidebar_target_width = 320
        self._sidebar_hidden_for_fullscreen = False
        self._set_window_geometry()
        self._configure_style()
        self._load_icon()

        self.video_player = VideoPlayer()
        self.json_exporter = JSONExporter()
        self.csv_exporter = CSVExporter()
        self.html_generator = HTMLGenerator2()

        self.default_players = _load_default_players()
        self.player_vars = [tk.StringVar(value=value) for value in self.default_players]
        self.session_name_var = tk.StringVar(value=f"session_video_{datetime.now():%Y%m%d_%H%M}")
        self.point_type_var = tk.StringVar(value=TYPE_OPTIONS[0][0])
        self.player_var = tk.StringVar()
        self.defender_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Pret")
        self.video_name_var = tk.StringVar(value="Aucune video")
        self.current_time_var = tk.StringVar(value="00:00.00 / 00:00.00")
        self.progress_var = tk.DoubleVar(value=0.0)

        self.current_video_path: str | None = None
        self.progress_dragging = False
        self.annotation_manager = AnnotationManager(data_folder="data", enable_background_ai=False)
        self.annotation_manager.set_players(self.get_players())

        for variable in self.player_vars:
            variable.trace_add("write", self._on_players_changed)

        self._ensure_output_dirs()
        self._build_ui()
        self._refresh_player_choices()
        self._bind_shortcuts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self._apply_video_first_layout)
        self.root.after(200, self._tick)

    def _set_window_geometry(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 1600 if screen_width >= 1600 else max(1360, screen_width - 40)
        height = 900 if screen_height >= 900 else max(820, screen_height - 80)
        x_pos = max((screen_width - width) // 2, 0)
        y_pos = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.root.minsize(1360, 820)

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Summary.TLabel", font=("Segoe UI", 10, "bold"))

    def _load_icon(self) -> None:
        icon_path = _first_existing_path("assets/icon.ico")
        if not icon_path:
            return
        try:
            self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

    def _ensure_output_dirs(self) -> None:
        for path in (
            Path("data"),
            Path("data/exports"),
            Path("data/reports"),
            Path("data/backups"),
        ):
            path.mkdir(parents=True, exist_ok=True)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        self.main_frame = main

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 8))
        self.header_frame = header
        ttk.Label(header, text="PFPADEL Video Simple", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Lecteur video + saisie rapide par Entree.",
        ).pack(side="left", padx=(12, 0))
        ttk.Label(header, textvariable=self.status_var, style="Summary.TLabel").pack(side="right")

        body = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        body.pack(fill="both", expand=True)
        self.main_paned = body

        left = ttk.Frame(body, padding=(0, 0, 10, 0))
        right = ttk.Frame(body, width=self.sidebar_target_width)
        self.video_panel_frame = left
        self.sidebar_frame = right
        body.add(left, weight=8)
        body.add(right, weight=1)

        self._build_video_panel(left)
        self._build_control_panel(right)

    def _build_video_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Video", style="Section.TLabelframe", padding=10)
        frame.pack(fill="both", expand=True)
        self.video_section_frame = frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        top_bar = ttk.Frame(frame)
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top_bar.columnconfigure(1, weight=1)

        ttk.Button(top_bar, text="Charger video", command=self.load_video).grid(row=0, column=0, padx=(0, 8))
        ttk.Label(top_bar, textvariable=self.video_name_var).grid(row=0, column=1, sticky="w")
        self.focus_button = ttk.Button(top_bar, text="Focus video", command=self.toggle_video_focus)
        self.focus_button.grid(row=0, column=2, padx=(8, 8))
        ttk.Button(top_bar, text="Plein ecran", command=self.toggle_fullscreen).grid(row=0, column=3)

        controls = ttk.Frame(frame)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for index in range(9):
            controls.columnconfigure(index, weight=1 if index == 7 else 0)

        self.play_button = ttk.Button(controls, text="Lecture / Pause", command=self.toggle_play_pause)
        self.play_button.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(controls, text="-10s", command=lambda: self.seek_relative(-10)).grid(row=0, column=1, padx=(0, 6))
        ttk.Button(controls, text="-2s", command=lambda: self.seek_relative(-2)).grid(row=0, column=2, padx=(0, 6))
        ttk.Button(controls, text="+2s", command=lambda: self.seek_relative(2)).grid(row=0, column=3, padx=(0, 6))
        ttk.Button(controls, text="+10s", command=lambda: self.seek_relative(10)).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(controls, text="Annuler dernier", command=self.remove_last_point).grid(row=0, column=5, padx=(0, 6))
        ttk.Label(controls, textvariable=self.current_time_var).grid(row=0, column=6, padx=(12, 0))

        progress = ttk.Frame(frame)
        progress.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        progress.columnconfigure(0, weight=1)
        self.progress_scale = ttk.Scale(progress, from_=0, to=100, variable=self.progress_var, orient=tk.HORIZONTAL)
        self.progress_scale.grid(row=0, column=0, sticky="ew")
        self.progress_scale.bind("<ButtonPress-1>", self._on_progress_press)
        self.progress_scale.bind("<ButtonRelease-1>", self._on_progress_release)

        self.vlc_frame = tk.Frame(frame, bg="#000000")
        self.vlc_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=10)
        frame.rowconfigure(3, weight=1)
        self.vlc_frame.bind("<Double-Button-1>", lambda _event: self.toggle_fullscreen())

    def _build_control_panel(self, parent: ttk.Frame) -> None:
        top = ttk.LabelFrame(parent, text="Session", style="Section.TLabelframe", padding=10)
        top.pack(fill="x", pady=(0, 8))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Nom session").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(top, textvariable=self.session_name_var).grid(row=0, column=1, sticky="ew")

        players = ttk.LabelFrame(parent, text="Joueurs", style="Section.TLabelframe", padding=10)
        players.pack(fill="x", pady=(0, 8))
        for index, variable in enumerate(self.player_vars, start=1):
            players.columnconfigure(index * 2 - 1, weight=1)
            ttk.Label(players, text=f"Joueur {index}").grid(row=index - 1, column=0, sticky="w", padx=(0, 8), pady=2)
            ttk.Entry(players, textvariable=variable).grid(row=index - 1, column=1, sticky="ew", pady=2)

        annotate = ttk.LabelFrame(parent, text="Ajouter une stat", style="Section.TLabelframe", padding=10)
        annotate.pack(fill="x", pady=(0, 8))
        annotate.columnconfigure(1, weight=1)

        ttk.Label(annotate, text="Type").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=2)
        self.point_type_combo = ttk.Combobox(
            annotate,
            textvariable=self.point_type_var,
            values=[label for label, _ in TYPE_OPTIONS],
            state="readonly",
        )
        self.point_type_combo.grid(row=0, column=1, sticky="ew", pady=2)
        self.point_type_combo.bind("<<ComboboxSelected>>", self._sync_form_state)

        ttk.Label(annotate, text="Joueur / attaquant").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=2)
        self.player_combo = ttk.Combobox(annotate, textvariable=self.player_var, state="readonly")
        self.player_combo.grid(row=1, column=1, sticky="ew", pady=2)

        ttk.Label(annotate, text="Defenseur").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=2)
        self.defender_combo = ttk.Combobox(annotate, textvariable=self.defender_var, state="readonly")
        self.defender_combo.grid(row=2, column=1, sticky="ew", pady=2)

        ttk.Button(
            annotate,
            text="Enregistrer la stat (Entree)",
            command=self.add_current_annotation,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        actions = ttk.LabelFrame(parent, text="Exports", style="Section.TLabelframe", padding=10)
        actions.pack(fill="x", pady=(0, 8))
        ttk.Button(actions, text="Charger JSON", command=self.load_json).pack(fill="x", pady=2)
        ttk.Button(actions, text="Sauver JSON", command=self.export_json).pack(fill="x", pady=2)
        ttk.Button(actions, text="Exporter CSV", command=self.export_csv).pack(fill="x", pady=2)
        ttk.Button(actions, text="Rapport simple", command=self.export_html).pack(fill="x", pady=2)
        ttk.Button(actions, text="Nouvelle session", command=self.new_session).pack(fill="x", pady=2)

        history = ttk.LabelFrame(parent, text="Points enregistres", style="Section.TLabelframe", padding=10)
        history.pack(fill="both", expand=True)
        history.columnconfigure(0, weight=1)
        history.rowconfigure(0, weight=1)

        columns = ("id", "temps", "type", "joueur", "defenseur")
        self.tree = ttk.Treeview(history, columns=columns, show="headings", height=18)
        for key, label, width in (
            ("id", "#", 48),
            ("temps", "Temps", 90),
            ("type", "Type", 130),
            ("joueur", "Joueur", 140),
            ("defenseur", "Defenseur", 140),
        ):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(history, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Return>", self._on_return_key)
        self.root.bind("<space>", self._on_space_key)
        self.root.bind("<Left>", lambda _event: self.seek_relative(-2))
        self.root.bind("<Right>", lambda _event: self.seek_relative(2))
        self.root.bind("<Up>", lambda _event: self.seek_relative(10))
        self.root.bind("<Down>", lambda _event: self.seek_relative(-10))
        self.root.bind("<F11>", lambda _event: self.toggle_fullscreen())
        self.root.bind("<f>", lambda _event: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda _event: self._exit_fullscreen())
        self.root.bind("<F10>", lambda _event: self.toggle_video_focus())
        self.root.bind("<Control-o>", lambda _event: self.load_video())
        self.root.bind("<Control-s>", lambda _event: self.export_json())

    def _apply_video_first_layout(self) -> None:
        if not getattr(self, "sidebar_visible", True):
            return
        try:
            total_width = self.main_paned.winfo_width()
            if total_width <= 0:
                self.root.after(120, self._apply_video_first_layout)
                return
            sash_position = max(total_width - self.sidebar_target_width, int(total_width * 0.72))
            self.main_paned.sashpos(0, sash_position)
        except Exception:
            pass

    def _refresh_video_target(self) -> None:
        try:
            self.vlc_frame.update_idletasks()
            self.vlc_frame.update()
            self.video_player.set_vlc_window(self.vlc_frame.winfo_id())
        except Exception:
            pass

    def _set_sidebar_visibility(self, show: bool) -> None:
        if show == self.sidebar_visible:
            return

        try:
            if show:
                self.main_paned.add(self.sidebar_frame, weight=1)
                self.sidebar_visible = True
                self.focus_button.configure(text="Focus video")
                self.root.after(80, self._apply_video_first_layout)
            else:
                self.main_paned.forget(self.sidebar_frame)
                self.sidebar_visible = False
                self.focus_button.configure(text="Afficher panneau")
        finally:
            self.root.after(80, self._refresh_video_target)

    def toggle_video_focus(self) -> None:
        self._set_sidebar_visibility(not self.sidebar_visible)
        if self.sidebar_visible:
            self.status_var.set("Panneau lateral affiche.")
        else:
            self.status_var.set("Mode focus video actif.")

    def _on_return_key(self, _event) -> str | None:
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Entry, ttk.Entry)) and focus_widget not in (self.player_combo, self.defender_combo, self.point_type_combo):
            return None
        self.add_current_annotation()
        return "break"

    def _on_space_key(self, _event) -> str | None:
        focus_widget = self.root.focus_get()
        if isinstance(focus_widget, (tk.Entry, ttk.Entry)):
            return None
        self.toggle_play_pause()
        return "break"

    def _on_players_changed(self, *_args) -> None:
        self._refresh_player_choices()
        self.annotation_manager.set_players(self.get_players())
        self._refresh_tree()

    def _refresh_player_choices(self) -> None:
        players = self.get_players()
        self.player_combo.configure(values=players)
        self.defender_combo.configure(values=players)

        if self.player_var.get() not in players:
            self.player_var.set(players[0] if players else "")
        if self.defender_var.get() not in players:
            self.defender_var.set(players[1] if len(players) > 1 else "")
        self._sync_form_state()

    def _sync_form_state(self, *_args) -> None:
        point_type = TYPE_LABEL_TO_CODE.get(self.point_type_var.get(), "point_gagnant")
        defender_state = "readonly" if point_type == "faute_provoquee" else "disabled"
        self.defender_combo.configure(state=defender_state)
        if point_type != "faute_provoquee":
            self.defender_var.set("")

    def get_players(self) -> list[str]:
        players = [value.get().strip() for value in self.player_vars if value.get().strip()]
        while len(players) < 4:
            players.append(f"Joueur {len(players) + 1}")
        return players[:4]

    def load_video(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Charger une video",
            filetypes=[("Videos", "*.mp4;*.avi;*.mov;*.mkv"), ("Tous les fichiers", "*.*")],
        )
        if not filepath:
            return
        self._load_video_from_path(filepath, ask_reset=bool(self.annotation_manager.annotations))

    def _load_video_from_path(
        self,
        filepath: str,
        ask_reset: bool = False,
        preserve_session_name: bool = False,
    ) -> None:
        if ask_reset and not messagebox.askyesno(
            "Nouvelle video",
            "Charger une autre video va demarrer une nouvelle session.\nContinuer ?",
        ):
            return

        try:
            if ask_reset:
                self._reset_annotations()

            self.vlc_frame.update_idletasks()
            self.vlc_frame.update()
            self.video_player.set_vlc_window(self.vlc_frame.winfo_id())
            self.video_player.load_video(filepath)
            self.video_player.pause()

            self.current_video_path = filepath
            self.annotation_manager.set_video(filepath)
            self.annotation_manager.set_players(self.get_players())
            self.video_name_var.set(Path(filepath).name)
            if not preserve_session_name:
                self.session_name_var.set(Path(filepath).stem)
            self.progress_var.set(0.0)
            self._update_time_display()
            self.status_var.set(f"Video chargee: {Path(filepath).name}")
        except Exception as exc:
            self.status_var.set(f"Erreur video: {exc}")
            messagebox.showerror("Erreur video", str(exc))

    def _reset_annotations(self) -> None:
        current_video = self.current_video_path
        self.annotation_manager = AnnotationManager(data_folder="data", enable_background_ai=False)
        self.annotation_manager.set_players(self.get_players())
        if current_video:
            self.annotation_manager.set_video(current_video)
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _tick(self) -> None:
        try:
            if self.video_player.video_loaded and self.video_player.total_frames > 0:
                if self.video_player.vlc_player:
                    vlc_position = self.video_player.get_vlc_position()
                    if vlc_position >= 0:
                        self.video_player.current_frame = int(vlc_position * self.video_player.total_frames)
                self._update_time_display()
                if not self.progress_dragging:
                    current_ts = self.video_player.get_current_timestamp()
                    self.progress_var.set(current_ts)

            self.play_button.configure(text="Pause" if self.video_player.is_playing else "Lecture")
        finally:
            self.root.after(200, self._tick)

    def _update_time_display(self) -> None:
        if not self.video_player.video_loaded:
            self.current_time_var.set("00:00.00 / 00:00.00")
            return
        duration = self.video_player.total_frames / self.video_player.fps if self.video_player.fps > 0 else 0.0
        current_ts = self.video_player.get_current_timestamp()
        self.progress_scale.configure(to=max(duration, 1.0))
        self.current_time_var.set(f"{_format_seconds(current_ts)} / {_format_seconds(duration)}")

    def toggle_play_pause(self) -> None:
        if not self.video_player.video_loaded:
            messagebox.showwarning("Video", "Chargez une video d'abord.")
            return
        self.video_player.toggle_play_pause()
        self.status_var.set("Lecture" if self.video_player.is_playing else "Pause")

    def seek_relative(self, seconds: int) -> None:
        if not self.video_player.video_loaded:
            return
        if seconds < 0:
            self.video_player.rewind(abs(seconds))
        else:
            self.video_player.forward(seconds)
        self._update_time_display()

    def _on_progress_press(self, _event) -> None:
        self.progress_dragging = True

    def _on_progress_release(self, _event) -> None:
        self.progress_dragging = False
        if self.video_player.video_loaded:
            self.video_player.seek_time(self.progress_var.get())
            self._update_time_display()

    def add_current_annotation(self) -> None:
        if not self.video_player.video_loaded:
            messagebox.showwarning("Stat", "Chargez une video avant d'enregistrer une stat.")
            return

        point_type = TYPE_LABEL_TO_CODE.get(self.point_type_var.get(), "point_gagnant")
        player = self.player_var.get().strip()
        defender = self.defender_var.get().strip()
        if not player:
            messagebox.showwarning("Stat", "Selectionnez un joueur.")
            return
        if point_type == "faute_provoquee":
            if not defender:
                messagebox.showwarning("Stat", "Selectionnez un defenseur.")
                return
            if defender == player:
                messagebox.showwarning("Stat", "Attaquant et defenseur doivent etre differents.")
                return

        try:
            if self.video_player.vlc_player:
                self.video_player.sync_from_vlc()
            timestamp = self.video_player.get_current_timestamp()
            frame = self.video_player.current_frame

            if point_type == "point_gagnant":
                self.annotation_manager.add_point_gagnant(player, timestamp, frame, None, None)
            elif point_type == "faute_directe":
                self.annotation_manager.add_faute_directe(player, timestamp, frame, None, None)
            else:
                self.annotation_manager.add_faute_provoquee(player, defender, timestamp, frame, None, None, None)

            self._refresh_tree()
            self.status_var.set(f"Point enregistre a {_format_seconds(timestamp)}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def remove_last_point(self) -> None:
        removed = self.annotation_manager.remove_last_annotation()
        if not removed:
            return
        self._refresh_tree()
        self.status_var.set("Dernier point supprime.")

    def _sync_manager_metadata(self) -> None:
        self.annotation_manager.set_players(self.get_players())
        session_name = self.session_name_var.get().strip()
        if session_name:
            self.annotation_manager.match_info["video"] = session_name
        if self.current_video_path:
            self.annotation_manager.match_info["video_path"] = self.current_video_path

    def _refresh_tree(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        for point in self.annotation_manager.get_all_annotations():
            point_type = TYPE_CODE_TO_LABEL.get(point.get("type", ""), point.get("type", ""))
            player = point.get("joueur") or point.get("attaquant") or ""
            defender = point.get("defenseur") or ""
            values = (
                point.get("id", ""),
                _format_seconds(float(point.get("timestamp", 0.0))),
                point_type,
                player,
                defender,
            )
            self.tree.insert("", "end", values=values)

        children = self.tree.get_children()
        if children:
            self.tree.see(children[-1])

    def new_session(self) -> None:
        if not messagebox.askyesno("Nouvelle session", "Effacer les stats actuelles ?"):
            return

        self._reset_annotations()
        self.session_name_var.set(
            Path(self.current_video_path).stem if self.current_video_path else f"session_video_{datetime.now():%Y%m%d_%H%M}"
        )
        self.status_var.set("Nouvelle session prete.")

    def export_json(self) -> None:
        if not self.annotation_manager.annotations:
            messagebox.showwarning("Export", "Aucune stat a exporter.")
            return

        try:
            self._sync_manager_metadata()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"match_{timestamp}")
            output_path = Path("data/exports") / f"{filename}_{timestamp}.json"
            saved_path = self.json_exporter.export(self.annotation_manager, str(output_path))
            self.status_var.set(f"JSON sauve: {saved_path}")
            messagebox.showinfo("Export JSON", f"Fichier cree:\n{saved_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def export_csv(self) -> None:
        if not self.annotation_manager.annotations:
            messagebox.showwarning("Export", "Aucune stat a exporter.")
            return

        try:
            self._sync_manager_metadata()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"stats_{timestamp}")
            output_path = Path("data/exports") / f"{filename}_{timestamp}.csv"
            saved_path = self.csv_exporter.export(self.annotation_manager, str(output_path))
            self.status_var.set(f"CSV exporte: {saved_path}")
            messagebox.showinfo("Export CSV", f"Fichier cree:\n{saved_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def export_html(self) -> None:
        if not self.annotation_manager.annotations:
            messagebox.showwarning("Rapport", "Aucune stat a exporter.")
            return

        try:
            self._sync_manager_metadata()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"rapport_simple_{timestamp}")
            output_path = Path("data/reports") / f"{filename}_{timestamp}.html"
            saved_path = self.html_generator.generate_report(self.annotation_manager, str(output_path), fast_mode=True)
            self.status_var.set(f"Rapport simple cree: {saved_path}")
            try:
                webbrowser.open(Path(saved_path).resolve().as_uri())
            except Exception:
                pass
            messagebox.showinfo("Rapport simple", f"Fichier cree:\n{saved_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def load_json(self) -> None:
        filepath = filedialog.askopenfilename(
            title="Charger un JSON",
            initialdir=str(Path("data/exports")),
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not filepath:
            return

        try:
            data = self.json_exporter.load(filepath)
            manager = AnnotationManager(data_folder="data", enable_background_ai=False)
            manager.load_from_dict(data)
            manager.set_players(
                [
                    player if isinstance(player, str) else str(player.get("nom", ""))
                    for player in manager.match_info.get("joueurs", [])
                ]
            )
            self.annotation_manager = manager

            players = manager.match_info.get("joueurs", []) or []
            normalized_players = []
            for player in players:
                if isinstance(player, dict):
                    normalized_players.append(str(player.get("nom", "")).strip())
                else:
                    normalized_players.append(str(player).strip())
            while len(normalized_players) < 4:
                normalized_players.append(f"Joueur {len(normalized_players) + 1}")
            for variable, player_name in zip(self.player_vars, normalized_players[:4]):
                variable.set(player_name)

            self.session_name_var.set(str(manager.match_info.get("video") or Path(filepath).stem))
            self.current_video_path = manager.match_info.get("video_path")
            self.video_name_var.set(Path(self.current_video_path).name if self.current_video_path else "Video non chargee")
            self._refresh_player_choices()
            self._refresh_tree()

            if self.current_video_path and Path(self.current_video_path).exists():
                self._load_video_from_path(
                    self.current_video_path,
                    ask_reset=False,
                    preserve_session_name=True,
                )

            self.status_var.set(f"JSON charge: {filepath}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def toggle_fullscreen(self) -> None:
        if self.fullscreen:
            self._exit_fullscreen()
            return

        self._set_immersive_video_mode(True)

    def _set_immersive_video_mode(self, enabled: bool) -> None:
        enabled = bool(enabled)
        self.immersive_video_mode = enabled
        self.fullscreen = enabled

        try:
            self.root.attributes("-fullscreen", enabled)
        except Exception:
            pass

        if enabled:
            self._sidebar_hidden_for_fullscreen = self.sidebar_visible
            if self.sidebar_visible:
                self._set_sidebar_visibility(False)
            if self.header_frame.winfo_manager():
                self.header_frame.pack_forget()
            self.main_frame.configure(padding=0)
            self.video_panel_frame.configure(padding=0)
            self.video_section_frame.configure(text="", padding=0)
            self.vlc_frame.grid_configure(padx=0, pady=0)
            self.status_var.set("Plein ecran actif. Echap pour quitter.")
        else:
            if not self.header_frame.winfo_manager():
                self.header_frame.pack(fill="x", pady=(0, 8), before=self.main_paned)
            if self._sidebar_hidden_for_fullscreen:
                self._set_sidebar_visibility(True)
            self._sidebar_hidden_for_fullscreen = False
            self.main_frame.configure(padding=12)
            self.video_panel_frame.configure(padding=(0, 0, 10, 0))
            self.video_section_frame.configure(text="Video", padding=10)
            self.vlc_frame.grid_configure(padx=10, pady=10)
            self.root.after(120, self._apply_video_first_layout)
            self.status_var.set("Plein ecran quitte.")

        self.root.after(120, self._refresh_video_target)

    def _exit_fullscreen(self) -> None:
        if not self.fullscreen:
            return

        self._set_immersive_video_mode(False)

    def _on_close(self) -> None:
        try:
            self.video_player.release()
        finally:
            self.root.destroy()
