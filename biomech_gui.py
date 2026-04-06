"""
Minimal Tkinter GUI to test biomechanics (pose) on a video with YOLOv8.

Run:
  .venv\\Scripts\\python biomech_gui.py
"""

from __future__ import annotations

import os
import threading
import queue
import time
import json
import csv
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk


def _safe_import_torch():
    try:
        import torch  # type: ignore
        return torch
    except Exception:
        return None


def _cuda_available():
    torch = _safe_import_torch()
    if torch is None:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


class SimpleTracker:
    def __init__(self, max_age: int = 15):
        self.max_age = max_age
        self.tracks = []
        self.next_id = 1

    def _center(self, bbox):
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def _dist(self, p1, p2):
        dx = p1[0] - p2[0]
        dy = p1[1] - p2[1]
        return (dx * dx + dy * dy) ** 0.5

    def update(self, detections, frame_index: int):
        # detections: list of dict with bbox
        assigned_det = set()
        assigned_track = set()
        pairs = []

        for ti, trk in enumerate(self.tracks):
            for di, det in enumerate(detections):
                bbox = det.get("bbox_xyxy")
                if not bbox:
                    continue
                c_det = self._center(bbox)
                c_trk = trk["center"]
                w = max(bbox[2] - bbox[0], trk["bbox"][2] - trk["bbox"][0], 1.0)
                h = max(bbox[3] - bbox[1], trk["bbox"][3] - trk["bbox"][1], 1.0)
                threshold = max(60.0, 0.7 * max(w, h))
                d = self._dist(c_det, c_trk)
                if d <= threshold:
                    pairs.append((d, ti, di))

        pairs.sort(key=lambda x: x[0])

        det_to_track = [None] * len(detections)
        for _d, ti, di in pairs:
            if ti in assigned_track or di in assigned_det:
                continue
            assigned_track.add(ti)
            assigned_det.add(di)
            bbox = detections[di]["bbox_xyxy"]
            center = self._center(bbox)
            self.tracks[ti].update({
                "bbox": bbox,
                "center": center,
                "last_seen": frame_index,
                "misses": 0,
            })
            det_to_track[di] = self.tracks[ti]["id"]

        # Unmatched tracks
        for ti, trk in enumerate(self.tracks):
            if ti not in assigned_track:
                trk["misses"] += 1

        # Remove old tracks
        self.tracks = [t for t in self.tracks if t["misses"] <= self.max_age]

        # New tracks for unmatched detections
        for di, det in enumerate(detections):
            if di in assigned_det:
                continue
            bbox = det.get("bbox_xyxy")
            if not bbox:
                continue
            center = self._center(bbox)
            new_track = {
                "id": self.next_id,
                "bbox": bbox,
                "center": center,
                "last_seen": frame_index,
                "misses": 0,
            }
            self.next_id += 1
            self.tracks.append(new_track)
            det_to_track[di] = new_track["id"]

        return det_to_track


class BiomechApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Biomech Pose Test (YOLOv8)")
        self.geometry("1000x650")

        self._worker = None
        self._stop_event = threading.Event()
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._preview_image = None
        self._video_info = None
        self._calibration = None
        self._last_outputs = {}

        self._build_ui()
        self._poll_queue()

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        file_frame = ttk.LabelFrame(self, text="Fichier video")
        file_frame.grid(row=0, column=0, sticky="ew", padx=12, pady=10)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="Chemin").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.video_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.video_path_var).grid(
            row=0, column=1, padx=8, pady=8, sticky="ew"
        )
        ttk.Button(file_frame, text="Parcourir...", command=self._browse_video).grid(
            row=0, column=2, padx=8, pady=8
        )
        ttk.Button(file_frame, text="Preanalyse", command=self._preanalyze).grid(
            row=0, column=3, padx=8, pady=8
        )
        ttk.Button(file_frame, text="Calibration", command=self._open_calibration).grid(
            row=0, column=4, padx=8, pady=8
        )

        self.video_info_var = tk.StringVar(value="Info: -")
        ttk.Label(file_frame, textvariable=self.video_info_var).grid(
            row=1, column=0, columnspan=5, padx=8, pady=(0, 8), sticky="w"
        )

        self.calib_info_var = tk.StringVar(value="Calibration: -")
        ttk.Label(file_frame, textvariable=self.calib_info_var).grid(
            row=2, column=0, columnspan=5, padx=8, pady=(0, 8), sticky="w"
        )

        options_frame = ttk.LabelFrame(self, text="Options")
        options_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=0)
        for i in range(6):
            options_frame.columnconfigure(i, weight=1)

        ttk.Label(options_frame, text="Modele").grid(row=0, column=0, padx=8, pady=8, sticky="w")
        self.model_var = tk.StringVar(value="yolov8n-pose.pt")
        ttk.Combobox(
            options_frame,
            textvariable=self.model_var,
            values=[
                "yolov8n-pose.pt",
                "yolov8s-pose.pt",
                "yolov8m-pose.pt",
                "yolov8l-pose.pt",
                "yolov8x-pose.pt",
            ],
            state="readonly",
            width=20,
        ).grid(row=0, column=1, padx=8, pady=8, sticky="w")

        ttk.Label(options_frame, text="Device").grid(row=0, column=2, padx=8, pady=8, sticky="w")
        device_options = ["auto", "cpu"]
        if _cuda_available():
            device_options.append("cuda:0")
        self.device_var = tk.StringVar(value="auto")
        ttk.Combobox(
            options_frame,
            textvariable=self.device_var,
            values=device_options,
            state="readonly",
            width=12,
        ).grid(row=0, column=3, padx=8, pady=8, sticky="w")

        self.fp16_var = tk.BooleanVar(value=False)
        fp16_cb = ttk.Checkbutton(
            options_frame, text="FP16 (CUDA)", variable=self.fp16_var
        )
        fp16_cb.grid(row=0, column=4, padx=8, pady=8, sticky="w")
        if not _cuda_available():
            fp16_cb.state(["disabled"])

        ttk.Label(options_frame, text="Unites").grid(row=0, column=5, padx=8, pady=8, sticky="w")
        self.units_var = tk.StringVar(value="pixels")
        ttk.Combobox(
            options_frame,
            textvariable=self.units_var,
            values=["pixels", "metres"],
            state="readonly",
            width=10,
        ).grid(row=0, column=6, padx=8, pady=8, sticky="w")

        ttk.Label(options_frame, text="Frames max").grid(row=1, column=0, padx=8, pady=8, sticky="w")
        self.max_frames_var = tk.StringVar(value="300")
        self.max_frames_entry = ttk.Entry(options_frame, textvariable=self.max_frames_var, width=10)
        self.max_frames_entry.grid(
            row=1, column=1, padx=8, pady=8, sticky="w"
        )

        ttk.Label(options_frame, text="Stride").grid(row=1, column=2, padx=8, pady=8, sticky="w")
        self.stride_var = tk.StringVar(value="1")
        ttk.Entry(options_frame, textvariable=self.stride_var, width=10).grid(
            row=1, column=3, padx=8, pady=8, sticky="w"
        )

        self.save_video_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Sauver video annotee", variable=self.save_video_var
        ).grid(row=1, column=4, padx=8, pady=8, sticky="w")

        self.full_video_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Traiter toute la video", variable=self.full_video_var,
            command=self._toggle_full_video
        ).grid(row=1, column=5, padx=8, pady=8, sticky="w")

        self.export_json_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Exporter JSON brut", variable=self.export_json_var
        ).grid(row=2, column=0, padx=8, pady=8, sticky="w")

        self.export_csv_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Exporter CSV brut", variable=self.export_csv_var
        ).grid(row=2, column=1, padx=8, pady=8, sticky="w")

        self.export_analysis_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, text="Exporter analyse (json/csv/html)", variable=self.export_analysis_var
        ).grid(row=2, column=2, padx=8, pady=8, sticky="w")

        run_frame = ttk.Frame(self)
        run_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=10)
        run_frame.columnconfigure(0, weight=1)
        run_frame.rowconfigure(1, weight=1)

        controls = ttk.Frame(run_frame)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(2, weight=1)

        ttk.Button(controls, text="Demarrer", command=self._start).grid(
            row=0, column=0, padx=6, pady=6
        )
        ttk.Button(controls, text="Stop", command=self._stop).grid(
            row=0, column=1, padx=6, pady=6
        )

        self.status_var = tk.StringVar(value="Pret.")
        ttk.Label(controls, textvariable=self.status_var).grid(
            row=0, column=2, padx=6, pady=6, sticky="w"
        )

        outputs = ttk.Frame(controls)
        outputs.grid(row=0, column=3, padx=6, pady=6, sticky="e")
        self.btn_open_folder = ttk.Button(outputs, text="Ouvrir dossier", command=self._open_output_folder)
        self.btn_open_html = ttk.Button(outputs, text="Ouvrir HTML", command=lambda: self._open_output("analysis_html"))
        self.btn_open_json = ttk.Button(outputs, text="Ouvrir JSON", command=lambda: self._open_output("analysis_json"))
        self.btn_open_csv = ttk.Button(outputs, text="Ouvrir CSV", command=lambda: self._open_output("analysis_csv"))

        self.btn_open_folder.grid(row=0, column=0, padx=4)
        self.btn_open_html.grid(row=0, column=1, padx=4)
        self.btn_open_json.grid(row=0, column=2, padx=4)
        self.btn_open_csv.grid(row=0, column=3, padx=4)

        for btn in (self.btn_open_folder, self.btn_open_html, self.btn_open_json, self.btn_open_csv):
            btn.state(["disabled"])

        self.progress = ttk.Progressbar(run_frame, mode="determinate")
        self.progress.grid(row=0, column=0, sticky="ew", padx=6, pady=(36, 6))

        preview_frame = ttk.LabelFrame(run_frame, text="Apercu")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.grid(row=0, column=0, sticky="nsew")

    def _browse_video(self):
        path = filedialog.askopenfilename(
            title="Choisir une video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")]
        )
        if path:
            self.video_path_var.set(path)
            self._preanalyze(show_error=False)

    def _toggle_full_video(self):
        if self.full_video_var.get():
            self.max_frames_entry.state(["disabled"])
            if self._video_info and self._video_info.get("total_frames"):
                self.max_frames_var.set(str(self._video_info["total_frames"]))
            else:
                self.max_frames_var.set("0")
        else:
            self.max_frames_entry.state(["!disabled"])

    def _preanalyze(self, show_error: bool = True) -> bool:
        video_path = self.video_path_var.get().strip()
        if not video_path or not os.path.exists(video_path):
            if show_error:
                messagebox.showerror("Erreur", "Choisissez une video valide.")
            return False

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            if show_error:
                messagebox.showerror("Erreur", "Impossible d'ouvrir la video.")
            return False

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0
        cap.release()

        duration = (total_frames / fps) if fps > 0 else 0.0
        try:
            size_mb = os.path.getsize(video_path) / (1024 * 1024)
        except Exception:
            size_mb = 0.0

        self._video_info = {
            "path": video_path,
            "total_frames": total_frames,
            "fps": fps,
            "width": width,
            "height": height,
            "duration_sec": duration,
            "size_mb": size_mb,
        }

        info_txt = (
            f"Info: frames={total_frames}, fps={fps:.2f}, "
            f"dur={duration:.1f}s, res={width}x{height}, size={size_mb:.1f}MB"
        )
        self.video_info_var.set(info_txt)

        if self.full_video_var.get():
            self.max_frames_var.set(str(total_frames))
            self.max_frames_entry.state(["disabled"])

        self._load_calibration(video_path)
        return True

    def _get_calibration_path(self, video_path: str) -> str:
        base, _ext = os.path.splitext(video_path)
        return f"{base}_calibration.json"

    def _load_calibration(self, video_path: str) -> bool:
        calib_path = self._get_calibration_path(video_path)
        if not os.path.exists(calib_path):
            self._calibration = None
            self.calib_info_var.set("Calibration: -")
            return False
        try:
            with open(calib_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "H" not in data:
                raise ValueError("Calibration invalide (H manquant)")
            self._calibration = data
            err = data.get("control_error_m")
            if err is not None:
                self.calib_info_var.set(f"Calibration: OK (erreur={err:.3f} m)")
            else:
                self.calib_info_var.set("Calibration: OK")
            return True
        except Exception as e:
            self._calibration = None
            self.calib_info_var.set(f"Calibration: erreur ({e})")
            return False

    def _open_calibration(self):
        video_path = self.video_path_var.get().strip()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Erreur", "Choisissez une video valide.")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            messagebox.showerror("Erreur", "Impossible d'ouvrir la video.")
            return

        ret, frame = cap.read()
        cap.release()
        if not ret:
            messagebox.showerror("Erreur", "Impossible de lire une frame.")
            return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        max_w, max_h = 980, 520
        scale = min(max_w / img.width, max_h / img.height, 1.0)
        disp_w = int(img.width * scale)
        disp_h = int(img.height * scale)
        if scale < 1.0:
            img = img.resize((disp_w, disp_h), Image.LANCZOS)

        win = tk.Toplevel(self)
        win.title("Calibration terrain (demi-terrain haut)")
        win.geometry(f"{disp_w + 40}x{disp_h + 170}")
        win.resizable(False, False)

        info_var = tk.StringVar(
            value="Cliquez 4 points: 1) filet gauche, 2) haut gauche, 3) haut droit, 4) filet droit"
        )
        ttk.Label(win, textvariable=info_var, wraplength=disp_w + 10).pack(padx=12, pady=8)

        canvas = tk.Canvas(win, width=disp_w, height=disp_h, highlightthickness=1, highlightbackground="#aaa")
        canvas.pack(padx=12, pady=6)

        photo = ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, image=photo, anchor="nw")
        canvas.image = photo  # keep ref

        control_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            win, text="Ajouter point de controle (service line x ligne centrale)", variable=control_var
        ).pack(padx=12, pady=(4, 6), anchor="w")

        status_var = tk.StringVar(value="Points: 0/4")
        ttk.Label(win, textvariable=status_var).pack(padx=12, pady=(0, 6), anchor="w")

        points = []
        control_point = {"value": None}
        markers = []

        def draw_point(x, y, label):
            r = 5
            markers.append(canvas.create_oval(x - r, y - r, x + r, y + r, fill="#ff3b30", outline=""))
            markers.append(canvas.create_text(x + 8, y - 8, text=label, fill="#ff3b30"))

        def compute_homography():
            if len(points) < 4:
                return None, None
            src = np.array(points[:4], dtype=np.float32)
            dst = np.array([[0, 0], [0, 10], [10, 10], [10, 0]], dtype=np.float32)
            H, _ = cv2.findHomography(src, dst)
            err = None
            if H is not None and control_point["value"] is not None:
                pt = np.array([[control_point["value"]]], dtype=np.float32)
                proj = cv2.perspectiveTransform(pt, H)[0][0]
                dx = float(proj[0] - 5.0)
                dy = float(proj[1] - 3.0)
                err = (dx * dx + dy * dy) ** 0.5
            return H, err

        def update_status():
            status_var.set(f"Points: {min(len(points), 4)}/4")
            if len(points) >= 4:
                H, err = compute_homography()
                if H is None:
                    info_var.set("Homographie invalide. Reessayez.")
                else:
                    if control_point["value"] is not None and err is not None:
                        info_var.set(f"Calibration OK. Erreur controle: {err:.3f} m")
                    else:
                        info_var.set("Calibration OK. (Cliquez point de controle si besoin)")
                save_btn.state(["!disabled"])
            else:
                save_btn.state(["disabled"])

        def on_click(event):
            if len(points) < 4:
                x = int(event.x / scale)
                y = int(event.y / scale)
                points.append([x, y])
                draw_point(event.x, event.y, f"P{len(points)}")
                update_status()
                return
            if control_var.get() and control_point["value"] is None:
                x = int(event.x / scale)
                y = int(event.y / scale)
                control_point["value"] = [x, y]
                draw_point(event.x, event.y, "CTRL")
                update_status()

        canvas.bind("<Button-1>", on_click)

        def on_reset():
            points.clear()
            control_point["value"] = None
            for m in markers:
                canvas.delete(m)
            markers.clear()
            info_var.set(
                "Cliquez 4 points: 1) filet gauche, 2) haut gauche, 3) haut droit, 4) filet droit"
            )
            update_status()

        def on_save():
            H, err = compute_homography()
            if H is None:
                messagebox.showerror("Erreur", "Calibration invalide.")
                return
            data = {
                "video": video_path,
                "points_px": points[:4],
                "points_world_m": [[0, 0], [0, 10], [10, 10], [10, 0]],
                "control_px": control_point["value"],
                "control_world_m": [5, 3],
                "control_error_m": err,
                "H": H.tolist(),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            try:
                calib_path = self._get_calibration_path(video_path)
                with open(calib_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._calibration = data
                if err is not None:
                    self.calib_info_var.set(f"Calibration: OK (erreur={err:.3f} m)")
                else:
                    self.calib_info_var.set("Calibration: OK")
                messagebox.showinfo("Calibration", f"Calibration sauvegardee:\n{calib_path}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de sauver calibration: {e}")

        btns = ttk.Frame(win)
        btns.pack(padx=12, pady=8, fill="x")
        ttk.Button(btns, text="Reset", command=on_reset).pack(side="left")
        save_btn = ttk.Button(btns, text="Sauver", command=on_save)
        save_btn.pack(side="left", padx=6)
        save_btn.state(["disabled"])
        ttk.Button(btns, text="Fermer", command=win.destroy).pack(side="right")

    def _start(self):
        if self._worker and self._worker.is_alive():
            messagebox.showwarning("En cours", "Un traitement est deja en cours.")
            return

        video_path = self.video_path_var.get().strip()
        if not video_path or not os.path.exists(video_path):
            messagebox.showerror("Erreur", "Choisissez une video valide.")
            return

        if not self._video_info or self._video_info.get("path") != video_path:
            self._preanalyze(show_error=False)

        units = self.units_var.get().strip().lower()
        if units == "metres" and not self._calibration:
            messagebox.showwarning(
                "Calibration manquante",
                "Pas de calibration detectee. Les sorties seront en pixels."
            )
            self.units_var.set("pixels")
            units = "pixels"

        try:
            max_frames = int(self.max_frames_var.get().strip())
        except Exception:
            max_frames = 300
            self.max_frames_var.set("300")

        if self.full_video_var.get():
            if self._video_info and self._video_info.get("total_frames"):
                max_frames = int(self._video_info["total_frames"])
                self.max_frames_var.set(str(max_frames))
            else:
                max_frames = 0
                self.max_frames_var.set("0")

        try:
            stride = max(1, int(self.stride_var.get().strip()))
        except Exception:
            stride = 1
            self.stride_var.set("1")

        self._stop_event.clear()
        self.progress["value"] = 0
        self.status_var.set("Demarrage...")
        self._last_outputs = {}
        for btn in (self.btn_open_folder, self.btn_open_html, self.btn_open_json, self.btn_open_csv):
            btn.state(["disabled"])

        args = {
            "video_path": video_path,
            "model_name": self.model_var.get().strip(),
            "device": self.device_var.get().strip(),
            "fp16": bool(self.fp16_var.get()),
            "max_frames": max_frames,
            "stride": stride,
            "save_video": bool(self.save_video_var.get()),
            "export_json": bool(self.export_json_var.get()),
            "export_csv": bool(self.export_csv_var.get()),
            "export_analysis": bool(self.export_analysis_var.get()),
            "units": units,
            "calibration": self._calibration,
        }
        self._worker = threading.Thread(target=self._run_worker, kwargs=args, daemon=True)
        self._worker.start()

    def _stop(self):
        self._stop_event.set()
        self.status_var.set("Arret demande...")

    def _resolve_device(self, device_choice: str) -> str:
        choice = (device_choice or "auto").lower()
        if choice == "cpu":
            return "cpu"
        if choice.startswith("cuda"):
            return choice
        # auto
        return "cuda:0" if _cuda_available() else "cpu"

    def _run_worker(self, video_path: str, model_name: str, device: str, fp16: bool,
                    max_frames: int, stride: int, save_video: bool,
                    export_json: bool, export_csv: bool, export_analysis: bool,
                    units: str, calibration: dict | None):
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as e:
            self._queue.put(("error", f"Ultralytics non disponible: {e}"))
            return

        device = self._resolve_device(device)
        if device.startswith("cpu"):
            fp16 = False

        self._queue.put(("status", f"Chargement modele: {model_name} (device={device})"))
        try:
            model = YOLO(model_name)
        except Exception as e:
            self._queue.put(("error", f"Erreur chargement modele: {e}"))
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            self._queue.put(("error", "Impossible d'ouvrir la video."))
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720

        base, _ext = os.path.splitext(video_path)

        out_path = None
        writer = None
        if save_video:
            out_path = f"{base}_pose.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

        json_path = f"{base}_pose.json" if export_json else None
        csv_path = f"{base}_pose.csv" if export_csv else None

        analysis_json_path = f"{base}_pose_analysis.json" if export_analysis else None
        analysis_csv_path = f"{base}_pose_analysis.csv" if export_analysis else None
        analysis_html_path = f"{base}_pose_analysis.html" if export_analysis else None

        H = None
        if units == "metres" and calibration and calibration.get("H"):
            try:
                H = np.array(calibration["H"], dtype=np.float32)
            except Exception:
                H = None

        csv_file = None
        csv_writer = None
        csv_kpt_count = None
        csv_include_m = H is not None and units == "metres"

        frames_payload = []
        frame_counts = []
        tracker = SimpleTracker(max_age=max(10, stride * 3))
        track_stats = {}
        summary = {
            "processed_frames": 0,
            "frames_with_detections": 0,
            "total_detections": 0,
            "total_keypoints": 0,
            "sum_keypoint_conf": 0.0,
            "min_keypoint_conf": None,
            "max_keypoint_conf": None,
        }

        processed = 0
        t0 = time.time()

        frame_index = 0
        while cap.isOpened():
            if self._stop_event.is_set():
                break
            ret, frame = cap.read()
            if not ret:
                break

            if max_frames > 0 and frame_index >= max_frames:
                break

            if frame_index % stride == 0:
                results = model.predict(
                    frame,
                    device=device,
                    half=fp16,
                    verbose=False
                )
                annotated = results[0].plot()
                processed += 1
                summary["processed_frames"] += 1
                # Extract keypoints data
                frame_ts = frame_index / fps if fps > 0 else 0.0
                dets_payload = []
                det_count = 0
                keypoints = results[0].keypoints
                boxes = results[0].boxes

                if keypoints is not None and getattr(keypoints, "xy", None) is not None:
                    kp_xy = keypoints.xy
                    kp_conf = getattr(keypoints, "conf", None)
                    try:
                        kp_xy = kp_xy.cpu().numpy()
                    except Exception:
                        kp_xy = None
                    if kp_conf is not None:
                        try:
                            kp_conf = kp_conf.cpu().numpy()
                        except Exception:
                            kp_conf = None

                    if kp_xy is not None:
                        kpt_count = kp_xy.shape[1]
                        kp_xy_m = None
                        if H is not None and units == "metres":
                            try:
                                pts = kp_xy.reshape(-1, 1, 2).astype(np.float32)
                                pts_m = cv2.perspectiveTransform(pts, H)
                                kp_xy_m = pts_m.reshape(kp_xy.shape)
                            except Exception:
                                kp_xy_m = None
                        # Prepare CSV writer once we know keypoint count
                        if export_csv and csv_writer is None:
                            csv_kpt_count = kpt_count
                            csv_file = open(csv_path, "w", newline="", encoding="utf-8")
                            header = [
                                "frame_index", "timestamp_sec", "person_index", "track_id",
                                "bbox_x1", "bbox_y1", "bbox_x2", "bbox_y2", "bbox_conf",
                                "pos_x", "pos_y",
                            ]
                            for i in range(csv_kpt_count):
                                header.extend([f"kp{i}_x", f"kp{i}_y", f"kp{i}_conf"])
                            if csv_include_m:
                                header.extend(["pos_x_m", "pos_y_m"])
                                for i in range(csv_kpt_count):
                                    header.extend([f"kp{i}_x_m", f"kp{i}_y_m"])
                            csv_writer = csv.writer(csv_file)
                            csv_writer.writerow(header)

                        # Boxes
                        box_xyxy = None
                        box_conf = None
                        if boxes is not None and getattr(boxes, "xyxy", None) is not None:
                            try:
                                box_xyxy = boxes.xyxy.cpu().numpy()
                            except Exception:
                                box_xyxy = None
                            try:
                                box_conf = boxes.conf.cpu().numpy()
                            except Exception:
                                box_conf = None

                        for i in range(kp_xy.shape[0]):
                            pos_px = None
                            det = {
                                "person_index": i,
                                "keypoints_xy": kp_xy[i].tolist(),
                                "keypoints_conf": kp_conf[i].tolist() if kp_conf is not None else None,
                            }
                            if box_xyxy is not None and i < box_xyxy.shape[0]:
                                det["bbox_xyxy"] = box_xyxy[i].tolist()
                                det["bbox_conf"] = float(box_conf[i]) if box_conf is not None else None
                                x1, y1, x2, y2 = box_xyxy[i].tolist()
                                pos_px = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
                                det["position_px"] = pos_px
                            if kp_xy_m is not None:
                                det["keypoints_xy_m"] = kp_xy_m[i].tolist()
                                if pos_px is not None and H is not None:
                                    pt = np.array([[pos_px]], dtype=np.float32)
                                    pos_m = cv2.perspectiveTransform(pt, H)[0][0].tolist()
                                    det["position_m"] = pos_m
                            dets_payload.append(det)

                        # Summary stats
                        det_count = int(kp_xy.shape[0])

                        if kp_conf is not None:
                            try:
                                conf_sum = float(kp_conf.sum())
                                conf_count = int(kp_conf.size)
                                conf_min = float(kp_conf.min())
                                conf_max = float(kp_conf.max())
                            except Exception:
                                conf_sum = 0.0
                                conf_count = 0
                                conf_min = None
                                conf_max = None

                            summary["sum_keypoint_conf"] += conf_sum
                            summary["total_keypoints"] += conf_count
                            if conf_min is not None:
                                if summary["min_keypoint_conf"] is None:
                                    summary["min_keypoint_conf"] = conf_min
                                else:
                                    summary["min_keypoint_conf"] = min(
                                        summary["min_keypoint_conf"], conf_min
                                    )
                            if conf_max is not None:
                                if summary["max_keypoint_conf"] is None:
                                    summary["max_keypoint_conf"] = conf_max
                                else:
                                    summary["max_keypoint_conf"] = max(
                                        summary["max_keypoint_conf"], conf_max
                                    )

                summary["total_detections"] += det_count
                if det_count > 0:
                    summary["frames_with_detections"] += 1
                frame_counts.append({
                    "frame_index": frame_index,
                    "timestamp_sec": round(frame_ts, 6),
                    "detections": det_count,
                })

                # Tracking and per-player stats (requires bbox)
                if dets_payload:
                    det_to_track = tracker.update(dets_payload, frame_index)
                    dt = (stride / fps) if fps > 0 else 0.0
                    for di, det in enumerate(dets_payload):
                        track_id = det_to_track[di]
                        det["track_id"] = track_id
                        if track_id is None:
                            continue
                        if track_id not in track_stats:
                            track_stats[track_id] = {
                                "distance": 0.0,
                                "last_pos": None,
                                "frames": 0,
                                "forehand": 0,
                                "backhand": 0,
                                "swing_active": False,
                                "swing_peak_speed": 0.0,
                                "swing_peak_side": None,
                                "last_wr_pos": None,
                            }
                        stats = track_stats[track_id]

                        # Position for distance
                        if units == "metres" and det.get("position_m") is not None:
                            pos = det.get("position_m")
                        else:
                            pos = det.get("position_px")
                        if pos is not None:
                            stats["frames"] += 1
                            if stats["last_pos"] is not None:
                                dx = pos[0] - stats["last_pos"][0]
                                dy = pos[1] - stats["last_pos"][1]
                                stats["distance"] += (dx * dx + dy * dy) ** 0.5
                            stats["last_pos"] = pos

                        # Forehand/Backhand heuristic (right-handed)
                        kp = det.get("keypoints_xy_m") if (units == "metres" and det.get("keypoints_xy_m") is not None) else det.get("keypoints_xy")
                        kp_conf = det.get("keypoints_conf")
                        if kp is not None and isinstance(kp, list) and len(kp) >= 11:
                            # COCO indexes
                            idx_ls, idx_rs = 5, 6
                            idx_lh, idx_rh = 11, 12
                            idx_rw = 10

                            def _kp_ok(idx):
                                if kp_conf is None:
                                    return True
                                try:
                                    return float(kp_conf[idx]) >= 0.2
                                except Exception:
                                    return False

                            mid_x = None
                            if _kp_ok(idx_ls) and _kp_ok(idx_rs):
                                mid_x = (kp[idx_ls][0] + kp[idx_rs][0]) / 2.0
                            elif _kp_ok(idx_lh) and _kp_ok(idx_rh):
                                mid_x = (kp[idx_lh][0] + kp[idx_rh][0]) / 2.0
                            elif pos is not None:
                                mid_x = pos[0]

                            if _kp_ok(idx_rw) and mid_x is not None:
                                rw = kp[idx_rw]
                                wr_pos = [rw[0], rw[1]]
                                if stats["last_wr_pos"] is not None and dt > 0:
                                    dx = wr_pos[0] - stats["last_wr_pos"][0]
                                    dy = wr_pos[1] - stats["last_wr_pos"][1]
                                    speed = ((dx * dx + dy * dy) ** 0.5) / dt
                                else:
                                    speed = 0.0

                                if units == "metres":
                                    speed_thr = 4.0
                                else:
                                    speed_thr = 300.0

                                side = "forehand" if wr_pos[0] >= mid_x else "backhand"

                                if (not stats["swing_active"]) and speed > speed_thr:
                                    stats["swing_active"] = True
                                    stats["swing_peak_speed"] = speed
                                    stats["swing_peak_side"] = side
                                elif stats["swing_active"]:
                                    if speed > stats["swing_peak_speed"]:
                                        stats["swing_peak_speed"] = speed
                                        stats["swing_peak_side"] = side
                                    if speed < speed_thr * 0.6:
                                        if stats["swing_peak_side"] == "forehand":
                                            stats["forehand"] += 1
                                        elif stats["swing_peak_side"] == "backhand":
                                            stats["backhand"] += 1
                                        stats["swing_active"] = False
                                        stats["swing_peak_speed"] = 0.0
                                        stats["swing_peak_side"] = None

                                stats["last_wr_pos"] = wr_pos

                    # CSV export after tracking (to include track_id)
                    if export_csv and csv_writer is not None:
                        for det in dets_payload:
                            row = [
                                frame_index,
                                round(frame_ts, 6),
                                det.get("person_index"),
                                det.get("track_id"),
                            ]
                            bbox = det.get("bbox_xyxy")
                            if bbox:
                                row.extend([float(x) for x in bbox])
                                row.append(det.get("bbox_conf", ""))
                            else:
                                row.extend(["", "", "", "", ""])

                            pos_px = det.get("position_px")
                            if pos_px is not None:
                                row.extend([float(pos_px[0]), float(pos_px[1])])
                            else:
                                row.extend(["", ""])

                            kp_xy = det.get("keypoints_xy") or []
                            kp_conf = det.get("keypoints_conf") or []
                            kpt_count = csv_kpt_count or len(kp_xy)
                            for j in range(kpt_count):
                                if j < len(kp_xy):
                                    row.extend([
                                        float(kp_xy[j][0]),
                                        float(kp_xy[j][1]),
                                        float(kp_conf[j]) if j < len(kp_conf) else ""
                                    ])
                                else:
                                    row.extend(["", "", ""])

                            if csv_include_m:
                                pos_m = det.get("position_m")
                                if pos_m is not None:
                                    row.extend([float(pos_m[0]), float(pos_m[1])])
                                else:
                                    row.extend(["", ""])
                                kp_xy_m = det.get("keypoints_xy_m") or []
                                for j in range(kpt_count):
                                    if j < len(kp_xy_m):
                                        row.extend([float(kp_xy_m[j][0]), float(kp_xy_m[j][1])])
                                    else:
                                        row.extend(["", ""])
                            csv_writer.writerow(row)

                if export_json:
                    frames_payload.append({
                        "frame_index": frame_index,
                        "timestamp_sec": round(frame_ts, 6),
                        "detections": dets_payload,
                    })
            else:
                annotated = frame

            if writer is not None:
                writer.write(annotated)

            if frame_index % stride == 0:
                # Send preview for processed frames
                self._queue.put(("frame", annotated))

            # Progress
            if total_frames > 0:
                self._queue.put(("progress", frame_index + 1, total_frames))

            frame_index += 1

        cap.release()
        if writer is not None:
            writer.release()
        if csv_file is not None:
            csv_file.close()

        if export_json and json_path is not None:
            meta = {
                "video_path": video_path,
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "model": model_name,
                "device": device,
                "fp16": fp16,
                "max_frames": max_frames,
                "stride": stride,
                "units": units,
                "calibration": calibration if (units == "metres" and calibration) else None,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            payload = {"meta": meta, "frames": frames_payload}
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

        if export_analysis:
            avg_conf = (
                summary["sum_keypoint_conf"] / summary["total_keypoints"]
                if summary["total_keypoints"] > 0 else 0.0
            )
            avg_persons = (
                summary["total_detections"] / summary["processed_frames"]
                if summary["processed_frames"] > 0 else 0.0
            )
            det_rate = (
                summary["frames_with_detections"] / summary["processed_frames"]
                if summary["processed_frames"] > 0 else 0.0
            )

            analysis_meta = {
                "video_path": video_path,
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height,
                "model": model_name,
                "device": device,
                "fp16": fp16,
                "max_frames": max_frames,
                "stride": stride,
                "units": units,
                "calibration": calibration if (units == "metres" and calibration) else None,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            analysis_summary = {
                "processed_frames": summary["processed_frames"],
                "frames_with_detections": summary["frames_with_detections"],
                "total_detections": summary["total_detections"],
                "avg_persons_per_frame": round(avg_persons, 4),
                "detection_rate": round(det_rate, 4),
                "total_keypoints": summary["total_keypoints"],
                "avg_keypoint_conf": round(avg_conf, 6),
                "min_keypoint_conf": summary["min_keypoint_conf"],
                "max_keypoint_conf": summary["max_keypoint_conf"],
                "processing_fps": round(processed / max(time.time() - t0, 1e-6), 2),
            }
            players_summary = []
            for pid in sorted(track_stats.keys()):
                st = track_stats[pid]
                duration_sec = st["frames"] * ((stride / fps) if fps > 0 else 0.0)
                avg_speed = (st["distance"] / duration_sec) if duration_sec > 0 else 0.0
                players_summary.append({
                    "id": pid,
                    "distance": round(st["distance"], 3),
                    "distance_unit": "m" if units == "metres" else "px",
                    "frames_seen": st["frames"],
                    "avg_speed": round(avg_speed, 3),
                    "avg_speed_unit": "m/s" if units == "metres" else "px/s",
                    "forehand_count": st["forehand"],
                    "backhand_count": st["backhand"],
                })

            if analysis_json_path:
                payload = {
                    "meta": analysis_meta,
                    "summary": analysis_summary,
                    "players": players_summary,
                    "per_frame": frame_counts,
                }
                with open(analysis_json_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

            if analysis_csv_path:
                with open(analysis_csv_path, "w", newline="", encoding="utf-8") as f:
                    writer_csv = csv.writer(f)
                    writer_csv.writerow(["metric", "value"])
                    for key, value in analysis_summary.items():
                        writer_csv.writerow([key, value])
                    if players_summary:
                        writer_csv.writerow([])
                        writer_csv.writerow(["player_id", "distance", "distance_unit", "frames_seen",
                                            "avg_speed", "avg_speed_unit", "forehand", "backhand"])
                        for p in players_summary:
                            writer_csv.writerow([
                                p["id"], p["distance"], p["distance_unit"], p["frames_seen"],
                                p["avg_speed"], p["avg_speed_unit"], p["forehand_count"], p["backhand_count"]
                            ])

            if analysis_html_path:
                html = [
                    "<html><head><meta charset='utf-8'>",
                    "<title>Pose Analysis</title>",
                    "<style>",
                    "body{font-family:Arial, sans-serif; margin:24px;}",
                    "table{border-collapse:collapse; width:100%; max-width:900px;}",
                    "th,td{border:1px solid #ddd; padding:8px; text-align:left;}",
                    "th{background:#f3f3f3;}",
                    "</style></head><body>",
                    "<h1>Pose Analysis Summary</h1>",
                    "<h2>Meta</h2>",
                    "<table><tbody>",
                ]
                for key, value in analysis_meta.items():
                    html.append(f"<tr><th>{key}</th><td>{value}</td></tr>")
                html.extend(["</tbody></table>", "<h2>Summary</h2>", "<table><tbody>"])
                for key, value in analysis_summary.items():
                    html.append(f"<tr><th>{key}</th><td>{value}</td></tr>")
                html.append("</tbody></table>")
                if players_summary:
                    html.append("<h2>Players</h2>")
                    html.append("<table><thead><tr>")
                    html.append("<th>ID</th><th>Distance</th><th>Unit</th><th>Frames</th>"
                                "<th>Avg Speed</th><th>Speed Unit</th><th>Forehand</th><th>Backhand</th>")
                    html.append("</tr></thead><tbody>")
                    for p in players_summary:
                        html.append(
                            f"<tr><td>{p['id']}</td><td>{p['distance']}</td>"
                            f"<td>{p['distance_unit']}</td><td>{p['frames_seen']}</td>"
                            f"<td>{p['avg_speed']}</td><td>{p['avg_speed_unit']}</td>"
                            f"<td>{p['forehand_count']}</td><td>{p['backhand_count']}</td></tr>"
                        )
                    html.append("</tbody></table>")
                html.append("</body></html>")
                with open(analysis_html_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(html))

        outputs = {
            "output_dir": os.path.dirname(video_path),
            "analysis_json": analysis_json_path if (export_analysis and analysis_json_path) else None,
            "analysis_csv": analysis_csv_path if (export_analysis and analysis_csv_path) else None,
            "analysis_html": analysis_html_path if (export_analysis and analysis_html_path) else None,
        }
        self._queue.put(("outputs", outputs))

        dt = max(time.time() - t0, 1e-6)
        fps_proc = processed / dt
        if self._stop_event.is_set():
            self._queue.put(("status", "Arrete."))
        else:
            msg = f"Termine. Frames traitees: {processed}, FPS: {fps_proc:.2f}"
            if out_path:
                msg += f" | Video: {out_path}"
            if json_path:
                msg += f" | JSON: {json_path}"
            if csv_path:
                msg += f" | CSV: {csv_path}"
            if analysis_json_path:
                msg += f" | Analysis JSON: {analysis_json_path}"
            if analysis_csv_path:
                msg += f" | Analysis CSV: {analysis_csv_path}"
            if analysis_html_path:
                msg += f" | Analysis HTML: {analysis_html_path}"
            self._queue.put(("status", msg))

    def _poll_queue(self):
        try:
            while True:
                msg = self._queue.get_nowait()
                kind = msg[0]
                if kind == "status":
                    self.status_var.set(msg[1])
                elif kind == "error":
                    self.status_var.set("Erreur.")
                    messagebox.showerror("Erreur", msg[1])
                elif kind == "progress":
                    current, total = msg[1], msg[2]
                    if total > 0:
                        self.progress["value"] = (current / total) * 100
                elif kind == "frame":
                    self._update_preview(msg[1])
                elif kind == "outputs":
                    self._last_outputs = msg[1] or {}
                    out_dir = self._last_outputs.get("output_dir")
                    if out_dir and os.path.isdir(out_dir):
                        self.btn_open_folder.state(["!disabled"])
                    if self._last_outputs.get("analysis_html"):
                        self.btn_open_html.state(["!disabled"])
                    if self._last_outputs.get("analysis_json"):
                        self.btn_open_json.state(["!disabled"])
                    if self._last_outputs.get("analysis_csv"):
                        self.btn_open_csv.state(["!disabled"])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _open_output_folder(self):
        out_dir = self._last_outputs.get("output_dir")
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showinfo("Info", "Aucun dossier de sortie.")
            return
        try:
            os.startfile(out_dir)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dossier: {e}")

    def _open_output(self, key: str):
        path = self._last_outputs.get(key)
        if not path or not os.path.exists(path):
            messagebox.showinfo("Info", "Fichier non disponible.")
            return
        try:
            os.startfile(path)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le fichier: {e}")

    def _update_preview(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        # Resize to fit preview area
        max_w = 900
        max_h = 420
        img.thumbnail((max_w, max_h))
        self._preview_image = ImageTk.PhotoImage(img)
        self.preview_label.configure(image=self._preview_image)


if __name__ == "__main__":
    app = BiomechApp()
    app.mainloop()
