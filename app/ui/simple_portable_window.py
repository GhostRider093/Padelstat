"""Portable manual-entry UI for lightweight Full HD use."""

from __future__ import annotations

import json
import re
import sys
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.annotations.annotation_manager import AnnotationManager
from app.exports.csv_exporter import CSVExporter
from app.exports.html_generator import HTMLGenerator
from app.exports.json_exporter import JSONExporter


TYPE_OPTIONS = [
    ("Point gagnant", "point_gagnant"),
    ("Faute directe", "faute_directe"),
    ("Faute provoquee", "faute_provoquee"),
]
TYPE_LABEL_TO_CODE = dict(TYPE_OPTIONS)
TYPE_CODE_TO_LABEL = {code: label for label, code in TYPE_OPTIONS}

SHOT_OPTIONS = [
    ("", ""),
    ("Service", "service"),
    ("Volee coup droit", "volee_coup_droit"),
    ("Volee revers", "volee_revers"),
    ("Volee balle haute", "volee_balle_haute"),
    ("Fond de court coup droit", "fond_de_court_coup_droit"),
    ("Fond de court revers", "fond_de_court_revers"),
    ("Fond de court balle haute", "fond_de_court_balle_haute"),
    ("Smash", "smash"),
    ("Lobe", "lobe"),
    ("Amorti", "amorti"),
    ("Bandeja", "bandeja"),
    ("Vibora", "vibora"),
    ("Autre", "autre"),
]
SHOT_LABEL_TO_CODE = dict(SHOT_OPTIONS)
SHOT_CODE_TO_LABEL = {code: label for label, code in SHOT_OPTIONS if code}

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


def _parse_timestamp(raw_value: str, fallback_seconds: float) -> float:
    text = (raw_value or "").strip()
    if not text:
        return round(float(fallback_seconds), 2)

    text = text.replace(",", ".")
    if ":" not in text:
        return round(float(text), 2)

    parts = text.split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            return round(int(minutes) * 60 + float(seconds), 2)
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 2)
    except ValueError as exc:
        raise ValueError(f"Horodatage invalide: {raw_value}") from exc

    raise ValueError(f"Horodatage invalide: {raw_value}")


@dataclass
class PortableEntryRow:
    owner: "PortableSimpleWindow"
    parent: ttk.Frame
    index: int

    def __post_init__(self) -> None:
        self.frame = ttk.Frame(self.parent, padding=(0, 2))
        self.number_label = ttk.Label(self.frame, text=str(self.index), width=4, anchor="center")

        self.timestamp_var = tk.StringVar()
        self.point_type_var = tk.StringVar(value=TYPE_OPTIONS[0][0])
        self.player_var = tk.StringVar()
        self.defender_var = tk.StringVar()
        self.shot_var = tk.StringVar()
        self.defender_shot_var = tk.StringVar()

        self.timestamp_entry = ttk.Entry(self.frame, textvariable=self.timestamp_var, width=12)
        self.point_type_combo = ttk.Combobox(
            self.frame,
            textvariable=self.point_type_var,
            values=[label for label, _ in TYPE_OPTIONS],
            width=18,
            state="readonly",
        )
        self.player_combo = ttk.Combobox(self.frame, textvariable=self.player_var, width=20, state="readonly")
        self.defender_combo = ttk.Combobox(self.frame, textvariable=self.defender_var, width=20, state="readonly")
        self.shot_combo = ttk.Combobox(
            self.frame,
            textvariable=self.shot_var,
            values=[label for label, _ in SHOT_OPTIONS],
            width=26,
            state="readonly",
        )
        self.defender_shot_combo = ttk.Combobox(
            self.frame,
            textvariable=self.defender_shot_var,
            values=[label for label, _ in SHOT_OPTIONS],
            width=26,
            state="readonly",
        )
        self.delete_button = ttk.Button(self.frame, text="Suppr.", width=9, command=self._remove)

        self.number_label.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        self.timestamp_entry.grid(row=0, column=1, padx=(0, 6), sticky="ew")
        self.point_type_combo.grid(row=0, column=2, padx=(0, 6), sticky="ew")
        self.player_combo.grid(row=0, column=3, padx=(0, 6), sticky="ew")
        self.defender_combo.grid(row=0, column=4, padx=(0, 6), sticky="ew")
        self.shot_combo.grid(row=0, column=5, padx=(0, 6), sticky="ew")
        self.defender_shot_combo.grid(row=0, column=6, padx=(0, 6), sticky="ew")
        self.delete_button.grid(row=0, column=7, sticky="ew")

        self.point_type_combo.bind("<<ComboboxSelected>>", self._sync_state)
        for variable in (
            self.timestamp_var,
            self.point_type_var,
            self.player_var,
            self.defender_var,
            self.shot_var,
            self.defender_shot_var,
        ):
            variable.trace_add("write", self._notify_change)

        self.set_players(self.owner.get_players())
        self._sync_state()

    def _notify_change(self, *_args) -> None:
        self.owner.refresh_summary()

    def _remove(self) -> None:
        self.owner.remove_row(self)

    def set_index(self, index: int) -> None:
        self.index = index
        self.number_label.configure(text=str(index))

    def grid(self, row_index: int) -> None:
        self.frame.grid(row=row_index, column=0, sticky="ew", pady=1)

    def destroy(self) -> None:
        self.frame.destroy()

    def set_players(self, players: list[str]) -> None:
        current_player = self.player_var.get()
        current_defender = self.defender_var.get()
        self.player_combo.configure(values=players)
        self.defender_combo.configure(values=players)
        if current_player not in players:
            self.player_var.set("")
        if current_defender not in players:
            self.defender_var.set("")

    def _sync_state(self, *_args) -> None:
        point_type = TYPE_LABEL_TO_CODE.get(self.point_type_var.get(), "point_gagnant")
        is_provoked = point_type == "faute_provoquee"
        defender_state = "readonly" if is_provoked else "disabled"
        self.defender_combo.configure(state=defender_state)
        self.defender_shot_combo.configure(state=defender_state)
        if not is_provoked:
            self.defender_var.set("")
            self.defender_shot_var.set("")

    def is_blank(self) -> bool:
        return not any(
            (
                self.timestamp_var.get().strip(),
                self.player_var.get().strip(),
                self.defender_var.get().strip(),
            )
        )

    def load_point(self, point: dict) -> None:
        point_type = str(point.get("type", "point_gagnant"))
        self.point_type_var.set(TYPE_CODE_TO_LABEL.get(point_type, TYPE_OPTIONS[0][0]))
        timestamp = point.get("timestamp", "")
        self.timestamp_var.set("" if timestamp in ("", None) else str(timestamp))
        self.player_var.set(str(point.get("joueur") or point.get("attaquant") or ""))
        self.defender_var.set(str(point.get("defenseur") or ""))
        self.shot_var.set(
            SHOT_CODE_TO_LABEL.get(
                str(point.get("type_coup") or point.get("type_coup_attaquant") or ""),
                "",
            )
        )
        self.defender_shot_var.set(
            SHOT_CODE_TO_LABEL.get(str(point.get("type_coup_defenseur") or ""), "")
        )
        self._sync_state()

    def to_point(self, point_id: int, fallback_seconds: float) -> dict | None:
        if self.is_blank():
            return None

        point_type = TYPE_LABEL_TO_CODE.get(self.point_type_var.get(), "point_gagnant")
        player = self.player_var.get().strip()
        if not player:
            raise ValueError(f"Ligne {self.index}: joueur / attaquant manquant.")

        timestamp = _parse_timestamp(self.timestamp_var.get(), fallback_seconds)
        shot = SHOT_LABEL_TO_CODE.get(self.shot_var.get(), "") or "autre"

        point = {
            "id": point_id,
            "type": point_type,
            "timestamp": timestamp,
            "frame": 0,
            "capture": None,
        }

        if point_type in ("point_gagnant", "faute_directe"):
            point["joueur"] = player
            point["type_coup"] = shot
            return point

        defender = self.defender_var.get().strip()
        if not defender:
            raise ValueError(f"Ligne {self.index}: defenseur manquant.")
        if defender == player:
            raise ValueError(f"Ligne {self.index}: attaquant et defenseur identiques.")

        point["attaquant"] = player
        point["defenseur"] = defender
        point["type_coup_attaquant"] = shot
        point["type_coup_defenseur"] = SHOT_LABEL_TO_CODE.get(self.defender_shot_var.get(), "") or "autre"
        return point


class PortableSimpleWindow:
    """Minimal portable UI with manual entry rows only."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PFPADEL Portable Simple")
        self._set_window_geometry()
        self._configure_style()
        self._load_icon()

        self.json_exporter = JSONExporter()
        self.csv_exporter = CSVExporter()
        self.html_generator = HTMLGenerator()
        self.default_players = _load_default_players()

        self.session_name_var = tk.StringVar(value=f"session_portable_{datetime.now():%Y%m%d_%H%M}")
        self.status_var = tk.StringVar(value="Pret")
        self.player_vars = [tk.StringVar(value=value) for value in self.default_players]
        self.rows: list[PortableEntryRow] = []

        for variable in self.player_vars:
            variable.trace_add("write", self._on_players_changed)

        self._ensure_output_dirs()
        self._build_ui()
        self._populate_initial_rows()
        self._bind_shortcuts()
        self.refresh_summary()

    def _set_window_geometry(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 1920 if screen_width >= 1920 else max(1280, screen_width)
        height = 1080 if screen_height >= 1080 else max(720, screen_height - 60)
        x_pos = max((screen_width - width) // 2, 0)
        y_pos = max((screen_height - height) // 2, 0)
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")
        self.root.minsize(1280, 720)

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

    def _bind_shortcuts(self) -> None:
        self.root.bind("<Control-n>", lambda _event: self.add_row())
        self.root.bind("<Control-s>", lambda _event: self.save_session())
        self.root.bind("<Control-o>", lambda _event: self.load_json())

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="PFPADEL Portable Simple", style="Title.TLabel").pack(side="left")
        ttk.Label(
            header,
            text="Interface manuelle 1920x1080, sans video ni vocal.",
        ).pack(side="left", padx=(12, 0))
        ttk.Label(header, textvariable=self.status_var, style="Summary.TLabel").pack(side="right")

        top_section = ttk.Frame(main)
        top_section.pack(fill="x", pady=(0, 12))
        top_section.columnconfigure(1, weight=1)

        ttk.Label(top_section, text="Nom de session").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(top_section, textvariable=self.session_name_var).grid(row=0, column=1, sticky="ew")

        players_frame = ttk.LabelFrame(main, text="Joueurs", style="Section.TLabelframe", padding=12)
        players_frame.pack(fill="x", pady=(0, 12))
        for index, variable in enumerate(self.player_vars, start=1):
            players_frame.columnconfigure(index * 2 - 1, weight=1)
            ttk.Label(players_frame, text=f"Joueur {index}").grid(row=0, column=(index - 1) * 2, sticky="w", padx=(0, 6))
            ttk.Entry(players_frame, textvariable=variable).grid(
                row=0, column=(index - 1) * 2 + 1, sticky="ew", padx=(0, 12)
            )

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="Ajouter ligne", command=self.add_row).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Nouvelle session", command=self.new_session).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Sauver session", command=self.save_session).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Charger JSON", command=self.load_json).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Exporter JSON", command=self.export_json).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Exporter CSV", command=self.export_csv).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Rapport HTML", command=self.export_html).pack(side="left")

        table_frame = ttk.LabelFrame(main, text="Lignes de saisie", style="Section.TLabelframe", padding=12)
        table_frame.pack(fill="both", expand=True)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(1, weight=1)

        headings = ttk.Frame(table_frame)
        headings.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        for column_index, (title, width) in enumerate(
            [
                ("#", 4),
                ("Temps", 12),
                ("Type", 18),
                ("Joueur / Attaquant", 20),
                ("Defenseur", 20),
                ("Coup joueur", 26),
                ("Coup defenseur", 26),
                ("Action", 9),
            ]
        ):
            ttk.Label(headings, text=title, width=width, anchor="center").grid(row=0, column=column_index, padx=(0, 6))

        canvas_holder = ttk.Frame(table_frame)
        canvas_holder.grid(row=1, column=0, sticky="nsew")
        canvas_holder.columnconfigure(0, weight=1)
        canvas_holder.rowconfigure(0, weight=1)

        self.rows_canvas = tk.Canvas(canvas_holder, highlightthickness=0)
        self.rows_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(canvas_holder, orient="vertical", command=self.rows_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.rows_canvas.configure(yscrollcommand=scrollbar.set)

        self.rows_frame = ttk.Frame(self.rows_canvas)
        self.rows_window = self.rows_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", self._on_rows_configure)
        self.rows_canvas.bind("<Configure>", self._on_canvas_configure)

        summary = ttk.Frame(main)
        summary.pack(fill="x", pady=(10, 0))
        self.summary_label = ttk.Label(summary, style="Summary.TLabel")
        self.summary_label.pack(side="left")
        ttk.Label(summary, text="Formats temps acceptes: secondes, mm:ss, hh:mm:ss").pack(side="right")

    def _populate_initial_rows(self) -> None:
        for _ in range(12):
            self.add_row(refresh=False)

    def _on_rows_configure(self, _event) -> None:
        self.rows_canvas.configure(scrollregion=self.rows_canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.rows_canvas.itemconfigure(self.rows_window, width=event.width)

    def _on_players_changed(self, *_args) -> None:
        players = self.get_players()
        for row in self.rows:
            row.set_players(players)
        self.refresh_summary()

    def _ensure_output_dirs(self) -> None:
        for path in (
            Path("data"),
            Path("data/exports"),
            Path("data/reports"),
            Path("data/backups"),
        ):
            path.mkdir(parents=True, exist_ok=True)

    def get_players(self) -> list[str]:
        players = [value.get().strip() for value in self.player_vars if value.get().strip()]
        while len(players) < 4:
            players.append(f"Joueur {len(players) + 1}")
        return players[:4]

    def add_row(self, refresh: bool = True) -> None:
        row = PortableEntryRow(owner=self, parent=self.rows_frame, index=len(self.rows) + 1)
        self.rows.append(row)
        self._reflow_rows()
        if refresh:
            self.refresh_summary("Ligne ajoutee.")

    def remove_row(self, row: PortableEntryRow) -> None:
        if len(self.rows) <= 1:
            row.timestamp_var.set("")
            row.player_var.set("")
            row.defender_var.set("")
            row.shot_var.set("")
            row.defender_shot_var.set("")
            self.refresh_summary("La derniere ligne a ete videe.")
            return

        row.destroy()
        self.rows.remove(row)
        self._reflow_rows()
        self.refresh_summary("Ligne supprimee.")

    def _reflow_rows(self) -> None:
        for index, row in enumerate(self.rows, start=1):
            row.set_index(index)
            row.grid(index - 1)

    def _build_manager(self) -> AnnotationManager:
        manager = AnnotationManager(data_folder="data", enable_background_ai=False)
        players = self.get_players()
        manager.set_players(players)
        manager.match_info["date"] = datetime.now().strftime("%Y-%m-%d")
        manager.match_info["video"] = self.session_name_var.get().strip() or "Saisie manuelle"
        manager.match_info["video_path"] = None

        points = []
        next_fallback_timestamp = 1.0
        for row in self.rows:
            point = row.to_point(point_id=len(points) + 1, fallback_seconds=next_fallback_timestamp)
            if not point:
                continue
            next_fallback_timestamp = max(next_fallback_timestamp + 1.0, float(point["timestamp"]) + 1.0)
            points.append(point)

        if not points:
            raise ValueError("Aucune ligne valide a exporter.")

        manager.annotations = points
        manager.current_point_id = len(points) + 1
        return manager

    def refresh_summary(self, message: str | None = None) -> None:
        filled_rows = sum(0 if row.is_blank() else 1 for row in self.rows)
        self.summary_label.configure(text=f"{filled_rows} ligne(s) remplies sur {len(self.rows)}")
        if message:
            self.status_var.set(message)

    def new_session(self) -> None:
        if not messagebox.askyesno("Nouvelle session", "Effacer les lignes actuelles ?"):
            return

        for row in self.rows:
            row.destroy()
        self.rows.clear()
        for default, variable in zip(self.default_players, self.player_vars):
            variable.set(default)
        self.session_name_var.set(f"session_portable_{datetime.now():%Y%m%d_%H%M}")
        self._populate_initial_rows()
        self.refresh_summary("Nouvelle session creee.")

    def save_session(self) -> None:
        try:
            manager = self._build_manager()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"session_{timestamp}")
            output_path = Path("data/exports") / f"{filename}_{timestamp}.json"
            saved_path = self.json_exporter.export(manager, str(output_path))
            self.refresh_summary(f"Session sauvee: {saved_path}")
            messagebox.showinfo("Session", f"Session sauvee dans:\n{saved_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def export_json(self) -> None:
        try:
            manager = self._build_manager()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"match_{timestamp}")
            output_path = Path("data/exports") / f"{filename}_{timestamp}.json"
            exported_path = self.json_exporter.export(manager, str(output_path))
            self.refresh_summary(f"JSON exporte: {exported_path}")
            messagebox.showinfo("Export JSON", f"Fichier cree:\n{exported_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def export_csv(self) -> None:
        try:
            manager = self._build_manager()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"stats_{timestamp}")
            output_path = Path("data/exports") / f"{filename}_{timestamp}.csv"
            exported_path = self.csv_exporter.export(manager, str(output_path))
            self.refresh_summary(f"CSV exporte: {exported_path}")
            messagebox.showinfo("Export CSV", f"Fichier cree:\n{exported_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def export_html(self) -> None:
        try:
            manager = self._build_manager()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = _safe_filename(self.session_name_var.get(), f"rapport_{timestamp}")
            output_path = Path("data/reports") / f"{filename}_{timestamp}.html"
            exported_path = self.html_generator.generate_report(
                manager,
                output_path=str(output_path),
                video_player=None,
                fast_mode=True,
            )
            self.refresh_summary(f"Rapport HTML cree: {exported_path}")
            try:
                webbrowser.open(Path(exported_path).resolve().as_uri())
            except Exception:
                pass
            messagebox.showinfo("Rapport HTML", f"Fichier cree:\n{exported_path}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))

    def load_json(self) -> None:
        initial_dir = Path("data/exports")
        filepath = filedialog.askopenfilename(
            title="Charger un fichier JSON",
            initialdir=str(initial_dir if initial_dir.exists() else Path.cwd()),
            filetypes=[("JSON", "*.json"), ("Tous les fichiers", "*.*")],
        )
        if not filepath:
            return

        try:
            data = self.json_exporter.load(filepath)
            match_info = data.get("match", {}) or {}
            players = match_info.get("joueurs", []) or []
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

            self.session_name_var.set(str(match_info.get("video") or Path(filepath).stem))

            for row in self.rows:
                row.destroy()
            self.rows.clear()

            points = data.get("points", []) or []
            if not points:
                self._populate_initial_rows()
            else:
                for point in points:
                    row = PortableEntryRow(owner=self, parent=self.rows_frame, index=len(self.rows) + 1)
                    row.load_point(point)
                    self.rows.append(row)
                self.add_row(refresh=False)

            self._reflow_rows()
            self.refresh_summary(f"JSON charge: {filepath}")
        except Exception as exc:
            self.status_var.set(f"Erreur: {exc}")
            messagebox.showerror("Erreur", str(exc))
